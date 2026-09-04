import fs from 'node:fs';

const translations = {
  ru: {
    'common.showAllCustomFields': 'Показать все пользовательские поля ({count})',
    'common.showFewerCustomFields': 'Показать меньше пользовательских полей',
    'filaments.dsSystemExtraFieldsLabel': 'Системные дополнительные поля филамента',
    'filaments.dsCustomFieldsLabel': 'Пользовательские поля филамента',
    'filaments.dsNoSystemExtraFields': 'Системные дополнительные поля для филамента не настроены.',
    'filaments.dsBatchCustomFieldsDisabled': 'Пользовательские поля отдельных филаментов недоступны при пакетной печати.',
    'spools.dsSystemExtraFieldsLabel': 'Системные дополнительные поля катушки',
    'spools.dsCustomFieldsLabel': 'Пользовательские поля катушки',
    'spools.dsNoSystemExtraFields': 'Системные дополнительные поля для катушки не настроены.',
    'spools.dsBatchCustomFieldsDisabled': 'Пользовательские поля отдельных катушек недоступны при пакетной печати.',
    'labelPrint.btnExportAml': 'Экспорт AML',
    'labelPrint.createTemporaryPdf': 'Создать временный PDF для печати',
    'labelPrint.individualExportsUnavailableInSheetMode': 'Экспорт отдельных этикеток недоступен в режиме листа этикеток.',
    'labelPrint.amlExportFailed': 'Не удалось экспортировать AML.',
    'labelPrint.preparingBrowserPrint': 'Подготовка печати в браузере…',
    'labelPrint.browserPrintFailed': 'Не удалось выполнить печать из браузера.',
    'labelPrint.temporaryPdfPreviewTitle': 'Предварительный просмотр временного PDF для печати',
    'labelPrint.backToLabelPreview': 'Вернуться к предварительному просмотру этикетки',
    'labelPrint.openPdfForPrinting': 'Открыть PDF для печати',
    'labelPrint.downloadPdf': 'Скачать PDF',
    'labelPrint.inlinePdfUnsupported': 'Этот браузер не может показать временный PDF в области предварительного просмотра. Откройте или скачайте PDF для печати.',
    'labelPrint.printPopupBlocked': 'Разрешите всплывающие окна, чтобы открыть PDF для печати.',
    'labelPrint.printPdfFailed': 'Не удалось создать PDF для печати.',
    'labelPrint.printHelpScale': 'Выберите точный размер бумаги и печатайте с масштабом 100% или «Фактический размер».',
    'labelPrint.printHelpBrowserSystemDialog': 'Используйте системный диалог печати ОС, чтобы задать размер бумаги, ориентацию, поворот и выравнивание для конкретного принтера.',
    'labelPrint.printHelpPdfFallbackPrefix': 'Если печать из браузера получается пустой, обрезанной, смещённой, повёрнутой или неправильного размера, включите',
    'labelPrint.printHelpPdfFallbackSuffix': '.',
    'labelPrint.printHelpPdfOpenOnly': 'FilaMan отображает временный PDF в области предварительного просмотра для печати и не сохраняет его.',
    'labelPrint.printHelpPdfSystemDialog': 'Даже в режиме временного PDF может потребоваться системный диалог печати ОС для стабильного и повторяемого результата.',
    'labelPrint.printHelpPdfDownloadSetting': 'Если браузер не может показать PDF в области предварительного просмотра, используйте «Открыть PDF для печати» или «Скачать PDF».',
  },
  uk: {
    'common.showAllCustomFields': 'Показати всі користувацькі поля ({count})',
    'common.showFewerCustomFields': 'Показати менше користувацьких полів',
    'filaments.dsSystemExtraFieldsLabel': 'Системні додаткові поля філаменту',
    'filaments.dsCustomFieldsLabel': 'Користувацькі поля філаменту',
    'filaments.dsNoSystemExtraFields': 'Системні додаткові поля для філаменту не налаштовані.',
    'filaments.dsBatchCustomFieldsDisabled': 'Користувацькі поля окремих філаментів недоступні під час пакетного друку.',
    'spools.dsSystemExtraFieldsLabel': 'Системні додаткові поля котушки',
    'spools.dsCustomFieldsLabel': 'Користувацькі поля котушки',
    'spools.dsNoSystemExtraFields': 'Системні додаткові поля для котушки не налаштовані.',
    'spools.dsBatchCustomFieldsDisabled': 'Користувацькі поля окремих котушок недоступні під час пакетного друку.',
    'labelPrint.btnExportAml': 'Експорт AML',
    'labelPrint.createTemporaryPdf': 'Створити тимчасовий PDF для друку',
    'labelPrint.individualExportsUnavailableInSheetMode': 'Експорт окремих етикеток недоступний у режимі аркуша етикеток.',
    'labelPrint.amlExportFailed': 'Не вдалося експортувати AML.',
    'labelPrint.preparingBrowserPrint': 'Підготовка друку в браузері…',
    'labelPrint.browserPrintFailed': 'Не вдалося виконати друк із браузера.',
    'labelPrint.temporaryPdfPreviewTitle': 'Попередній перегляд тимчасового PDF для друку',
    'labelPrint.backToLabelPreview': 'Повернутися до попереднього перегляду етикетки',
    'labelPrint.openPdfForPrinting': 'Відкрити PDF для друку',
    'labelPrint.downloadPdf': 'Завантажити PDF',
    'labelPrint.inlinePdfUnsupported': 'Цей браузер не може показати тимчасовий PDF в області попереднього перегляду. Відкрийте або завантажте PDF для друку.',
    'labelPrint.printPopupBlocked': 'Дозвольте спливні вікна, щоб відкрити PDF для друку.',
    'labelPrint.printPdfFailed': 'Не вдалося створити PDF для друку.',
    'labelPrint.printHelpScale': 'Виберіть точний розмір паперу та друкуйте з масштабом 100% або «Фактичний розмір».',
    'labelPrint.printHelpBrowserSystemDialog': 'Використовуйте системний діалог друку ОС, щоб задати розмір паперу, орієнтацію, поворот і вирівнювання для конкретного принтера.',
    'labelPrint.printHelpPdfFallbackPrefix': 'Якщо друк із браузера виходить порожнім, обрізаним, зміщеним, повернутим або неправильного розміру, увімкніть',
    'labelPrint.printHelpPdfFallbackSuffix': '.',
    'labelPrint.printHelpPdfOpenOnly': 'FilaMan показує тимчасовий PDF в області попереднього перегляду для друку та не зберігає його.',
    'labelPrint.printHelpPdfSystemDialog': 'Навіть у режимі тимчасового PDF може знадобитися системний діалог друку ОС для стабільного та повторюваного результату.',
    'labelPrint.printHelpPdfDownloadSetting': 'Якщо браузер не може показати PDF в області попереднього перегляду, використовуйте «Відкрити PDF для друку» або «Завантажити PDF».',
  },
};

