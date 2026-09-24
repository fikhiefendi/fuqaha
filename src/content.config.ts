import { defineCollection } from 'astro:content';
import { glob, file } from 'astro/loaders';
import { z } from 'astro/zod';
import { MADHHABS, WORK_TYPES } from './site.config';

const madhhab = z.enum(Object.keys(MADHHABS) as [keyof typeof MADHHABS]);

// Text that may be given in Turkish, English and/or Arabic (at least one).
const localized = z
  .object({ tr: z.string().optional(), en: z.string().optional(), ar: z.string().optional() })
  .refine((v) => v.tr || v.en || v.ar, 'At least one language is required');

// Posts live in posts/<lang>/<slug>.md; the same slug in another folder is its translation.
const posts = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/posts' }),
  schema: ({ image }) =>
    z.object({
      title: z.string(),
      date: z.coerce.date(),
      summary: z.string(),
      tags: z.array(z.string()).default([]),
      cover: image().optional(),
      coverAlt: z.string().optional(),
      /** Id of an image in src/lib/images.ts, used when there is no cover. */
      photo: z.string().optional(),
      featured: z.boolean().default(true),
      draft: z.boolean().default(false),
    }),
});

// Places are shared by scholars (birth, death, residence…) so coordinates live in one file.
const places = defineCollection({
  loader: file('./src/data/places.yaml'),
  schema: z.object({
    name: localized,
    region: localized,
    regionId: z.string(),
    lat: z.number(),
    lng: z.number(),
    /** al-Thurayya gazetteer identifier, when the coordinates come from it. */
    uri: z.string().optional(),
    coordSource: z.enum(['thurayya', 'approx']).default('approx'),
  }),
});

// Dates are stored in the Hijri calendar; the Gregorian equivalent is computed.
const date = z.object({
  hijri: z.number().int().optional(),
  month: z.number().int().min(1).max(12).optional(),
  day: z.number().int().min(1).max(30).optional(),
  approx: z.boolean().default(false),
  /** Other years given by the sources. */
  alt: z.array(z.number().int()).default([]),
  place: z.string().optional(),
});

const scholars = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/scholars' }),
  schema: z.object({
    name: z.object({ ar: z.string(), tr: z.string(), en: z.string() }),
    fullNameAr: z.string().optional(),
    madhhab,
    birth: date.optional(),
    death: date.default({ approx: false, alt: [] }),
    places: z
      .array(
        z.object({
          place: z.string(),
          // nisbe: the place the jurist's name refers to (origin)
          role: z.enum(['nisbe', 'dogum', 'vefat', 'ikamet', 'rihle', 'ders', 'kadilik']),
        }),
      )
      .default([]),
    teachers: z.array(z.string()).default([]),
    students: z.array(z.string()).default([]),
    works: z
      .array(z.object({ ar: z.string(), tr: z.string().optional(), en: z.string().optional() }))
      .default([]),
    summary: localized,
    addedAt: z.coerce.date(),
    /** Position in the source book, used for the default ordering. */
    order: z.number().int().default(0),
    featured: z.boolean().default(false),
    sources: z
      .array(
        z.object({
          book: z.string(),
          bookTr: z.string().optional(),
          author: z.string().optional(),
          authorTr: z.string().optional(),
          edition: z.string().optional(),
          volume: z.union([z.number(), z.string()]).optional(),
          page: z.union([z.number(), z.string()]).optional(),
          entry: z.string().optional(),
          /** True when the page follows a digital library's automatic numbering, not the print. */
          autoNumbering: z.boolean().default(false),
        }),
      )
      .min(1),
  }),
});

const works = defineCollection({
  loader: glob({ pattern: '**/*.{yaml,yml}', base: './src/content/works' }),
  schema: z.object({
    type: z.enum(Object.keys(WORK_TYPES) as [keyof typeof WORK_TYPES]),
    title: z.string(),
    titleTranslation: localized.optional(),
    authors: z.array(z.string()).min(1),
    editors: z.array(z.string()).default([]),
    language: z.string(),
    year: z.number().int().optional(),
    publisher: z.string().optional(),
    journal: z.string().optional(),
    volume: z.union([z.number(), z.string()]).optional(),
    issue: z.union([z.number(), z.string()]).optional(),
    pages: z.string().optional(),
    university: z.string().optional(),
    city: z.string().optional(),
    topics: z.array(z.string()).default([]),
    scholars: z.array(z.string()).default([]),
    madhhab: madhhab.optional(),
    url: z.url().optional(),
    doi: z.string().optional(),
    abstract: z.string().optional(),
    addedAt: z.coerce.date(),
  }),
});

// Fixed pages (about, contribute, licence) in pages/<lang>/<slug>.md.
const pages = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/pages' }),
  schema: z.object({
    title: z.string(),
    lead: z.string(),
    photo: z.string().optional(),
  }),
});

export const collections = { posts, places, scholars, works, pages };
