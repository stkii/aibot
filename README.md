# AIBot

![Python](https://img.shields.io/badge/Python-3.12-blue.svg?logo=python&logoColor=white&style=flat&labelColor=24292e)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

**AIBot**は、あなただけのキャラクターを設定して会話を行ったり、キャラクターが文章やコードの修正などの作業をサポートしてくれるDiscord Botです。

## Getting started

以下は、macOSのユーザーがAIBotをローカル環境で起動するまでの手順です。

### 事前準備

* Python 3.12
  * uvの利用を推奨しています。詳細は[uv公式サイト](https://docs.astral.sh/uv/)を参照してください
* Dockerのインストール
* APIキーの取得 (Anthropic、Google、OpenAIからひとつ以上)

### Discordアプリケーションの作成と招待

1. [Discord Developer Portal](https://discord.com/developers/bots)にアクセスし、新しいDiscordアプリケーションを作成してください。

2. Botタブに移動して以下の操作を行ってください：
   - "**Reset Token**"をクリックしてトークンを生成し、安全に保管して`.env`ファイルの`DISCORD_BOT_TOKEN`変数に追加してください。
   - "**SERVER MEMBERS INTENT**"と"**MESSAGE CONTENT INTENT**"を有効にしてください。

3. OAuth2タブに移動し、以下のスコープと権限を選択してボットの招待リンクを生成してください。

    **SCOPES**
    - application commands
    - bot

    **BOT PERMISSIONS**
    - View Channels
    - Send Messages
    - Create Public Threads
    - Send Messages in Threads
    - Manage Messages
    - Manage Threads
    - Read Message History
    - Use Slash Commands

4. 生成されたURLを使用してボットをサーバーに招待してください。


### BOTの起動

#### 1. リポジトリのクローンと依存関係のインストール

```bash
# 1) リポジトリのクローン
git clone https://github.com/stkii/aibot.git
cd aibot/

# 2) 依存関係のインストール
# uvを使用する場合
uv sync

# uvを使用しない場合
pip install -r requirements.lock
```

#### 2. 環境設定ファイルの準備

設定に`.env` ファイルを使用します。以下の手順に従ってください：
* `.env.sample` のコピーを作成し、`.env` に改名
* `.env` に実際の値を入力

#### 3. システム指示の設定

`resources/sample.yml` はシステム指示の一例です。`resources/instructions.yml` を作成し、システム指示を記述してください。

#### 4. VOICEVOXエンジンとBOTの起動

`.env` と `resources/instructions.yml` の内容が**正しいことを確認**してから、botを起動してください。

```bash
# VOICEVOXエンジンの起動
docker pull voicevox/voicevox_engine:cpu-latest
docker run --rm -p '127.0.0.1:50021:50021' voicevox/voicevox_engine:cpu-latest

# Botの起動
python -m src.aibot --log <log_level>
```

> [!TIP]
> `--log <log_level>` パラメータは任意で、ログレベルを設定できます。使用可能な値は `DEBUG`、`INFO`、`WARNING`、`ERROR`、`CRITICAL`（大文字小文字は区別されません）です。
> 指定しない場合、デフォルトで `INFO` が使用されます。

## Docker

事前に、**Docker**がインストール済みであること、`.env` に適切な値が入力されていることを確認してください。

読み上げ機能を利用するには、VOICEVOXエンジンを事前に起動する必要があります。

```bash
# VOICEVOXエンジンの起動
docker pull voicevox/voicevox_engine:cpu-latest
docker run --rm -p '127.0.0.1:50021:50021' voicevox/voicevox_engine:cpu-latest

# AIBotイメージのBuild
docker build -t aibot:latest .

# Botの起動
docker run -d --name aibot --env-file .env aibot:latest
```

## VOICEVOX利用について

### 使用している音声

* **四国めたん**（VOICEVOX:四国めたん）
* **ずんだもん**（VOICEVOX:ずんだもん）
* **春日部つむぎ**（VOICEVOX:春日部つむぎ）
* **冥鳴ひまり**（VOICEVOX:冥鳴ひまり）

### ライセンス・利用規約について

当該プロジェクトはMITライセンスを採用しています。

**改変・再配布する場合**は、**VOICEVOX利用規約**と、**各音声の利用規約**を必ず確認してください。

利用規約は、[VOICEVOX公式サイト](https://voicevox.hiroshiba.jp/)または下記コマンドから確認することができます。

```bash
docker run --rm voicevox/voicevox_engine:cpu-latest cat /opt/voicevox_engine/README.md
```
