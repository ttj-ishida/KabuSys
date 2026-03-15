# KabuSys

日本株向けの自動売買システム（ライブラリ）です。  
マーケットデータ収集・前処理・特徴量生成・シグナル生成・発注/約定・モニタリングのための基盤機能を提供します。

バージョン: 0.1.0

---

## 主な特徴

- 環境変数による設定管理（.env 自動読み込み機能付き）
- DuckDB を用いた多層データスキーマ（Raw / Processed / Feature / Execution）
- 発注・約定・ポジション管理用のテーブル群
- J-Quants / kabuステーション / Slack 連携のための設定項目を用意
- テスト・ローカル実行を考慮した設定オーバーライド機能

---

## 要件

- Python 3.10+
- duckdb（データベース）
- （実際に外部 API を使う場合は）Requests 等の HTTP クライアント、Slack ライブラリ等を別途追加

依存パッケージはプロジェクトに合わせて requirements.txt や pyproject.toml を用意してください。最低限 DuckDB が必要です:

例:
```
pip install duckdb
```

---

## セットアップ

1. リポジトリをクローン／展開
2. 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```
3. 必要パッケージをインストール
   ```
   pip install duckdb
   # 実運用で必要な追加パッケージは別途インストール
   ```
4. 環境変数の準備
   - プロジェクトルートに `.env` を作成してください（.env.example を参考に）。  
   - 自動読み込みは、プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を起点に `.env` → `.env.local` の順で行われます。
   - OS 環境変数は .env の値より優先されます。

自動ロードを無効化したいとき（テスト等）は、環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してからパッケージをインポートしてください。

---

## 環境変数（主な設定項目）

必須項目:
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API のパスワード
- SLACK_BOT_TOKEN: Slack ボットトークン
- SLACK_CHANNEL_ID: Slack チャネル ID

任意／デフォルトあり:
- KABU_API_BASE_URL: kabuステーション API のエンドポイント（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルトは development
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL。デフォルト: INFO）

.env のパースはシェル風の簡易パーサに対応しています:
- export KEY=val 形式を許容
- クォート（' or "）内のエスケープ処理に対応
- クォートなしの場合は、空白直前の `#` をコメントとして扱います

例（.env）:
```
JQUANTS_REFRESH_TOKEN="your-jquants-refresh-token"
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（サンプル）

- 設定参照:
```python
from kabusys.config import settings

token = settings.jquants_refresh_token
if settings.is_live:
    # ライブ用処理
    ...
```

- DuckDB スキーマ初期化:
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は Path オブジェクトを返します
conn = init_schema(settings.duckdb_path)  # ファイルがなければ親ディレクトリを作成して初期化
# conn は duckdb.DuckDBPyConnection オブジェクト
```

- 既存 DB に接続:
```python
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
```

- 自動環境読み込みを無効化する（テストなど）:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
python -c "import kabusys; ..."
```

---

## ディレクトリ構成

プロジェクトは src レイアウトを採用しています。主要ファイルは以下の通りです。

- src/
  - kabusys/
    - __init__.py
    - config.py             -- 環境変数・設定管理（.env 自動読み込み、Settings クラス）
    - data/
      - __init__.py
      - schema.py          -- DuckDB スキーマ定義と初期化（init_schema, get_connection）
    - strategy/
      - __init__.py         -- 戦略関連（今後実装）
    - execution/
      - __init__.py         -- 発注・実行関連（今後実装）
    - monitoring/
      - __init__.py         -- 監視・記録関連（今後実装）

主要な DB テーブル（schema.py に定義）
- Raw レイヤー: raw_prices, raw_financials, raw_news, raw_executions
- Processed レイヤー: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature レイヤー: features, ai_scores
- Execution レイヤー: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance

インデックスや外部キー制約も定義済みで、典型的なクエリパターンに最適化されています。

---

## 開発メモ / 注意点

- 型注釈や構文により Python 3.10 以上が想定されています。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われるため、CWD に依存しません。
- init_schema() は冪等（既存テーブルがあれば作成をスキップ）になっています。
- 実取引（live）で使用する場合は、KABUSYS_ENV を `live` に設定し、十分な検証を行ってください。

---

必要に応じて README に追加したい項目（API リファレンス、運用手順、例の戦略など）があれば教えてください。