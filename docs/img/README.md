# docs/img/ — Static image assets

## Required before launch

### `social-preview.png` (1200 × 630 px)
Used by Open Graph and Twitter Card meta tags. Referenced in `index.html`.

Suggested content: screenshot of the dashboard map with the title overlaid.
Tools: Figma, GIMP, or screenshot + annotate.

**Until this file exists:** social shares will show no preview image.
GitHub also shows this image as the repo's "social preview" if you set it
under repo → Settings → Social Preview.

### `favicon.png` (32 × 32 px)
PNG fallback for browsers that don't support SVG favicons (old Edge, etc.).
Export the `favicon.svg` at 32×32 px.

### `apple-touch-icon.png` (180 × 180 px)
Used when someone adds the site to their iOS home screen.
Export the `favicon.svg` at 180×180 px with some padding.
