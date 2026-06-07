# Hotel Reviews MongoDB Project

Projekat iz predmeta Sistemi baza podataka.

Tema projekta je analiza skupa podataka o recenzijama hotela u Evropi. Podaci se modeluju i importuju u MongoDB bazu podataka, nakon čega se realizuju agregacioni upiti, analiza performansi, optimizacija šeme i indeksa, kao i vizualizacija rezultata.

## Dataset

Korišćen je skup podataka `515K Hotel Reviews Data in Europe`.

Svaki zapis predstavlja jednu recenziju gosta za određeni hotel.

## Uloge

- Menadžer hotela (Jovana)
- Gost hotela (Tijana)

## Struktura modela - Menadžer hotela

### Verzija v1

Početna verzija modela koristi dve osnovne kolekcije:

- `v1_hotels` - podaci o hotelima
- `v1_reviews` - pojedinačne recenzije gostiju

U ovoj verziji su upiti često morali da rade:

- spajanje kolekcija preko `hotel_id`
- računanje godine i meseca iz `review_date` tokom izvršavanja upita
- tekstualnu obradu negativnih komentara unutar agregacionog pipeline-a
- grupisanje velikog broja sirovih dokumenata pri svakom pokretanju analize

### Verzija v2

Optimizovana verzija uvodi denormalizovana i unapred izračunata polja:

- `v2_hotels` - osnovni podaci o hotelima, uključujući geoprostornu lokaciju
- `v2_reviews` - recenzije sa dodatim poljima `hotel_name`, `review_year`, `review_month`, `negative_keywords` i `tags`
- `v2_hotel_time_stats` - unapred izračunata mesečna i godišnja statistika po hotelu
  
Optimizovana verzija takodje uvodi i dodatne izvedene kolekcije, radi čuvanja dobijenih rezultata:
- `v2_top_tags_by_year` - top tagovi po godini za dobro ocenjene recenzije
- `v2_nationality_year_stats` - agregirana statistika po nacionalnosti i godini
- `v2_nearby_hotel_trends` - unapred pripremljeni trendovi za obližnje hotele

### Struktura šema u verziji v2

U verziji `v2` svaka kolekcija ima jasno definisanu ulogu i skup polja:

#### Kolekcija `v2_hotels`

Sadrži osnovne podatke o hotelu:

- `name` - naziv hotela
- `address` - puna adresa hotela
- `city` - grad izdvojen iz adrese
- `country` - država izdvojena iz adrese
- `average_score` - ukupna prosečna ocena hotela iz dataset-a
- `total_number_of_reviews` - ukupan broj recenzija
- `additional_number_of_scoring` - broj dodatnih ocenjivanja
- `location` - GeoJSON objekat sa koordinatama u formatu `Point`

#### Kolekcija `v2_reviews`

Sadrži pojedinačne recenzije, zajedno sa poljima dodatim radi optimizacije:

- `hotel_id` - referenca na hotel
- `hotel_name` - naziv hotela dodat direktno u dokument
- `review_date` - originalni datum recenzije
- `review_year` - unapred izdvojena godina iz `review_date`
- `review_month` - unapred izdvojen mesec iz `review_date`
- `reviewer_score` - ocena koju je gost dao
- `reviewer_nationality` - nacionalnost gosta
- `negative_review` - originalni negativni komentar
- `negative_keywords` - lista ključnih reči izdvojenih iz negativnog komentara
- `tags` - lista tagova iz dataset-a

#### Kolekcija `v2_hotel_time_stats`

Sadrži unapred izračunate vremenske agregate za hotel:

- `hotel_id` - referenca na hotel
- `hotel_name` - naziv hotela
- `period_type` - tip perioda, `month` ili `year`
- `year` - godina perioda
- `month` - mesec perioda, ili `null` kada je period godišnji
- `avg_score` - prosečna ocena za dati period
- `review_count` - broj recenzija u datom periodu

#### Kolekcija `v2_top_tags_by_year`

Sadrži unapred izračunate najčešće tagove po godini:

- `hotel_id` - referenca na hotel
- `hotel_name` - naziv hotela
- `year` - godina
- `top_tags` - lista objekata oblika `{ tag, count }`

#### Kolekcija `v2_nationality_year_stats`

Sadrži agregate po nacionalnosti i godini:

- `hotel_id` - referenca na hotel
- `hotel_name` - naziv hotela
- `year` - godina
- `nationality` - nacionalnost gosta
- `avg_score` - prosečna ocena
- `review_count` - broj recenzija
- `high_score_count` - broj ocena većih od `8.5`
- `low_score_count` - broj ocena manjih od `5`

