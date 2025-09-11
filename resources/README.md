# Resources

このディレクトリには、AIBotの動作をカスタマイズするための設定ファイルが含まれています。

## システム指示設定

> [!IMPORTANT]
> AIBotを使用する前に、必ず `./instructions/instructions.yml` を作成してシステム指示を設定してください。

```bash
cd ./instructions/

touch instructions.yml
```

システム指示は、YAMLファイル内で各スラッシュコマンドごとに独立した指示を定義します。そのため、キャラクターの性格や口調、振る舞いなど、コマンドの種類に関わらず**共通して**設定したい内容は、各コマンドごとに**重複して**記述してください。

## LLMモデル設定

> [!NOTE]
> このセクションは、LLMモデルの設定をカスタマイズしたいユーザー向けの情報です。デフォルト設定で十分な場合は、この設定をスキップすることができます。

LLMモデルとそのパラメーターの設定は、`llm-models.json` ファイルにて行います。各スラッシュコマンドに対応するモデルは、`{COMMAND_NAME}_models` というキーで定義されており、使用されるモデルはプロバイダー設定と以下に示す優先順位によって決定されます。

### プロバイダー設定

`/provider` コマンドを使用することで、利用するLLMプロバイダー（Anthropic / Google / OpenAI）を設定します。ここで設定されたプロバイダーを、以下では `有効プロバイダー` といいます。

### 優先順位

* スラッシュコマンドが実行されると、対応する `{COMMAND_NAME}_models` で定義されたモデルを探し、使用します。

* `{COMMAND_NAME}_models` でモデルが定義されていない場合、または定義されているモデルのプロバイダーが `有効プロバイダー` と一致しない場合は、`default_models` で定義されたモデルを使用します。

> [!WARNING]
> `default_models` に `有効プロバイダー` と一致するプロバイダーキーを持つモデルが定義されていない場合、エラーが発生します。使用予定のプロバイダーに対応するモデルは必ず確認し、設定してください。複数または全てのプロバイダー（Anthropic / Google / OpenAI）に対応するモデルを設定することもできます。

## 読み上げ話者設定

> [!NOTE]
> このセクションは、読み上げ機能で使用する話者をカスタマイズしたいユーザー向けの情報です。デフォルト設定で十分な場合は、この設定をスキップすることができます。

読み上げ話者の設定は、`speakers.json` で行います。VOICEVOXエンジンを起動して話者情報を取得し、追加したい `話者の名前`、`スタイル`、`id`を追加してください。

```bash
docker pull voicevox/voicevox_engine:cpu-latest
docker run --rm -p '127.0.0.1:50021:50021' voicevox/voicevox_engine:cpu-latest

# 話者情報全体を取得
curl http://localhost:50021/speakers

# 話者情報を名前、スタイル、idに絞って取得
curl -s http://localhost:50021/speakers \
  | jq -r '.[] | {name, styles: [.styles[] | {id, name}]}'
```
