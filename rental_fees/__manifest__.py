{
    "name": "rental_fees",
    "category": "Business",
    "summary": "Commown module to compute fees to be paid to its device suppliers",
    "version": "12.0.1.0.0",
    "description": """
        Commown module to compute fees to be paid to its device suppliers.
    """,
    "author": "Commown SCIC",
    "license": "AGPL-3",
    "website": "https://commown.coop",
    "depends": [
        "product_rental",
        "purchase",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/rental_fees.xml",
    ],
}