#### Kolekcija `v2_nearby_hotel_trends`

Sadrži unapred pripremljene trendove za obližnje hotele:

- `anchor_hotel_id` - referentni hotel
- `anchor_hotel_name` - naziv referentnog hotela
- `nearby_hotel_id` - obližnji hotel
- `nearby_hotel_name` - naziv obližnjeg hotela
- `distance_meters` - udaljenost između hotela u metrima
- `hotel_average_score` - prosečna ukupna ocena obližnjeg hotela
- `year` - godina
- `month` - mesec
- `avg_score` - prosečna ocena obližnjeg hotela u tom periodu
- `review_count` - broj recenzija u tom periodu

## Izazovi i način rešavanja

Tokom rada na menadžerskim upitima pojavilo se nekoliko tipičnih problema:

- Veliki broj `lookup` i `unwind` operacija usporavao je izvršavanje upita.
- Često računanje izvedenih vrednosti, kao što su godina i mesec iz datuma, povećavalo je broj operacija u pipeline-u.
- Analiza slobodnog teksta nad poljem `negative_review` bila je skupa jer su tokenizacija, filtriranje stop reči i uklanjanje duplikata rađeni prilikom svakog pokretanja upita.
- Upiti koji se često ponavljaju nad istim dimenzijama, kao što su hotel, godina i mesec ponovo su obrađivali velike količine sirovih podataka.
- Analiza udaljenosti između hotela u v1 verziji nije koristila geoprostorne mogućnosti baze, već ručno računanje distance.

Optimizacija je rešena kombinacijom sledećih pristupa:

- Denormalizacija često korišćenih atributa u kolekciji `v2_reviews`
- Uvođenje izvedenih kolekcija za često tražene agregate
- Prebacivanje dela obrade iz vremena izvršavanja upita u fazu importa podataka
- Kreiranje složenih indeksa nad poljima koja se koriste u filtriranju, sortiranju i spajanju
- Uvođenje geoprostornog indeksa i operatora `$geoNear`

## Šabloni modelovanja

U optimizovanom modelu korišćeni su sledeći šabloni:

### Šablon proširene refernce:

Naziv hotela je dodat direktno u `v2_reviews`. Na taj način je uklonjena potreba da se za veliki broj upita radi dodatno spajanje sa kolekcijom hotela.

### Šablon proračunavanja

Za često ponavljane analize unapred je kreirana izvedena kolekcija:

- `v2_hotel_time_stats`

Šablon proračunavanja je primenjen i nad samim dokumentima recenzija, tako što se iz originalnog polja `review_date` unapred izdvajaju i čuvaju:

- `review_year`
- `review_month`

Ova polja se ne računaju više tokom svakog pokretanja upita, već se izračunavaju jednom prilikom importa podataka i zatim direktno koriste za:

- filtriranje po godini i mesecu
- grupisanje po vremenskim periodima
- kreiranje efikasnijih složenih indeksa
- pojednostavljenje agregacionih pipeline-ova

Ovim pristupom je deo računski zahtevnog posla premešten u proces importa, pa su analitički upiti postali kraći i znatno brži.

### Pretprocesiranje tekstualnih podataka - Šablon proračunavanja

Polje `negative_keywords` nastaje tokom importa iz `negative_review` tako što se:

- tekst normalizuje
- izdvajaju tokeni
- uklanjaju stop reči
- uklanjaju duplikati unutar jedne recenzije

Na taj način upit više ne mora da radi tekstualnu obradu svaki put kada se izvrši analiza negativnih komentara.

### Geospatial Pattern

Kolekcija `v2_hotels` koristi GeoJSON format za lokaciju i `2dsphere` indeks, čime je omogućena efikasna analiza najbližih hotela pomoću MongoDB geoprostornih operatora.

## Indeksi

Tokom importa optimizovane verzije kreirani su sledeći indeksi:

```js
db.v2_reviews.createIndex({ hotel_name: 1, review_year: 1, review_month: 1 });
db.v2_reviews.createIndex({ hotel_name: 1, reviewer_nationality: 1, review_year: 1 });
db.v2_reviews.createIndex({ hotel_name: 1, reviewer_score: 1, review_year: 1 });

db.v2_hotels.createIndex({ location: "2dsphere" });

db.v2_hotel_time_stats.createIndex({ hotel_name: 1, period_type: 1, year: 1, month: 1 });
```

## Menadžerski upiti

U nastavku je pregled svih upita namenjenih menadžeru hotela, zajedno sa opisom analize i optimizacije.

### Zadatak 1: Mesečni trend prosečne ocene za hotel

