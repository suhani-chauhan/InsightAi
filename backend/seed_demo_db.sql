-- ============================================================
-- InsightAI Enterprise Demo Database
-- PostgreSQL | 25+ tables, 20,000+ rows
-- Covers: E-Commerce, HR, Projects, Support, Analytics
-- ============================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- REFERENCE DATA
-- ============================================================

CREATE TABLE currencies (
    code CHAR(3) PRIMARY KEY,
    name VARCHAR(60) NOT NULL,
    symbol VARCHAR(5) NOT NULL
);

INSERT INTO currencies (code, name, symbol) VALUES
('USD','US Dollar','$'),('EUR','Euro','€'),('GBP','British Pound','£'),
('JPY','Japanese Yen','¥'),('CAD','Canadian Dollar','CA$'),
('AUD','Australian Dollar','A$'),('CHF','Swiss Franc','CHF'),
('CNY','Chinese Yuan','¥'),('INR','Indian Rupee','₹'),('BRL','Brazilian Real','R$'),
('SEK','Swedish Krona','kr'),('NOK','Norwegian Krone','kr'),
('SGD','Singapore Dollar','S$'),('KRW','South Korean Won','₩'),('NZD','New Zealand Dollar','NZ$');

CREATE TABLE countries (
    id SERIAL PRIMARY KEY,
    code CHAR(2) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    region VARCHAR(50),
    currency_code CHAR(3) REFERENCES currencies(code)
);

INSERT INTO countries (code, name, region, currency_code) VALUES
('US','United States','North America','USD'),
('GB','United Kingdom','Europe','GBP'),
('DE','Germany','Europe','EUR'),
('FR','France','Europe','EUR'),
('JP','Japan','Asia','JPY'),
('CA','Canada','North America','CAD'),
('AU','Australia','Oceania','AUD'),
('CN','China','Asia','CNY'),
('IN','India','Asia','INR'),
('BR','Brazil','South America','BRL'),
('MX','Mexico','North America','USD'),
('IT','Italy','Europe','EUR'),
('ES','Spain','Europe','EUR'),
('KR','South Korea','Asia','KRW'),
('SG','Singapore','Asia','SGD'),
('NL','Netherlands','Europe','EUR'),
('SE','Sweden','Europe','SEK'),
('NO','Norway','Europe','NOK'),
('CH','Switzerland','Europe','CHF'),
('NZ','New Zealand','Oceania','NZD');

-- ============================================================
-- ORGANIZATION
-- ============================================================

CREATE TABLE companies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    industry VARCHAR(80),
    country_code CHAR(2) REFERENCES countries(code),
    founded_year INT CHECK (founded_year BETWEEN 1800 AND 2025),
    revenue_usd NUMERIC(18,2),
    employee_count INT,
    website VARCHAR(200),
    is_public BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO companies (name, industry, country_code, founded_year, revenue_usd, employee_count, website, is_public) VALUES
('Apex Technologies','Technology','US',2005,450000000,3200,'apextech.com',TRUE),
('GlobalTrade Co','Retail','GB',1998,1200000000,8500,'globaltrade.co.uk',TRUE),
('Nexus Financial','Finance','US',2010,320000000,1800,'nexusfinancial.com',TRUE),
('BioCore Labs','Healthcare','DE',2001,890000000,4200,'biocorelabs.de',TRUE),
('SkyBuild Group','Construction','AU',1985,670000000,5600,'skybuild.com.au',FALSE),
('DataStream Inc','Technology','CA',2015,180000000,950,'datastream.ca',FALSE),
('MediPlus Corp','Healthcare','FR',1992,540000000,3100,'mediplus.fr',TRUE),
('EcoPower Ltd','Energy','NL',2008,730000000,2800,'ecopower.nl',TRUE),
('FastFreight','Logistics','SG',2003,290000000,4100,'fastfreight.sg',FALSE),
('CreativeHub','Marketing','US',2018,95000000,420,'creativehub.io',FALSE);

CREATE TABLE departments (
    id SERIAL PRIMARY KEY,
    company_id INT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    code VARCHAR(20),
    parent_dept_id INT REFERENCES departments(id),
    budget NUMERIC(14,2),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(company_id, code)
);

DO $$
DECLARE
    v_company_id INT;
    dept_names TEXT[] := ARRAY['Engineering','Product','Sales','Marketing','Finance',
                                'HR','Operations','Legal','Customer Success','Data Science'];
    dept TEXT;
    i INT := 0;
BEGIN
    FOR v_company_id IN SELECT id FROM companies ORDER BY id LOOP
        i := 0;
        FOREACH dept IN ARRAY dept_names LOOP
            i := i + 1;
            INSERT INTO departments (company_id, name, code, budget)
            VALUES (v_company_id, dept,
                    LEFT(UPPER(REPLACE(dept,' ','')),4)||'-'||v_company_id,
                    (random()*5000000+500000)::NUMERIC(14,2));
        END LOOP;
    END LOOP;
END $$;

CREATE TABLE employees (
    id SERIAL PRIMARY KEY,
    company_id INT NOT NULL REFERENCES companies(id),
    department_id INT REFERENCES departments(id),
    first_name VARCHAR(60) NOT NULL,
    last_name VARCHAR(60) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    phone VARCHAR(25),
    job_title VARCHAR(100),
    employment_type VARCHAR(20) CHECK (employment_type IN ('full_time','part_time','contractor','intern')),
    salary NUMERIC(12,2),
    hire_date DATE NOT NULL,
    termination_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    manager_id INT REFERENCES employees(id),
    country_code CHAR(2) REFERENCES countries(code),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_employees_company ON employees(company_id);
CREATE INDEX idx_employees_dept ON employees(department_id);
CREATE INDEX idx_employees_manager ON employees(manager_id);

DO $$
DECLARE
    first_names TEXT[] := ARRAY['Alice','Bob','Carol','David','Emma','Frank','Grace','Henry',
        'Isabel','James','Kate','Liam','Mia','Noah','Olivia','Paul','Quinn','Rachel',
        'Sam','Tina','Uma','Victor','Wendy','Xander','Yara','Zoe','Alex','Blake',
        'Cameron','Dana','Elliot','Fiona','George','Hana','Ivan','Julia','Kevin',
        'Luna','Marco','Nina','Oscar','Petra','Ryan','Sofia','Tom','Ursula',
        'Vlad','Wren','Xavier','Yuki'];
    last_names TEXT[] := ARRAY['Smith','Johnson','Williams','Brown','Jones','Garcia','Miller',
        'Davis','Wilson','Moore','Taylor','Anderson','Thomas','Jackson','White',
        'Harris','Martin','Thompson','Robinson','Lewis','Lee','Walker','Hall',
        'Allen','Young','King','Scott','Green','Adams','Baker','Carter','Mitchell',
        'Perez','Roberts','Turner','Phillips','Campbell','Parker','Evans','Edwards',
        'Collins','Stewart','Sanchez','Morris','Rogers','Reed','Cook','Morgan','Bell','Murphy'];
    titles TEXT[] := ARRAY['Software Engineer','Senior Engineer','Staff Engineer','Principal Engineer',
        'Product Manager','Senior PM','Director of Product','Engineering Manager',
        'VP of Engineering','CTO','Data Analyst','Senior Data Analyst','Data Scientist',
        'ML Engineer','Sales Executive','Account Manager','Sales Director',
        'Marketing Specialist','Growth Manager','CMO','DevOps Engineer','SRE',
        'QA Engineer','UX Designer','UI Designer','Business Analyst',
        'Finance Analyst','CFO','HR Specialist','HR Manager','Operations Manager',
        'Legal Counsel','Customer Success Manager','Support Lead'];
    emp_types TEXT[] := ARRAY['full_time','full_time','full_time','full_time','part_time','contractor','intern'];
    country_codes TEXT[] := ARRAY['US','US','US','GB','DE','FR','CA','AU','IN','SG','JP','NL'];
    v_company_id INT;
    v_dept_id INT;
    v_emp_id INT;
    v_first_manager INT;
    fn TEXT; ln TEXT; etitle TEXT;
    hire_d DATE;
    sal NUMERIC;
    i INT;
BEGIN
    FOR v_company_id IN SELECT id FROM companies ORDER BY id LOOP
        v_first_manager := NULL;
        FOR i IN 1..50 LOOP
            SELECT id INTO v_dept_id FROM departments
            WHERE company_id = v_company_id ORDER BY random() LIMIT 1;

            fn := first_names[(random()*49+1)::INT];
            ln := last_names[(random()*49+1)::INT];
            etitle := titles[(random()*33+1)::INT];
            hire_d := '2015-01-01'::DATE + (random()*3285)::INT;
            sal := CASE
                WHEN etitle LIKE '%CTO%' OR etitle LIKE '%CFO%' OR etitle LIKE '%CMO%' THEN (random()*100000+200000)::NUMERIC(12,2)
                WHEN etitle LIKE 'VP%' OR etitle LIKE 'Director%' THEN (random()*80000+130000)::NUMERIC(12,2)
                WHEN etitle LIKE 'Senior%' OR etitle LIKE 'Staff%' OR etitle LIKE 'Principal%' THEN (random()*40000+100000)::NUMERIC(12,2)
                WHEN etitle LIKE 'Manager%' OR etitle LIKE '%Manager%' THEN (random()*30000+90000)::NUMERIC(12,2)
                ELSE (random()*40000+55000)::NUMERIC(12,2)
            END;

            INSERT INTO employees (
                company_id, department_id, first_name, last_name, email, phone,
                job_title, employment_type, salary, hire_date, is_active, manager_id, country_code
            ) VALUES (
                v_company_id, v_dept_id, fn, ln,
                lower(fn)||'.'||lower(ln)||'.'||v_company_id||i||'@corp'||v_company_id||'.com',
                '+1-'||(random()*900+100)::INT||'-'||(random()*900+100)::INT||'-'||(random()*9000+1000)::INT,
                etitle,
                emp_types[(random()*6+1)::INT],
                sal, hire_d,
                CASE WHEN random() > 0.05 THEN TRUE ELSE FALSE END,
                CASE WHEN i > 1 AND v_first_manager IS NOT NULL THEN v_first_manager ELSE NULL END,
                country_codes[(random()*11+1)::INT]
            ) RETURNING id INTO v_emp_id;

            IF i = 1 THEN v_first_manager := v_emp_id; END IF;
        END LOOP;
    END LOOP;
END $$;

-- Give remaining NULL managers a real manager from same company
UPDATE employees e
SET manager_id = (
    SELECT e2.id FROM employees e2
    WHERE e2.company_id = e.company_id AND e2.id != e.id
    ORDER BY random() LIMIT 1
)
WHERE manager_id IS NULL AND random() > 0.05;

-- ============================================================
-- PRODUCTS & INVENTORY
-- ============================================================

CREATE TABLE product_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    parent_id INT REFERENCES product_categories(id),
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE
);

