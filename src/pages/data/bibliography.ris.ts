import { toRis } from '../../lib/cite';
import { getWorks, record } from '../../lib/works';

export async function GET() {
  const works = await getWorks();
  return new Response(works.map((w) => toRis(record(w))).join('\r\n') + '\r\n', {
    headers: { 'Content-Type': 'application/x-research-info-systems; charset=utf-8' },
  });
}