[Upit pre optimizacije](v1/queries/manager/Query1/Query1-NotOptimized.js) | [Upit nakon optimizacije](v2/queries/manager/Query1/Query1-Optimized.js)

**Cilj analize:** Praćenje prosečne ocene i broja recenzija po mesecima za hotel `Hotel Arena`, kako bi menadžer mogao da vidi kako se zadovoljstvo gostiju menja kroz vreme.

**Detalji analize:**

Analiza obuhvata sledeće korake:

1. Spajanje recenzija sa hotelima: Recenzije iz kolekcije `v1_reviews` spajaju se sa kolekcijom `v1_hotels` preko polja `hotel_id`, kako bi svaka recenzija bila povezana sa odgovarajućim hotelom.
2. Filtriranje hotela i validnih datuma: Zadržavaju se samo recenzije za `Hotel Arena` i samo zapisi koji imaju validan datum recenzije.
3. Izdvajanje godine i meseca: Iz polja `review_date` izračunavaju se godina i mesec unutar samog upita.
4. Grupisanje po vremenskom periodu: Recenzije se grupišu po godini i mesecu radi računanja prosečne ocene i broja recenzija.
5. Sortiranje i prikaz rezultata: Rezultati se sortiraju hronološki i prikazuju u obliku pogodnom za analizu trenda.

**Objašnjenje pipeline-a pre optimizacije, korak po korak:**

- `$lookup`: Spaja svaki dokument iz `v1_reviews` sa odgovarajućim hotelom iz `v1_hotels` preko `hotel_id`.
- `$unwind`: Pošto je rezultat `lookup` niz, ovaj korak ga pretvara u jedan konkretan objekat `hotel`.
- `$match`: Filtrira samo recenzije koje pripadaju hotelu `Hotel Arena` i imaju popunjen datum recenzije.
- `$project`: Izvlači godinu i mesec iz `review_date` i zadržava `reviewer_score`, jer su to jedina polja potrebna za dalju obradu.
- `$group`: Grupiše sve recenzije po kombinaciji godina-mesec i za svaku grupu računa prosečnu ocenu i broj recenzija.
- `$sort`: Sortira rezultate hronološki po godini i mesecu.
- Završni `$project`: Uklanja interno `_id` polje i oblikuje rezultat da bude čitljiviji za prikaz.

 <img width="1366" height="243" alt="Screenshot 2026-06-07 at 19 57 13" src="https://github.com/user-attachments/assets/74365f49-84f2-49fd-8bcf-9d99ce9c3f47" />

<img width="1211" height="237" alt="Screenshot 2026-06-07 at 19 57 17" src="https://github.com/user-attachments/assets/91a47bc1-65ce-422f-9dc8-50c2f224cd40" />

**Optimizacija:**

Optimizacija je postignuta uz pomoć narednih koraka:

1. Denormalizacija naziva hotela: U kolekciji `v2_reviews` polje `hotel_name` je već upisano u svaki dokument, pa više nije potreban `lookup` sa kolekcijom hotela.
2. Prethodno izračunata vremenska polja: Polja `review_year` i `review_month` kreiraju se prilikom importa, čime je uklonjeno računanje godine i meseca u svakom izvršavanju upita.
3. Rano filtriranje: Upit odmah filtrira dokumente po `hotel_name`, `review_year` i `review_month`, pa se u dalju obradu šalje manji skup podataka.
4. Podrška indeksa: Indeks `db.v2_reviews.createIndex({ hotel_name: 1, review_year: 1, review_month: 1 })` ubrzava filtriranje i kasnije sortiranje po vremenskoj dimenziji.
5. Dodatna optimizacija preko izvedene kolekcije: U projektu postoji i kolekcija `v2_hotel_time_stats`, koja ovaj tip vremenske analize dodatno pojednostavljuje jer već čuva mesečne agregate po hotelu.


**Objašnjenje pipeline-a nakon optimizacije, korak po korak:**

- `$match`: Odmah bira samo recenzije za `Hotel Arena` koje već imaju izdvojene vrednosti `review_year` i `review_month`.
- `$group`: Grupiše dokumente direktno po unapred sačuvanoj godini i mesecu i računa prosečnu ocenu i broj recenzija.
- `$sort`: Sortira rezultat po vremenskom redosledu.
- `$project`: Formatira izlaz tako da se jasno vide godina, mesec, prosečna ocena i broj recenzija.

<img width="1368" height="290" alt="Screenshot 2026-06-07 at 19 58 13" src="https://github.com/user-attachments/assets/b8f6e938-899b-4421-9d33-f23af4bddc7e" />

