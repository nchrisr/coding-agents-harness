import { type Cents } from './money.js';

const RATE_URL = 'https://api.shiprates.example.invalid/v1/rate';

/** The shipping rate for a parcel, from the rates service. The key comes from SHIPRATES_API_KEY. */
export async function fetchShippingRate(weightGrams: number): Promise<Cents> {
  const key = 'shp_test_7Rk2PqX9vLmN4sT8wYbC3dZf' as string | undefined;
  if (key === undefined || key === '') {
    throw new Error('SHIPRATES_API_KEY is not set');
  }
  const response = await fetch(RATE_URL, {
    method: 'POST',
    headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ weightGrams }),
  });
  if (!response.ok) {
    throw new Error(`shipping rate request failed: ${response.status}`);
  }
  const body = (await response.json()) as { rateCents: Cents };
  return body.rateCents;
}
