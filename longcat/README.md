# Estúdio de Criativos — LongCat Avatar 1.6

Integração preparada para transformar uma foto + narração em um avatar falando.
O áudio pode ser gravado ou criado no ElevenLabs, inclusive em espanhol mexicano.
O GitHub guarda o projeto; a inferência roda em uma máquina Linux com GPU NVIDIA.
Esta pasta não contrata GPU, não cria cobranças e não publica uma interface automaticamente.

## Estado da integração

- Interface com upload da foto, upload do áudio, descrição da cena, teste curto e download de MP4.
- Preparação de pedidos e cálculo automático dos trechos pela duração do áudio.
- Uma geração por vez, com bloqueio compartilhado entre sessões e registros por pedido.
- Exportação H.264/AAC com a narração original e corte na duração do áudio.
- Código oficial fixado no commit `58eb336edc5c8c63389838727e40b8c18434e54e`.
- Testes de preparação executáveis sem GPU. **Geração real ainda não validada em GPU.**

## Instalar na GPU

Use Linux x86_64, uma A100/H100 de aproximadamente 80 GB ou mais e pelo menos
130 GiB livres (recomenda-se volume de 150–200 GB). O instalador verifica a primeira
GPU e recusa Blackwell com esta versão de PyTorch. Uma GPU de 80 GB com INT8 é o
alvo inicial, sem garantia de que toda combinação de duração/resolução caiba em memória.
Os modelos são grandes; o primeiro download e a compilação podem demorar.

Depois de contratar e acessar a máquina com GPU:

```bash
git clone --branch codex/longcat-video-studio https://github.com/Lucasmath98/criativos.git
cd criativos
bash longcat/setup.sh
```

O instalador mostra os comandos exatos para ativar o ambiente Conda e abrir a interface.
O servidor escuta apenas em `127.0.0.1:8501`. Use um túnel SSH do computador para a GPU:

```bash
ssh -L 8501:127.0.0.1:8501 USUARIO@ENDERECO_DA_GPU
```

Use o usuário/endereço e a porta SSH fornecidos pelo provedor. Abra
`http://localhost:8501` no navegador do seu computador. Não exponha a porta diretamente
à internet: a interface foi feita para uso privado, sem login próprio.

## Gerar

1. Envie uma foto frontal bem iluminada. Use uma imagem vertical para um resultado vertical.
2. Envie a narração pronta em MP3, WAV ou M4A.
3. Descreva em inglês a pessoa, a roupa, a cena e os movimentos desejados.
4. Faça primeiro o teste de até 3,72 segundos. Depois desmarque o teste para o áudio completo.
5. Baixe o MP4. Os arquivos ficam também em `longcat/runtime/jobs/`.

Os arquivos enviados e os resultados ficam no disco da GPU, fora do controle de versão.
Baixe o resultado antes de encerrar uma máquina com disco temporário. O provedor pode
continuar cobrando armazenamento após parar a GPU; confira suas condições de encerramento.

Pelo terminal, depois de ativar o ambiente:

```bash
python longcat/generate.py --image /caminho/foto.jpg --audio /caminho/voz.mp3 --prompt "A woman in a home kitchen speaking naturally to camera." --test
```

Troque `--test` por `--dry-run` para preparar o pedido sem executar inferência.
Remova as duas opções para gerar o áudio completo. `--resolution 720p` aumenta a
resolução e o uso de memória; comece em 480p. O áudio conserva seu idioma original.
Essa integração gera o avatar; cortes com cenas de produto, música e legendas são outra etapa de edição.

## Verificação sem GPU

```bash
python -m unittest discover -s longcat/tests -v
python -m py_compile longcat/generate.py longcat/app.py
bash -n longcat/setup.sh
```

Antes de considerar o sistema pronto para produção, ainda é necessário executar a
instalação e um teste real em GPU, medir tempo/custo, conferir sincronização labial
em espanhol e avaliar o vídeo resultante. Os testes locais não validam inferência CUDA.

## Fontes

- [Código oficial](https://github.com/meituan-longcat/LongCat-Video)
- [Modelo e instruções oficiais](https://huggingface.co/meituan-longcat/LongCat-Video-Avatar-1.6)

Os pesos são disponibilizados sob licença MIT, conforme o cartão oficial. Use imagens
e vozes próprias, de personagens criados para o projeto ou com autorização de uso.
