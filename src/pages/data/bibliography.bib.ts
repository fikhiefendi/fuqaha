import { toBibtex } from '../../lib/cite';
import { getWorks, record } from '../../lib/works';

export async function GET() {
  const works = await getWorks();
  return new Response(works.map((w) => toBibtex(record(w))).join('\n\n') + '\n', {
    headers: { 'Content-Type': 'application/x-bibtex; charset=utf-8' },
  });
}
