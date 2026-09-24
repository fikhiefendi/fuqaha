import { toCsv } from '../../lib/cite';
import { getWorks, record } from '../../lib/works';

export async function GET() {
  const works = await getWorks();
  return new Response(toCsv(works.map(record)), { headers: { 'Content-Type': 'text/csv; charset=utf-8' } });
}