INSERT INTO product_categories (name, slug, description) VALUES
('Electronics','electronics','Electronic devices and accessories'),
('Clothing','clothing','Apparel and fashion items'),
('Home & Garden','home-garden','Home improvement and garden supplies'),
('Sports & Outdoors','sports-outdoors','Sporting goods and outdoor equipment'),
('Books & Media','books-media','Books, music, movies and digital content'),
('Health & Beauty','health-beauty','Health products and beauty supplies'),
('Food & Beverages','food-beverages','Groceries and beverages'),
('Automotive','automotive','Car parts and accessories'),
('Toys & Games','toys-games','Children toys and board games'),
('Office Supplies','office-supplies','Office equipment and stationery');

INSERT INTO product_categories (name, slug, parent_id, description) VALUES
('Laptops','laptops',1,'Portable computers'),
('Smartphones','smartphones',1,'Mobile phones'),
('Headphones','headphones',1,'Audio equipment'),
('Tablets','tablets',1,'Tablet devices'),
('Cameras','cameras',1,'Digital cameras and accessories'),
('Mens Clothing','mens-clothing',2,'Men''s apparel'),
('Womens Clothing','womens-clothing',2,'Women''s apparel'),
('Footwear','footwear',2,'Shoes and boots'),
('Fitness Equipment','fitness-equipment',4,'Gym and fitness gear'),
('Outdoor Gear','outdoor-gear',4,'Camping and hiking equipment'),
('Supplements','supplements',6,'Vitamins and health supplements'),
('Skincare','skincare',6,'Facial and body care products'),
('Smart Home','smart-home',1,'Smart home devices'),
('Coffee & Tea','coffee-tea',7,'Specialty coffee and tea'),
('Kitchen Tools','kitchen-tools',3,'Cooking utensils and appliances');

CREATE TABLE suppliers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    contact_name VARCHAR(100),
    email VARCHAR(150),
    phone VARCHAR(25),
    country_code CHAR(2) REFERENCES countries(code),
    lead_time_days INT DEFAULT 7,
    rating NUMERIC(3,2) CHECK (rating BETWEEN 0 AND 5),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO suppliers (name, contact_name, email, phone, country_code, lead_time_days, rating) VALUES
('TechSource Global','Mark Chen','mark@techsource.com','+1-800-111-2222','US',5,4.5),
('EuroSupply GmbH','Hans Weber','h.weber@eurosupply.de','+49-30-111222','DE',10,4.2),
('AsiaTrade Ltd','Li Wei','li.wei@asiatrade.cn','+86-21-111222','CN',21,3.8),
('FastParts Inc','Sarah Kim','sarah@fastparts.com','+1-415-222333','US',3,4.7),
('GlobalTextiles','Priya Sharma','p.sharma@globaltex.in','+91-22-111222','IN',14,4.0),
('NordSupply AB','Erik Larsson','erik@nordsupply.se','+46-8-111222','SE',7,4.6),
('PacificGoods Co','James Tanaka','j.tanaka@pacificgoods.jp','+81-3-111222','JP',12,4.3),
('BrazilExport SA','Carlos Mendez','c.mendez@brazilexport.br','+55-11-111222','BR',18,3.9),
('CanadaParts','Emily Taylor','emily@canadaparts.ca','+1-416-333444','CA',4,4.8),
('AustroParts Pty','Michael Wong','m.wong@austroparts.au','+61-2-111222','AU',6,4.4),
('MedSupply Corp','Dr Anne Mueller','a.mueller@medsupply.de','+49-89-111222','DE',8,4.9),
('FoodCo International','Roberto Rossi','r.rossi@foodco.it','+39-2-111222','IT',3,4.1),
('AutoParts World','Jean Dupont','j.dupont@autoparts.fr','+33-1-111222','FR',7,4.3),
('SportGear Pro','Tom Bradley','t.bradley@sportgear.com','+1-213-444555','US',5,4.6),
('HomeStyle Ltd','Emma Davies','e.davies@homestyle.co.uk','+44-20-111222','GB',9,4.2),
('BeautySource Japan','Yuki Yamamoto','y.yamamoto@beautysource.jp','+81-6-111222','JP',11,4.7),
('EduMedia Group','Anna Kowalski','a.kowalski@edumedia.us','+1-312-555666','US',2,4.5),
('ToyFactory Shenzhen','Zhang Wei','z.wei@toyfactory.cn','+86-755-111222','CN',25,3.7),
('OfficeFirst Korea','David Park','d.park@officefirst.kr','+82-2-111222','KR',4,4.4),
('GreenHarvest','Maria Santos','m.santos@greenharvest.br','+55-21-111222','BR',6,4.0);

CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    sku VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    category_id INT REFERENCES product_categories(id),
    supplier_id INT REFERENCES suppliers(id),
    cost_price NUMERIC(12,2) NOT NULL CHECK (cost_price > 0),
    list_price NUMERIC(12,2) NOT NULL CHECK (list_price > 0),
    weight_kg NUMERIC(8,3),
    is_active BOOLEAN DEFAULT TRUE,
    tags TEXT[],
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_products_supplier ON products(supplier_id);

DO $$
DECLARE
    pdata TEXT[][] := ARRAY[
        ARRAY['Pro Laptop X1','11'],ARRAY['Ultra Laptop Z5','11'],
        ARRAY['Gaming Laptop Beast','11'],ARRAY['Business Notebook S3','11'],
        ARRAY['Budget Laptop Go','11'],ARRAY['iPhone Pro Max','12'],
        ARRAY['Galaxy Ultra S25','12'],ARRAY['Pixel 9 Pro','12'],
        ARRAY['OnePlus 13 Pro','12'],ARRAY['Xiaomi 14 Ultra','12'],
        ARRAY['AirPods Pro 3','13'],ARRAY['Sony WH-1000XM6','13'],
        ARRAY['Bose QC Ultra','13'],ARRAY['Sennheiser HD 560S','13'],
        ARRAY['JBL Tour One M2','13'],ARRAY['iPad Pro 13 M4','14'],
        ARRAY['Surface Pro 11','14'],ARRAY['Galaxy Tab S10 Ultra','14'],
        ARRAY['Kindle Scribe 2024','14'],ARRAY['Lenovo Tab P12 Pro','14'],
        ARRAY['Sony Alpha A7 V','15'],ARRAY['Canon EOS R6 Mark III','15'],
        ARRAY['Nikon Z8 Body','15'],ARRAY['Fujifilm X100VI','15'],
        ARRAY['GoPro Hero 13','15'],ARRAY['Nike Air Max 2025','18'],
        ARRAY['Adidas Ultraboost 25','18'],ARRAY['New Balance 1080v14','18'],
        ARRAY['Asics Gel Nimbus 27','18'],ARRAY['Brooks Ghost 16','18'],
        ARRAY['Levis 501 Jeans','16'],ARRAY['Gap Slim Fit Chinos','16'],
        ARRAY['Uniqlo Oxford Shirt','16'],ARRAY['Zara Slim Blazer','16'],
        ARRAY['H&M Basic T-Shirt 3-Pack','16'],ARRAY['Yoga Mat Pro 6mm','19'],
        ARRAY['Resistance Band Set 11pc','19'],ARRAY['Kettlebell 16kg Cast Iron','19'],
        ARRAY['Pull-up Bar Doorway','19'],ARRAY['Adjustable Dumbbell 32.5kg','19'],
        ARRAY['Camping Tent 4 Person','20'],ARRAY['Hiking Boots XTR Waterproof','20'],
        ARRAY['Trail Backpack 60L','20'],ARRAY['Sleeping Bag -10C','20'],
        ARRAY['Trekking Poles Carbon','20'],ARRAY['The Art of SQL','5'],
        ARRAY['Clean Code Book','5'],ARRAY['System Design Interview','5'],
        ARRAY['Python Crash Course 3rd Ed','5'],ARRAY['Designing Data-Intensive Apps','5'],
        ARRAY['Vitamin D3 5000IU 365ct','21'],ARRAY['Omega-3 Fish Oil 2000mg','21'],
        ARRAY['Multivitamin Complex','21'],ARRAY['Whey Protein 5lb Chocolate','21'],
        ARRAY['Creatine Monohydrate 500g','21'],ARRAY['Organic Coffee Blend 1kg','24'],
        ARRAY['Matcha Green Tea Premium','24'],ARRAY['Cold Brew Concentrate 1L','24'],
        ARRAY['Ethiopian Single Origin 500g','24'],ARRAY['Herbal Tea Variety 60ct','24'],
        ARRAY['Car Phone Mount MagSafe','8'],ARRAY['Dash Cam 4K Dual','8'],
        ARRAY['OBD2 Bluetooth Scanner','8'],ARRAY['LED Headlight Kit H11','8'],
        ARRAY['Tire Pressure Monitor Kit','8'],ARRAY['LEGO Technic Bugatti','9'],
        ARRAY['Barbie Dreamhouse 2025','9'],ARRAY['Hot Wheels Track Builder','9'],
        ARRAY['Puzzle 1000pc Van Gogh','9'],ARRAY['Building Blocks 1000pc','9'],
        ARRAY['Ergonomic Office Chair','10'],ARRAY['Standing Desk 160cm Bamboo','10'],
        ARRAY['Monitor Arm Dual VESA','10'],ARRAY['Wireless Keyboard Slim','10'],
        ARRAY['Mesh Office Chair Pro','10'],ARRAY['Apple Watch Series 10','13'],
        ARRAY['Garmin Forerunner 965','13'],ARRAY['Fitbit Sense 3','13'],
        ARRAY['Oura Ring Gen4','13'],ARRAY['Polar H10 Heart Monitor','19'],
        ARRAY['Ninja Blender Pro 1500W','15'],ARRAY['Cosori Air Fryer 8L','15'],
        ARRAY['Breville Smart Coffee Maker','15'],ARRAY['Instant Pot Duo 8Qt','15'],
        ARRAY['Vitamix E310 Blender','15'],ARRAY['Face Serum Vitamin C 30ml','22'],
        ARRAY['Retinol Eye Cream 15ml','22'],ARRAY['SPF 50 Moisturizer 100ml','22'],
        ARRAY['Hyaluronic Acid Serum','22'],ARRAY['Niacinamide Toner 200ml','22'],
        ARRAY['Electric Toothbrush Oral-B','6'],ARRAY['Argan Oil Shampoo 500ml','6'],
        ARRAY['Beard Grooming Kit 12pc','16'],ARRAY['Hair Dryer Ionic Pro','6'],
        ARRAY['Face Wash Charcoal 150ml','22'],ARRAY['Samsung 27in 4K Monitor','11'],
        ARRAY['LG UltraGear 32in Gaming','11'],ARRAY['Logitech MX Master 3S','11'],
        ARRAY['Keychron K2 Pro Keyboard','11'],ARRAY['Anker 10-in-1 USB-C Hub','11'],
        ARRAY['Eufy Security Cam 4K','23'],ARRAY['August Smart Lock Pro','23'],
        ARRAY['Ring Video Doorbell Pro 2','23'],ARRAY['Philips Hue Starter Kit','23'],
        ARRAY['TP-Link Tapo Hub','23'],ARRAY['DJI Mini 4 Pro Drone','15'],
        ARRAY['Canon Powershot V10','15'],ARRAY['Insta360 X4','15'],
        ARRAY['Guitar Acoustic Fender','5'],ARRAY['Ukulele Soprano Kala','5'],
        ARRAY['Chess Set Weighted Pieces','9'],ARRAY['Monopoly Deluxe Edition','9'],
        ARRAY['Catan Board Game','9'],ARRAY['Ticket to Ride Europe','9'],
        ARRAY['Watercolor Set 48 Colors','5'],ARRAY['Acrylic Paint Kit 60pc','5'],
        ARRAY['BBQ Grill Portable 2-Burner','3'],ARRAY['Lodge Cast Iron Skillet 12in','15'],
        ARRAY['Global Chef Knife 8in','15'],ARRAY['Epicurean Cutting Board','15'],
        ARRAY['Foam Roller Deep Tissue 60cm','19'],ARRAY['Jump Rope Speed Cable','19'],
        ARRAY['Medicine Ball 8kg Slam','19'],ARRAY['Ab Wheel Rollout Pro','19']
    ];
    i INT;
    v_cat_id INT;
    v_sup_id INT;
    cost_p NUMERIC;
    list_p NUMERIC;
