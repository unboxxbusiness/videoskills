### **Step 1: Run the YouTube Scan (In Terminal)**

Choose one of these commands depending on how much quota you want to use:

- **Daily Scan (Saves Quota - 60 units/run):**
    
    ```
    bash
    
    python e:\videosskills\asktvideos\scripts\fetch_competitors.py
    ```
    
- **Deep Scan (Scans Top Ever Viral Videos - 2,060 units/run):** *(Change `SKIP_SEARCH: bool = False` in `asktvideos/scripts/fetch_competitors.py` first, then run)*:
    
    ```
    bash
    
    python e:\videosskills\asktvideos\scripts\fetch_competitors.py
    ```
    

---

### **Step 2: Generate the Content (In Chat)**

Type the prompt that matches your need for today:

- **Default (Choose #1 Top Viral AI Topic):**
    
    > `"In asktvideos, read competitor_report.json and generate today's script"`
    > 
- **By Rank/Position:**
    
    > `"In asktvideos, read competitor_report.json and write the script for the #2 viral short"` *(Change #2 to #3, #4, etc.)*
    > 
- **By Category / Pillar:**
    
    > `"In asktvideos, read competitor_report.json and generate today's script for the AI Automation category"` *(Or use `AI Tools`, `AI News`, `AI Careers`, `AI Business`)*
    > 
- **By Topic / Keyword:**
    
    > `"In asktvideos, read competitor_report.json and write the script about 'Cursor AI Editor'"`
    >