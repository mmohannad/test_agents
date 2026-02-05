// Dropdown options and attachment field schemas for Manual Entry mode.

import type { Locale } from "./i18n";

// ============================================================================
// APPLICATION TYPES
// ============================================================================

export const APPLICATION_TYPES = [
  "توكيل خاص لمركبة",
  "توكيل خاص لعقار",
  "توكيل خاص في أمور عامة",
  "توكيل خاص لشركة/مؤسسة",
  "توكيل خاص",
  "توكيل خاص لإنهاء المعاملات لدى الجهات الحكومية",
  "توكيل عام",
] as const;

export const APPLICATION_TYPE_LABELS_EN: Record<string, string> = {
  "توكيل خاص لمركبة": "Special POA for Vehicle",
  "توكيل خاص لعقار": "Special POA for Property",
  "توكيل خاص في أمور عامة": "Special POA for General Matters",
  "توكيل خاص لشركة/مؤسسة": "Special POA for Company/Institution",
  "توكيل خاص": "Special POA",
  "توكيل خاص لإنهاء المعاملات لدى الجهات الحكومية": "Special POA for Government Transactions",
  "توكيل عام": "General POA",
};

// ============================================================================
// CAPACITY OPTIONS
// ============================================================================

export const CAPACITY_OPTIONS = [
  "القيم",
  "المفوض",
  "الوصي",
  "الولي الطبيعي",
  "شريك في شركة أجنبية",
  "شريك في شريكة",
  "شريك في مصنع",
  "عن نفسه (بصفته الشخصية)",
  "مالك السجل التجاري",
  "مخول بالتوقيع في السجل التجاري",
  "مخول بالتوقيع في قيد المنشأة",
  "مندوب عن شركة",
  "وكيل بموجب وكالة",
  "وكيل الغائب",
  "محامي",
  "رئيس مجلس إدارة",
  "رئيس تنفيذي",
  "عضو مجلس إدارة",
  "حارس قضائي",
  "ناظر وقف",
  "مصفي",
  "مؤسس",
  "مدير",
  "مالك رخصة تجارية",
  "شريك في رخصة تجارية",
  "مدير رخصة تجارية",
  "وريث",
  "رئيس مجلس الأمناء",
  "نائب رئيس مجلس إدارة",
  "مفوض بموجب محضر اجتماع",
  "مخول بالتوقيع عن شركة أجنبية",
  "نائب رئيس مجلس إدارة بشركة أجنبية",
  "مدير تنفيذي بشركة أجنبية",
  "العضو المنتدب بشركة أجنبية",
  "مديروالعضو المنتدب",
  "مدير بشركة أجنبية",
  "مدير للتفليسة",
  "مصفى بشركة أجنبية",
  "نائب رئيس المجلس التنفيذي",
  "جهة اعتبارية أجنبية",
  "عضو مجلس رقابي",
  "الرئيس التنفيذي بشركة أجنبية",
  "حارس قضائي بشركة أجنبية",
  "مدير تفليسة بشركة أجنبية",
  "العضو المنتدب",
  "رئيس مجلس الإدارة والعضو المنتدب",
  "مالك شركة أجنبية",
  "وكيل عن وريث",
  "مدير تنفيذي",
  "رئيس مجلس إدارة بشركة أجنبية",
  "نائب رئيس مجلس الإدارة والعضو المنتدب",
  "عضو مجلس رقابي بشركة أجنبية",
] as const;

