# Customer Portal Imagery

Drop image files here to customize the look of the customer portal. Every
file is **optional** — if missing, the portal renders a tinted placeholder
that matches the violet theme.

## Files the portal looks for

| Filename | Recommended size | Used for |
|---|---|---|
| `hero_banner.jpg` (or `.png`) | 800 × 260 | Big promo banner above the menu |
| `category_bakery.png`         | 96 × 96 transparent | Bakery category card |
| `category_burger.png`         | 96 × 96 transparent | Burger category card |
| `category_beverages.png`      | 96 × 96 transparent | Beverages category card |
| `category_chicken.png`        | 96 × 96 transparent | Chicken category card |
| `category_pizza.png`          | 96 × 96 transparent | Pizza category card |
| `category_seafood.png`        | 96 × 96 transparent | Seafood category card |
| `category_main_dishes.png`    | 96 × 96 transparent | Main Dishes category |
| `category_snacks.png`         | 96 × 96 transparent | Snacks category |
| `category_default.png`        | 96 × 96 transparent | Fallback for any other category |
| `avatar_user.png`             | 256 × 256 (square) | Header user avatar (auto circle-cropped) |

## Naming convention for new categories

The portal converts a category name to its filename like this:

```
"Main Dishes"  →  category_main_dishes.png
"Iced Drinks"  →  category_iced_drinks.png
```

(lowercased, spaces and dashes become underscores). Drop a 96×96 PNG with
that name in this folder and it shows up automatically.

## Per-product images

Product images are managed from the **Products** tab in the staff portal —
click *Edit Product → Choose Image…*. Those files are stored under
`assets/images/` (one folder up) and are shown on the dish cards in the
menu and in the cart line items.
