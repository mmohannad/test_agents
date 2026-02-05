"use client";

import {
  APPLICATION_TYPES,
  APPLICATION_TYPE_LABELS_EN,
  CAPACITY_OPTIONS,
  CAPACITY_LABELS_EN,
  ID_TYPE_OPTIONS,
  ID_TYPE_LABELS_EN,
  getOptionLabel,
  type ManualParty,
} from "@/lib/manualDefaults";
import { useLocale } from "@/lib/i18n";

interface ApplicationFormProps {
  applicationType: string;
  onApplicationTypeChange: (v: string) => void;
  firstParty: ManualParty;
  onFirstPartyChange: (p: ManualParty) => void;
  secondParty: ManualParty;
  onSecondPartyChange: (p: ManualParty) => void;
  namadhij: string;
  onNamadhijChange: (v: string) => void;
}

function SectionHeader({ title }: { title: string }) {
  return (
    <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider border-b border-gray-700 pb-1 mb-3">
      {title}
    </h3>
  );
}

function SelectField({
  label,
  value,
  options,
  onChange,
  dir,
  placeholder,
  labelsEn,
  locale,
}: {
  label: string;
  value: string;
  options: readonly string[];
  onChange: (v: string) => void;
  dir?: "ltr" | "rtl";
  placeholder?: string;
  labelsEn?: Record<string, string>;
  locale?: "ar" | "en";
}) {
  return (
    <div>
      <label className="block text-xs text-gray-400 mb-1">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        dir={dir}
        className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-sm text-gray-100 focus:outline-none focus:border-blue-500"
      >
        <option value="">{placeholder ?? "— اختر —"}</option>
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {labelsEn && locale ? getOptionLabel(opt, locale, labelsEn) : opt}
          </option>
        ))}
      </select>
    </div>
  );
}

function TextField({
  label,
  value,
  onChange,
  type = "text",
  dir,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: "text" | "date" | "email" | "tel";
  dir?: "ltr" | "rtl";
  placeholder?: string;
}) {
  return (
    <div>
      <label className="block text-xs text-gray-400 mb-1">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        dir={dir}
        placeholder={placeholder}
        className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-sm text-gray-100 focus:outline-none focus:border-blue-500"
      />
    </div>
  );
}

function PartySection({
  title,
  party,
  onChange,
  showExtended,
}: {
  title: string;
  party: ManualParty;
  onChange: (p: ManualParty) => void;
  showExtended: boolean;
}) {
  const { locale, t } = useLocale();
  const update = (key: keyof ManualParty, value: string) =>
    onChange({ ...party, [key]: value });

  return (
    <div className="space-y-3">
      <SectionHeader title={title} />
      <SelectField
        label={t("appForm.capacity")}
        value={party.capacity}
        options={CAPACITY_OPTIONS}
        onChange={(v) => update("capacity", v)}
        dir="rtl"
        placeholder={t("appForm.selectCapacity")}
        labelsEn={CAPACITY_LABELS_EN}
        locale={locale}
      />
      <SelectField
        label={t("appForm.idType")}
        value={party.idType}
        options={ID_TYPE_OPTIONS}
        onChange={(v) => update("idType", v)}
        dir="rtl"
        placeholder={t("appForm.selectIdType")}
        labelsEn={ID_TYPE_LABELS_EN}
        locale={locale}
      />
      <div className="grid grid-cols-2 gap-3">
        <TextField
          label={t("appForm.idNumber")}
          value={party.idNumber}
          onChange={(v) => update("idNumber", v)}
        />
        <TextField
          label={t("appForm.expirationDate")}
          value={party.expirationDate}
          onChange={(v) => update("expirationDate", v)}
          type="date"
        />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <TextField
          label={t("appForm.citizenship")}
          value={party.citizenship}
          onChange={(v) => update("citizenship", v)}
        />
        <TextField
          label={t("appForm.fullName")}
          value={party.fullName}
          onChange={(v) => update("fullName", v)}
        />
      </div>
      {showExtended && (
        <div className="grid grid-cols-2 gap-3">
          <TextField
            label={t("appForm.phone")}
            value={party.phone}
            onChange={(v) => update("phone", v)}
            type="tel"
          />
          <TextField
            label={t("appForm.email")}
            value={party.email}
            onChange={(v) => update("email", v)}
            type="email"
          />
        </div>
      )}
    </div>
  );
}

export function ApplicationForm({
  applicationType,
  onApplicationTypeChange,
  firstParty,
  onFirstPartyChange,
  secondParty,
  onSecondPartyChange,
  namadhij,
  onNamadhijChange,
}: ApplicationFormProps) {
  const { locale, t } = useLocale();
  return (
    <div className="p-5 space-y-6">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-base font-bold text-gray-100">
          {t("appForm.title")}
        </h2>
        <span className="text-xs text-gray-500">{t("appForm.subtitle")}</span>
      </div>

      {/* Application Type */}
      <div>
        <SectionHeader title={t("appForm.applicationType")} />
        <SelectField
          label={t("appForm.applicationType")}
          value={applicationType}
          options={APPLICATION_TYPES}
          onChange={onApplicationTypeChange}
          labelsEn={APPLICATION_TYPE_LABELS_EN}
          locale={locale}
        />
      </div>

      {/* First Party */}
      <PartySection
        title={t("appForm.firstParty")}
        party={firstParty}
        onChange={onFirstPartyChange}
        showExtended={true}
      />

      {/* Second Party */}
      <PartySection
        title={t("appForm.secondParty")}
        party={secondParty}
        onChange={onSecondPartyChange}
        showExtended={false}
      />

      {/* Namadhij */}
      <div>
        <SectionHeader title={t("appForm.namadhij")} />
        <label className="block text-xs text-gray-400 mb-1">
          {t("appForm.namadhij")}
        </label>
        <textarea
          value={namadhij}
          onChange={(e) => onNamadhijChange(e.target.value)}
          rows={5}
          placeholder={t("appForm.namadhijPlaceholder")}
          className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-blue-500 resize-y"
        />
      </div>
    </div>
  );
}
