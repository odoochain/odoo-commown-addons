# Copyright (C) 2022: Commown (https://commown.coop)
# @author: Florent Cayré
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Contract emails",
    "category": "",
    "version": "12.0.1.0.1",
    "author": "Commown SCIC",
    "license": "AGPL-3",
    "website": "https://commown.coop",
    "depends": [
        "contract",
        "mail",
    ],
    "data": [
        "data/cron.xml",
        "data/mail_channel.xml",
        "security/ir.model.access.csv",
        "views/contract.xml",
    ],
    "installable": True,
    "application": False,
}
