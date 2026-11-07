// edit decision list.
// cuts: [clip, firstWordStart, lastWordStart] picked from the whisper transcript (null = first / last word).
// beats: what is on screen, anchored to a spoken word ({at: "word", n: occurrence}) or a time in seconds.
// rec ranges are seconds in the screen recording; the edit speeds / slows them to fit the beat.
import data from "./data.json";

const H = data.http;

export const SECTIONS = [
  {
    k: "open",
    cuts: [["c01", null, null]],
    beats: [
      { at: 0, type: "kinetic", lines: [["Every", "tool", "can", "write", "a", "lesson"], ["in", "*10", "*seconds."]] },
      { at: "hard", type: "face" },
      { at: "So", type: "logo" },
    ],
  },
  {
    k: "intro",
    cuts: [["c02", 1.02, 5.78], ["c02", 11.36, 15.84], ["c02", 19.3, 29.04]],
    beats: [
      { at: 0, type: "face" },
      { at: "This", type: "screen", rec: "create", from: 0.5, rate: 1, label: "redpen" },
      { at: "Kalvium's", type: "face" },
      { at: "you", type: "screen", rec: "create", from: 9.2, rate: 1.25, label: "title + learning objective in" },
      { at: "runs", type: "screen", rec: "create", from: 19.5, rate: 1.1, label: "research → lesson → qc 1 + qc 2" },
    ],
  },
  {
    k: "research",
    cuts: [["c03", 0.0, 7.78], ["c03", 8.42, 16.6], ["c03", 20.66, 30.32], ["c04", null, null]],
    beats: [
      { at: 0, type: "face" },
      { at: "splits", type: "screen", rec: "create", from: 24, rate: 9, label: "live research log", badge: true },
      { at: "Wikipedia,", type: "screen", rec: "research", from: 3, rate: 1.1, label: "spec · docs · wikipedia · books · youtube" },
      { at: "YouTube,", type: "screen", rec: "research", from: 14.8, rate: 1.2, label: "videos cut to the minutes that matter" },
      { at: "Stack", type: "face" },
      { at: "tells", type: "screen", rec: "research", from: 22.5, rate: 0.9, label: "real learner confusion · stack overflow" },
      { at: "Every", n: 0, type: "screen", rec: "research", from: 9.6, rate: 0.9, label: "tier A / B / C, with the reason" },
    ],
  },
  {
    k: "time",
    cuts: [["c08", 0.0, 4.46], ["c09", null, null]],
    beats: [
      { at: 0, type: "screen", rec: "lesson", from: 3.2, rate: 1, label: `${H.minutes} of 45 minutes, computed` },
      { at: "instead", type: "screen", rec: "lesson", from: 6.8, rate: 1, label: "45-minute run sheet" },
      { at: "Video", type: "face" },
      { at: "watch", n: 0, type: "screen", rec: "lesson", from: 37.2, rate: 0.45, label: "watch 7:19–8:07, not the whole video" },
    ],
  },
  {
    k: "qc1",
    silent: 24,
    beats: [
      { at: 0, type: "kinetic", lines: [["QC", "1"], ["*Facts."]] },
      { at: 2.2, type: "screen", rec: "lesson", from: 12.6, rate: 1, big: "every claim → a quote from its source" },
      { at: 7.4, type: "stat", big: `${H.quotes}/${H.claims}`, label: "quotes found word-for-word in the sources" },
      { at: 10.2, type: "screen", rec: "qc1", from: 18.5, rate: 1.4, big: "checked by code, not by the model" },
      { at: 14.4, type: "screen", rec: "qc1", from: 26.4, rate: 1.4, big: "code examples are actually run" },
      { at: 18.8, type: "screen", rec: "qc1", from: 37.8, rate: 1.2, big: `${H.probes[0]}/${H.probes[1]} claims tested with live HTTP` },
    ],
  },
  {
    k: "qc2",
    cuts: [["c11", null, null], ["c12", 0.0, 5.5], ["c12", 10.32, 12.06], ["c12", 17.48, 24.08], ["c15", 0.0, 3.5]],
    beats: [
      { at: 0, type: "face" },
      { at: "simulated", n: 0, type: "screen", rec: "qc2", from: 16.4, rate: 0.45, label: "4 simulated students · before → after" },
      { at: "That", type: "stat", big: `${H.pre}% → ${H.post}%`, label: "simulated class, before → after the lesson" },
      { at: "whether", n: 1, type: "screen", rec: "qc2", from: 3.4, rate: 1.1, label: "item analysis" },
      { at: "which", type: "screen", rec: "qc2", from: 19.5, rate: 0.8, label: "options nobody picks" },
      { at: "To", type: "face" },
      { at: "So,", type: "note", text: "It flags what a human should look at. It doesn't grade the lesson." },
    ],
  },
  {
    k: "fixes",
    cuts: [["c16", null, null], ["c17", 10.6, 11.78], ["c17", 14.16, 15.18], ["c17", 20.06, 22.1], ["c17", 23.14, 24.1], ["c17", 27.9, 29.04]],
    beats: [
      { at: 0, type: "screen", rec: "fix", from: 3.6, rate: 1.6, label: "pick findings → see the diff" },
      { at: "Every", n: 1, type: "screen", rec: "fix", from: 19.0, rate: 1.4, label: "applied as a new version" },
      { at: "nothing", type: "screen", rec: "edit", from: 19.2, rate: 1, label: "nothing is overwritten" },
      { at: "And", type: "face" },
      { at: "you", type: "screen", rec: "export", from: 3.2, rate: 1.4, label: "gated export, reason on record" },
    ],
  },
  {
    k: "fail",
    cuts: [["c18", null, null]],
    beats: [
      { at: 0, type: "face" },
      { at: "that", type: "screen", rec: "retry", from: 3.2, rate: 1, label: "a real free-tier quota failure" },
      { at: "everything", type: "screen", rec: "retry", from: 8.4, rate: 1, label: "saved work stays · retry one step" },
      { at: "retry", type: "screen", rec: "retry", from: 441.5, rate: 1, label: "retried: done" },
    ],
  },
  {
    k: "stack",
    cuts: [["c19", 1.14, 18.58], ["c19", 19.18, 21.32]],
    beats: [
      { at: 0, type: "face" },
      { at: "Python,", type: "stack", marks: [["Python,", 0], ["Gemini", 1], ["embeddings", 2], ["yt-dlp", 3], ["plain", 6], ["every", 7]] },

    ],
  },
  {
    k: "close",
    cuts: [["c22", 1.56, 4.98], ["c22", 8.68, 13.52], ["c22", 15.28, 18.74]],
    beats: [
      { at: 0, type: "face" },
      { at: "tested", type: "proof" },
      { at: "So", type: "face" },
      { at: "thanks", type: "end" },
    ],
  },
];

// whisper mishearings -> what was said, keyed by clip + word start time (or word text for every occurrence)
export const FIX_AT = {
  "c02@1.66": "Tamil", "c02@1.94": "Adhavan.", "c22@3.78": "Claude", "c22@15.92": "Adhavan,",
  "c19@14.28": "yt-dlp", "c19@14.64": "", "c17@14.9": "overwritten,", "c17@15.18": "", "c03@14.22": "books,",
  "c03@15.3": "", "c11@0.0": "QC 2", "c02@19.3": "You",
};
export const FIX_WORD = { tear: "tier" };
