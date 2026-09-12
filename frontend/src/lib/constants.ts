export const SCENE_PRESETS = [
  {
    value: "white_amazon",
    label: "White Amazon",
    prompt: "single product centered on a pure white cyclorama, broad softbox lighting, subtle grounding reflection, clean ecommerce catalog photograph",
  },
  {
    value: "luxury_studio",
    label: "Luxury studio",
    prompt: "single product on a dark polished stone pedestal, charcoal studio backdrop, warm rim lights, dramatic spotlight, premium fragrance advertising campaign",
  },
  {
    value: "wooden_table",
    label: "Wooden table",
    prompt: "single product on a richly grained oak tabletop, warm window light, sunlit interior and shelves softly blurred in the background",
  },
  {
    value: "coffee_shop",
    label: "Coffee shop",
    prompt: "single product on a cafe table, cozy coffee shop interior, amber pendant lights and espresso bar bokeh, shallow depth of field",
  },
  {
    value: "office_desk",
    label: "Office desk",
    prompt: "single product on a clean walnut office desk, bright window daylight, modern laptop and green plant softly out of focus",
  },
  {
    value: "marble_surface",
    label: "Marble surface",
    prompt: "single product on veined white Carrara marble, airy premium vanity setting, diffused daylight, elegant beauty advertising photograph",
  },
  {
    value: "outdoor_lifestyle",
    label: "Outdoor lifestyle",
    prompt: "single product on natural stone in a lush green garden, leaves and warm sunlight bokeh, fresh outdoor lifestyle advertising photograph",
  },
] as const;

export const BASE_NEGATIVE_PROMPT =
  "duplicate product, extra product, floating product, distorted silhouette, warped geometry, changed logo, unreadable label, watermark, low resolution, motion blur, noisy";

export const DEFAULT_GENERATION_SETTINGS = {
  steps: 25,
  guidance_scale: 8,
  strength: 0.9,
  controlnet_conditioning_scale: 0.3,
  canvas_size: 512,
} as const;
