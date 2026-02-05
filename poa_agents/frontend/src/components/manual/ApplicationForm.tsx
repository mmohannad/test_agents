"use client";

import {
  APPLICATION_TYPES,
  CAPACITY_OPTIONS,
  ID_TYPE_OPTIONS,
  type ManualParty,
} from "@/lib/manualDefaults";

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
}: {
  label: string;
  value: string;
  options: readonly string[];
  onChange: (v: string) => void;
  dir?: "ltr" | "rtl";
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
        <option value="">— Select —</option>
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
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
  const update = (key: keyof ManualParty, value: string) =>
    onChange({ ...party, [key]: value });

  return (
    <div className="space-y-3">
      <SectionHeader title={title} />
      <SelectField
        label="Capacity"
        value={party.capacity}
        options={CAPACITY_OPTIONS}
        onChange={(v) => update("capacity", v)}
        dir="rtl"
      />
      <SelectField
        label="ID Type"
        value={party.idType}
        options={ID_TYPE_OPTIONS}
        onChange={(v) => update("idType", v)}
        dir="rtl"
      />
      <div className="grid grid-cols-2 gap-3">
        <TextField
          label="ID Number"
          value={party.idNumber}
          onChange={(v) => update("idNumber", v)}
        />
        <TextField
          label="Expiration Date"
          value={party.expirationDate}
          onChange={(v) => update("expirationDate", v)}
          type="date"
        />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <TextField
          label="Citizenship"
          value={party.citizenship}
          onChange={(v) => update("citizenship", v)}
        />
        <TextField
          label="Full Name"
          value={party.fullName}
          onChange={(v) => update("fullName", v)}
        />
      </div>
      {showExtended && (
        <div className="grid grid-cols-2 gap-3">
          <TextField
            label="Phone Number"
            value={party.phone}
            onChange={(v) => update("phone", v)}
            type="tel"
          />
          <TextField
            label="Email Address"
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
  return (
    <div className="p-5 space-y-6">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-base font-bold text-gray-100">
          Application Data
        </h2>
        <span className="text-xs text-gray-500">Manual Entry</span>
      </div>

      {/* Application Type */}
      <div>
        <SectionHeader title="Application Type" />
        <SelectField
          label="Application type"
          value={applicationType}
          options={APPLICATION_TYPES}
          onChange={onApplicationTypeChange}
        />
      </div>

      {/* First Party */}
      <PartySection
        title="First Party"
        party={firstParty}
        onChange={onFirstPartyChange}
        showExtended={true}
      />

      {/* Second Party */}
      <PartySection
        title="Second Party"
        party={secondParty}
        onChange={onSecondPartyChange}
        showExtended={false}
      />

      {/* Namadhij */}
      <div>
        <SectionHeader title="Namadhij (Permissions to be Granted)" />
        <label className="block text-xs text-gray-400 mb-1">
          Namadhij
        </label>
        <textarea
          value={namadhij}
          onChange={(e) => onNamadhijChange(e.target.value)}
          rows={5}
          placeholder="Enter the permissions / powers to be granted..."
          className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-blue-500 resize-y"
        />
      </div>
    </div>
  );
}