export const CAPACITY_LABELS_EN: Record<string, string> = {
  "القيم": "Guardian",
  "المفوض": "Delegate",
  "الوصي": "Trustee",
  "الولي الطبيعي": "Natural Guardian",
  "شريك في شركة أجنبية": "Partner in Foreign Company",
  "شريك في شريكة": "Partner in Partnership",
  "شريك في مصنع": "Partner in Factory",
  "عن نفسه (بصفته الشخصية)": "Self (Personal Capacity)",
  "مالك السجل التجاري": "Commercial Registration Owner",
  "مخول بالتوقيع في السجل التجاري": "Authorized Signatory in CR",
  "مخول بالتوقيع في قيد المنشأة": "Authorized Signatory in Establishment Record",
  "مندوب عن شركة": "Company Representative",
  "وكيل بموجب وكالة": "Agent by Power of Attorney",
  "وكيل الغائب": "Agent of Absentee",
  "محامي": "Lawyer",
  "رئيس مجلس إدارة": "Chairman of the Board",
  "رئيس تنفيذي": "CEO",
  "عضو مجلس إدارة": "Board Member",
  "حارس قضائي": "Judicial Receiver",
  "ناظر وقف": "Waqf Supervisor",
  "مصفي": "Liquidator",
  "مؤسس": "Founder",
  "مدير": "Manager",
  "مالك رخصة تجارية": "Trade License Owner",
  "شريك في رخصة تجارية": "Partner in Trade License",
  "مدير رخصة تجارية": "Trade License Manager",
  "وريث": "Heir",
  "رئيس مجلس الأمناء": "Chairman of Board of Trustees",
  "نائب رئيس مجلس إدارة": "Vice Chairman of the Board",
  "مفوض بموجب محضر اجتماع": "Delegate by Meeting Minutes",
  "مخول بالتوقيع عن شركة أجنبية": "Authorized Signatory for Foreign Company",
  "نائب رئيس مجلس إدارة بشركة أجنبية": "Vice Chairman in Foreign Company",
  "مدير تنفيذي بشركة أجنبية": "Executive Manager in Foreign Company",
  "العضو المنتدب بشركة أجنبية": "Managing Director in Foreign Company",
  "مديروالعضو المنتدب": "Manager & Managing Director",
  "مدير بشركة أجنبية": "Manager in Foreign Company",
  "مدير للتفليسة": "Bankruptcy Manager",
  "مصفى بشركة أجنبية": "Liquidator in Foreign Company",
  "نائب رئيس المجلس التنفيذي": "Vice Chairman of Executive Council",
  "جهة اعتبارية أجنبية": "Foreign Legal Entity",
  "عضو مجلس رقابي": "Supervisory Board Member",
  "الرئيس التنفيذي بشركة أجنبية": "CEO in Foreign Company",
  "حارس قضائي بشركة أجنبية": "Judicial Receiver in Foreign Company",
  "مدير تفليسة بشركة أجنبية": "Bankruptcy Manager in Foreign Company",
  "العضو المنتدب": "Managing Director",
  "رئيس مجلس الإدارة والعضو المنتدب": "Chairman & Managing Director",
  "مالك شركة أجنبية": "Foreign Company Owner",
  "وكيل عن وريث": "Agent of Heir",
  "مدير تنفيذي": "Executive Manager",
  "رئيس مجلس إدارة بشركة أجنبية": "Chairman in Foreign Company",
  "نائب رئيس مجلس الإدارة والعضو المنتدب": "Vice Chairman & Managing Director",
  "عضو مجلس رقابي بشركة أجنبية": "Supervisory Board Member in Foreign Company",
};

// ============================================================================
// ID TYPE OPTIONS
// ============================================================================

export const ID_TYPE_OPTIONS = [
  "الرقم الشخصي",
  "السجل التجاري",
  "جواز سفر",
  "رخصة تجارية",
  "رقم المنشأة",
  "شركة أجنبية",
  "صادر من المملكة العربية السعودية",
  "صادر من دولة الكويت",
  "صادر من سلطنة عمان",
  "صادر من مملكة البحرين",
  "صادر من الإمارات العربية المتحدة",
  "هوي",
] as const;

export const ID_TYPE_LABELS_EN: Record<string, string> = {
  "الرقم الشخصي": "Personal ID Number",
  "السجل التجاري": "Commercial Registration",
  "جواز سفر": "Passport",
  "رخصة تجارية": "Trade License",
  "رقم المنشأة": "Establishment Number",
  "شركة أجنبية": "Foreign Company",
  "صادر من المملكة العربية السعودية": "Issued by Saudi Arabia",
  "صادر من دولة الكويت": "Issued by Kuwait",
  "صادر من سلطنة عمان": "Issued by Oman",
  "صادر من مملكة البحرين": "Issued by Bahrain",
  "صادر من الإمارات العربية المتحدة": "Issued by UAE",
  "هوي": "ID Card",
};

// ============================================================================
// SIGNATORY POSITIONS (moved from AttachmentPanel.tsx)
// ============================================================================

export const SIGNATORY_POSITIONS = [
  "مدير",
  "شريك",
  "مدير عام",
  "مفوض بالتوقيع",
  "الرئيس التنفيذي",
  "رئيس مجلس الإدارة",
] as const;

export const SIGNATORY_POSITION_LABELS_EN: Record<string, string> = {
  "مدير": "Manager",
  "شريك": "Partner",
  "مدير عام": "General Manager",
  "مفوض بالتوقيع": "Authorized Signatory",
  "الرئيس التنفيذي": "CEO",
  "رئيس مجلس الإدارة": "Chairman of the Board",
};

// ============================================================================
// ATTACHMENT TYPES
// ============================================================================