BEGIN
    FOR i IN 1..array_length(pdata, 1) LOOP
        v_cat_id := pdata[i][2]::INT;
        SELECT id INTO v_sup_id FROM suppliers ORDER BY random() LIMIT 1;
        cost_p := (random()*480+12)::NUMERIC(12,2);
        list_p := (cost_p * (1.25 + random()*0.75))::NUMERIC(12,2);
        INSERT INTO products (sku, name, category_id, supplier_id, cost_price, list_price, weight_kg, is_active)
        VALUES (
            'SKU-'||LPAD(i::TEXT,5,'0'),
            pdata[i][1],
            v_cat_id,
            v_sup_id,
            cost_p,
            list_p,
            (random()*8+0.1)::NUMERIC(8,3),
            TRUE
        );
    END LOOP;
END $$;

CREATE TABLE warehouses (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    code VARCHAR(10) UNIQUE NOT NULL,
    country_code CHAR(2) REFERENCES countries(code),
    city VARCHAR(100),
    capacity_units INT,
    is_active BOOLEAN DEFAULT TRUE
);

INSERT INTO warehouses (name, code, country_code, city, capacity_units) VALUES
('US East Hub','US-E','US','New York',50000),
('US West Hub','US-W','US','Los Angeles',45000),
('UK Distribution','UK-1','GB','London',30000),
('Germany Central','DE-1','DE','Frankfurt',35000),
('Asia Pacific Hub','SG-1','SG','Singapore',40000),
('Australia East','AU-1','AU','Sydney',25000),
('Canada Toronto','CA-1','CA','Toronto',20000),
('France Lyon','FR-1','FR','Lyon',18000),
('Japan Tokyo','JP-1','JP','Tokyo',22000),
('Netherlands Rotterdam','NL-1','NL','Rotterdam',28000);

CREATE TABLE inventory (
    id SERIAL PRIMARY KEY,
    product_id INT NOT NULL REFERENCES products(id),
    warehouse_id INT NOT NULL REFERENCES warehouses(id),
    quantity_on_hand INT NOT NULL DEFAULT 0 CHECK (quantity_on_hand >= 0),
    quantity_reserved INT NOT NULL DEFAULT 0 CHECK (quantity_reserved >= 0),
    reorder_point INT DEFAULT 10,
    last_counted_at TIMESTAMP,
    UNIQUE(product_id, warehouse_id)
);

INSERT INTO inventory (product_id, warehouse_id, quantity_on_hand, quantity_reserved, reorder_point, last_counted_at)
SELECT
    p.id,
    w.id,
    (random()*800+5)::INT,
    (random()*80)::INT,
    (random()*30+5)::INT,
    NOW() - (random()*45)::INT * INTERVAL '1 day'
FROM products p
CROSS JOIN warehouses w
WHERE random() > 0.25;

-- ============================================================
-- CUSTOMERS & CRM
-- ============================================================

CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    type VARCHAR(20) CHECK (type IN ('individual','business')) DEFAULT 'individual',
    first_name VARCHAR(60),
    last_name VARCHAR(60),
    company_name VARCHAR(150),
    email VARCHAR(150) UNIQUE NOT NULL,
    phone VARCHAR(25),
    country_code CHAR(2) REFERENCES countries(code),
    loyalty_tier VARCHAR(20) CHECK (loyalty_tier IN ('bronze','silver','gold','platinum')) DEFAULT 'bronze',
    lifetime_value NUMERIC(14,2) DEFAULT 0,
    acquisition_source VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_customers_email ON customers(email);
CREATE INDEX idx_customers_country ON customers(country_code);
CREATE INDEX idx_customers_tier ON customers(loyalty_tier);

DO $$
DECLARE
    first_names TEXT[] := ARRAY['Alice','Bob','Carol','David','Emma','Frank','Grace','Henry',
        'Isabel','James','Kate','Liam','Mia','Noah','Olivia','Paul','Quinn','Rachel',
        'Sam','Tina','Uma','Victor','Wendy','Xander','Yara','Zoe','Alex','Blake',
        'Cameron','Dana','Elliot','Fiona','George','Hana','Ivan','Julia','Kevin',
        'Luna','Marco','Nina','Oscar','Petra','Ryan','Sofia','Tom','Ursula',
        'Vlad','Wren','Xavier','Yuki'];
    last_names TEXT[] := ARRAY['Smith','Johnson','Williams','Brown','Jones','Garcia','Miller',
        'Davis','Wilson','Moore','Taylor','Anderson','Thomas','Jackson','White',
        'Harris','Martin','Thompson','Robinson','Lewis','Lee','Walker','Hall',
        'Allen','Young','King','Scott','Green','Adams','Baker'];
    domains TEXT[] := ARRAY['gmail.com','yahoo.com','outlook.com','icloud.com','proton.me',
                             'hotmail.com','aol.com','mail.com'];
    sources TEXT[] := ARRAY['organic','paid_search','social_media','referral','email','direct','affiliate','podcast'];
    tiers TEXT[] := ARRAY['bronze','bronze','bronze','silver','silver','gold','platinum'];
    ctypes TEXT[] := ARRAY['individual','individual','individual','individual','business'];
    country_codes TEXT[] := ARRAY['US','US','US','GB','DE','FR','CA','AU','IN','SG','JP','NL','BR','MX','IT'];
    i INT;
    ctype TEXT;
    fn TEXT; ln TEXT;
BEGIN
    FOR i IN 1..750 LOOP
        ctype := ctypes[(random()*4+1)::INT];
        fn := first_names[(random()*49+1)::INT];
        ln := last_names[(random()*29+1)::INT];
        INSERT INTO customers (type, first_name, last_name, company_name, email, phone,
                               country_code, loyalty_tier, acquisition_source, lifetime_value)
        VALUES (
            ctype,
            CASE WHEN ctype = 'individual' THEN fn ELSE NULL END,
            CASE WHEN ctype = 'individual' THEN ln ELSE NULL END,
            CASE WHEN ctype = 'business' THEN fn||' '||ln||' '||(ARRAY['LLC','Inc','Corp','Ltd','Co'])[(random()*4+1)::INT] ELSE NULL END,
            lower(fn)||'.'||lower(ln)||i||'@'||domains[(random()*7+1)::INT],
            '+1-'||(random()*900+100)::INT||'-'||(random()*900+100)::INT||'-'||(random()*9000+1000)::INT,
            country_codes[(random()*14+1)::INT],
            tiers[(random()*6+1)::INT],
            sources[(random()*7+1)::INT],
            (random()*25000)::NUMERIC(14,2)
        );
    END LOOP;