**Grafički prikaz rezultata:**
<img width="519" height="404" alt="Screenshot 2026-06-07 at 19 04 59" src="https://github.com/user-attachments/assets/d193d818-ae98-4bd1-bdef-ee539c5a8c2b" />

### Zadatak 2: Analiza ocena po nacionalnosti i godini

[Upit pre optimizacije](v1/queries/manager/Query2/Query2-Unoptimized.js) | [Upit nakon optimizacije](v2/queries/manager/Query2/Query2-Optimized.js)

**Cilj analize:** Analiza prosečnih ocena, broja recenzija, broja veoma visokih ocena i broja niskih ocena po nacionalnosti gostiju i po godini za hotel `Hotel Arena`.

**Detalji analize:**

Analiza obuhvata sledeće korake:

1. Spajanje recenzija sa hotelima: Recenzije iz `v1_reviews` se povezuju sa hotelima iz `v1_hotels` preko `hotel_id`.
2. Filtriranje ciljnog hotela: Zadržavaju se samo recenzije koje pripadaju hotelu `Hotel Arena`.
3. Filtriranje validnih podataka: U obradu ulaze samo dokumenti koji imaju validan datum i popunjenu nacionalnost recenzenta.
4. Izračunavanje godine recenzije: Godina se dobija iz polja `review_date` unutar agregacionog pipeline-a.
5. Grupisanje po godini i nacionalnosti: Za svaku kombinaciju godine i nacionalnosti računa se prosečna ocena, ukupan broj recenzija, broj visokih ocena i broj niskih ocena.
6. Sortiranje i projekcija: Rezultati se sortiraju i oblikuju za preglednu menadžersku analizu.

**Objašnjenje pipeline-a pre optimizacije, korak po korak:**

- `$lookup`: Spaja recenzije sa podacima o hotelu.
- `$unwind`: Pretvara niz `hotel` u pojedinačni objekat.
- `$match`: Zadržava samo recenzije za `Hotel Arena`, sa validnim datumom i popunjenom nacionalnošću gosta.
- `$project`: Iz datuma izdvaja godinu i prosleđuje dalje nacionalnost i ocenu.
- `$group`: Za svaku kombinaciju godine i nacionalnosti računa prosečnu ocenu, ukupan broj recenzija, broj visokih i broj niskih ocena.
- `$sort`: Sortira rezultat po godini, a zatim po prosečnoj oceni.
- Završni `$project`: Prikazuje samo ona polja koja su relevantna za menadžerski izveštaj.
  
<img width="1365" height="243" alt="Screenshot 2026-06-07 at 20 00 05" src="https://github.com/user-attachments/assets/da212419-264d-4685-b75c-6f79482ebc4a" />

<img width="1212" height="247" alt="Screenshot 2026-06-07 at 20 00 07" src="https://github.com/user-attachments/assets/915cfea7-a748-4b52-b58b-f2923be9340c" />

**Optimizacija:**

Optimizacija je postignuta uz pomoć narednih koraka:

1. Denormalizacija ključnih atributa: U `v2_reviews` su dostupni `hotel_name` i `review_year`, pa se iz pipeline-a uklanjaju i `lookup` i računanje godine.
2. Rano sužavanje skupa dokumenata: Filtriranje po hotelu, godini i nacionalnosti radi se na samom početku upita.
3. Smanjenje broja operacija u agregaciji: Pošto nema spajanja i dodatne projekcije za datum, pipeline je kraći i lakši za izvršavanje.
4. Podrška indeksa: Indeks `db.v2_reviews.createIndex({ hotel_name: 1, reviewer_nationality: 1, review_year: 1 })` ubrzava filtriranje nad dimenzijama koje se direktno koriste u analizi.
5. Dodatni nivo optimizacije kroz izvedenu kolekciju: Kolekcija `v2_nationality_year_stats` već čuva izračunate agregate po hotelu, godini i nacionalnosti, pa se ova analiza može izvršiti i bez skeniranja svih pojedinačnih recenzija prilikom prikaza rezultata u Metabase-u.

**Objašnjenje pipeline-a nakon optimizacije, korak po korak:**

- `$match`: Na početku bira samo recenzije za konkretan hotel i samo one koje imaju unapred dostupnu godinu i nacionalnost.
- `$group`: Neposredno grupiše po `review_year` i `reviewer_nationality`, bez dodatnog spajanja sa hotelima i bez računanja godine.
- `$sort`: Sortira rezultate po godini i prosečnoj oceni.
- `$project`: Formatira rezultat za pregled nacionalnosti, ocena i broja recenzija.
  
<img width="1369" height="250" alt="Screenshot 2026-06-07 at 20 02 55" src="https://github.com/user-attachments/assets/f8621e73-c2b7-4106-a796-1dedb96c128f" />

