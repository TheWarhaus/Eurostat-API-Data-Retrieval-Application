![Project Logo](./src/icons/title.png)

# Eurostat API Data Retrival Application

**A desktop application based on Python code for downloading Eurostat data. No coding required. Pick a database, filter only the parameters you need like on Eurostat, and export the result to Excel.**

**Author:** *TheWarhaus*

**Version:** 0.1


## What This App Does

The application provides a 2-step workflow:

1. Enter or search for a Eurostat dataset code.
2. Load dimensions and codelists, apply filters, fetch data, and export the result to `.xlsx`.

The GUI is built with `tkinter`. Data retrieval is done through `eurostat` package.

## How The Application Works

1. Run the `main.py` code.

### Step 1: Load a database

1. User enters dataset code (for example `lfsq_eegais`) or opens search popup, where he/she can browse the Eurostat database.
2. App calls:
	 - `fetch_dimensions(db)`
	 - `fetch_codelist(db, each_dimension)`
3. Results are loaded asynchronously to keep the UI responsive.

### Step 2: Apply filters and fetch data

1. For each non-time dimension, user selects one or more values.
2. Optional `From`/`To` time inputs are converted to Eurostat period syntax.
3. Optionaly user can select `Panel data format` to retrieve the data in panel format.
4. App calls `fetch_data(db, filter_pars=...)`.
5. First 50 rows are shown in the preview table.
6. Full result is exported to Excel after clicking on `Download to Excel` with filename:
	 - `<database_code>_<timestamp>.xlsx`

## Project Structure

```text
Eurostat-API-Data-Retrieval-Application/
|-- main.py
|-- README.md
|-- LICENSE
`-- src/
		|-- __init__.py
		|-- eurostat_utils.py
		|-- helpers.py
		|-- create dictionaries/
		|   |-- database dictionary/
		|   |   |-- create dictionary.py
		|   |   |-- database_dictionary.json
		|   |   `-- table_of_contents.xml
		|   `-- parameter abreviations/
		|       |-- dictionary_creation.py
		|       |-- lookup_dictionary.json
		|       `-- ALL_CODELISTS.xml
		`-- icons/
				|-- app.ico
				|-- icon.png
				`-- create icons.py
```

## Key Files

- `main.py`
	- GUI application entry point.
	- Step 1: database code input + search popup.
	- Step 2: parameter filtering + time bounds + data preview + Excel export.
- `src/eurostat_utils.py`
	- Wrapper functions for Eurostat API calls:
		- `fetch_dimensions(db)`
		- `fetch_codelist(db, dimension)`
		- `fetch_data(db, filters)`
		- `to_eurostat_period(...)`
- `src/helpers.py`
	- Utility functions for package checks, codelist normalization, output path, and dictionary lookup labels.
- `src/create dictionaries/...`
	- Offline scripts to generate lookup JSON files from downloaded XML files.

## Runtime Dependencies

Important implementation details:

- The app dynamically installs missing Python packages.
- The app currently expects these JSON files to exist:
	- `database_dictionary.json`
	- `lookup_dictionary.json`

## Update Dictionaries

If Eurostat metadata changed, regenerate the JSON dictionaries.

1. Download source XML files latest versions:
	- Download respective XML files from:
		- *Database dictionary:* `https://ec.europa.eu/eurostat/api/dissemination/catalogue/toc/xml`
		- *Parameter abreviations:* `https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/codelist/ESTAT/`
	- Place those respective files in:
	 	- *Database dictionary:* `src/create dictionaries/database dictionary/table_of_contents.xml`
	 	- *Parameter abreviations:* `src/create dictionaries/parameter abreviations/ALL_CODELISTS.xml`
2. Run:

```bat
"src\create dictionaries\database dictionary\create dictionary.py"
"src\create dictionaries\parameter abreviations\dictionary_creation.py"
```

3. Ensure output JSON files were updated.
