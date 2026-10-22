# useled-stories-midia

Mídia pública e publicador automático dos stories da [@useledluminarias](https://www.instagram.com/useledluminarias/).

- **branch `stories`**: as artes (JPEG 1080x1920). O Instagram baixa a imagem daqui na hora de publicar.
- **`fila/fila.json`**: a fila de stories (horário, link da arte, tema, modelo). Montada 2x por semana (seg 10h e qui 12h).
- **`.github/workflows/publicar-story.yml`**: publica o próximo story às ~9h e ~20h (Brasília).
- **`.github/workflows/renovar-token.yml`**: renova o token do Instagram todo domingo.

Segredos necessários (Settings → Secrets and variables → Actions):
- `IG_ACCESS_TOKEN`: token do app "USE LED Stories".
- `GH_PAT`: token pessoal do GitHub (fine-grained, só este repositório, permissão *Secrets: Read and write*), usado para salvar o token renovado.