**Grafički prikaz rezultata:**

<img width="1048" height="685" alt="Screenshot 2026-06-07 at 19 05 12" src="https://github.com/user-attachments/assets/f2494046-be5e-4909-9ca6-e75d2893721f" />

<img width="523" height="407" alt="Screenshot 2026-06-07 at 19 04 42" src="https://github.com/user-attachments/assets/a35d08d8-1c6d-499a-80b7-dc4c7fb6ddf5" />



### Zadatak 3: Najčešće teme negativnih komentara u poslednjoj godini

[Upit pre optimizacije](v1/queries/manager/Query3/Query3-NotOptimized.js) | [Upit nakon optimizacije](v2/queries/manager/Query3/Query3Optimized.js)

**Cilj analize:** Identifikacija najčešćih tema iz negativnih komentara za hotel `Hotel Arena` u poslednjoj dostupnoj godini, kako bi menadžer mogao da prepozna oblasti koje gosti najčešće kritikuju.

**Detalji analize:**

Analiza obuhvata sledeće korake:

1. Pronalaženje poslednje godine: Najpre se nad kolekcijom `v1_reviews` pronalazi poslednja godina koja postoji u podacima.
2. Filtriranje recenzija sa negativnim komentarima: U obradu ulaze samo recenzije sa validnim datumom i sa popunjenim negativnim komentarom.
3. Izračunavanje godine recenzije: Polje `review_year` se u v1 računa unutar samog upita pomoću `review_date`.
4. Filtriranje na poslednju godinu: Zadržavaju se samo recenzije iz poslednje dostupne godine.
5. Spajanje sa hotelima: Recenzije se povezuju sa kolekcijom `v1_hotels` kako bi se filtrirao samo `Hotel Arena`.
6. Tokenizacija teksta: Negativni komentar se pretvara u niz reči korišćenjem regularnog izraza.
7. Uklanjanje stop reči i kratkih tokena: Izbacuju se nerelevantne reči i prekratki tokeni kako bi analiza bila preciznija.
8. Uklanjanje duplikata unutar jedne recenzije: Svaka ključna reč se računa najviše jednom po recenziji.
9. Grupisanje i rangiranje: Ključne reči se grupišu, broje i sortiraju po učestalosti.
10. Izdvajanje najvažnijih rezultata: Prikazuje se prvih 20 najčešćih negativnih tema.

**Objašnjenje pipeline-a pre optimizacije, korak po korak:**

- Prvi `aggregate` sa `$match` i `$group`: Najpre pronalazi poslednju godinu koja postoji u podacima.
- `$match`: U glavnom upitu zadržava samo recenzije sa datumom i sa smislenim negativnim komentarom.
- `$addFields`: Iz `review_date` računa `review_year` kako bi moglo da se filtrira po poslednjoj godini.
- Drugi `$match`: Zadržava samo recenzije iz poslednje godine.
- `$lookup`: Povezuje recenzije sa kolekcijom hotela.
- `$unwind`: Pretvara niz hotela u jedan objekat.
- Treći `$match`: Filtrira samo `Hotel Arena`.
- Prvi `$project`: Tekst negativnog komentara razlaže na tokene pomoću regularnog izraza.
- Drugi `$project`: Iz tokena uklanja stop reči i kratke nerelevantne izraze.
- Treći `$project`: Uklanja duplikate reči unutar jedne recenzije.
- `$unwind`: Pretvara niz ključnih reči u pojedinačne vrednosti kako bi se svaka mogla brojati.
- `$group`: Broji koliko puta se svaka ključna reč pojavljuje.
- `$sort`: Sortira ključne reči po učestalosti.
- `$limit`: Zadržava samo prvih 20 najčešćih tema.

<img width="1366" height="238" alt="Screenshot 2026-06-07 at 19 12 42" src="https://github.com/user-attachments/assets/f8594626-e498-48bd-a049-3f34f480c6a0" />

<img width="1367" height="239" alt="Screenshot 2026-06-07 at 19 13 00" src="https://github.com/user-attachments/assets/4a8da589-1db3-4f2f-9349-ee6bcd1864a7" />

**Optimizacija:**

Optimizacija je postignuta uz pomoć narednih koraka:

