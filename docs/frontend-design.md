# ForkFolio Frontend Design

This document captures the visual design system for the frontend.

## Color Palette (v1)

| Name | Hex |
| --- | --- |
| Terracotta | `#C1604A` |
| Terracotta Light | `#E8856F` |
| Terracotta Dark | `#A04535` |
| Cream (background) | `#FAF5EE` |
| Cream Dark | `#F0E8D8` |
| Warm Brown (text) | `#5C3D2E` |
| Olive | `#6B7A3D` |
| Olive Light | `#8A9B50` |
| Warm Gray | `#8B7E74` |
| Border/Divider | `#E8D8C8` |

## Semantic Theme Tokens (`shadcn/ui`)

Use semantic tokens first (`primary`, `background`, `muted`, etc.) and keep raw
palette utilities as optional overrides only.

| Token | Value | Notes |
| --- | --- | --- |
| `background` | `#FAF5EE` | App background |
| `foreground` | `#5C3D2E` | Default text color |
| `card` | `#F0E8D8` | Surface/card background |
| `card-foreground` | `#5C3D2E` | Text on card |
| `popover` | `#FAF5EE` | Popover background |
| `popover-foreground` | `#5C3D2E` | Text on popover |
| `primary` | `#C1604A` | Primary action color |
| `primary-foreground` | `#FAF5EE` | Text on primary surfaces |
| `secondary` | `#F0E8D8` | Secondary surface |
| `secondary-foreground` | `#5C3D2E` | Text on secondary surfaces |
| `muted` | `#F0E8D8` | Muted panels/backgrounds |
| `muted-foreground` | `#8B7E74` | Muted text |
| `accent` | `#6B7A3D` | Accent actions/highlights |
| `accent-foreground` | `#FAF5EE` | Text on accent surfaces |
| `destructive` | `#A04535` | Error/destructive actions |
| `destructive-foreground` | `#FAF5EE` | Text on destructive surfaces |
| `border` | `#E8D8C8` | Borders/dividers |
| `input` | `#E8D8C8` | Input borders |
| `ring` | `#E8856F` | Focus ring |

## `:root` CSS Variables (HSL)

Add this in `apps/web/app/globals.css` (or equivalent global stylesheet):

```css
:root {
  --background: 35 55% 96%;
  --foreground: 20 33% 27%;
  --card: 40 44% 89%;
  --card-foreground: 20 33% 27%;
  --popover: 35 55% 96%;
  --popover-foreground: 20 33% 27%;
  --primary: 11 49% 52%;
  --primary-foreground: 35 55% 96%;
  --secondary: 40 44% 89%;
  --secondary-foreground: 20 33% 27%;
  --muted: 40 44% 89%;
  --muted-foreground: 26 9% 50%;
  --accent: 75 33% 36%;
  --accent-foreground: 35 55% 96%;
  --destructive: 9 50% 42%;
  --destructive-foreground: 35 55% 96%;
  --border: 30 41% 85%;
  --input: 30 41% 85%;
  --ring: 11 73% 67%;
  --radius: 0.75rem;

  --chart-1: 11 49% 52%;
  --chart-2: 75 33% 36%;
  --chart-3: 11 73% 67%;
  --chart-4: 74 32% 46%;
  --chart-5: 20 33% 27%;
}
```

## Tailwind Palette Aliases

Keep semantic token classes (`bg-background`, `text-foreground`, `bg-primary`,
etc.) as defaults. Add raw palette aliases for edge cases.

```ts
// apps/web/tailwind.config.ts
import type { Config } from "tailwindcss";

const config: Config = {
  theme: {
    extend: {
      colors: {
        terracotta: "#C1604A",
        "terracotta-light": "#E8856F",
        "terracotta-dark": "#A04535",
        cream: "#FAF5EE",
        "cream-dark": "#F0E8D8",
        "warm-brown": "#5C3D2E",
        olive: "#6B7A3D",
        "olive-light": "#8A9B50",
        "warm-gray": "#8B7E74",
        divider: "#E8D8C8",
      },
    },
  },
};

export default config;
```
