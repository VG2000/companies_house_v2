# 📢 Company Data Processing Pipeline

This project processes **Companies House** data by fetching, filtering, and updating records in the `Company` model.

---

## 🚀 Steps to Updating the Company Model  

### **1️⃣ Fetch Company Data Files**  
Download all **7 company data files** from the [Companies House website](https://download.companieshouse.gov.uk/BasicCompanyData-2025-02-01-part1_7.zip).  

### **2️⃣ Filter the Data**  
- Open each individual file.  
- Apply the following filters:  
  - **CompanyStatus** must be `"Active"`.  
  - **Accounts.AccountCategory** must be one of:  
    - `"FULL"`  
    - `"GROUP"`  
    - `"MEDIUM"`  

### **3️⃣ Save Filtered Data**  
Delete all previous company name columns as they are not saveds in the database
Save the filtered data into:  
```sh
data/active_full_group_medium_companies.csv

### **4️⃣ Update or Create Records**

Run process_company_data() in company_data/companies_house_company_parser.py. This will update or create records and 
    also run update_full_accounts_paper_filed() and last_full_statement_url ().
