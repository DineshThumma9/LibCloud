export type IconAppearance = { isLight: boolean; isBlank: boolean };

export function setsEqual(a: Set<string>, b: Set<string>): boolean {
  if (a.size !== b.size) return false;
  for (const value of a) {
    if (!b.has(value)) return false;
  }
  return true;
}

const measuredIconCache = new Map<string, IconAppearance>();
const measuredIconPromises = new Map<string, Promise<IconAppearance>>();

/**
 * Sample an icon's rendered pixels. Mostly-white marks (including raster
 * PNG/JPEG/ICO logos) need a dark chip so they do not disappear into the
 * light one. Icons that render nothing (empty clip paths, sprite sheets,
 * broken SVG) are flagged as blank so the UI can show an initial instead.
 * Results are cached per data URI.
 */
export function measureIconAppearance(icon: string): Promise<IconAppearance> {
  const cached = measuredIconCache.get(icon);
  if (cached !== undefined) return Promise.resolve(cached);
  const inFlight = measuredIconPromises.get(icon);
  if (inFlight) return inFlight;

  const promise = new Promise<IconAppearance>((resolve) => {
    const image = document.createElement("img");
    image.onload = () => {
      try {
        const size = 32;
        const canvas = document.createElement("canvas");
        canvas.width = size;
        canvas.height = size;
        const ctx = canvas.getContext("2d", { willReadFrequently: true });
        if (!ctx) return resolve({ isLight: false, isBlank: false });
        ctx.drawImage(image, 0, 0, size, size);
        const data = ctx.getImageData(0, 0, size, size).data;
        let visible = 0;
        let dark = 0;
        let pale = 0;
        let saturated = 0;
        let luminanceSum = 0;
        for (let i = 0; i < data.length; i += 4) {
          if (data[i + 3] < 32) continue;
          visible++;
          const r = data[i];
          const g = data[i + 1];
          const b = data[i + 2];
          const luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b;
          luminanceSum += luminance;
          if (luminance < 60) dark++;
          if (luminance > 200) pale++;
          if (Math.max(r, g, b) - Math.min(r, g, b) > 30) saturated++;
        }
        if (visible < 20) {
          const blank = { isLight: false, isBlank: true };
          measuredIconCache.set(icon, blank);
          return resolve(blank);
        }
        const average = luminanceSum / visible;
        const isLight =
          (dark / visible < 0.12 && average >= 170) ||
          (pale / visible > 0.6 && dark / visible < 0.2) ||
          (saturated / visible < 0.2 && average > 130 && dark / visible < 0.05);
        const appearance = { isLight, isBlank: false };
        measuredIconCache.set(icon, appearance);
        resolve(appearance);
      } catch {
        resolve({ isLight: false, isBlank: false });
      }
    };
    image.onerror = () => {
      const blank = { isLight: false, isBlank: true };
      measuredIconCache.set(icon, blank);
      resolve(blank);
    };
    image.src = icon;
  }).finally(() => {
    measuredIconPromises.delete(icon);
  });

  measuredIconPromises.set(icon, promise);
  return promise;
}