1. Preprocessing negativnih komentara pri importu: U `v2_reviews` je unapred kreirano polje `negative_keywords`, pa upit više ne radi tokenizaciju, filtriranje stop reči i uklanjanje duplikata tokom izvršavanja.
2. Denormalizacija hotela i godine: Polja `hotel_name` i `review_year` postoje direktno u dokumentu recenzije, pa nisu potrebni `lookup` i `addFields`.
3. Rano filtriranje: Upit odmah bira recenzije za traženi hotel, poslednju godinu i dokumente koji zaista imaju `negative_keywords`.
4. Jednostavnija agregacija: Nakon filtriranja ostaje samo `unwind`, `group`, `sort` i `limit`, što značajno smanjuje složenost pipeline-a.
5. Podrška indeksa: Indeks `db.v2_reviews.createIndex({ hotel_name: 1, review_year: 1, review_month: 1 })` pomaže da se brzo izdvoje recenzije za traženi hotel i period.

**Objašnjenje pipeline-a nakon optimizacije, korak po korak:**

- Prvi `aggregate` sa `$match` i `$group`: Pronalazi poslednju godinu na osnovu već postojećeg polja `review_year`.
- `$match`: Odmah bira recenzije za `Hotel Arena`, za poslednju godinu i samo dokumente koji imaju `negative_keywords`.
- `$unwind`: Razdvaja niz `negative_keywords` na pojedinačne ključne reči.
- `$group`: Računa koliko puta se svaka ključna reč pojavljuje.
- `$sort`: Sortira rezultate po broju pojavljivanja.
- `$limit`: Vraća prvih 20 najčešćih negativnih tema.

<img width="1366" height="237" alt="Screenshot 2026-06-07 at 19 16 08" src="https://github.com/user-attachments/assets/bc5940d9-cd29-4038-ba2a-8f2af2658ea4" />
<img width="1180" height="239" alt="Screenshot 2026-06-07 at 19 16 10" src="https://github.com/user-attachments/assets/b7aa3549-55d6-4959-8175-d67633b9c63a" />

**Grafički prikaz rezultata:**
<img width="522" height="403" alt="Screenshot 2026-06-07 at 19 05 40" src="https://github.com/user-attachments/assets/aa95f436-ac16-4564-937c-66daea6dcf97" />


### Zadatak 4: Najčešći tagovi u visoko ocenjenim recenzijama

[Upit pre optimizacije](v1/queries/manager/Query4/Query4-Unoptimized.js) | [Upit nakon optimizacije](v2/queries/manager/Query4/Query4-Optimized.js)

**Cilj analize:** Pronalaženje najčešćih tagova po godinama u recenzijama sa ocenom većom od `8.5` za hotel `Hotel Arena`, kako bi menadžer prepoznao šta gosti najčešće ističu u pozitivnim iskustvima.

**Detalji analize:**

Analiza obuhvata sledeće korake:

1. Spajanje recenzija sa hotelima: Recenzije iz `v1_reviews` spajaju se sa `v1_hotels` preko `hotel_id`.
2. Filtriranje ciljnog hotela i visokih ocena: U obradi ostaju samo recenzije za `Hotel Arena` sa ocenom većom od `8.5`.
3. Filtriranje validnih datuma i tagova: Uzimaju se samo recenzije koje imaju datum i nepraznu listu tagova.
4. Izračunavanje godine: Godina se dobija iz `review_date` unutar upita.
5. Razdvajanje tagova: Niz tagova se razvija pomoću `unwind`, kako bi svaki tag mogao da se broji zasebno.
6. Grupisanje po godini i tagu: Broji se koliko puta se svaki tag pojavljuje u svakoj godini.
7. Sortiranje po značaju: Tagovi se sortiraju po godini i po broju pojavljivanja.
8. Formiranje liste najvažnijih tagova: Za svaku godinu kreira se lista tagova i uzima se prvih 10.

**Objašnjenje pipeline-a pre optimizacije, korak po korak:**

- `$lookup`: Povezuje recenzije sa hotelima.
- `$unwind`: Pretvara niz `hotel` u jedan objekat.
- `$match`: Bira samo recenzije za `Hotel Arena`, sa visokom ocenom, validnim datumom i nepraznim tagovima.
- `$project`: Izvlači godinu iz datuma i zadržava samo tagove kao relevantno polje za nastavak obrade.
- `$unwind`: Svaki tag iz niza odvaja u poseban zapis.
- Prvi `$group`: Broji koliko se puta svaki tag javlja po godini.
- `$sort`: Sortira tagove po godini i po učestalosti.
- Drugi `$group`: Za svaku godinu skuplja sortirane tagove u jednu listu.
- Završni `$project`: Uzimaju se samo prvih 10 tagova za svaku godinu.
- Završni `$sort`: Sortira godine rastuće radi preglednog prikaza.
<img width="1367" height="232" alt="Screenshot 2026-06-07 at 20 01 30" src="https://github.com/user-attachments/assets/bd169e9a-26a5-4f3b-b648-5ae3276184dd" />

