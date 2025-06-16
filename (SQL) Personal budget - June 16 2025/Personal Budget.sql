/*
SELECT current_user, now();

DROP TABLE transactions;

CREATE TABLE transactions(
	uuid SERIAL PRIMARY KEY,
	date DATE NOT NULL,
	account VARCHAR(255),
	vendor VARCHAR(255),
	category VARCHAR(255),
	amount DECIMAL(10,2),
	spent_on_others DECIMAL(10,2),
	month VARCHAR(15),
	year SMALLINT NOT NULL CHECK (year >= 2000)
);
*/

SELECT * FROM transactions;

SELECT category, COUNT(*), SUM(ABS(amount))
FROM transactions
GROUP BY category;

/* Average spending for 2024 */
SELECT category, ROUND((SUM(ABS(amount))/12),-1)
FROM transactions
WHERE EXTRACT(YEAR FROM date) = 2024
AND amount < 0
GROUP BY category
ORDER BY (SUM(ABS(amount))/12) DESC;

/* Average spending 2024 and 2022 */
SELECT
	spend2024.category,
	ROUND((SUM(ABS(spend2024.amount))/12),-1) AS total_spend_2024,
	ROUND((SUM(ABS(spend2022.amount))/12),-1) AS total_spend_2024
FROM transactions AS spend2024
LEFT JOIN transactions AS spend2022
	ON spend2024.category = spend2022.category
	AND EXTRACT(YEAR FROM spend2022.date) = 2022
	AND spend2022.category != 'Income'
WHERE EXTRACT(YEAR FROM spend2024.date) = 2024 
AND spend2024.category != 'Income'
GROUP BY spend2024.category
ORDER BY spend2024.category;

/* Monthly spending 2024 and 2022 (corrected) */
SELECT 
    spend2024.category,
    ROUND((SUM(ABS(spend2024.amount)) / 12), -1) AS avg_spend_2024,
    ROUND((SUM(ABS(spend2022.amount)) / 12), -1) AS avg_spend_2022
FROM 
    (SELECT category, SUM(amount) AS amount FROM transactions 
     WHERE EXTRACT(YEAR FROM date) = 2024 
     AND category != 'Income'
     GROUP BY category) AS spend2024
LEFT JOIN 
    (SELECT category, SUM(amount) AS amount FROM transactions 
     WHERE EXTRACT(YEAR FROM date) = 2022 
     AND category != 'Income'
     GROUP BY category) AS spend2022
ON spend2024.category = spend2022.category
GROUP BY spend2024.category
ORDER BY avg_spend_2024 DESC;

/* Average spending by month by year */
CREATE OR REPLACE VIEW VIEW_transactions_expense_summary AS
SELECT 
    category,
    ROUND(SUM(CASE WHEN EXTRACT(MONTH FROM date) = 1 THEN ABS(amount) END), 2) AS jan,
    ROUND(SUM(CASE WHEN EXTRACT(MONTH FROM date) = 2 THEN ABS(amount) END), 2) AS feb,
    ROUND(SUM(CASE WHEN EXTRACT(MONTH FROM date) = 3 THEN ABS(amount) END), 2) AS mar,
    ROUND(SUM(CASE WHEN EXTRACT(MONTH FROM date) = 4 THEN ABS(amount) END), 2) AS apr,
    ROUND(SUM(CASE WHEN EXTRACT(MONTH FROM date) = 5 THEN ABS(amount) END), 2) AS may,
    ROUND(SUM(CASE WHEN EXTRACT(MONTH FROM date) = 6 THEN ABS(amount) END), 2) AS jun,
    ROUND(SUM(CASE WHEN EXTRACT(MONTH FROM date) = 7 THEN ABS(amount) END), 2) AS jul,
    ROUND(SUM(CASE WHEN EXTRACT(MONTH FROM date) = 8 THEN ABS(amount) END), 2) AS aug,
    ROUND(SUM(CASE WHEN EXTRACT(MONTH FROM date) = 9 THEN ABS(amount) END), 2) AS sep,
    ROUND(SUM(CASE WHEN EXTRACT(MONTH FROM date) = 10 THEN ABS(amount) END), 2) AS oct,
    ROUND(SUM(CASE WHEN EXTRACT(MONTH FROM date) = 11 THEN ABS(amount) END), 2) AS nov,
    ROUND(SUM(CASE WHEN EXTRACT(MONTH FROM date) = 12 THEN ABS(amount) END), 2) AS dec,
	ROUND(SUM(ABS(amount)), 2) AS year
FROM transactions
WHERE year = 2024 AND category != 'Income'
GROUP BY category
ORDER BY year DESC;