export const ATTACHMENT_TYPES = {
  PERSONAL_ID: "هوية شخصية",
  COMMERCIAL_REGISTRATION: "سجل تجاري",
  AUTHORIZATION: "تفويض",
  POWER_OF_ATTORNEY: "توكيل",
  PASSPORT: "جواز سفر",
  TRADE_LICENSE: "رخصة تجارية",
  FOUNDATION_CONTRACT: "عقد تأسيس",
  ESTABLISHMENT_RECORD: "قيد منشأة",
} as const;

export const ATTACHMENT_TYPE_LABELS_EN: Record<keyof typeof ATTACHMENT_TYPES, string> = {
  PERSONAL_ID: "Personal ID",
  COMMERCIAL_REGISTRATION: "Commercial Registration",
  AUTHORIZATION: "Authorization",
  POWER_OF_ATTORNEY: "Power of Attorney",
  PASSPORT: "Passport",
  TRADE_LICENSE: "Trade License",
  FOUNDATION_CONTRACT: "Foundation Contract",
  ESTABLISHMENT_RECORD: "Establishment Record",
};

export type AttachmentTypeCode = keyof typeof ATTACHMENT_TYPES;

// ============================================================================
// ATTACHMENT FIELD SCHEMAS
// ============================================================================

export interface AttachmentFieldDef {
  key: string;
  label: string;      // Arabic (existing)
  label_en: string;   // English (new)
  type?: "text" | "date"; // defaults to "text"
}

export const ATTACHMENT_FIELD_SCHEMAS: Record<AttachmentTypeCode, AttachmentFieldDef[]> = {
  PERSONAL_ID: [
    { key: "id_number", label: "رقم الهوية", label_en: "ID Number" },
    { key: "id_type", label: "نوع الهوية", label_en: "ID Type" },
    { key: "name_en", label: "الاسم الكامل", label_en: "Full Name" },
    { key: "date_of_birth", label: "تاريخ الميلاد", label_en: "Date of Birth", type: "date" },
    { key: "id_expiry", label: "تاريخ انتهاء الهوية", label_en: "ID Expiry Date", type: "date" },
    { key: "citizenship", label: "الجنسية", label_en: "Citizenship" },
    { key: "gender", label: "الجنس", label_en: "Gender" },
  ],
  PASSPORT: [
    { key: "passport_number", label: "رقم الجواز", label_en: "Passport Number" },
    { key: "name_en", label: "الاسم الكامل", label_en: "Full Name" },
    { key: "date_of_birth", label: "تاريخ الميلاد", label_en: "Date of Birth", type: "date" },
    { key: "id_expiry", label: "تاريخ الانتهاء", label_en: "Expiry Date", type: "date" },
    { key: "citizenship", label: "الجنسية", label_en: "Citizenship" },
    { key: "nationality", label: "الجنسية", label_en: "Nationality" },
    { key: "gender", label: "الجنس", label_en: "Gender" },
    { key: "place_of_issue", label: "مكان الإصدار", label_en: "Place of Issue" },
  ],
  COMMERCIAL_REGISTRATION: [
    { key: "cr_number", label: "رقم السجل التجاري", label_en: "CR Number" },
    { key: "company_name", label: "اسم الشركة", label_en: "Company Name" },
    { key: "cr_issue_date", label: "تاريخ إصدار السجل", label_en: "CR Issue Date", type: "date" },
    { key: "cr_expiry_date", label: "تاريخ انتهاء السجل", label_en: "CR Expiry Date", type: "date" },
    { key: "cr_status", label: "حالة السجل", label_en: "CR Status" },
  ],
  POWER_OF_ATTORNEY: [
    { key: "poa_number", label: "رقم التوكيل", label_en: "POA Number" },
    { key: "poa_date", label: "تاريخ التوكيل", label_en: "POA Date", type: "date" },
    { key: "poa_expiry", label: "تاريخ انتهاء التوكيل", label_en: "POA Expiry Date", type: "date" },
    { key: "grantor_name", label: "اسم الموكل", label_en: "Grantor Name" },
    { key: "agent_name", label: "اسم الوكيل", label_en: "Agent Name" },
    { key: "poa_type", label: "نوع التوكيل", label_en: "POA Type" },
    { key: "granted_powers", label: "الصلاحيات الممنوحة", label_en: "Granted Powers" },
    { key: "has_substitution_right", label: "حق الإنابة", label_en: "Substitution Right" },
    { key: "notary_name", label: "اسم الموثق", label_en: "Notary Name" },
    { key: "poa_full_text", label: "نص التوكيل الكامل", label_en: "Full POA Text" },
  ],
  AUTHORIZATION: [
    { key: "authorization_number", label: "رقم التفويض", label_en: "Authorization Number" },
    { key: "authorization_date", label: "تاريخ التفويض", label_en: "Authorization Date", type: "date" },
    { key: "authorization_expiry", label: "تاريخ انتهاء التفويض", label_en: "Authorization Expiry Date", type: "date" },
    { key: "authorizer_name", label: "اسم المفوِّض", label_en: "Authorizer Name" },
    { key: "authorized_person", label: "اسم المفوَّض", label_en: "Authorized Person Name" },
    { key: "scope", label: "نطاق التفويض", label_en: "Authorization Scope" },
  ],
  TRADE_LICENSE: [
    { key: "license_number", label: "رقم الرخصة", label_en: "License Number" },
    { key: "company_name_en", label: "اسم الشركة (إنجليزي)", label_en: "Company Name (English)" },
    { key: "company_name_ar", label: "اسم الشركة (عربي)", label_en: "Company Name (Arabic)" },
    { key: "license_expiry", label: "تاريخ انتهاء الرخصة", label_en: "License Expiry Date", type: "date" },
    { key: "license_issue_date", label: "تاريخ إصدار الرخصة", label_en: "License Issue Date", type: "date" },
    { key: "activity_type", label: "نوع النشاط", label_en: "Activity Type" },
    { key: "owner_name", label: "اسم المالك", label_en: "Owner Name" },
  ],
  FOUNDATION_CONTRACT: [
    { key: "company_name_en", label: "اسم الشركة (إنجليزي)", label_en: "Company Name (English)" },
    { key: "company_name_ar", label: "اسم الشركة (عربي)", label_en: "Company Name (Arabic)" },
    { key: "contract_date", label: "تاريخ العقد", label_en: "Contract Date", type: "date" },
    { key: "capital", label: "رأس المال", label_en: "Capital" },
    { key: "partners", label: "الشركاء", label_en: "Partners" },
    { key: "manager_name", label: "اسم المدير", label_en: "Manager Name" },
    { key: "company_type", label: "نوع الشركة", label_en: "Company Type" },
  ],
  ESTABLISHMENT_RECORD: [
    { key: "establishment_number", label: "رقم المنشأة", label_en: "Establishment Number" },
    { key: "establishment_name_en", label: "اسم المنشأة (إنجليزي)", label_en: "Establishment Name (English)" },
    { key: "establishment_name_ar", label: "اسم المنشأة (عربي)", label_en: "Establishment Name (Arabic)" },
    { key: "record_expiry", label: "تاريخ انتهاء القيد", label_en: "Record Expiry Date", type: "date" },
    { key: "activity_type", label: "نوع النشاط", label_en: "Activity Type" },
    { key: "owner_name", label: "اسم المالك", label_en: "Owner Name" },
  ],
};

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Get the display label for a dropdown option value based on the current locale.
 *
 * @param value - The canonical Arabic value
 * @param locale - Current locale ('ar' or 'en')
 * @param labelsEn - Record mapping Arabic values to English labels
 * @returns The localized label
 */