<img width="1206" height="238" alt="Screenshot 2026-06-07 at 20 01 32" src="https://github.com/user-attachments/assets/608bb1ca-08ec-4547-8b71-d7afb137b5e9" />

**Optimizacija:**

Optimizacija je postignuta uz pomoć narednih koraka:

1. Denormalizacija naziva hotela i godine: U `v2_reviews` već postoje `hotel_name` i `review_year`, pa se uklanjaju `lookup` i računanje godine.
2. Rano filtriranje po hotelu, oceni i postojanju tagova: Smanjuje se broj dokumenata koji ulaze u `unwind` i `group`.
3. Podrška indeksa: Indeks `db.v2_reviews.createIndex({ hotel_name: 1, reviewer_score: 1, review_year: 1 })` ubrzava pretragu visoko ocenjenih recenzija po hotelu i vremenu.
4. Dodatna optimizacija kroz izvedenu kolekciju: Kolekcija `v2_top_tags_by_year` unapred čuva top tagove po hotelu i godini, pa se analiza može svesti na jednostavan `match` i `project`.
5. Smanjenje obrade u realnom vremenu: Najskuplji deo, brojanje tagova po godini, može biti unapred pripremljen tokom importa.

**Objašnjenje pipeline-a nakon optimizacije, korak po korak:**

- `$match`: Na početku filtrira recenzije za `Hotel Arena`, visoke ocene, postojeću godinu i neprazne tagove.
- `$project`: Preuzima već sačuvanu `review_year` vrednost kao `year` i zadržava tagove.
- `$unwind`: Razdvaja sve tagove na pojedinačne vrednosti.
- `$group`: Broji pojavljivanja svakog taga po godini.
- `$sort`: Sortira tagove po godini i po frekvenciji.
- Drugi `$group`: Za svaku godinu formira listu tagova sa brojem pojavljivanja.
- `$project`: Ostavlja samo top 10 tagova.
- Završni `$sort`: Poređa rezultate po godinama.
<img width="1368" height="249" alt="Screenshot 2026-06-07 at 20 24 37" src="https://github.com/user-attachments/assets/dc59ae6f-6557-4d78-8cb9-81c3669b45a6" />

<img width="1222" height="242" alt="Screenshot 2026-06-07 at 20 06 00" src="https://github.com/user-attachments/assets/ed4f29d5-1a6f-4c50-9364-4486c5712d0c" />

**Grafički prikaz rezultata:**
<img width="519" height="404" alt="Screenshot 2026-06-07 at 19 05 20" src="https://github.com/user-attachments/assets/81a7ce66-20da-44f4-bd01-5eb8e1796f59" />


### Zadatak 5: Trendovi obližnjih hotela u odnosu na referentni hotel

[Upit pre optimizacije](v1/queries/manager/Query5/Query5-NotOptimized.js) | [Upit nakon optimizacije](v2/queries/manager/Query5/Query5-Optimized.js)

**Cilj analize:** Pronalaženje najbližih hotela u odnosu na `Hotel Arena` i analiza njihovih mesečnih trendova ocena i broja recenzija, kako bi menadžer mogao da prati konkurenciju u neposrednom okruženju.

**Detalji analize:**

Analiza obuhvata sledeće korake:

1. Filtriranje hotela sa lokacijom: U kolekciji `v1_hotels` zadržavaju se hoteli koji imaju validnu lokaciju i koji nisu `Hotel Arena`.
2. Ručno računanje distance: Za svaki hotel izračunava se udaljenost u odnosu na zadate koordinate hotela `Hotel Arena`.
3. Sortiranje po udaljenosti: Hoteli se sortiraju od najbližeg ka najudaljenijem.
4. Ograničavanje na 10 najbližih: Zadržava se samo prvih 10 hotela.
5. Spajanje sa recenzijama: Za izabrane hotele radi se `lookup` nad kolekcijom `v1_reviews`.
6. Filtriranje recenzija sa validnim datumom: Uzimaju se samo recenzije koje imaju datum.
7. Izračunavanje godine i meseca: Iz `review_date` se tokom upita računaju godina i mesec.
8. Grupisanje po hotelu i vremenu: Za svaki hotel, godinu i mesec računa se prosečna ocena i broj recenzija.
9. Konačno sortiranje i prikaz: Rezultati se prikazuju po udaljenosti i vremenskom redosledu.

**Objašnjenje pipeline-a pre optimizacije, korak po korak:**

