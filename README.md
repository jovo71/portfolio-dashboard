# 📊 Portfolio Dashboard

Een professionele webapplicatie voor het monitoren van uw persoonlijke beleggingsportefeuille. Gebouwd met React + TypeScript (frontend) en Python FastAPI (backend), met SQLite als database.

![Dashboard Preview](docs/preview.png)

---

## ✨ Functionaliteiten

- **Realtime koersen** via Yahoo Finance, automatisch bijgewerkt op geconfigureerde tijden
- **Performanceberekeningen** voor meerdere periodes (vandaag, week, maand, YTD, sinds aankoop, aangepast)
- **Dividend beheer** — registreer uitbetalingen en volg uw dividendrendement
- **Kostenanalyse** — beheers-, service-, transactie- en bewaarkosten per belegging
- **Interactieve grafieken** — portefeuillewaarde, rendement, verdeling en kosteninzicht
- **CSV import/export** voor beleggingen
- **Donkere en lichte modus**
- **Responsive design** voor desktop en mobiel
- **Systeemstatus pagina** met scheduler- en updatelogboek
- **JWT authenticatie** met configureerbaar wachtwoord

---

## 🚀 Snel starten met Docker

### Vereisten
- [Docker](https://docs.docker.com/get-docker/) en [Docker Compose](https://docs.docker.com/compose/install/)

### Stap 1 — Repository klonen
```bash
git clone https://github.com/uwgebruiker/portfolio-dashboard.git
cd portfolio-dashboard
```

### Stap 2 — Configuratie aanpassen
```bash
# Inloggegevens instellen
nano config/auth.yaml
```
```yaml
username: admin
password: uwEigenWachtwoord123
```

```bash
# Omgevingsvariabelen instellen (optioneel)
cp .env.example .env
nano .env
```

### Stap 3 — Applicatie starten
```bash
docker compose up -d
```

De applicatie is nu bereikbaar op **http://localhost**

### Stap 4 — Voorbeelddata laden (optioneel)
```bash
docker compose exec backend python seed_data.py
```

---

## 💻 Lokaal draaien (zonder Docker)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Voorbeelddata laden
python seed_data.py

# Server starten
uvicorn app.main:app --reload --port 8000
```

API documentatie: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend: http://localhost:3000

---

## ⚙️ Configuratie

### Inloggegevens (`config/auth.yaml`)
```yaml
username: admin
password: uwWachtwoord
```

### Omgevingsvariabelen (`.env`)
| Variabele | Standaard | Omschrijving |
|-----------|-----------|--------------|
| `SECRET_KEY` | `verander-dit` | JWT ondertekeningssleutel |
| `UPDATE_TIME_1` | `08:00` | Eerste dagelijkse koersupdate |
| `UPDATE_TIME_2` | `13:00` | Tweede dagelijkse koersupdate |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | JWT verlooptijd (minuten) |
| `DATABASE_URL` | SQLite pad | Database connectiestring |

---

## 📁 Projectstructuur

```
portfolio-dashboard/
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI routers
│   │   │   ├── auth.py
│   │   │   ├── investments.py
│   │   │   ├── prices.py
│   │   │   ├── dividends.py
│   │   │   ├── costs.py
│   │   │   ├── performance.py
│   │   │   └── system.py
│   │   ├── services/      # Businesslogica
│   │   │   ├── price_service.py
│   │   │   ├── performance_service.py
│   │   │   └── scheduler.py
│   │   ├── main.py        # FastAPI applicatie
│   │   ├── database.py    # Database setup
│   │   ├── models.py      # SQLAlchemy modellen
│   │   ├── schemas.py     # Pydantic schemas
│   │   └── auth.py        # JWT authenticatie
│   ├── tests/
│   │   └── test_api.py    # Unit tests
│   ├── seed_data.py       # Voorbeelddata
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── pages/         # Paginacomponenten
│   │   │   ├── LoginPage.tsx
│   │   │   ├── DashboardPage.tsx
│   │   │   ├── PortfolioPage.tsx
│   │   │   ├── DividendPage.tsx
│   │   │   ├── CostsPage.tsx
│   │   │   └── SystemPage.tsx
│   │   ├── components/
│   │   │   └── Layout.tsx
│   │   ├── api.ts         # API client
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── index.css      # Design system
│   ├── package.json
│   ├── Dockerfile
│   └── nginx.conf
├── config/
│   └── auth.yaml          # Inloggegevens
├── .env.example
├── .github/
│   └── workflows/
│       └── ci.yml         # GitHub Actions
└── docker-compose.yml
```

---

## 🗄️ Datamodel

```
investments          — Beleggingen (naam, ISIN, ticker, broker, stuks, prijs, ...)
price_history        — Dagelijkse koerssnapshots per belegging
dividends            — Dividenduitbetalingen per belegging
cost_entries         — Kosten per belegging (beheer, service, transactie, ...)
system_logs          — Logboek van koersupdates en systeemgebeurtenissen
```

---

## 🧪 Tests uitvoeren

```bash
cd backend
pytest tests/ -v
```

---

## 📈 Performanceberekeningen

```
Koersrendement (%)   = (Huidige waarde − Startwaarde) / Startwaarde × 100
Dividendrendement    = Ontvangen dividend in periode
Totaalrendement      = Koersrendement + Dividend − Kosten
```

Periodes: Vandaag · Week · Maand · YTD · Sinds aankoop · Aangepast

---

## 🔌 API Endpoints

| Methode | Pad | Omschrijving |
|---------|-----|--------------|
| POST | `/api/auth/login` | Inloggen |
| GET | `/api/investments/` | Alle beleggingen |
| POST | `/api/investments/` | Belegging toevoegen |
| PUT | `/api/investments/{id}` | Belegging wijzigen |
| DELETE | `/api/investments/{id}` | Belegging verwijderen |
| POST | `/api/investments/import/csv` | CSV importeren |
| GET | `/api/investments/export/csv` | CSV exporteren |
| POST | `/api/prices/refresh` | Koersen verversen |
| GET | `/api/dividends/` | Dividendoverzicht |
| POST | `/api/dividends/` | Dividend toevoegen |
| GET | `/api/costs/` | Kostenoverzicht |
| POST | `/api/costs/` | Kostenpost toevoegen |
| GET | `/api/performance/` | Performanceberekening |
| GET | `/api/performance/history` | Historische portefeuillewaarde |
| GET | `/api/system/status` | Systeemstatus |

Volledige API documentatie: http://localhost:8000/docs

---

## 🔮 Toekomstige uitbreidingen

De architectuur is voorbereid op:

- Automatische import vanuit DeGiro en Rabobank (CSV/API)
- Meerdere gebruikers met rollen
- E-mailnotificaties bij grote koersbewegingen
- Dividendkalender
- Benchmark vergelijking (AEX, MSCI World, S&P 500)
- Inflatiegecorrigeerd rendement
- Meerdere valuta met wisselkoersen
- Cloud deployment (AWS/GCP/Azure)

---

## 🔒 Beveiliging

- Wachtwoord staat **niet** in de broncode; gebruik `config/auth.yaml` of omgevingsvariabelen
- Voeg `config/auth.yaml` toe aan `.gitignore` voor publieke repositories
- Verander `SECRET_KEY` in productie
- Gebruik HTTPS in productie (bijv. met Traefik of Nginx Proxy Manager)

---

## 📄 Licentie

MIT License — vrij te gebruiken en aan te passen.
