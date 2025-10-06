# Resources

このディレクトリには、AIBotの動作をカスタマイズするための設定ファイルが含まれています。

## Agents設定

エージェントの設定は、`agents.yml` で行います。このファイルで複数のAIエージェント（キャラクターや目的別の応答者）を定義できます。

### 基本構造

```yaml
agents:
  エージェント名:
    model: モデル名
    instruction: |
      システム指示
```

### 設定項目

- **エージェント名**: 任意の識別子（例：`general`, `code`, `helper`）
- **model**: 使用するAIモデル（例：`gpt-5`, `gpt-4o-mini`）
- **instruction**: エージェントの振る舞いや性格を定義するシステム指示

### 動作の仕組み

ボットは自動的にトリアージエージェントを作成し、メッセージ内容に応じて最適なエージェントを選択して応答します。

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
