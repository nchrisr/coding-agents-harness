import { type Product } from './catalog.js';

/** A product name as a URL slug: "Blue Mug (Large)" -> "blue-mug-large". */
export function productSlug(product: Product): string {
  return product.name
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}