END $$;

CREATE TABLE customer_addresses (
    id SERIAL PRIMARY KEY,
    customer_id INT NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    label VARCHAR(30) DEFAULT 'home',
    street VARCHAR(200),
    city VARCHAR(100),
    state VARCHAR(100),
    postal_code VARCHAR(20),
    country_code CHAR(2) REFERENCES countries(code),
    is_default BOOLEAN DEFAULT FALSE
);

INSERT INTO customer_addresses (customer_id, label, street, city, state, postal_code, country_code, is_default)
SELECT
    c.id,
    (ARRAY['home','work','shipping','billing'])[(random()*3+1)::INT],
    (random()*9900+100)::INT||' '||(ARRAY['Main St','Oak Ave','Park Blvd','Lake Dr','Hill Rd',
        'Elm Way','Cedar Ln','Maple Dr','River Rd','Sunset Blvd'])[(random()*9+1)::INT],
    (ARRAY['New York','Los Angeles','Chicago','Houston','Phoenix','San Francisco',
           'Seattle','Boston','Miami','Denver','Austin','Portland','Nashville'])[(random()*12+1)::INT],
    (ARRAY['NY','CA','IL','TX','AZ','CA','WA','MA','FL','CO','TX','OR','TN'])[(random()*12+1)::INT],
    LPAD((random()*89999+10000)::INT::TEXT,5,'0'),
    'US',
    TRUE
FROM customers c;

-- Some customers have a second address
INSERT INTO customer_addresses (customer_id, label, street, city, state, postal_code, country_code, is_default)
SELECT
    c.id,
    'work',
    (random()*9900+100)::INT||' Business Pkwy',
    (ARRAY['New York','Los Angeles','Chicago','Houston','Phoenix'])[(random()*4+1)::INT],
    (ARRAY['NY','CA','IL','TX','AZ'])[(random()*4+1)::INT],
    LPAD((random()*89999+10000)::INT::TEXT,5,'0'),
    'US',
    FALSE
FROM customers c
WHERE random() > 0.6;

-- ============================================================
-- PROMOTIONS
-- ============================================================

CREATE TABLE promotions (
    id SERIAL PRIMARY KEY,
    code VARCHAR(30) UNIQUE NOT NULL,
    description VARCHAR(200),
    type VARCHAR(20) CHECK (type IN ('percentage','fixed_amount','free_shipping','bogo')),
    value NUMERIC(10,2),
    min_order_amount NUMERIC(12,2) DEFAULT 0,
    max_uses INT,
    used_count INT DEFAULT 0,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO promotions (code, description, type, value, min_order_amount, max_uses, start_date, end_date) VALUES
('SAVE10','10% off any order','percentage',10,0,5000,'2023-01-01','2026-12-31'),
('SAVE20','20% off orders over $100','percentage',20,100,2000,'2023-01-01','2026-12-31'),
('FLAT50','$50 off orders over $250','fixed_amount',50,250,500,'2023-06-01','2025-06-30'),
('FREESHIP','Free shipping on all orders','free_shipping',0,30,NULL,'2023-01-01','2026-12-31'),
('WELCOME15','15% off first order','percentage',15,0,NULL,'2023-01-01','2026-12-31'),
('SUMMER30','30% summer sale','percentage',30,75,800,'2023-06-01','2023-08-31'),
('BFCM40','Black Friday 40% off','percentage',40,50,3000,'2023-11-24','2023-11-27'),
('NEWYEAR25','New Year 25% off','percentage',25,100,1000,'2024-01-01','2024-01-07'),
('LOYAL20','Loyalty member 20% off','percentage',20,0,NULL,'2023-01-01','2026-12-31'),
('FLASH5','Flash sale $5 off','fixed_amount',5,25,200,'2024-03-01','2024-03-03'),
('SPRING15','Spring collection 15% off','percentage',15,60,600,'2024-03-20','2024-06-21'),
('TECH25','25% off electronics','percentage',25,150,400,'2024-01-15','2024-02-15');

-- ============================================================
-- ORDERS & SALES
-- ============================================================

CREATE TABLE payment_methods (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    type VARCHAR(30) CHECK (type IN ('card','bank_transfer','wallet','crypto','cash'))
);

INSERT INTO payment_methods (name, type) VALUES
('Visa Credit','card'),('Mastercard Credit','card'),('American Express','card'),
('PayPal','wallet'),('Stripe','card'),('Bank Transfer','bank_transfer'),
('Cash on Delivery','cash'),('Apple Pay','wallet'),('Google Pay','wallet'),
('Cryptocurrency','crypto'),('Klarna','wallet'),('Afterpay','wallet');

CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    order_number VARCHAR(30) UNIQUE NOT NULL,
    customer_id INT NOT NULL REFERENCES customers(id),
    status VARCHAR(30) CHECK (status IN ('draft','pending','confirmed','processing','shipped','delivered','cancelled','returned')) DEFAULT 'pending',
    currency_code CHAR(3) REFERENCES currencies(code) DEFAULT 'USD',
    subtotal NUMERIC(14,2) NOT NULL DEFAULT 0,
    discount_amount NUMERIC(14,2) DEFAULT 0,
    tax_amount NUMERIC(14,2) DEFAULT 0,
    shipping_amount NUMERIC(14,2) DEFAULT 0,
    total_amount NUMERIC(14,2) NOT NULL DEFAULT 0,
    shipping_address_id INT REFERENCES customer_addresses(id),
    notes TEXT,
    placed_at TIMESTAMP DEFAULT NOW(),
    shipped_at TIMESTAMP,
    delivered_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_placed_at ON orders(placed_at);

CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id INT NOT NULL REFERENCES products(id),
    quantity INT NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(12,2) NOT NULL,
    discount_pct NUMERIC(5,2) DEFAULT 0 CHECK (discount_pct BETWEEN 0 AND 100),
    line_total NUMERIC(14,2) NOT NULL
);

CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_order_items_product ON order_items(product_id);

DO $$
DECLARE
    v_customer_id INT;
    v_order_id INT;
    v_product_id INT;
    v_product_price NUMERIC;
    v_address_id INT;
    v_qty INT;
    v_line NUMERIC;
    v_subtotal NUMERIC;
    v_discount NUMERIC;
    v_tax NUMERIC;
    v_shipping NUMERIC;
    v_total NUMERIC;
    statuses TEXT[] := ARRAY['delivered','delivered','delivered','delivered','shipped','shipped',
                              'processing','confirmed','pending','cancelled','returned'];
    i INT; j INT;
    item_count INT;
    order_date TIMESTAMP;
BEGIN
    FOR i IN 1..3000 LOOP
        SELECT id INTO v_customer_id FROM customers ORDER BY random() LIMIT 1;
        SELECT id INTO v_address_id FROM customer_addresses
        WHERE customer_id = v_customer_id AND is_default = TRUE LIMIT 1;

        order_date := '2022-06-01'::TIMESTAMP + (random()*1000)::INT * INTERVAL '1 day'
                      + (random()*86400)::INT * INTERVAL '1 second';

        INSERT INTO orders (order_number, customer_id, status, subtotal, total_amount,
                            shipping_address_id, placed_at, shipped_at, delivered_at)
        VALUES (
            'ORD-'||LPAD(i::TEXT,7,'0'),
            v_customer_id,
            statuses[(random()*10+1)::INT],
            0, 0, v_address_id,
            order_date,
            CASE WHEN random() > 0.25 THEN order_date + (random()*3+1)::INT * INTERVAL '1 day' ELSE NULL END,
            CASE WHEN random() > 0.35 THEN order_date + (random()*7+4)::INT * INTERVAL '1 day' ELSE NULL END
        ) RETURNING id INTO v_order_id;

        v_subtotal := 0;
        item_count := (random()*5+1)::INT;

        FOR j IN 1..item_count LOOP
            SELECT id, list_price INTO v_product_id, v_product_price
            FROM products ORDER BY random() LIMIT 1;

            v_qty := (random()*4+1)::INT;
            v_line := (v_qty * v_product_price)::NUMERIC(14,2);
            v_subtotal := v_subtotal + v_line;

            INSERT INTO order_items (order_id, product_id, quantity, unit_price, line_total)
            VALUES (v_order_id, v_product_id, v_qty, v_product_price, v_line);
        END LOOP;

        v_discount := CASE WHEN random() > 0.65 THEN (v_subtotal * (0.05 + random()*0.25))::NUMERIC(14,2) ELSE 0 END;
        v_tax := ((v_subtotal - v_discount) * 0.085)::NUMERIC(14,2);
        v_shipping := CASE WHEN v_subtotal > 75 THEN 0 ELSE CASE WHEN random() > 0.5 THEN 9.99 ELSE 14.99 END END;
        v_total := (v_subtotal - v_discount + v_tax + v_shipping)::NUMERIC(14,2);

        UPDATE orders
        SET subtotal = v_subtotal::NUMERIC(14,2),
            discount_amount = v_discount,
            tax_amount = v_tax,
            shipping_amount = v_shipping,
            total_amount = v_total
        WHERE id = v_order_id;
    END LOOP;
END $$;

-- ============================================================
-- PAYMENTS & FINANCE
-- ============================================================

CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    order_id INT NOT NULL REFERENCES orders(id),
    payment_method_id INT REFERENCES payment_methods(id),
    amount NUMERIC(14,2) NOT NULL,
    currency_code CHAR(3) REFERENCES currencies(code) DEFAULT 'USD',
    status VARCHAR(20) CHECK (status IN ('pending','completed','failed','refunded','partial_refund')) DEFAULT 'pending',
    transaction_ref VARCHAR(100),
    gateway_response JSONB,
    paid_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_payments_order ON payments(order_id);
