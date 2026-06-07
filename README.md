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

**Optimizacija:**

Optimizacija je postignuta uz pomoć narednih koraka:

1. Denormalizacija naziva hotela: U kolekciji `v2_reviews` polje `hotel_name` je već upisano u svaki dokument, pa više nije potreban `lookup` sa kolekcijom hotela.
2. Prethodno izračunata vremenska polja: Polja `review_year` i `review_month` kreiraju se prilikom importa, čime je uklonjeno računanje godine i meseca u svakom izvršavanju upita.
3. Rano filtriranje: Upit odmah filtrira dokumente po `hotel_name`, `review_year` i `review_month`, pa se u dalju obradu šalje manji skup podataka.
4. Podrška indeksa: Indeks `db.v2_reviews.createIndex({ hotel_name: 1, review_year: 1, review_month: 1 })` ubrzava filtriranje i kasnije sortiranje po vremenskoj dimenziji.
5. Dodatna optimizacija preko izvedene kolekcije: U projektu postoji i kolekcija `v2_hotel_time_stats`, koja ovaj tip vremenske analize dodatno pojednostavljuje jer već čuva mesečne agregate po hotelu.

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

**Optimizacija:**

Optimizacija je postignuta uz pomoć narednih koraka:

1. Denormalizacija ključnih atributa: U `v2_reviews` su dostupni `hotel_name` i `review_year`, pa se iz pipeline-a uklanjaju i `lookup` i računanje godine.
2. Rano sužavanje skupa dokumenata: Filtriranje po hotelu, godini i nacionalnosti radi se na samom početku upita.
3. Smanjenje broja operacija u agregaciji: Pošto nema spajanja i dodatne projekcije za datum, pipeline je kraći i lakši za izvršavanje.
4. Podrška indeksa: Indeks `db.v2_reviews.createIndex({ hotel_name: 1, reviewer_nationality: 1, review_year: 1 })` ubrzava filtriranje nad dimenzijama koje se direktno koriste u analizi.
5. Dodatni nivo optimizacije kroz izvedenu kolekciju: Kolekcija `v2_nationality_year_stats` već čuva izračunate agregate po hotelu, godini i nacionalnosti, pa se ova analiza može izvršiti i bez skeniranja svih pojedinačnih recenzija.

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

**Optimizacija:**

Optimizacija je postignuta uz pomoć narednih koraka:

1. Preprocessing negativnih komentara pri importu: U `v2_reviews` je unapred kreirano polje `negative_keywords`, pa upit više ne radi tokenizaciju, filtriranje stop reči i uklanjanje duplikata tokom izvršavanja.
2. Denormalizacija hotela i godine: Polja `hotel_name` i `review_year` postoje direktno u dokumentu recenzije, pa nisu potrebni `lookup` i `addFields`.
3. Rano filtriranje: Upit odmah bira recenzije za traženi hotel, poslednju godinu i dokumente koji zaista imaju `negative_keywords`.
4. Jednostavnija agregacija: Nakon filtriranja ostaje samo `unwind`, `group`, `sort` i `limit`, što značajno smanjuje složenost pipeline-a.
5. Podrška indeksa: Indeks `db.v2_reviews.createIndex({ hotel_name: 1, review_year: 1, review_month: 1 })` pomaže da se brzo izdvoje recenzije za traženi hotel i period.

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

**Optimizacija:**

Optimizacija je postignuta uz pomoć narednih koraka:

1. Denormalizacija naziva hotela i godine: U `v2_reviews` već postoje `hotel_name` i `review_year`, pa se uklanjaju `lookup` i računanje godine.
2. Rano filtriranje po hotelu, oceni i postojanju tagova: Smanjuje se broj dokumenata koji ulaze u `unwind` i `group`.
3. Podrška indeksa: Indeks `db.v2_reviews.createIndex({ hotel_name: 1, reviewer_score: 1, review_year: 1 })` ubrzava pretragu visoko ocenjenih recenzija po hotelu i vremenu.
4. Dodatna optimizacija kroz izvedenu kolekciju: Kolekcija `v2_top_tags_by_year` unapred čuva top tagove po hotelu i godini, pa se analiza može svesti na jednostavan `match` i `project`.
5. Smanjenje obrade u realnom vremenu: Najskuplji deo, brojanje tagova po godini, može biti unapred pripremljen tokom importa.

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

**Optimizacija:**

Optimizacija je postignuta uz pomoć narednih koraka:

1. Uvođenje geoprostornog modela: Kolekcija `v2_hotels` čuva lokaciju u GeoJSON formatu, što omogućava korišćenje MongoDB operatora `$geoNear`.
2. Geoprostorni indeks: Indeks `db.v2_hotels.createIndex({ location: "2dsphere" })` omogućava brzo pronalaženje najbližih hotela bez ručnog računanja distance nad celom kolekcijom.
3. Prebacivanje vremenskih agregata u izvedenu kolekciju: Umesto spajanja sa svim pojedinačnim recenzijama, optimizovani upit koristi `v2_hotel_time_stats`, gde su mesečni proseci i broj recenzija već unapred izračunati.
4. Smanjenje broja obrađenih dokumenata: Nakon `$geoNear` odmah se bira samo 10 najbližih hotela, pa se tek onda radi povezivanje sa vremenskom statistikom.
5. Dodatna mogućnost potpune prekomputacije: U projektu postoji i kolekcija `v2_nearby_hotel_trends`, koja unapred čuva trendove najbližih hotela za svaki referentni hotel, čime se ova analiza može dodatno ubrzati.

## Zaključak

Optimizacija menadžerskih upita u ovom projektu nije zasnovana samo na dodavanju indeksa, već i na promeni načina modelovanja podataka. Najveći dobitak postignut je:

- denormalizacijom najčešće korišćenih atributa
- prebacivanjem dela obrade u fazu importa
- uvođenjem izvedenih kolekcija za ponovljive analize
- korišćenjem geoprostornih mogućnosti MongoDB-a

Na ovaj način su upiti postali jednostavniji, pregledniji i pogodniji za menadžerske analize nad velikim skupom recenzija.
