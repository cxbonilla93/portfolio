# Set environment
# Load dependencies
import os          # provides tools for interacting with the operating system (e.g., paths, directories)
import pandas as pd  # main library for data frames, CSV import/export, and tabular manipulation
import re           # regular-expression engine for finding and replacing text patterns
import types        # lets you check whether an object is a module, class, etc., useful when cleaning variables
from typing import Union  # offers type hints that can express “this value may be one of several types”

# Set wd to path where file is saved
dname = os.getcwd()  # returns the current working directory
os.chdir(dname)      # sets the working directory to that same path (keeps notebook in sync with file location)

# Load properties raw data
raw_data = pd.read_csv('Eviction data for import.csv')
raw_data

# Creates a helper named squeeze that trims a string and turns any run of tabs, new-lines, or multiple spaces into a single space
def squeeze(text: str) -> str:
    return re.sub(r"\s+", " ", str(text).strip())

# For each row in raw_data:  
#   1. Remove empty cells,  
#   2. Clean every remaining cell with squeeze,  
#   3. Join the pieces with one space,  
# then write that joined text back into the first column
raw_data.iloc[:, 0] = (
    raw_data
        .apply(lambda r: " ".join(r.dropna().map(squeeze)), axis=1)
)

# Deletes any extra columns whose names start with “Unnamed” (common placeholders from CSV import)
raw_data = raw_data.loc[:, ~raw_data.columns.str.match(r"^Unnamed")]

# Rename the sole remaining column for clarity
raw_data.columns = ["raw_record"]

# Make a working copy of raw data
evictions = raw_data.copy()

# Extract case id

# Reset the DataFrame index and add a sequential “primary_key” column starting at 1
evictions = evictions.reset_index(drop=True)
evictions.insert(0, "primary_key", evictions.index + 1)

# Pull the first chunk of text (up to the first space) from each raw_record and store it as case_id
evictions["case_id"] = evictions["raw_record"].str.extract(r"^(\S+)")

# Count how many characters long each case_id is and tally how many rows share each length
case_count_checksum = (
    evictions["case_id"]
      .str.len()
      .value_counts()
      .sort_index()
)

# Display the total number of rows and the length distribution of case_id values
print("Row count of evictions = " + str(len(evictions)))
print(case_count_checksum)

# Extract case number

# Pull the 5-digit number that appears right after the first space and store it as case_number
evictions["case_number"] = evictions["raw_record"].str.extract(r"^\S+\s+(\d{5})")

# Count how many characters long each case_number is and tally how many rows share each length
case_count_checksum = (
    evictions["case_number"]
        .str.len()
        .value_counts()
        .sort_index()
)

# Display the total row count and the length distribution of case_number values
print("Row count of evictions = " + str(len(evictions)))
print(case_count_checksum)

# In this context, a “token” is simply one chunk of text separated from others by spaces.
# For example, in the string "2021CV1010700289 10107 CV WERJ", the tokens are:
#   1) 2021CV1010700289   2) 10107   3) CV   4) WERJ

# Pull the fourth whitespace-delimited token from raw_record and store it in case_type
evictions["case_type"] = evictions["raw_record"].str.split(" ").str[3]

# Replace "Kathryn" entries in case_type with a missing value (pd.NA)
evictions.loc[evictions["case_type"].eq("Kathryn"), "case_type"] = pd.NA

# Count and display every distinct case_type value, including missing ones
case_type = evictions["case_type"].value_counts(dropna=False).sort_index()
print("Distinct values for case_type (token #3):")
print(case_type)

# Extract the case name
# Identify any date in either 2021-07-20 or 07/20/2021 format and store the pattern
date_regex   = r"(?:\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"

# Build a pattern that captures every character between the word “CV” and the first date
# Example slice:  “CV  WERJ 4 Bogard Street LLC VS Franklin Signorelli  2021-07-20”
case_regex   = re.compile(r"\bCV\b\s+(.+?)\s+" + date_regex)

# Pull the captured text (case name) from raw_record, then trim extra spaces and quotes
evictions["case_name"] = (
    evictions["raw_record"]
        .str.extract(case_regex)[0]      # grab group 1
        .str.strip(' "')
)

# Take the very first word or code that appears at the start of each case_name
first_token_regex = evictions["case_name"].str.extract(r"^\s*([A-Za-z0-9]+)", expand=False)

# Create a True/False mask showing rows where that first word matches the case_type column
prefix_mask = (
    first_token_regex.fillna("")          # make NaN / <NA> harmless
    == evictions["case_type"].fillna("") # neutralise missing values
)

# For rows flagged by the mask, remove the duplicate first word from case_name
evictions.loc[prefix_mask, "case_name"] = (
    evictions.loc[prefix_mask, "case_name"]
      .str.replace(r"^\s*[A-Za-z0-9]+\s*", "", regex=True)
      .str.lstrip(' "')                # trim leading quote / blank
)

# Extract plaintiff and defendants

# Capture plaintiff / defendant around the first “VS” (or “VS.”)
#    – case-insensitive, period after VS is optional
vs_split_regex = re.compile(
    r"^(?P<plaintiff>.*?)\s+VS\.?\s+(?P<defendant>.*)$",
    flags=re.I,
)

