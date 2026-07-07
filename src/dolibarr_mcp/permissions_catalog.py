"""Dolibarr core permission catalog.

Auto-generated from the Dolibarr core module descriptors by
``scripts/extract_permissions.py``. Do not edit by hand: regenerate it
when targeting a new Dolibarr version.

Keys are the module ``rights_class`` (the first segment of a permission
path, e.g. ``facture``). Each permission maps its full dotted path
(``<rights_class>.<perms>[.<subperms>]``) to its upstream English label.
"""

from __future__ import annotations

CORE_PERMISSIONS: dict[str, dict] = {
    'accounting': {
        'module': 'Accounting',
        'permissions': {
            'accounting.bind.write': 'Bind products and invoices with accounting accounts',
            'accounting.chartofaccount': 'Manage chart of accounts, setup of accountancy',
            'accounting.comptarapport.lire': 'Report and export reports (turnover, balance, journals, ledger)',
            'accounting.fiscalyear.write': 'Manage fiscal periods, validate movements and close periods',
            'accounting.mouvements.creer': 'Write/Edit operations in Ledger',
            'accounting.mouvements.export': 'Export operations of the Ledger',
            'accounting.mouvements.lire': 'Read operations in Ledger',
            'accounting.mouvements.supprimer': 'Delete operations in Ledger',
            'accounting.mouvements.supprimer_tous': 'Delete all operations by year and journal in Ledger',
        },
    },
    'adherent': {
        'module': 'Adherent',
        'permissions': {
            'adherent.configurer': 'Setup types of membership',
            'adherent.cotisation.creer': 'Create/modify/remove membership fees',
            'adherent.cotisation.lire': 'Read membership fees',
            'adherent.creer': 'Create/modify members (need also user module permissions if member linked to a user)',
            'adherent.export': 'Export members',
            'adherent.lire': "Read members\\' card",
            'adherent.supprimer': 'Remove members',
        },
    },
    'agenda': {
        'module': 'Agenda',
        'permissions': {
            'agenda.allactions.create': 'Create/modify actions/tasks of others',
            'agenda.allactions.delete': 'Delete actions/tasks of others',
            'agenda.allactions.read': 'Read actions/tasks of others',
            'agenda.export': 'Export actions/tasks of others',
            'agenda.myactions.create': 'Create/modify actions/tasks linked to his account',
            'agenda.myactions.delete': 'Delete actions/tasks linked to his account',
            'agenda.myactions.read': 'Read actions/tasks linked to his account',
        },
    },
    'ai': {
        'module': 'Ai',
        'permissions': {
            'ai.assistant.use': 'Use the AI Assistant',
        },
    },
    'api': {
        'module': 'Api',
        'permissions': {
            'api.apikey.generate': 'Generate/modify users API key',
        },
    },
    'asset': {
        'module': 'Asset',
        'permissions': {
            'asset.delete': 'Delete assets',
            'asset.model_advance.delete': 'Delete asset models',
            'asset.model_advance.read': 'Read asset models',
            'asset.model_advance.write': 'Create/Update asset models',
            'asset.read': 'Read assets',
            'asset.write': 'Create/Update assets',
        },
    },
    'banque': {
        'module': 'Banque',
        'permissions': {
            'banque.cheque': 'Gerer les envois de cheques',
            'banque.configurer': 'Configurer les comptes bancaires (creer, gerer categories)',
            'banque.consolidate': 'Rapprocher les ecritures bancaires',
            'banque.export': 'Exporter transactions et releves',
            'banque.lire': 'Read bank account and transactions',
            'banque.modifier': 'Creer/modifier montant/supprimer ecriture bancaire',
            'banque.transfer': 'Virements entre comptes',
        },
    },
    'barcode': {
        'module': 'Barcode',
        'permissions': {
            'barcode.creer_advance': 'Create/modify barcodes',
            'barcode.lire_advance': 'Read barcodes',
            'barcode.read': 'Generate PDF sheets of barcodes',
        },
    },
    'blockedlog': {
        'module': 'BlockedLog',
        'permissions': {
            'blockedlog.read': 'Read archived events and fingerprints',
        },
    },
    'bom': {
        'module': 'Bom',
        'permissions': {
            'bom.delete': 'Delete bom of Bom',
            'bom.read': 'Read bom of Bom',
            'bom.write': 'Create/Update bom of Bom',
        },
    },
    'bookcal': {
        'module': 'BookCal',
        'permissions': {
            'bookcal.availabilities.delete': 'Delete objects of BookCal',
            'bookcal.availabilities.read': 'Read objects of BookCal',
            'bookcal.availabilities.write': 'Create/Update objects of BookCal',
            'bookcal.calendar.delete': 'Delete Calendar object of BookCal',
            'bookcal.calendar.read': 'Read Calendar object of BookCal',
            'bookcal.calendar.write': 'Create/Update Calendar object of BookCal',
        },
    },
    'bookmark': {
        'module': 'Bookmark',
        'permissions': {
            'bookmark.creer': 'Creer/modifier les bookmarks',
            'bookmark.lire': 'Lire les bookmarks',
            'bookmark.supprimer': 'Supprimer les bookmarks',
        },
    },
    'categorie': {
        'module': 'Categorie',
        'permissions': {
            'categorie.creer': 'Creer/modifier les categories',
            'categorie.lire': 'Lire les categories',
            'categorie.supprimer': 'Supprimer les categories',
        },
    },
    'collab': {
        'module': 'Collab',
        'permissions': {
            'collab.delete': 'Delete website content',
            'collab.read': 'Read website content',
            'collab.write': 'Create/modify website content',
        },
    },
    'commande': {
        'module': 'Commande',
        'permissions': {
            'commande.commande.export': 'Export sales orders and attributes',
            'commande.creer': 'Creeat/modify sales orders',
            'commande.lire': 'Read sales orders',
            'commande.order_advance.annuler': 'Cancel sale orders',
            'commande.order_advance.close': 'Close sale orders',
            'commande.order_advance.generetedoc': 'Generate the documents sales orders',
            'commande.order_advance.send': 'Send sales orders by email',
            'commande.order_advance.validate': 'Validate sales orders',
            'commande.supprimer': 'Delete sales orders',
        },
    },
    'compta': {
        'module': 'Comptabilite',
        'permissions': {
            'compta.resultat.lire': 'Lire CA, bilans, resultats',
        },
    },
    'contrat': {
        'module': 'Contrat',
        'permissions': {
            'contrat.activer': "Activer un service d\\'un contrat",
            'contrat.creer': 'Creer / modifier les contrats',
            'contrat.desactiver': "Desactiver un service d\\'un contrat",
            'contrat.export': 'Export contracts',
            'contrat.lire': 'Lire les contrats',
            'contrat.supprimer': 'Supprimer un contrat',
        },
    },
    'cron': {
        'module': 'Cron',
        'permissions': {
            'cron.create': 'Create cron Jobs',
            'cron.delete': 'Delete cron Jobs',
            'cron.execute': 'Execute cron Jobs',
            'cron.read': 'Read cron jobs',
        },
    },
    'dav': {
        'module': 'Dav',
        'permissions': {
            'dav.delete': 'Delete myobject of dav',
            'dav.read': 'Read myobject of dav',
            'dav.write': 'Create/Update myobject of dav',
        },
    },
    'document': {
        'module': 'DocumentGeneration',
        'permissions': {
            'document.lire': 'Lire les documents',
            'document.supprimer': 'Supprimer les documents clients',
        },
    },
    'ecm': {
        'module': 'ECM',
        'permissions': {
            'ecm.read': 'Read or download documents',
            'ecm.setup': 'Administer directories of documents',
            'ecm.upload': 'Upload a document',
        },
    },
    'eventorganization': {
        'module': 'EventOrganization',
        'permissions': {
            'eventorganization.delete': 'Delete objects of EventOrganization',
            'eventorganization.read': 'Read objects of EventOrganization',
            'eventorganization.write': 'Create/Update objects of EventOrganization',
        },
    },
    'expedition': {
        'module': 'Expedition',
        'permissions': {
            'expedition.creer': 'Create/modify shipments',
            'expedition.delivery.creer': 'Create/modify delivery receipts',
            'expedition.delivery.lire': 'Read delivery receipts',
            'expedition.delivery.supprimer': 'Delete delivery receipts',
            'expedition.delivery_advance.validate': 'Validate delivery receipts',
            'expedition.lire': 'Read shipments',
            'expedition.shipment.export': 'Export shipments',
            'expedition.shipping_advance.send': 'Send shipments by email to customers',
            'expedition.shipping_advance.validate': 'Validate shipments',
            'expedition.supprimer': 'Delete shipments',
        },
    },
    'expensereport': {
        'module': 'ExpenseReport',
        'permissions': {
            'expensereport.approve': 'Approve expense reports',
            'expensereport.creer': 'Create/modify expense reports',
            'expensereport.export': 'Export expense reports',
            'expensereport.lire': 'Read expense reports (yours and your subordinates)',
            'expensereport.readall': 'Read expense reports of everybody',
            'expensereport.supprimer': 'Delete expense reports',
            'expensereport.to_paid': 'Pay expense reports',
            'expensereport.writeall_advance': 'Create expense reports for everybody',
        },
    },
    'export': {
        'module': 'Export',
        'permissions': {
            'export.creer': 'Creeate/modify export',
            'export.lire': 'Read exports',
        },
    },
    'facture': {
        'module': 'Facture',
        'permissions': {
            'facture.creer': 'Create and update invoices',
            'facture.facture.export': 'Export customer invoices, attributes and payments',
            'facture.invoice_advance.reopen': 'Re-open a fully paid invoice',
            'facture.invoice_advance.send': 'Send invoices by email',
            'facture.invoice_advance.unvalidate': 'Devalidate invoices',
            'facture.invoice_advance.validate': 'Validate invoices',
            'facture.lire': 'Read invoices',
            'facture.paiement': 'Issue payments on invoices',
            'facture.supprimer': 'Delete invoices',
        },
    },
    'ficheinter': {
        'module': 'Ficheinter',
        'permissions': {
            'ficheinter.creer': "Creer/modifier les fiches d\\'intervention",
            'ficheinter.export': 'Exporter les fiches interventions',
            'ficheinter.ficheinter_advance.send': "Envoyer les fiches d\\'intervention par courriel",
            'ficheinter.ficheinter_advance.unvalidate': "Dévalider les fiches d\\'intervention",
            'ficheinter.ficheinter_advance.validate': "Valider les fiches d\\'intervention ",
            'ficheinter.lire': "Lire les fiches d\\'intervention",
            'ficheinter.supprimer': "Supprimer les fiches d\\'intervention",
        },
    },
    'fournisseur': {
        'module': 'Fournisseur',
        'permissions': {
            'fournisseur.commande.approuver': 'Approuver une commande fournisseur',
            'fournisseur.commande.approve2': 'Approve supplier order (second level)',
            'fournisseur.commande.commander': 'Commander une commande fournisseur',
            'fournisseur.commande.creer': 'Creer une commande fournisseur',
            'fournisseur.commande.export': 'Exporter les commande fournisseurs, attributs',
            'fournisseur.commande.lire': 'Consulter les commandes fournisseur',
            'fournisseur.commande.receptionner': 'Receptionner une commande fournisseur',
            'fournisseur.commande.supprimer': 'Supprimer une commande fournisseur',
            'fournisseur.commande_advance.check': 'Check/Uncheck a supplier order reception',
            'fournisseur.facture.creer': 'Creer une facture fournisseur',
            'fournisseur.facture.export': 'Exporter les factures fournisseurs, attributes et reglements',
            'fournisseur.facture.lire': 'Consulter les factures fournisseur',
            'fournisseur.facture.supprimer': 'Supprimer une facture fournisseur',
            'fournisseur.lire': 'Consulter les fournisseurs',
            'fournisseur.supplier_invoice_advance.send': 'Envoyer les factures par mail',
            'fournisseur.supplier_invoice_advance.validate': 'Valider une facture fournisseur',
            'fournisseur.supplier_order_advance.validate': 'Valider une commande fournisseur',
        },
    },
    'ftp': {
        'module': 'FTP',
        'permissions': {
            'ftp.read': 'Use FTP client in read mode (browse and download only)',
            'ftp.write': 'Use FTP client in write mode (delete or upload files)',
        },
    },
    'gravatar': {
        'module': 'Gravatar',
        'permissions': {
            'gravatar.level1.level2': 'Permision label',
        },
    },
    'holiday': {
        'module': 'Holiday',
        'permissions': {
            'holiday.approve': 'Approve leave requests',
            'holiday.define_holiday': 'Setup leave requests of users (setup and update balance)',
            'holiday.delete': 'Delete leave requests',
            'holiday.read': 'Read leave requests (yours and your subordinates)',
            'holiday.readall': 'Read leave requests for everybody',
            'holiday.write': 'Create/modify leave requests',
            'holiday.writeall': 'Create/modify leave requests for everybody',
        },
    },
    'hrm': {
        'module': 'HRM',
        'permissions': {
            'hrm.all.delete': 'Delete skill/job/position',
            'hrm.all.read': 'Read skill/job/position',
            'hrm.all.write': 'Create/modify skill/job/position',
            'hrm.compare_advance.read': 'See comparison menu',
            'hrm.evaluation.delete': 'Delete evaluations',
            'hrm.evaluation.read': 'Read evaluations',
            'hrm.evaluation.readall': 'Read all evaluations',
            'hrm.evaluation.write': 'Create/modify your evaluation',
            'hrm.evaluation_advance.validate': 'Validate evaluation',
            'hrm.read_personal_information.read': 'Read personal/HR information',
            'hrm.write_personal_information.write': 'Write personal/HR information',
        },
    },
    'import': {
        'module': 'Import',
        'permissions': {
            'import.run': 'Run mass imports of external data (data load)',
        },
    },
    'intracommreport': {
        'module': 'Intracommreport',
        'permissions': {
            'intracommreport.delete': 'Delete intracomm report',
            'intracommreport.read': 'Read intracomm report',
            'intracommreport.write': 'Create/modify intracomm report',
        },
    },
    'knowledgemanagement': {
        'module': 'KnowledgeManagement',
        'permissions': {
            'knowledgemanagement.knowledgerecord.delete': 'Delete articles',
            'knowledgemanagement.knowledgerecord.read': 'Read articles',
            'knowledgemanagement.knowledgerecord.write': 'Create/Update articles',
            'knowledgemanagement.knowledgerecord_advance.validate': 'Validate articles',
        },
    },
    'loan': {
        'module': 'Loan',
        'permissions': {
            'loan.calc': 'Access loan calculator',
            'loan.delete': 'Delete loans',
            'loan.export': 'Export loans',
            'loan.read': 'Read loans',
            'loan.write': 'Create/modify loans',
        },
    },
    'mailing': {
        'module': 'Mailing',
        'permissions': {
            'mailing.creer': 'Creer/modifier les mailings (sujet, destinataires...)',
            'mailing.lire': 'Consulter les mailings',
            'mailing.mailing_advance.delete': 'Delete mailings after validation and/or sent',
            'mailing.mailing_advance.recipient': 'View recipients and info',
            'mailing.mailing_advance.send': 'Manually send mailings',
            'mailing.supprimer': 'Supprimer les mailings',
            'mailing.valider': 'Valider les mailings (permet leur envoi)',
        },
    },
    'margins': {
        'module': 'Margin',
        'permissions': {
            'margins.creer': 'Définir les marges',
            'margins.liretous': 'Visualiser les marges',
            'margins.read.all': 'Read every user margin',
        },
    },
    'modulebuilder': {
        'module': 'ModuleBuilder',
        'permissions': {
            'modulebuilder.run': 'Generate new modules',
        },
    },
    'mrp': {
        'module': 'Mrp',
        'permissions': {
            'mrp.delete': 'Delete Manufacturing Order',
            'mrp.read': 'Read Manufacturing Order',
            'mrp.write': 'Create/Update Manufacturing Order',
        },
    },
    'multicurrency': {
        'module': 'MultiCurrency',
        'permissions': {
            'multicurrency.currency.delete': 'Delete currencies and their rates',
            'multicurrency.currency.read': 'Read currencies and their rates',
            'multicurrency.currency.write': 'Create/Update currencies and their rates',
            'multicurrency.level1.level2': 'Permision label',
        },
    },
    'oauth': {
        'module': 'Oauth',
        'permissions': {
            'oauth.read': 'OauthAccess',
        },
    },
    'opensurvey': {
        'module': 'OpenSurvey',
        'permissions': {
            'opensurvey.read': 'Read surveys',
            'opensurvey.write': 'Create/modify surveys',
        },
    },
    'partnership': {
        'module': 'Partnership',
        'permissions': {
            'partnership.delete': 'Delete objects of Partnership',
            'partnership.read': 'Read objects of Partnership',
            'partnership.write': 'Create/Update objects of Partnership',
        },
    },
    'paymentbybanktransfer': {
        'module': 'PaymentByBankTransfer',
        'permissions': {
            'paymentbybanktransfer.create': 'Create/modify a bank transfer payment order',
            'paymentbybanktransfer.debit': 'Record Debits/Rejects of bank transfer payment order',
            'paymentbybanktransfer.read': 'Read bank transfer payment orders',
            'paymentbybanktransfer.send': 'Send/Transmit bank transfer payment order',
        },
    },
    'prelevement': {
        'module': 'Prelevement',
        'permissions': {
            'prelevement.bons.credit': 'Record Credits/Rejects of direct debit payment orders',
            'prelevement.bons.creer': 'Create/modify a direct debit payment order',
            'prelevement.bons.lire': 'Read direct debit payment orders',
            'prelevement.bons.send': 'Send/Transmit direct debit payment orders',
        },
    },
    'printing': {
        'module': 'Printing',
        'permissions': {
            'printing.read': 'DirectPrint',
        },
    },
    'produit': {
        'module': 'Product',
        'permissions': {
            'produit.creer': 'Create/modify products',
            'produit.export': 'Export products',
            'produit.ignore_price_min_advance': 'Ignore minimum price',
            'produit.lire': 'Read products',
            'produit.product_advance.read_prices': 'Read prices products',
            'produit.product_advance.read_supplier_prices': 'Read supplier prices',
            'produit.product_advance.write_supplier_prices': 'Write supplier prices',
            'produit.supprimer': 'Delete products',
        },
    },
    'projet': {
        'module': 'Projet',
        'permissions': {
            'projet.all.creer': 'Create/modify all projects and tasks (also private projects I am not contact for)',
            'projet.all.lire': 'Read all projects and tasks (also private projects I am not contact for)',
            'projet.all.supprimer': 'Delete all projects and tasks (also private projects I am not contact for)',
            'projet.creer': 'Create/modify projects and tasks (shared projects or projects I am contact for)',
            'projet.export': 'Export projects',
            'projet.lire': 'Read projects and tasks (shared projects or projects I am contact for)',
            'projet.supprimer': 'Delete project and tasks (shared projects or projects I am contact for)',
            'projet.time': 'Can enter time consumed on assigned tasks (timesheet)',
        },
    },
    'propale': {
        'module': 'Propale',
        'permissions': {
            'propale.creer': 'Create and update commercial proposals',
            'propale.export': 'Exporting commercial proposals and attributes',
            'propale.lire': 'Read commercial proposals',
            'propale.propal_advance.close': 'Close commercial proposals',
            'propale.propal_advance.reopen': 'Reopen commercial proposals',
            'propale.propal_advance.send': 'Send commercial proposals to customers',
            'propale.propal_advance.validate': 'Validate commercial proposals',
            'propale.supprimer': 'Delete commercial proposals',
        },
    },
    'quickmemo': {
        'module': 'QuickMemo',
        'permissions': {
            'quickmemo.memo.delete': 'Delete objects of QuickMemo',
            'quickmemo.memo.read': 'Read objects of QuickMemo',
            'quickmemo.memo.write': 'Create/Update objects of QuickMemo',
        },
    },
    'receiptprinter': {
        'module': 'ReceiptPrinter',
        'permissions': {
            'receiptprinter.read': 'ReceiptPrinter',
        },
    },
    'reception': {
        'module': 'Reception',
        'permissions': {
            'reception.creer': 'Create receptions',
            'reception.lire': 'Read receptions',
            'reception.reception.export': 'Export receptions',
            'reception.reception_advance.send': 'Send receptions to customers',
            'reception.reception_advance.validate': 'Validate receptions',
            'reception.supprimer': 'Delete receptions',
        },
    },
    'recruitment': {
        'module': 'Recruitment',
        'permissions': {
            'recruitment.recruitmentjobposition.delete': 'Delete Job positions to fill and candidatures',
            'recruitment.recruitmentjobposition.read': 'Read job positions to fill and candidatures',
            'recruitment.recruitmentjobposition.write': 'Create/Update job positions to fill and candidatures',
        },
    },
    'resource': {
        'module': 'Resource',
        'permissions': {
            'resource.delete': 'Delete resources',
            'resource.link': 'Link resources to agenda events',
            'resource.read': 'Read resources',
            'resource.write': 'Create/Modify resources',
        },
    },
    'salaries': {
        'module': 'Salaries',
        'permissions': {
            'salaries.delete': 'Delete payments of employee salary',
            'salaries.export': 'Export payments of employee salaries',
            'salaries.read': 'Read employee salaries and payments (yours only)',
            'salaries.readall': 'Read salaries and payments (of all employees)',
            'salaries.readchild': 'Read employee salaries and payments (yours and of your subordinates)',
            'salaries.write': 'Create/modify payments of empoyee salaries',
        },
    },
    'service': {
        'module': 'Service',
        'permissions': {
            'service.creer': 'Create/modify services',
            'service.export': 'Export services',
            'service.lire': 'Read services',
            'service.service_advance.read_prices': 'Read prices services',
            'service.service_advance.read_supplier_prices': 'Read supplier prices',
            'service.supprimer': 'Delete les services',
        },
    },
    'societe': {
        'module': 'Societe',
        'permissions': {
            'societe.client.readallthirdparties_advance': 'Read all third parties (without their objects) by internal users (otherwise only if commercial contact). Not effective for external users (limited to themselves).',
            'societe.client.voir': 'Read all third parties (and their objects) by internal users (otherwise only if commercial contact). Not effective for external users (limited to themselves).',
            'societe.contact.creer': 'Create and update contact',
            'societe.contact.export': 'Export contacts',
            'societe.contact.lire': 'Read contacts',
            'societe.contact.supprimer': 'Delete contacts',
            'societe.creer': 'Create and update third parties',
            'societe.export': 'Export third parties',
            'societe.lire': 'Read third parties',
            'societe.supprimer': 'Delete third parties',
            'societe.thirdparty_customer_advance.read': 'Read thirdparties customers',
            'societe.thirdparty_paymentinformation.write': 'Modify thirdparty information payment',
            'societe.thirdparty_supplier_advance.read': 'Read thirdparties suppliers',
        },
    },
    'stock': {
        'module': 'Stock',
        'permissions': {
            'stock.creer': 'Create/Modify stocks',
            'stock.inventory_advance.changePMP': 'inventoryChangePMPPermission',
            'stock.inventory_advance.delete': 'inventoryDeletePermission',
            'stock.inventory_advance.read': 'inventoryReadPermission',
            'stock.inventory_advance.validate': 'inventoryValidatePermission',
            'stock.inventory_advance.write': 'inventoryCreatePermission',
            'stock.lire': 'Read stocks',
            'stock.mouvement.creer': 'Create/modify stock movements',
            'stock.mouvement.lire': 'Read stock movements',
            'stock.supprimer': 'Delete stock',
            'stock.value_advance.read': 'Read stock value',
        },
    },
    'stocktransfer': {
        'module': 'StockTransfer',
        'permissions': {
            'stocktransfer.stocktransfer.delete': "$langs->trans('StockTransferRightDelete')",
            'stocktransfer.stocktransfer.read': "$langs->trans('StockTransferRightRead')",
            'stocktransfer.stocktransfer.write': "$langs->trans('StockTransferRightCreateUpdate')",
        },
    },
    'supplier_invoice': {
        'module': 'SupplierInvoice',
        'permissions': {
            'supplier_invoice.creer': 'Creer une facture fournisseur',
            'supplier_invoice.export': 'Exporter les factures fournisseurs, attributes et reglements',
            'supplier_invoice.lire': 'Consulter les factures fournisseur',
            'supplier_invoice.supplier_invoice_advance.send': 'Envoyer les factures par mail',
            'supplier_invoice.supplier_invoice_advance.validate': 'Valider une facture fournisseur',
            'supplier_invoice.supprimer': 'Supprimer une facture fournisseur',
        },
    },
    'supplier_order': {
        'module': 'SupplierOrder',
        'permissions': {
            'supplier_order.approuver': 'Approve purchase orders',
            'supplier_order.approve2': 'Approve supplier order (second level)',
            'supplier_order.commander': 'Order a purchase order',
            'supplier_order.creer': 'Create a purchase order',
            'supplier_order.export': 'Export purchase orders',
            'supplier_order.lire': 'Read purchase orders',
            'supplier_order.receptionner': 'Receive a purchase order',
            'supplier_order.supplier_order_advance.check': 'Check/Uncheck a supplier order reception',
            'supplier_order.supplier_order_advance.validate': 'Validate purchase orders',
            'supplier_order.supprimer': 'Delete a purchase order',
        },
    },
    'supplier_proposal': {
        'module': 'SupplierProposal',
        'permissions': {
            'supplier_proposal.cloturer': 'Close supplier price requests',
            'supplier_proposal.creer': 'Create/modify supplier proposals',
            'supplier_proposal.lire': 'Read supplier proposals',
            'supplier_proposal.send_advance': 'Send supplier proposals',
            'supplier_proposal.supprimer': 'Delete supplier proposals',
            'supplier_proposal.validate_advance': 'Validate supplier proposals',
        },
    },
    'takepos': {
        'module': 'TakePos',
        'permissions': {
            'takepos.editlines': 'Can modify added sales lines (prices, discount)',
            'takepos.editorderedlines': 'Edit ordered sales lines (useful only when option "Order printers" has been enabled). Allow to edit sales lines even after the order has been printed',
            'takepos.run': 'Use Point Of Sale (record a sale, add products, record payment)',
        },
    },
    'tax': {
        'module': 'Tax',
        'permissions': {
            'tax.charges.creer': 'Create/modify social contributions',
            'tax.charges.export': 'Export social contributions',
            'tax.charges.lire': 'Read social contibutions',
            'tax.charges.supprimer': 'Delete social contributions',
        },
    },
    'ticket': {
        'module': 'Ticket',
        'permissions': {
            'ticket.delete': 'Delete les tickets',
            'ticket.export': 'Export ticket',
            'ticket.manage_advance': 'Manage tickets',
            'ticket.read': 'Read ticket',
            'ticket.view.all': 'See all tickets, even if not assigned to (not effective for external users, always restricted to the thirdpardy they depends on)',
            'ticket.write': 'Create les tickets',
        },
    },
    'user': {
        'module': 'User',
        'permissions': {
            'user.group_advance.delete': 'Delete groups',
            'user.group_advance.read': 'Read groups',
            'user.group_advance.readperms': 'Read permissions of groups',
            'user.group_advance.write': 'Create/modify groups and permissions',
            'user.self.creer': 'Create/modify of its own user',
            'user.self.password': 'Modify its own password',
            'user.self_advance.readperms': 'Read its own permissions',
            'user.self_advance.writeperms': 'Modify its own permissions',
            'user.user.creer': 'Create/modify internal and external users, groups and permissions',
            'user.user.export': 'Export all users',
            'user.user.lire': 'Read information of other users, groups and permissions',
            'user.user.password': 'Modify the password of other users',
            'user.user.supprimer': 'Delete or disable other users',
            'user.user_advance.readperms': 'Read permissions of other users',
            'user.user_advance.write': 'Create/modify external users only',
        },
    },
    'variants': {
        'module': 'Variants',
        'permissions': {
            'variants.delete': 'Delete attributes of variants',
            'variants.read': 'Read attributes of variants',
            'variants.write': 'Create/Update attributes of variants',
        },
    },
    'webportal': {
        'module': 'WebPortal',
        'permissions': {
            'webportal.delete': 'Delete objects of WebPortal',
            'webportal.write': 'Administer users of the customer/partner webportal module',
        },
    },
    'website': {
        'module': 'Website',
        'permissions': {
            'website.delete': 'Delete website content',
            'website.export': 'Export website content',
            'website.read': 'Read website content',
            'website.write': 'Create/modify website content (html and javascript content)',
            'website.writephp': 'Create/modify website content (dynamic php code). Dangerous, must be reserved to restricted developers.',
        },
    },
    'workflow': {
        'module': 'Workflow',
        'permissions': {
            'workflow.read': 'Lire les workflow',
        },
    },
    'workstation': {
        'module': 'Workstation',
        'permissions': {
            'workstation.workstation.delete': 'Delete objects of Workstation',
            'workstation.workstation.read': 'Read objects of Workstation',
            'workstation.workstation.write': 'Create/Update objects of Workstation',
        },
    },
    'zapier': {
        'module': 'Zapier',
        'permissions': {
            'zapier.delete': 'Delete myobject of Zapier',
            'zapier.read': 'Read myobject of Zapier',
            'zapier.write': 'Create/Update myobject of Zapier',
        },
    },
}


def permission_exists(path: str) -> bool:
    """Return True if *path* is a known core permission path."""
    segments = path.split('.')
    module = segments[0] if segments else ''
    entry = CORE_PERMISSIONS.get(module)
    return bool(entry) and path in entry['permissions']