CREATE INDEX idx_payments_status ON payments(status);

INSERT INTO payments (order_id, payment_method_id, amount, currency_code, status, transaction_ref, paid_at)
SELECT
    o.id,
    (random()*11+1)::INT,
    o.total_amount,
    'USD',
    CASE o.status
        WHEN 'delivered'   THEN 'completed'
        WHEN 'shipped'     THEN 'completed'
        WHEN 'processing'  THEN 'completed'
        WHEN 'confirmed'   THEN 'completed'
        WHEN 'cancelled'   THEN 'refunded'
        WHEN 'returned'    THEN 'refunded'
        ELSE 'pending'
    END,
    'TXN-'||upper(substring(md5(random()::TEXT),1,16)),
    CASE WHEN o.status IN ('delivered','shipped','processing','confirmed')
         THEN o.placed_at + INTERVAL '10 minutes' ELSE NULL END
FROM orders o;

-- Some orders have failed first attempt then succeeded
INSERT INTO payments (order_id, payment_method_id, amount, currency_code, status, transaction_ref)
SELECT
    o.id,
    (random()*11+1)::INT,
    o.total_amount,
    'USD',
    'failed',
    'TXN-FAIL-'||upper(substring(md5(random()::TEXT),1,12))
FROM orders o
WHERE random() > 0.85 AND o.status = 'delivered';

CREATE TABLE invoices (
    id SERIAL PRIMARY KEY,
    invoice_number VARCHAR(30) UNIQUE NOT NULL,
    order_id INT REFERENCES orders(id),
    customer_id INT NOT NULL REFERENCES customers(id),
    status VARCHAR(20) CHECK (status IN ('draft','issued','paid','overdue','cancelled')) DEFAULT 'draft',
    issue_date DATE NOT NULL,
    due_date DATE NOT NULL,
    total_amount NUMERIC(14,2) NOT NULL,
    paid_amount NUMERIC(14,2) DEFAULT 0,
    currency_code CHAR(3) REFERENCES currencies(code) DEFAULT 'USD',
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_invoices_customer ON invoices(customer_id);
CREATE INDEX idx_invoices_status ON invoices(status);

INSERT INTO invoices (invoice_number, order_id, customer_id, status, issue_date, due_date,
                      total_amount, paid_amount, currency_code)
SELECT
    'INV-'||LPAD(o.id::TEXT,7,'0'),
    o.id,
    o.customer_id,
    CASE o.status
        WHEN 'delivered' THEN 'paid'
        WHEN 'shipped'   THEN 'issued'
        WHEN 'cancelled' THEN 'cancelled'
        ELSE 'issued'
    END,
    o.placed_at::DATE,
    o.placed_at::DATE + 30,
    o.total_amount,
    CASE WHEN o.status IN ('delivered','shipped') THEN o.total_amount ELSE 0 END,
    'USD'
FROM orders o;

CREATE TABLE order_promotions (
    id SERIAL PRIMARY KEY,
    order_id INT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    promotion_id INT NOT NULL REFERENCES promotions(id),
    discount_applied NUMERIC(12,2) NOT NULL,
    UNIQUE(order_id, promotion_id)
);

INSERT INTO order_promotions (order_id, promotion_id, discount_applied)
SELECT DISTINCT ON (o.id)
    o.id,
    p.id,
    o.discount_amount
FROM orders o
JOIN promotions p ON TRUE
WHERE o.discount_amount > 0
  AND random() > 0.4
ORDER BY o.id, random()
LIMIT 600;

UPDATE promotions p
SET used_count = COALESCE((SELECT COUNT(*) FROM order_promotions op WHERE op.promotion_id = p.id), 0);

-- ============================================================
-- HR MODULE
-- ============================================================

CREATE TABLE leave_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(60) NOT NULL,
    paid BOOLEAN DEFAULT TRUE,
    max_days_per_year INT
);

INSERT INTO leave_types (name, paid, max_days_per_year) VALUES
('Annual Leave', TRUE, 21),
('Sick Leave', TRUE, 10),
('Maternity Leave', TRUE, 90),
('Paternity Leave', TRUE, 14),
('Unpaid Leave', FALSE, 30),
('Study Leave', TRUE, 5),
('Compassionate Leave', TRUE, 5),
('Public Holiday', TRUE, NULL);

