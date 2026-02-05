// Dropdown options and attachment field schemas for Manual Entry mode.

export const APPLICATION_TYPES = [
  "Special POA for a vehicle",
  "Special POA for real estate",
  "Special POA in general matters",
  "Special POA for a company/institution",
  "Special POA",
  "Special POA for handling transactions with government agencies",
  "General POA",
] as const;

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

// Attachment document types — same as UnstructuredPanel DOC_TYPE_LABELS
export const ATTACHMENT_TYPES = {
  PERSONAL_ID: "Personal ID",
  COMMERCIAL_REGISTRATION: "Commercial Registration",
  AUTHORIZATION: "Authorization",
  POWER_OF_ATTORNEY: "Power of Attorney",
  PASSPORT: "Passport",
  TRADE_LICENSE: "Trade License",
  FOUNDATION_CONTRACT: "Foundation Contract",
  ESTABLISHMENT_RECORD: "Establishment Record",
} as const;

export type AttachmentTypeCode = keyof typeof ATTACHMENT_TYPES;

// Fields that appear in extracted_fields per attachment type
export interface AttachmentFieldDef {
  key: string;
  label: string;
  type?: "text" | "date"; // defaults to "text"
}

export const ATTACHMENT_FIELD_SCHEMAS: Record<AttachmentTypeCode, AttachmentFieldDef[]> = {
  PERSONAL_ID: [
    { key: "id_number", label: "ID Number" },
    { key: "id_type", label: "ID Type" },
    { key: "name_en", label: "Full Name" },
    { key: "date_of_birth", label: "Date of Birth", type: "date" },
    { key: "id_expiry", label: "ID Expiry Date", type: "date" },
    { key: "citizenship", label: "Citizenship" },
    { key: "gender", label: "Gender" },
  ],
  PASSPORT: [
    { key: "passport_number", label: "Passport Number" },
    { key: "name_en", label: "Full Name" },
    { key: "date_of_birth", label: "Date of Birth", type: "date" },
    { key: "id_expiry", label: "Expiry Date", type: "date" },
    { key: "citizenship", label: "Citizenship" },
    { key: "nationality", label: "Nationality" },
    { key: "gender", label: "Gender" },
    { key: "place_of_issue", label: "Place of Issue" },
  ],
  COMMERCIAL_REGISTRATION: [
    { key: "cr_number", label: "CR Number" },
    { key: "company_name", label: "Company Name" },
    { key: "cr_issue_date", label: "CR Issue Date", type: "date" },
    { key: "cr_expiry_date", label: "CR Expiry Date", type: "date" },
    { key: "cr_status", label: "CR Status" },
  ],
  POWER_OF_ATTORNEY: [
    { key: "poa_number", label: "POA Number" },
    { key: "poa_date", label: "POA Date", type: "date" },
    { key: "poa_expiry", label: "POA Expiry", type: "date" },
    { key: "grantor_name", label: "Grantor Name" },
    { key: "agent_name", label: "Agent Name" },
    { key: "poa_type", label: "POA Type" },
    { key: "granted_powers", label: "Granted Powers" },
    { key: "has_substitution_right", label: "Has Substitution Right" },
    { key: "notary_name", label: "Notary Name" },
    { key: "poa_full_text", label: "Full POA Text" },
  ],
  AUTHORIZATION: [
    { key: "authorization_number", label: "Authorization Number" },
    { key: "authorization_date", label: "Authorization Date", type: "date" },
    { key: "authorization_expiry", label: "Authorization Expiry", type: "date" },
    { key: "authorizer_name", label: "Authorizer Name" },
    { key: "authorized_person", label: "Authorized Person" },
    { key: "scope", label: "Scope" },
  ],
  TRADE_LICENSE: [
    { key: "license_number", label: "License Number" },
    { key: "company_name_en", label: "Company Name (EN)" },
    { key: "company_name_ar", label: "Company Name (AR)" },
    { key: "license_expiry", label: "License Expiry", type: "date" },
    { key: "license_issue_date", label: "License Issue Date", type: "date" },
    { key: "activity_type", label: "Activity Type" },
    { key: "owner_name", label: "Owner Name" },
  ],
  FOUNDATION_CONTRACT: [
    { key: "company_name_en", label: "Company Name (EN)" },
    { key: "company_name_ar", label: "Company Name (AR)" },
    { key: "contract_date", label: "Contract Date", type: "date" },
    { key: "capital", label: "Capital" },
    { key: "partners", label: "Partners" },
    { key: "manager_name", label: "Manager Name" },
    { key: "company_type", label: "Company Type" },
  ],
  ESTABLISHMENT_RECORD: [
    { key: "establishment_number", label: "Establishment Number" },
    { key: "establishment_name_en", label: "Establishment Name (EN)" },
    { key: "establishment_name_ar", label: "Establishment Name (AR)" },
    { key: "record_expiry", label: "Record Expiry", type: "date" },
    { key: "activity_type", label: "Activity Type" },
    { key: "owner_name", label: "Owner Name" },
  ],
};

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
