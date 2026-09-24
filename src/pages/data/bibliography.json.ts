import { getWorks, record } from '../../lib/works';

export async function GET() {
  const works = await getWorks();
  return new Response(JSON.stringify(works.map(record)), { headers: { 'Content-Type': 'application/json; charset=utf-8' } });
}