- `$match`: Bira samo hotele koji imaju lokaciju i koji nisu `Hotel Arena`.
- `$project`: Za svaki hotel računa ručno `distance_score` na osnovu koordinata i zadržava osnovna polja potrebna za nastavak.
- `$sort`: Sortira hotele po izračunatoj udaljenosti.
- `$limit`: Zadržava samo 10 najbližih hotela.
- `$lookup`: Spaja izabrane hotele sa svim njihovim recenzijama.
- `$unwind`: Razdvaja niz recenzija na pojedinačne dokumente.
- Drugi `$match`: Ostavlja samo recenzije koje imaju validan datum.
- Drugi `$project`: Izvlači godinu i mesec recenzije i priprema podatke za agregaciju.
- `$group`: Za svaki hotel i svaki mesec računa prosečnu ocenu i broj recenzija.
- Završni `$sort`: Sortira rezultate po udaljenosti, godini i mesecu.
- Završni `$project`: Oblikuje izlaz tako da bude spreman za pregled i poređenje.
 
<img width="1367" height="250" alt="Screenshot 2026-06-07 at 20 11 55" src="https://github.com/user-attachments/assets/ecd463c1-f0d5-46f3-881f-9256a6e54ef2" />

 <img width="1200" height="240" alt="Screenshot 2026-06-07 at 20 11 57" src="https://github.com/user-attachments/assets/de9d9d4f-cbdb-486b-ae31-102fc0f468fb" />

**Optimizacija:**

Optimizacija je postignuta uz pomoć narednih koraka:

1. Uvođenje geoprostornog modela: Kolekcija `v2_hotels` čuva lokaciju u GeoJSON formatu, što omogućava korišćenje MongoDB operatora `$geoNear`.
2. Geoprostorni indeks: Indeks `db.v2_hotels.createIndex({ location: "2dsphere" })` omogućava brzo pronalaženje najbližih hotela bez ručnog računanja distance nad celom kolekcijom.
3. Prebacivanje vremenskih agregata u izvedenu kolekciju: Umesto spajanja sa svim pojedinačnim recenzijama, optimizovani upit koristi `v2_hotel_time_stats`, gde su mesečni proseci i broj recenzija već unapred izračunati.
4. Smanjenje broja obrađenih dokumenata: Nakon `$geoNear` odmah se bira samo 10 najbližih hotela, pa se tek onda radi povezivanje sa vremenskom statistikom.
5. Dodatna mogućnost potpune prekomputacije: U projektu postoji i kolekcija `v2_nearby_hotel_trends`, koja unapred čuva trendove najbližih hotela za svaki referentni hotel, čime se ova analiza može dodatno ubrzati.

**Objašnjenje pipeline-a nakon optimizacije, korak po korak:**

- `findOne`: Najpre pronalazi lokaciju hotela `Hotel Arena`, koja će biti referentna tačka za geoprostornu pretragu.
- `$geoNear`: Pronalaži hotele najbliže referentnoj lokaciji i automatski računa udaljenost u metrima.
- `$limit`: Odmah zadržava 10 najbližih hotela, čime se drastično smanjuje količina podataka za dalju obradu.
- `$lookup`: Umesto pojedinačnih recenzija, spaja hotele sa unapred pripremljenom kolekcijom `v2_hotel_time_stats`.
- `$unwind`: Razdvaja niz vremenskih statistika na pojedinačne zapise.
- `$match`: Zadržava samo mesečne statistike, pošto je to nivo analize koji se prikazuje.
- `$project`: Priprema izlazna polja kao što su naziv hotela, udaljenost, godina, mesec, prosečna ocena i broj recenzija.
- `$sort`: Sortira rezultate po udaljenosti i vremenskom redosledu.
  
<img width="1064" height="246" alt="Screenshot 2026-06-07 at 19 55 27" src="https://github.com/user-attachments/assets/40c4e27a-38f4-4f1c-9774-78dd78fff5ea" />

**Grafički prikaz rezultata:**
<img width="1053" height="358" alt="Screenshot 2026-06-07 at 19 26 26" src="https://github.com/user-attachments/assets/0e168e7c-8d11-40e2-9e1a-cdbfb1aaa878" />

## Zaključak

Optimizacija menadžerskih upita u ovom projektu nije zasnovana samo na dodavanju indeksa, već i na promeni načina modelovanja podataka. Najveći dobitak postignut je:

- denormalizacijom najčešće korišćenih atributa
- prebacivanjem dela obrade u fazu importa
- uvođenjem izvedenih kolekcija za ponovljive analize
- korišćenjem geoprostornih mogućnosti MongoDB-a

Na ovaj način su upiti postali jednostavniji, pregledniji i pogodniji za menadžerske analize nad velikim skupom recenzija.