# Create a helper that returns plaintiff / defendant while covering edge-cases: no VS, VS at the start, or VS at the end
def split_with_fallback(case_name: str) -> tuple[str, str]:
    """
    Return (plaintiff, defendant). Handles lines with:
      • no VS separator,
      • VS at the start (missing plaintiff),
      • VS at the end (missing defendant).
    """
    if pd.isna(case_name):
        return "Unknown", "Unknown"

    # try normal split first
    m = vs_split_regex.match(case_name)
    if m:
        left  = m.group("plaintiff").strip(' "')
        right = m.group("defendant").strip(' "')
        left  = left  if left  else "Unknown"
        right = right if right else "Unknown"
        return left, right

    # no VS found – treat entire string as plaintiff
    return case_name.strip(' "'), "Unknown"

# Apply the helper so every row gets a plaintiff and defendant column
evictions[["plaintiff", "defendant"]] = evictions["case_name"].apply(
    lambda s: pd.Series(split_with_fallback(s))
)

# Build a pattern that matches stray “VS” or “VS.” tokens (case-insensitive)
vs_token_regex = re.compile(r"\bVS\.?\b", flags=re.I)   # matches VS or VS.

# Identify rows where either plaintiff or defendant is still flagged as "Unknown"
mask_unknown_side = (
    (evictions["plaintiff"]  == "Unknown") |
    (evictions["defendant"] == "Unknown")
)

# In those rows, remove leftover “VS” tokens from the plaintiff text
evictions.loc[mask_unknown_side, "plaintiff"] = (
    evictions.loc[mask_unknown_side, "plaintiff"]
        .str.replace(vs_token_regex, "", regex=True)
        .str.strip(' "')
        .replace("", "Unknown")             # put label back if empty
)

# Do the same cleanup for the defendant text
evictions.loc[mask_unknown_side, "defendant"] = (
    evictions.loc[mask_unknown_side, "defendant"]
        .str.replace(vs_token_regex, "", regex=True)
        .str.strip(' "')
        .replace("", "Unknown")
)

# Define a second fallback that tries to fetch a defendant name buried later in the raw_record
def fallback_defendant(raw_record: str, case_id: str) -> str:
    """
    Capture text between:
      • the second occurrence of case_id, and
      • the last number in the string.
    Returns 'Unknown' if the pattern isn't found.
    """
    # pattern: <case_id>   <captured text>   <final number> <end of string>
    pattern = rf"{re.escape(case_id)}\s+(?P<name>.*?)\s+\d+\b[^\d]*?$"
    m = re.search(pattern, raw_record)
    if not m:
        return "Unknown"

    name = m.group("name").strip(' "')
    name = re.sub(r"\s{2,}", " ", name)  # collapse double spaces
    name = re.sub(r"\bVS\.?\b", "", name, flags=re.I).strip()  # remove stray VS tokens
    return name if name else "Unknown"


# Apply the second fallback only to rows where defendant is still "Unknown"
mask_defendant_unknown = evictions["defendant"] == "Unknown"

evictions.loc[mask_defendant_unknown, "defendant"] = evictions.loc[mask_defendant_unknown].apply(
    lambda row: fallback_defendant(row["raw_record"], row["case_id"]),
    axis=1
)

# Pull all dates featured in dataset

# Many rows contain the unnecessary time stamp “00:00:00.000” right after a placeholder date; remove that text from raw_record
evictions["raw_record"] = (
    evictions["raw_record"]
        .str.replace(r"\s*00:00:00\.000", "", regex=True)  # delete the time stamp and any leading space
        .str.replace(r"\s{2,}", " ", regex=True)           # collapse any double spaces created by the deletion
        .str.strip()                                       # tidy any spaces left at the ends
)

# Find every date in YYYY-MM-DD format and store the list in a new column
evictions["dates_isolated"] = evictions["raw_record"].str.findall(r"\d{4}-\d{2}-\d{2}")

# Take the first date in that list as the filing date
evictions["filing_date"]    = evictions["dates_isolated"].str[0]   # may be NaN if no match

# Take the second date in that list as the execution date (may be missing)
evictions["execution_date"] = evictions["dates_isolated"].str[1]   # NaN if < 2 matches

# Convert both date columns from text to true datetime objects; bad strings become NaT
evictions["filing_date"]    = pd.to_datetime(evictions["filing_date"],
                                             errors="coerce", format="%Y-%m-%d")
evictions["execution_date"] = pd.to_datetime(evictions["execution_date"],
                                             errors="coerce", format="%Y-%m-%d")

# Print a quick summary showing how many non-missing values each date column contains
evictions.drop(columns="dates_isolated", inplace=True)

# Quick check on data quality
print(evictions[["filing_date", "execution_date"]].info(show_counts=True))

# Define a helper that lists how many unique dates exist and their min / max
def date_summary(col):
    non_null = evictions[col].dropna()
    print(f"{col}: {len(non_null.unique()):,} unique dates "
          f"— min {non_null.min().date()}, max {non_null.max().date()}")

date_summary("filing_date")
date_summary("execution_date")

