import { scholarRecords } from '../../lib/opendata';

export async function GET() {
  return new Response(JSON.stringify(await scholarRecords(), null, 1), { headers: { 'Content-Type': 'application/json; charset=utf-8' } });
}