export function getOptionLabel(value: string, locale: Locale, labelsEn: Record<string, string>): string {
  if (locale === "en" && labelsEn[value]) {
    return labelsEn[value];
  }
  return value; // Arabic is the value itself
}

// ============================================================================
// TYPES & INTERFACES
// ============================================================================

// Signatory for CR attachments
export interface Signatory {
  name_en: string;
  identification_number: string;
  nationality_en: string;
  percentage: string;
  position: string;
}

export function createEmptySignatory(): Signatory {
  return {
    name_en: "",
    identification_number: "",
    nationality_en: "",
    percentage: "",
    position: "",
  };
}

// Types for manual form state
export interface ManualParty {
  capacity: string;
  idType: string;
  idNumber: string;
  expirationDate: string;
  citizenship: string;
  fullName: string;
  phone: string;
  email: string;
}

export interface ManualAttachment {
  id: string;
  documentTypeCode: AttachmentTypeCode;
  extractedFields: Record<string, string>;
  rawTextAr: string;
  rawTextEn: string;
  signatories: Signatory[];
  saved: boolean;
}

export function createEmptyParty(): ManualParty {
  return {
    capacity: "",
    idType: "",
    idNumber: "",
    expirationDate: "",
    citizenship: "",
    fullName: "",
    phone: "",
    email: "",
  };
}

export function createEmptyAttachment(typeCode: AttachmentTypeCode = "PERSONAL_ID"): ManualAttachment {
  const fields: Record<string, string> = {};
  for (const f of ATTACHMENT_FIELD_SCHEMAS[typeCode]) {
    fields[f.key] = "";
  }
  return {
    id: `att-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    documentTypeCode: typeCode,
    extractedFields: fields,
    rawTextAr: "",
    rawTextEn: "",
    signatories: [],
    saved: false,
  };
}