const removedKeys = [
  'labelPrint.pngUnavailableInSheetMode',
  'labelPrint.printHelpBrave',
  'labelPrint.printHelpFirefox',
];

function resolveParent(target, dottedKey) {
  const parts = dottedKey.split('.');
  const leaf = parts.pop();
  let node = target;
  for (const part of parts) {
    if (!node[part] || typeof node[part] !== 'object' || Array.isArray(node[part])) node[part] = {};
    node = node[part];
  }
  return [node, leaf];
}

function setPath(target, dottedKey, value) {
  const [node, leaf] = resolveParent(target, dottedKey);
  node[leaf] = value;
}

function deletePath(target, dottedKey) {
  const [node, leaf] = resolveParent(target, dottedKey);
  delete node[leaf];
}

for (const [lang, entries] of Object.entries(translations)) {
  const path = `frontend/src/i18n/${lang}.json`;
  const data = JSON.parse(fs.readFileSync(path, 'utf8'));
  for (const key of removedKeys) deletePath(data, key);
  for (const [key, value] of Object.entries(entries)) setPath(data, key, value);
  fs.writeFileSync(path, `${JSON.stringify(data, null, 2)}\n`);
}

console.log(`Aligned RU/UK catalogs and applied ${Object.keys(translations.ru).length} translations per language.`);
