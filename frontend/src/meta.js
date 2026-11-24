import { CircleCheck, ScanText, MapPinned, TriangleAlert, CircleX, CircleSlash } from "lucide-react";

/** How each MATCH SOURCE value is presented. Status colours always ship with an icon + label. */
export const SOURCES = {
  ZIP: {
    tone: "good",
    icon: CircleCheck,
    label: "ZIP lookup",
    hint: "ZIP in the address matched the reference table",
  },
  "TEXT-MUNICIPALITY": {
    tone: "info",
    icon: ScanText,
    label: "Town named in text",
    hint: "No usable ZIP, but a municipality name was found",
  },
  "TEXT-PROVINCE": {
    tone: "warn",
    icon: MapPinned,
    label: "Province only",
    hint: "Only a province name was found; municipality left blank",
  },
  "ZIP NOT IN REFERENCE": {
    tone: "warn",
    icon: TriangleAlert,
    label: "Unknown ZIP",
    hint: "Add this ZIP to the reference table and run again",
  },
  "NO ZIP FOUND": {
    tone: "bad",
    icon: CircleX,
    label: "Nothing to match",
    hint: "No ZIP and no place name in the address",
  },
  "NO ADDRESS": {
    tone: "neutral",
    icon: CircleSlash,
    label: "Blank address",
    hint: "The address cell is empty",
  },
};

export const sourceMeta = (key) =>
  SOURCES[key] ?? { tone: "neutral", icon: CircleSlash, label: key, hint: "" };

/* Island groups keep a fixed colour and a north-to-south order, so the same
   group is always the same colour no matter its count. */
export const ISLAND_ORDER = ["NCR", "NORTH LUZON", "SOUTH LUZON", "VISAYAS", "MINDANAO"];
export const SLOTS = ["var(--s1)", "var(--s2)", "var(--s3)", "var(--s4)", "var(--s5)"];
/* label ink that reads on each slot (blue takes white, the rest take near-black) */
export const SLOT_INK = ["#ffffff", "#0f1b2d", "#0f1b2d", "#0f1b2d", "#0f1b2d"];
