---
name: Institutional Modernity
colors:
  surface: '#f8f9fa'
  surface-dim: '#d9dadb'
  surface-bright: '#f8f9fa'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f3f4f5'
  surface-container: '#edeeef'
  surface-container-high: '#e7e8e9'
  surface-container-highest: '#e1e3e4'
  on-surface: '#191c1d'
  on-surface-variant: '#5d3f3c'
  inverse-surface: '#2e3132'
  inverse-on-surface: '#f0f1f2'
  outline: '#926f6b'
  outline-variant: '#e7bdb8'
  surface-tint: '#c00014'
  primary: '#ba0013'
  on-primary: '#ffffff'
  primary-container: '#e31e24'
  on-primary-container: '#fffafa'
  inverse-primary: '#ffb4ab'
  secondary: '#555f6f'
  on-secondary: '#ffffff'
  secondary-container: '#d6e0f3'
  on-secondary-container: '#596373'
  tertiary: '#545b69'
  on-tertiary: '#ffffff'
  tertiary-container: '#6d7482'
  on-tertiary-container: '#fcfbff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#ffdad6'
  primary-fixed-dim: '#ffb4ab'
  on-primary-fixed: '#410002'
  on-primary-fixed-variant: '#93000d'
  secondary-fixed: '#d9e3f6'
  secondary-fixed-dim: '#bdc7d9'
  on-secondary-fixed: '#121c2a'
  on-secondary-fixed-variant: '#3d4756'
  tertiary-fixed: '#dce2f3'
  tertiary-fixed-dim: '#c0c7d6'
  on-tertiary-fixed: '#151c27'
  on-tertiary-fixed-variant: '#404754'
  background: '#f8f9fa'
  on-background: '#191c1d'
  surface-variant: '#e1e3e4'
typography:
  headline-xl:
    fontFamily: Inter
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  gutter: 20px
  margin-mobile: 16px
  margin-desktop: 32px
---

## Brand & Style
The design system is engineered for high-density administrative environments where clarity, speed, and institutional trust are paramount. The personality is professional and systematic, utilizing a "Modern Institutional" aesthetic that balances the vibrant energy of the brand's heritage with the sober requirements of data management. 

The visual narrative prioritizes utility and legibility. By using generous whitespace and a structured hierarchy, the system reduces cognitive load for power users who interact with the interface for extended periods. The resulting emotional response should be one of confidence, reliability, and precision.

## Colors
The palette is anchored by a high-chroma brand red, used strategically for primary actions and brand presence. To ensure a professional atmosphere suitable for administrative work, this red is complemented by a "Professional Grey" scale that manages depth and information hierarchy.

- **Primary Red:** Reserved for key call-to-actions, active states, and critical alerts.
- **Secondary/Neutral:** A range of cool-toned greys (from #1F2937 to #F9FAFB) provides the structural foundation for sidebars, headers, and backgrounds.
- **Semantic Colors:** Success (Green), Warning (Amber), and Info (Blue) should be desaturated slightly to remain harmonious with the vibrant primary red.

## Typography
This design system utilizes **Inter** exclusively to leverage its exceptional legibility and neutral, systematic tone. The type scale is optimized for data-heavy applications, emphasizing clear distinctions between headers and tabular data.

- **Scale:** A tight scale is used to maintain density in dashboards.
- **Weight:** Bold (700) and Semi-Bold (600) are used strictly for navigation and primary headings. Regular (400) is used for all body text to ensure maximum readability in long-form data entry.
- **Contrast:** High-contrast ratios between text and background are mandatory to meet institutional accessibility standards.

## Layout & Spacing
The layout follows a **fluid grid** model designed to maximize screen real estate on large administrative displays while remaining fully responsive for tablet-based field work.

- **Grid System:** A 12-column grid is standard for desktop. For dashboard views, a "Compact Mode" may be toggled, reducing the 16px gutter to 12px.
- **Rhythm:** An 8px linear scale (with a 4px sub-step) governs all spatial relationships. 
- **Adaptation:** On mobile devices, the 12-column grid collapses to a single-column stack with 16px side margins. Navigation transitions from a persistent left-hand sidebar to a bottom-tab bar or "hamburger" drawer.

## Elevation & Depth
To maintain an "Institutional" feel, depth is conveyed through **Tonal Layers** rather than aggressive shadows. This creates a flat, professional surface that feels integrated rather than floating.

- **Surface Tiers:** Backgrounds use the lightest grey (#F9FAFB). Content containers use pure white (#FFFFFF) with a subtle 1px border (#E5E7EB).
- **Interactive Depth:** Only primary buttons and active modals use "Ambient Shadows"—soft, 10% opacity grey shadows with a 4px-8px blur—to indicate focus without breaking the flat aesthetic.
- **Focus States:** High-visibility focus rings in the brand primary red (#E31E24) with a 2px offset are used for keyboard navigation.

## Shapes
Following the "Round Four" logic, the system uses a **Rounded** shape language (Level 2). This provides a modern, friendly touch that softens the rigidity of an administrative system without appearing overly casual.

- **Component Radius:** Buttons, inputs, and cards use a 0.5rem (8px) corner radius.
- **Large Containers:** Modals and large dashboard panels use 1rem (16px) to clearly define major content areas.
- **Circular Elements:** Avatars and icon backplates remain fully circular to echo the "C" motif in the brand logo.

## Components
Consistent component styling ensures the system remains intuitive across different administrative modules.

- **Buttons:** Primary buttons are solid brand red (#E31E24) with white text. Secondary buttons use a grey outline. Transitions should be a fast 150ms hover-state darkening.
- **Input Fields:** Use a 1px border (#D1D5DB). Upon focus, the border changes to the primary red with a soft 2px glow. Labels are always positioned above the input in `label-sm`.
- **Data Tables:** The heart of the system. Use `body-sm` for row content to maximize density. Headers are `label-sm` with a subtle grey background (#F3F4F6) and sticky positioning.
- **Chips/Status Tags:** Use a "Pastel" background logic (e.g., 10% opacity of the status color) with high-contrast text for high legibility without being distracting.
- **Side Navigation:** A dark-themed sidebar (#111827) provides a strong anchor for the layout, with active states highlighted by a vertical brand-red bar on the left edge of the menu item.