# Run the helper for filing and execution dates
execution_outliers = evictions[
    evictions["execution_date"].notna()            # make sure the cell isn’t NaT
    & (evictions["execution_date"].dt.year == 2102)
]

# Pick out any execution dates that were wrongly coded as the year 2102
execution_year_errors = evictions["execution_date"].notna() & (evictions["execution_date"].dt.year == 2102)

# Fix those errors by changing the year to 2021 while keeping month and day the same
evictions.loc[execution_year_errors, "execution_date"] = (
    evictions.loc[execution_year_errors, "execution_date"]
        .apply(lambda d: d.replace(year=2021))
)

# Identify any execution dates that fall before 2019 (1753 indicates “pending” in the source system)
execution_outliers = evictions[
    evictions["execution_date"].notna()            # make sure the cell isn’t NaT
    & (evictions["execution_date"].dt.year < 2019)
]
execution_outliers # 1753 is defined for eviction executions that are only pending

# Build small tables of all unique filing dates and execution dates for easy review
unique_filing = sorted(evictions["filing_date"].dropna().unique())
unique_filing    = pd.DataFrame({"filing_date": unique_filing})

unique_execution = sorted(evictions["execution_date"].dropna().unique())
unique_execution = pd.DataFrame({"execution_date": unique_execution})

# Display the two unique-date tables and the fully updated DataFrame
unique_filing
unique_execution

evictions

# Extract address

# Build a regex that finds dates written as YYYY-MM-DD
date_pattern_regex = re.compile(r"\d{4}-\d{2}-\d{2}")

# Define a helper that grabs the address found between
#   1) the second date in the line, and
#   2) the next appearance of the 5-digit case_number
def extract_address_from_record(
    raw_record: str,
    case_number: str,
) -> Union[str, pd.NA]:
    """
    Pull the address that sits between:
      • the SECOND ISO-formatted date in *raw_record*, and
      • the next occurrence of the 5-digit *case_number*.
    Returns <NA> if either boundary is missing.
    """
    # -- find all ISO dates in the row -----------------------------------------
    date_tokens = date_pattern_regex.findall(raw_record)
    if len(date_tokens) < 2:
        return pd.NA                      # no second date found → cannot parse
    second_date = date_tokens[1]

    # -- slice the string *after* the second date ------------------------------
    start_of_slice = raw_record.find(second_date) + len(second_date)
    trailing_text = raw_record[start_of_slice:]

    # -- locate the case number that *follows* the second date -----------------
    case_num_regex = re.compile(rf"\b{re.escape(case_number)}\b")
    case_match = case_num_regex.search(trailing_text)
    if not case_match:
        return pd.NA                      # case number not found after date

    # -- everything between the two anchors = address --------------------------
    end_of_slice = start_of_slice + case_match.start()
    address_raw = raw_record[start_of_slice:end_of_slice]

    # -- tidy-up: trim quotes / blanks and collapse double spaces --------------
    address_clean = (
        address_raw.strip(' "')
                   .replace("\t", " ")        # tabs → single space
    )
    address_clean = re.sub(r"\s{2,}", " ", address_clean)  # ≥2 spaces → 1

    return address_clean if address_clean else pd.NA

# Create a new column called address by running the helper on every row
evictions["address"] = evictions.apply(
    lambda row: extract_address_from_record(
        raw_record=row["raw_record"],
        case_number=row["case_number"],
    ),
    axis=1,
)

# Replace any missing address with the text “No address listed”
evictions["address"] = evictions["address"].fillna("No address listed")

# Grab the last standalone number in each raw_record and call it case_status_code; if none is found, mark as "Unknown"
evictions["case_status_code"] = (
    evictions["raw_record"]
      .str.extract(r"(\d+)\D*$", expand=False)       # returns NaN if no match
      .fillna("Unknown")
)

# Keep everything that comes after that final number and call it case_status; trim spaces/quotes and label blanks as "Unknown"
evictions["case_status"] = (
    evictions["raw_record"]
      .str.replace(r".*?\d+\s*", "", regex=True)     # keep tail only
      .str.strip(' "')                               # tidy quotes / blanks
      .replace("", "Unknown")                        # empty → Unknown
)

# Find rows whose text ends with the literal words "NULL NULL" (a sign that status information is missing)
null_tail_mask = evictions["raw_record"].str.strip().str.endswith("NULL NULL")

# For those rows, set a placeholder code of 99999 and the text "Status unavailable"
evictions.loc[null_tail_mask, "case_status_code"] = 99999
evictions.loc[null_tail_mask, "case_status"]      = "Status unavailable"

# In rows where case_status is “Status unavailable”, set execution_date to blank to avoid excel errors
evictions.loc[evictions["case_status"] == "Status unavailable", "execution_date"] = pd.NaT

# View dataframe in python
evictions

# Review column names
evictions.columns

# print(evictions['case_status'].value_counts()) # get a summary table of column values
# print(evictions['case_status_code'].value_counts()) # get a summary table of column values

# Coerce numeric
evictions["case_status_code"] = evictions["case_status_code"].astype("int64")

# Export as parquet
evictions.to_parquet("evictions.parquet")