CREATE TABLE leave_requests (
    id SERIAL PRIMARY KEY,
    employee_id INT NOT NULL REFERENCES employees(id),
    leave_type_id INT NOT NULL REFERENCES leave_types(id),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    days_requested INT NOT NULL CHECK (days_requested > 0),
    status VARCHAR(20) CHECK (status IN ('pending','approved','rejected','cancelled')) DEFAULT 'pending',
    reason TEXT,
    approved_by INT REFERENCES employees(id),
    created_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO leave_requests (employee_id, leave_type_id, start_date, end_date,
                             days_requested, status, reason, approved_by)
SELECT
    e.id,
    (random()*7+1)::INT,
    CURRENT_DATE + (random()*120-60)::INT,
    CURRENT_DATE + (random()*120-60+random()*9+1)::INT,
    (random()*9+1)::INT,
    (ARRAY['pending','approved','approved','approved','rejected','cancelled'])[(random()*5+1)::INT],
    (ARRAY['Family vacation','Medical appointment','Personal reasons','Home emergency',
            'Study exam','Wedding attendance','Bereavement','Conference attendance'])[(random()*7+1)::INT],
    (SELECT id FROM employees e2 WHERE e2.company_id = e.company_id AND e2.id != e.id ORDER BY random() LIMIT 1)
FROM employees e
WHERE random() > 0.45;

CREATE TABLE performance_reviews (
    id SERIAL PRIMARY KEY,
    employee_id INT NOT NULL REFERENCES employees(id),
    reviewer_id INT NOT NULL REFERENCES employees(id),
    review_period_start DATE NOT NULL,
    review_period_end DATE NOT NULL,
    overall_rating NUMERIC(3,2) CHECK (overall_rating BETWEEN 1 AND 5),
    goals_score NUMERIC(3,2) CHECK (goals_score BETWEEN 1 AND 5),
    skills_score NUMERIC(3,2) CHECK (skills_score BETWEEN 1 AND 5),
    collaboration_score NUMERIC(3,2) CHECK (collaboration_score BETWEEN 1 AND 5),
    leadership_score NUMERIC(3,2) CHECK (leadership_score BETWEEN 1 AND 5),
    comments TEXT,
    status VARCHAR(20) CHECK (status IN ('draft','submitted','acknowledged')) DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO performance_reviews (employee_id, reviewer_id, review_period_start, review_period_end,
    overall_rating, goals_score, skills_score, collaboration_score, leadership_score, status)
SELECT
    e.id,
    COALESCE(e.manager_id,
        (SELECT e2.id FROM employees e2
         WHERE e2.company_id = e.company_id AND e2.id != e.id
         ORDER BY random() LIMIT 1)),
    '2023-01-01',
    '2023-12-31',
    (random()*3+2)::NUMERIC(3,2),
    (random()*3+2)::NUMERIC(3,2),
    (random()*3+2)::NUMERIC(3,2),
    (random()*3+2)::NUMERIC(3,2),
    (random()*3+2)::NUMERIC(3,2),
    (ARRAY['submitted','submitted','submitted','acknowledged','draft'])[(random()*4+1)::INT]
FROM employees e
WHERE random() > 0.15;

-- 2024 reviews for some
INSERT INTO performance_reviews (employee_id, reviewer_id, review_period_start, review_period_end,
    overall_rating, goals_score, skills_score, collaboration_score, leadership_score, status)
SELECT
    e.id,
    COALESCE(e.manager_id,
        (SELECT e2.id FROM employees e2
         WHERE e2.company_id = e.company_id AND e2.id != e.id
         ORDER BY random() LIMIT 1)),
    '2024-01-01',
    '2024-12-31',
    (random()*3+2)::NUMERIC(3,2),
    (random()*3+2)::NUMERIC(3,2),
    (random()*3+2)::NUMERIC(3,2),
    (random()*3+2)::NUMERIC(3,2),
    (random()*3+2)::NUMERIC(3,2),
    (ARRAY['submitted','acknowledged','draft'])[(random()*2+1)::INT]
FROM employees e
WHERE random() > 0.5;

CREATE TABLE salary_history (
    id SERIAL PRIMARY KEY,
    employee_id INT NOT NULL REFERENCES employees(id),
    effective_date DATE NOT NULL,
    salary NUMERIC(12,2) NOT NULL,
    currency_code CHAR(3) REFERENCES currencies(code) DEFAULT 'USD',
    change_reason VARCHAR(100),
    changed_by INT REFERENCES employees(id)
);

-- Starting salary
INSERT INTO salary_history (employee_id, effective_date, salary, change_reason)
SELECT id, hire_date, (salary * 0.82)::NUMERIC(12,2), 'Initial hiring salary'
FROM employees;

-- Year 1 raise
INSERT INTO salary_history (employee_id, effective_date, salary, change_reason)
SELECT id, hire_date + INTERVAL '1 year', (salary * 0.90)::NUMERIC(12,2), 'Annual performance review'
FROM employees WHERE random() > 0.25;

-- Year 2 raise
INSERT INTO salary_history (employee_id, effective_date, salary, change_reason)
SELECT id, hire_date + INTERVAL '2 years', (salary * 0.96)::NUMERIC(12,2), 'Merit increase'
FROM employees WHERE random() > 0.4;

-- Current salary
INSERT INTO salary_history (employee_id, effective_date, salary, change_reason)
SELECT id, GREATEST(hire_date + INTERVAL '3 years', '2024-01-01'), salary, 'Current compensation'
FROM employees WHERE random() > 0.3;

-- ============================================================
-- PROJECTS & TASKS
-- ============================================================

CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    company_id INT NOT NULL REFERENCES companies(id),
    name VARCHAR(150) NOT NULL,
    code VARCHAR(20) UNIQUE,
    description TEXT,
    status VARCHAR(20) CHECK (status IN ('planning','active','on_hold','completed','cancelled')) DEFAULT 'planning',
    priority VARCHAR(10) CHECK (priority IN ('low','medium','high','critical')) DEFAULT 'medium',
    start_date DATE,
    end_date DATE,
    budget NUMERIC(14,2),
    spent_budget NUMERIC(14,2) DEFAULT 0,
    owner_id INT REFERENCES employees(id),
    created_at TIMESTAMP DEFAULT NOW()
);

DO $$
DECLARE
    pnames TEXT[] := ARRAY[
        'Platform Modernization','Mobile App Redesign','Data Pipeline Overhaul',
        'Customer Portal v3','AI Integration Suite','Security Audit Program',
        'ERP System Migration','Cloud Infrastructure Move','API Gateway Rebuild',
        'Analytics Dashboard v2','CRM System Upgrade','DevOps Automation Hub',
        'Product Catalog Revamp','Payment Gateway Integration','Advanced Reporting Suite',
        'Employee Self-Service Portal','Inventory Management System','B2B Partner Portal',
        'Machine Learning Pipeline','Real-time Notifications','Compliance Framework',
        'Data Warehouse Build','Microservices Migration','Zero Trust Security',
        'Customer 360 Platform'
    ];
    statuses TEXT[] := ARRAY['planning','active','active','active','active','on_hold','completed','completed','cancelled'];
    priorities TEXT[] := ARRAY['low','medium','medium','high','high','critical'];
    v_company_id INT;
    v_owner_id INT;
    i INT := 0;
BEGIN
    FOR v_company_id IN SELECT id FROM companies ORDER BY id LOOP
        FOR j IN 1..8 LOOP
            i := i + 1;
            SELECT id INTO v_owner_id FROM employees
            WHERE company_id = v_company_id ORDER BY random() LIMIT 1;
            INSERT INTO projects (company_id, name, code, status, priority,
                                  start_date, end_date, budget, spent_budget, owner_id)
            VALUES (
                v_company_id,
                pnames[((i-1)%25)+1],
                'P'||LPAD(i::TEXT,3,'0'),
                statuses[(random()*8+1)::INT],
                priorities[(random()*5+1)::INT],
                '2023-01-01'::DATE + (random()*365)::INT,
                '2024-06-01'::DATE + (random()*365)::INT,
                (random()*600000+50000)::NUMERIC(14,2),
                (random()*300000)::NUMERIC(14,2),
                v_owner_id
            );
        END LOOP;
    END LOOP;
END $$;

CREATE TABLE project_members (
    id SERIAL PRIMARY KEY,
    project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    employee_id INT NOT NULL REFERENCES employees(id),
    role VARCHAR(50) DEFAULT 'member',
    joined_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(project_id, employee_id)
);

INSERT INTO project_members (project_id, employee_id, role)
SELECT DISTINCT ON (p.id, e.id)
    p.id,
    e.id,
    (ARRAY['lead','developer','developer','designer','analyst','tester','manager','devops'])[(random()*7+1)::INT]
FROM projects p
JOIN employees e ON e.company_id = p.company_id
WHERE random() > 0.55
LIMIT 500;

CREATE TABLE tasks (
    id SERIAL PRIMARY KEY,
    project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    parent_task_id INT REFERENCES tasks(id),
    title VARCHAR(200) NOT NULL,
    description TEXT,
    assignee_id INT REFERENCES employees(id),
    status VARCHAR(20) CHECK (status IN ('backlog','todo','in_progress','review','done','cancelled')) DEFAULT 'todo',
    priority VARCHAR(10) CHECK (priority IN ('low','medium','high','critical')) DEFAULT 'medium',
    estimated_hours NUMERIC(6,2),
    actual_hours NUMERIC(6,2) DEFAULT 0,
    story_points INT CHECK (story_points IN (1,2,3,5,8,13,21)),
    due_date DATE,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_tasks_project ON tasks(project_id);
CREATE INDEX idx_tasks_assignee ON tasks(assignee_id);
CREATE INDEX idx_tasks_status ON tasks(status);

DO $$
DECLARE
    tnames TEXT[] := ARRAY[
        'Setup CI/CD pipeline','Write unit tests for auth module','Design database schema',
        'Implement REST API endpoints','Create UI wireframes and mockups','Conduct code review',
        'Deploy to staging environment','Performance load testing','Security vulnerability scan',
        'Write technical documentation','Fix login flow bug','Integrate Stripe payment API',
        'Data migration from legacy system','Setup Datadog monitoring','User acceptance testing',
        'Sprint planning session','Sprint retrospective','Product demo preparation',
        'Database query optimization','Implement feature flags','Setup error tracking',
        'API rate limiting implementation','OAuth2 integration','Refactor legacy code',
        'A/B test implementation','SEO optimization','Accessibility audit',
        'Create onboarding flow','Build admin dashboard','Cache layer implementation'
    ];
    statuses TEXT[] := ARRAY['backlog','todo','todo','in_progress','in_progress','review','done','done','done','cancelled'];
    priorities TEXT[] := ARRAY['low','medium','medium','medium','high','high','critical'];
    sp INT[] := ARRAY[1,2,3,3,5,5,8,13];
    v_project_id INT;
    v_company_id INT;
    v_assignee_id INT;
    i INT;
    st TEXT;
    done_at TIMESTAMP;
BEGIN
    FOR i IN 1..1500 LOOP
        SELECT p.id, p.company_id INTO v_project_id, v_company_id
        FROM projects p ORDER BY random() LIMIT 1;

        SELECT id INTO v_assignee_id FROM employees
        WHERE company_id = v_company_id ORDER BY random() LIMIT 1;

        st := statuses[(random()*9+1)::INT];
        done_at := CASE WHEN st = 'done'
                        THEN NOW() - (random()*120)::INT * INTERVAL '1 day'
                        ELSE NULL END;

        INSERT INTO tasks (project_id, title, assignee_id, status, priority,
                           estimated_hours, actual_hours, story_points, due_date, completed_at)
        VALUES (
            v_project_id,
            tnames[(random()*29+1)::INT]||' ['||i||']',
            v_assignee_id,
            st,
            priorities[(random()*6+1)::INT],
            (random()*40+1)::NUMERIC(6,2),
            CASE WHEN st IN ('in_progress','review','done') THEN (random()*38)::NUMERIC(6,2) ELSE 0 END,
            sp[(random()*7+1)::INT],
            CURRENT_DATE + (random()*90-45)::INT,
            done_at
        );
    END LOOP;
END $$;

CREATE TABLE time_logs (
    id SERIAL PRIMARY KEY,
    task_id INT NOT NULL REFERENCES tasks(id),
    employee_id INT NOT NULL REFERENCES employees(id),
    logged_at DATE NOT NULL,
    hours NUMERIC(5,2) NOT NULL CHECK (hours > 0 AND hours <= 16),
    description TEXT
);

INSERT INTO time_logs (task_id, employee_id, logged_at, hours, description)
SELECT
    t.id,
    COALESCE(t.assignee_id,
        (SELECT id FROM employees ORDER BY random() LIMIT 1)),
    CURRENT_DATE - (random()*90)::INT,
    (random()*7+0.5)::NUMERIC(5,2),
    (ARRAY['Implementation work','Testing and QA','Code review session',
            'Technical documentation','Debugging session','Team standup & planning',
            'Pair programming','Research and spikes'])[(random()*7+1)::INT]
FROM tasks t
WHERE t.status IN ('in_progress','review','done')
  AND random() > 0.2;

-- Multiple time log entries for same task (realistic)
INSERT INTO time_logs (task_id, employee_id, logged_at, hours, description)
SELECT
    t.id,
    COALESCE(t.assignee_id, (SELECT id FROM employees ORDER BY random() LIMIT 1)),
    CURRENT_DATE - (random()*60)::INT,
    (random()*5+0.5)::NUMERIC(5,2),
    'Additional work session'
FROM tasks t
WHERE t.status = 'done' AND random() > 0.5;

UPDATE tasks t
SET actual_hours = COALESCE(
    (SELECT SUM(hours) FROM time_logs tl WHERE tl.task_id = t.id), 0
);

-- ============================================================
-- SUPPORT TICKETS
-- ============================================================

CREATE TABLE ticket_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(80) NOT NULL,
    sla_hours INT DEFAULT 24,
    escalation_hours INT DEFAULT 48
);

INSERT INTO ticket_categories (name, sla_hours, escalation_hours) VALUES
('Billing & Payments',4,8),
('Technical Support',8,24),
('Account Management',2,6),
('Feature Request',72,168),
('Bug Report',24,48),
('General Inquiry',48,96),
('Shipping & Delivery',12,24),
('Returns & Refunds',8,16);

CREATE TABLE support_tickets (
    id SERIAL PRIMARY KEY,
    ticket_number VARCHAR(20) UNIQUE NOT NULL,
    customer_id INT REFERENCES customers(id),
    category_id INT REFERENCES ticket_categories(id),
    assigned_to INT REFERENCES employees(id),
    subject VARCHAR(200) NOT NULL,
    description TEXT,
    status VARCHAR(20) CHECK (status IN ('open','in_progress','waiting','resolved','closed')) DEFAULT 'open',
    priority VARCHAR(10) CHECK (priority IN ('low','medium','high','critical')) DEFAULT 'medium',
    satisfaction_score INT CHECK (satisfaction_score BETWEEN 1 AND 5),
    resolution_notes TEXT,
    opened_at TIMESTAMP DEFAULT NOW(),
    first_response_at TIMESTAMP,
    resolved_at TIMESTAMP,
    closed_at TIMESTAMP
);

CREATE INDEX idx_tickets_customer ON support_tickets(customer_id);
CREATE INDEX idx_tickets_status ON support_tickets(status);
CREATE INDEX idx_tickets_assigned ON support_tickets(assigned_to);

DO $$
DECLARE
    subjects TEXT[] := ARRAY[
        'Cannot login to account','Payment was not processed','Wrong item delivered',
        'Request for full refund','Product arrived damaged','Cancel subscription please',
        'Need to update billing address','Error during checkout process','Order shows missing',
        'Product quality does not match description','Account access suddenly blocked',
        'Invoice not received after purchase','Promo code not applying correctly',
        'Need return shipping label','App crashes on startup','Slow page loading issue',
        'Duplicate charge on my card','Tracking number not working','Password reset not working',
        'Cannot update my profile'
    ];
    statuses TEXT[] := ARRAY['open','in_progress','in_progress','waiting','resolved','resolved','closed','closed'];
    priorities TEXT[] := ARRAY['low','medium','medium','medium','high','high','critical'];
    v_customer_id INT;
    v_agent_id INT;
    v_cat_id INT;
    v_status TEXT;
    v_open_at TIMESTAMP;
    i INT;
BEGIN
    FOR i IN 1..800 LOOP
        SELECT id INTO v_customer_id FROM customers ORDER BY random() LIMIT 1;
        SELECT id INTO v_agent_id FROM employees ORDER BY random() LIMIT 1;
        v_cat_id := (random()*7+1)::INT;
        v_status := statuses[(random()*7+1)::INT];
        v_open_at := NOW() - (random()*180)::INT * INTERVAL '1 day';

        INSERT INTO support_tickets (ticket_number, customer_id, category_id, assigned_to,
            subject, status, priority, satisfaction_score,
            opened_at, first_response_at, resolved_at, closed_at)
        VALUES (
            'TKT-'||LPAD(i::TEXT,6,'0'),
            v_customer_id, v_cat_id, v_agent_id,
            subjects[(random()*19+1)::INT],
            v_status,
            priorities[(random()*6+1)::INT],
            CASE WHEN v_status IN ('resolved','closed') AND random() > 0.3
                 THEN (random()*4+1)::INT ELSE NULL END,
            v_open_at,
            CASE WHEN v_status != 'open' THEN v_open_at + (random()*8+0.5)::NUMERIC * INTERVAL '1 hour' ELSE NULL END,
            CASE WHEN v_status IN ('resolved','closed') THEN v_open_at + (random()*5+1)::INT * INTERVAL '1 day' ELSE NULL END,
            CASE WHEN v_status = 'closed' THEN v_open_at + (random()*7+3)::INT * INTERVAL '1 day' ELSE NULL END
        );
    END LOOP;
END $$;

CREATE TABLE ticket_messages (
    id SERIAL PRIMARY KEY,
    ticket_id INT NOT NULL REFERENCES support_tickets(id) ON DELETE CASCADE,
    sender_type VARCHAR(10) CHECK (sender_type IN ('customer','agent','system')),
    sender_id INT,
    message TEXT NOT NULL,
    is_internal BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_ticket_messages_ticket ON ticket_messages(ticket_id);

-- Initial customer message
INSERT INTO ticket_messages (ticket_id, sender_type, message, sent_at)
SELECT t.id, 'customer',
    'Hello, I am contacting you about: '||t.subject||
    '. Please help me resolve this issue as soon as possible. Thank you.',
    t.opened_at
FROM support_tickets t;

-- First agent response
INSERT INTO ticket_messages (ticket_id, sender_type, message, sent_at)
SELECT t.id, 'agent',
    'Thank you for reaching out! I have received your request regarding "'||t.subject||
    '". I am looking into this now and will get back to you within our SLA window. '||
    'Your ticket number is '||t.ticket_number||'.',
    t.first_response_at
FROM support_tickets t WHERE t.first_response_at IS NOT NULL;

-- Follow-up messages
INSERT INTO ticket_messages (ticket_id, sender_type, message, sent_at)
SELECT t.id, 'customer',
    'Hi, just following up on my previous message. Any updates on this matter?',
    t.opened_at + INTERVAL '2 days'
FROM support_tickets t WHERE t.status IN ('in_progress','waiting','resolved','closed') AND random() > 0.45;

INSERT INTO ticket_messages (ticket_id, sender_type, message, sent_at)
SELECT t.id, 'agent',
    'We have been working on your issue and have made progress. '||
    'We expect to have a resolution for you very soon. We appreciate your patience.',
    t.opened_at + INTERVAL '3 days'
FROM support_tickets t WHERE t.status IN ('resolved','closed') AND random() > 0.5;

-- Resolution message
INSERT INTO ticket_messages (ticket_id, sender_type, message, sent_at)
SELECT t.id, 'agent',
    'Great news! We have resolved your issue. '||
    'Please let us know if you need any further assistance. We are happy to help!',
    t.resolved_at
FROM support_tickets t WHERE t.resolved_at IS NOT NULL;

-- ============================================================
-- PRODUCT REVIEWS
-- ============================================================

CREATE TABLE product_reviews (
    id SERIAL PRIMARY KEY,
    product_id INT NOT NULL REFERENCES products(id),
    customer_id INT NOT NULL REFERENCES customers(id),
    order_id INT REFERENCES orders(id),
    rating INT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    title VARCHAR(150),
    body TEXT,
    is_verified_purchase BOOLEAN DEFAULT FALSE,
    helpful_votes INT DEFAULT 0,
    status VARCHAR(20) CHECK (status IN ('pending','approved','rejected')) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_reviews_product ON product_reviews(product_id);
CREATE INDEX idx_reviews_customer ON product_reviews(customer_id);

DO $$
DECLARE
    pos_titles TEXT[] := ARRAY['Absolutely love it!','Best purchase ever','Exceeded expectations',
        'Highly recommend','Amazing quality','Great value for money','Perfect!','5 stars'];
    neg_titles TEXT[] := ARRAY['Disappointed','Not worth the price','Poor quality',
        'Misleading description','Would not buy again'];
    neu_titles TEXT[] := ARRAY['Decent product','As described','Good but...','Average'];
    pos_bodies TEXT[] := ARRAY[
        'Really happy with this purchase. Works perfectly out of the box.',
        'The quality exceeded my expectations. Delivery was fast too.',
        'Would definitely buy again! Has been working great for weeks.',
        'Exactly as described, no surprises. Good value for money.',
        'Excellent build quality and packaging was very professional.'
    ];
    neg_bodies TEXT[] := ARRAY[
        'Stopped working after two weeks. Very disappointed with the quality.',
        'Not what I expected based on the product description. Misleading.',
        'Poor materials, feels very cheap for the price.',
        'Arrived damaged and customer service was not helpful.'
    ];
    v_product_id INT;
    v_customer_id INT;
    v_rating INT;
    i INT;
BEGIN
    FOR i IN 1..1000 LOOP
        SELECT id INTO v_product_id FROM products ORDER BY random() LIMIT 1;
        SELECT id INTO v_customer_id FROM customers ORDER BY random() LIMIT 1;
        v_rating := CASE
            WHEN random() > 0.75 THEN 5
            WHEN random() > 0.55 THEN 4
            WHEN random() > 0.3  THEN 3
            WHEN random() > 0.15 THEN 2
            ELSE 1
        END;
        INSERT INTO product_reviews (product_id, customer_id, rating, title, body,
                                     is_verified_purchase, helpful_votes, status)
        VALUES (
            v_product_id, v_customer_id, v_rating,
            CASE WHEN v_rating >= 4 THEN pos_titles[(random()*7+1)::INT]
                 WHEN v_rating = 3  THEN neu_titles[(random()*3+1)::INT]
                 ELSE neg_titles[(random()*4+1)::INT] END,
            CASE WHEN v_rating >= 4 THEN pos_bodies[(random()*4+1)::INT]
                 ELSE neg_bodies[(random()*3+1)::INT] END,
            CASE WHEN random() > 0.35 THEN TRUE ELSE FALSE END,
            (random()*80)::INT,
            (ARRAY['approved','approved','approved','approved','pending','rejected'])[(random()*5+1)::INT]
        );
    END LOOP;
END $$;

-- ============================================================
-- ANALYTICS EVENTS
-- ============================================================

CREATE TABLE event_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(80) UNIQUE NOT NULL,
    category VARCHAR(50)
);

INSERT INTO event_types (name, category) VALUES
('page_view','engagement'),('product_view','engagement'),
('add_to_cart','conversion'),('checkout_started','conversion'),
('order_placed','conversion'),('search','engagement'),
('signup','acquisition'),('login','engagement'),
('review_submitted','engagement'),('wishlist_add','engagement'),
('coupon_applied','conversion'),('checkout_completed','conversion'),
('product_compare','engagement'),('filter_used','engagement'),
('share_product','engagement'),('email_subscribe','acquisition'),
('push_notification_click','engagement'),('live_chat_started','engagement');

CREATE TABLE analytics_events (
    id BIGSERIAL PRIMARY KEY,
    event_type_id INT NOT NULL REFERENCES event_types(id),
    customer_id INT REFERENCES customers(id),
    session_id UUID DEFAULT gen_random_uuid(),
    page_url TEXT,
    referrer TEXT,
    device_type VARCHAR(20) CHECK (device_type IN ('desktop','mobile','tablet')),
    browser VARCHAR(50),
    os_name VARCHAR(30),
    country_code CHAR(2) REFERENCES countries(code),
    metadata JSONB,
    occurred_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_events_customer ON analytics_events(customer_id);
CREATE INDEX idx_events_occurred ON analytics_events(occurred_at);
CREATE INDEX idx_events_type ON analytics_events(event_type_id);

DO $$
DECLARE
    devices TEXT[] := ARRAY['desktop','desktop','desktop','mobile','mobile','tablet'];
    browsers TEXT[] := ARRAY['Chrome','Chrome','Safari','Firefox','Edge','Opera','Samsung Browser'];
    os_names TEXT[] := ARRAY['Windows','macOS','iOS','Android','Linux'];
    country_codes TEXT[] := ARRAY['US','US','US','GB','DE','CA','AU','FR','IN','SG','JP','NL','BR'];
    pages TEXT[] := ARRAY['/home','/products','/products/electronics','/product/detail',
                           '/cart','/checkout','/account','/search','/about','/blog',
                           '/deals','/new-arrivals','/wishlist'];
    referrers TEXT[] := ARRAY['https://google.com','https://facebook.com','https://instagram.com',
                               'https://twitter.com','direct','https://bing.com','email_campaign',NULL];
    v_customer_id INT;
    i INT;
BEGIN
    FOR i IN 1..8000 LOOP
        IF random() > 0.2 THEN
            SELECT id INTO v_customer_id FROM customers ORDER BY random() LIMIT 1;
        ELSE
            v_customer_id := NULL;
        END IF;

        INSERT INTO analytics_events (event_type_id, customer_id, page_url, referrer,
            device_type, browser, os_name, country_code, metadata, occurred_at)
        VALUES (
            (random()*17+1)::INT,
            v_customer_id,
            pages[(random()*12+1)::INT],
            referrers[(random()*7+1)::INT],
            devices[(random()*5+1)::INT],
            browsers[(random()*6+1)::INT],
            os_names[(random()*4+1)::INT],
            country_codes[(random()*12+1)::INT],
            jsonb_build_object(
                'duration_ms', (random()*8000+100)::INT,
                'scroll_depth_pct', (random()*100)::INT,
                'clicks', (random()*20)::INT
            ),
            NOW() - (random()*500)::INT * INTERVAL '1 day'
                   - (random()*86400)::INT * INTERVAL '1 second'
        );
    END LOOP;
END $$;

-- ============================================================
-- FINALIZE: Update derived columns
-- ============================================================

-- Recalculate customer lifetime values from real orders
UPDATE customers c
SET lifetime_value = COALESCE((
    SELECT SUM(o.total_amount)
    FROM orders o
    WHERE o.customer_id = c.id
      AND o.status NOT IN ('cancelled','returned')
), 0),
updated_at = NOW();

-- Update loyalty tiers based on actual LTV
UPDATE customers SET loyalty_tier = 'platinum' WHERE lifetime_value >= 5000;
UPDATE customers SET loyalty_tier = 'gold'     WHERE lifetime_value >= 2000 AND lifetime_value < 5000;
UPDATE customers SET loyalty_tier = 'silver'   WHERE lifetime_value >= 500  AND lifetime_value < 2000;
UPDATE customers SET loyalty_tier = 'bronze'   WHERE lifetime_value < 500;

-- ============================================================
-- VIEWS
-- ============================================================

CREATE OR REPLACE VIEW vw_order_summary AS
SELECT
    o.id,
    o.order_number,
    o.status,
    COALESCE(c.first_name||' '||c.last_name, c.company_name) AS customer_name,
    c.email AS customer_email,
    c.loyalty_tier,
    co.name AS country,
    o.subtotal,
    o.discount_amount,
    o.tax_amount,
    o.shipping_amount,
    o.total_amount,
    COUNT(oi.id) AS item_count,
    SUM(oi.quantity) AS total_units,
    o.placed_at,
    o.shipped_at,
    o.delivered_at
FROM orders o
JOIN customers c ON c.id = o.customer_id
LEFT JOIN countries co ON co.code = c.country_code
JOIN order_items oi ON oi.order_id = o.id
GROUP BY o.id, c.id, co.name;

CREATE OR REPLACE VIEW vw_product_performance AS
SELECT
    p.id,
    p.sku,
    p.name AS product_name,
    pc.name AS category,
    s.name AS supplier,
    p.cost_price,
    p.list_price,
    ROUND(p.list_price - p.cost_price, 2) AS gross_profit,
    ROUND(((p.list_price - p.cost_price) / p.list_price * 100)::NUMERIC, 2) AS margin_pct,
    COALESCE(SUM(oi.quantity), 0) AS total_units_sold,
    COALESCE(SUM(oi.line_total), 0) AS total_revenue,
    COALESCE(SUM(i_agg.quantity_on_hand), 0) AS total_stock,
    ROUND(COALESCE(AVG(pr.rating), 0)::NUMERIC, 2) AS avg_rating,
    COUNT(DISTINCT pr.id) AS review_count
FROM products p
LEFT JOIN product_categories pc ON pc.id = p.category_id
LEFT JOIN suppliers s ON s.id = p.supplier_id
LEFT JOIN order_items oi ON oi.product_id = p.id
LEFT JOIN (
    SELECT product_id, SUM(quantity_on_hand) AS quantity_on_hand
    FROM inventory GROUP BY product_id
) i_agg ON i_agg.product_id = p.id
LEFT JOIN product_reviews pr ON pr.product_id = p.id AND pr.status = 'approved'
GROUP BY p.id, pc.name, s.name;

CREATE OR REPLACE VIEW vw_employee_summary AS
SELECT
    e.id,
    e.first_name,
    e.last_name,
    e.email,
    e.job_title,
    e.employment_type,
    e.salary,
    e.hire_date,
    EXTRACT(YEAR FROM AGE(CURRENT_DATE, e.hire_date)) AS years_at_company,
    comp.name AS company,
    d.name AS department,
    COALESCE(m.first_name||' '||m.last_name, 'No Manager') AS manager_name,
    e.is_active,
    ROUND(COALESCE(AVG(pr.overall_rating), 0)::NUMERIC, 2) AS avg_performance_rating,
    COUNT(DISTINCT lr.id) AS total_leave_requests
FROM employees e
JOIN companies comp ON comp.id = e.company_id
LEFT JOIN departments d ON d.id = e.department_id
LEFT JOIN employees m ON m.id = e.manager_id
LEFT JOIN performance_reviews pr ON pr.employee_id = e.id
LEFT JOIN leave_requests lr ON lr.employee_id = e.id
GROUP BY e.id, comp.name, d.name, m.first_name, m.last_name;

CREATE OR REPLACE VIEW vw_support_metrics AS
SELECT
    DATE_TRUNC('week', t.opened_at)::DATE AS week_start,
    tc.name AS category,
    COUNT(*) AS total_tickets,
    COUNT(*) FILTER (WHERE t.status = 'closed')   AS closed_tickets,
    COUNT(*) FILTER (WHERE t.status = 'open')     AS open_tickets,
    COUNT(*) FILTER (WHERE t.priority = 'critical') AS critical_tickets,
    ROUND(AVG(EXTRACT(EPOCH FROM (t.resolved_at - t.opened_at))/3600)
          FILTER (WHERE t.resolved_at IS NOT NULL)::NUMERIC, 2) AS avg_resolution_hours,
    ROUND(AVG(t.satisfaction_score)
          FILTER (WHERE t.satisfaction_score IS NOT NULL)::NUMERIC, 2) AS avg_csat
FROM support_tickets t
LEFT JOIN ticket_categories tc ON tc.id = t.category_id
GROUP BY 1, 2
ORDER BY 1 DESC, 2;

CREATE OR REPLACE VIEW vw_monthly_revenue AS
SELECT
    DATE_TRUNC('month', o.placed_at)::DATE AS month,
    COUNT(DISTINCT o.id) AS order_count,
    COUNT(DISTINCT o.customer_id) AS unique_customers,
    ROUND(SUM(o.total_amount)::NUMERIC, 2) AS gross_revenue,
    ROUND(SUM(o.discount_amount)::NUMERIC, 2) AS total_discounts,
    ROUND(SUM(o.tax_amount)::NUMERIC, 2) AS total_tax,
    ROUND(AVG(o.total_amount)::NUMERIC, 2) AS avg_order_value,
    COUNT(*) FILTER (WHERE o.status = 'cancelled') AS cancelled_orders,
    COUNT(*) FILTER (WHERE o.status = 'returned') AS returned_orders
FROM orders o
GROUP BY 1
ORDER BY 1;

CREATE OR REPLACE VIEW vw_inventory_status AS
SELECT
    p.id AS product_id,
    p.sku,
    p.name AS product_name,
    pc.name AS category,
    w.name AS warehouse,
    w.city,
    i.quantity_on_hand,
    i.quantity_reserved,
    i.quantity_on_hand - i.quantity_reserved AS available_qty,
    i.reorder_point,
    CASE
        WHEN i.quantity_on_hand = 0 THEN 'out_of_stock'
        WHEN i.quantity_on_hand <= i.reorder_point THEN 'low_stock'
        ELSE 'in_stock'
    END AS stock_status,
    i.last_counted_at
FROM inventory i
JOIN products p ON p.id = i.product_id
JOIN warehouses w ON w.id = i.warehouse_id
JOIN product_categories pc ON pc.id = p.category_id;

-- ============================================================
-- SUMMARY
-- ============================================================
DO $$
DECLARE
    tbl RECORD;
    total_rows BIGINT := 0;
    cnt BIGINT;
BEGIN
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'InsightAI Demo DB - Seed Complete!';
    RAISE NOTICE '==============================================';
    FOR tbl IN
        SELECT tablename FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY tablename
    LOOP
        EXECUTE 'SELECT COUNT(*) FROM '||tbl.tablename INTO cnt;
        total_rows := total_rows + cnt;
        RAISE NOTICE '  %-35s %s rows', tbl.tablename, cnt;
    END LOOP;
    RAISE NOTICE '----------------------------------------------';
    RAISE NOTICE '  TOTAL ROWS: %', total_rows;
    RAISE NOTICE '==============================================';
END $$;
