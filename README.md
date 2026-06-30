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
* OpenAI APIキーの取得

### Botの作成と招待

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

#### 1. インストール

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

#### 2. 設定ファイル

設定に `.env` ファイルを使用します。以下の手順に従ってください：
* `.env.sample` のコピーを作成し、`.env` に名前を変更
* `.env` に実際の値を入力

#### 3. Agentsの設定

[resources/](https://github.com/stkii/aibot/tree/main/resources) に移動して、Agentsを定義してください。詳細は、当該ディレクトリの `README.md` を参照してください。

#### 4. BOTの起動

```bash
# Botの起動
python -m src.aibot --log <log_level>
```

> [!TIP]
> `--log <log_level>` パラメータは任意で、ログレベルを設定できます。使用可能な値は `DEBUG`、`INFO`、`WARNING`、`ERROR`、`CRITICAL`（大文字小文字は区別されません）です。
> 指定しない場合、デフォルトで `INFO` が使用されます。

## Docker

[resources/](https://github.com/stkii/aibot/tree/main/resources) に移動して、システム指示を定義してください。必要に応じて、使用するLLMモデルをカスタマイズすることもできます。詳細は、当該ディレクトリの `README.md` を参照してください。

```bash
# サービスの起動（初回はイメージのビルドとダウンロードが実行されます）
docker-compose up -d

# ログの確認
docker-compose logs -f

# サービスの停止
docker-compose down
```

### 個別サービスの操作

```bash
# AIBotのみ再起動
docker-compose restart aibot

# AIBotのログのみ確認
docker-compose logs -f aibot
```
