# KabuSys

KabuSys は日本株向けの自動売買基盤ライブラリです。DuckDB をデータ層に用い、J-Quants などから市場データを取得して ETL → 特徴量生成 → シグナル生成 → 発注（実装層）へと繋ぐ設計になっています。研究（research）用のファクター計算・探索ツールも同梱しています。

バージョン: 0.1.0

---

## 主な特徴

- データ取得
  - J-Quants API クライアント（株価日足・財務データ・マーケットカレンダー）
  - RSS ベースのニュース収集（SSRF / XML bomb / サイズ制限対策含む）
- ETL パイプライン
  - 差分取得、バックフィル対応、品質チェックのフレームワーク
  - DuckDB へ冪等（ON CONFLICT）で保存
- 特徴量 & 戦略
  - ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - Z スコア正規化、ユニバースフィルタ
  - シグナル生成（複数コンポーネントの重み付き統合、Bear レジーム抑制、エグジット判定）
- カレンダー管理
  - JPX カレンダーの差分更新と営業日判定ユーティリティ
- 監査（audit）設計
  - シグナル→発注→約定まで追跡可能な監査テーブル群（UUID によるトレーサビリティ）
- 研究用ユーティリティ
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計サマリ等

---

## 必要要件（例）

- Python 3.10+
- duckdb
- defusedxml

（プロジェクトでは標準ライブラリを優先して使用していますが、DuckDB と defusedxml は外部依存です。）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

パッケージ化されている場合は以下のように開発インストールできます（プロジェクトルートに setup/pyproject がある想定）:
```bash
pip install -e .
```

---

## 環境変数 / 設定

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から自動読込されます（ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動読込を無効化できます）。

必須となる主要な環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API パスワード（execution 層で使用）
- SLACK_BOT_TOKEN — Slack 通知用トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意 / デフォルト:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト `development`
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト `INFO`
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH — モニタリング用 SQLite（デフォルト `data/monitoring.db`）

設定は `kabusys.config.settings` 経由で取得できます。

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成・有効化
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール
   ```bash
   pip install duckdb defusedxml
   # 追加ツールがある場合は適宜インストール
   ```

3. 環境変数を設定する（.env をプロジェクトルートに作成）
   例 `.env`（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=xxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C...
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

   自動読み込みは OS 環境変数 > .env.local > .env の順で行われます。

4. DuckDB スキーマ初期化
   ```python
   # Python REPL またはスクリプトで
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```

---

## 使い方（代表的な呼び出し例）

下記は最小限の呼び出し例です。各関数は DuckDB の接続（kabusys.data.schema.init_schema が返す接続）を受け取ります。

- 日次 ETL（市場カレンダー・株価・財務の差分取得と品質チェック）
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
conn.close()
```

- 特徴量構築（features テーブルへ）
```python
from kabusys.data.schema import init_schema
from kabusys.strategy import build_features
from datetime import date

conn = init_schema("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2026, 1, 31))
print(f"upserted features: {n}")
conn.close()
```

- シグナル生成（signals テーブルへ）
```python
from kabusys.data.schema import init_schema
from kabusys.strategy import generate_signals
from datetime import date

conn = init_schema("data/kabusys.duckdb")
total = generate_signals(conn, target_date=date(2026, 1, 31))
print(f"signals written: {total}")
conn.close()
```

- ニュース収集ジョブ（RSS 収集 → raw_news / news_symbols へ保存）
```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203","6758", "9984"}  # 有効な銘柄コード集合
result = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(result)
conn.close()
```

- カレンダー更新バッチ
```python
from kabusys.data.schema import init_schema
from kabusys.data.calendar_management import calendar_update_job

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved calendar rows: {saved}")
conn.close()
```

- 設定の読み取り
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```

---

## 主なモジュール構成（ディレクトリ構成）

以下はソースツリーの主要ファイル／パッケージの概観（src/kabusys 以下）。

- kabusys/
  - __init__.py
  - config.py — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得 / 保存ユーティリティ）
    - news_collector.py — RSS ニュース収集・整形・保存
    - schema.py — DuckDB スキーマ定義と初期化
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — 市場カレンダー管理・判定ユーティリティ
    - features.py — features API 再エクスポート
    - audit.py — 監査ログ（signal_events / order_requests / executions 等）
  - research/
    - __init__.py
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン・IC・ファクター要約
  - strategy/
    - __init__.py
    - feature_engineering.py — features テーブル生成
    - signal_generator.py — final_score 計算と signals 生成
  - execution/ — 発注 / 実行層（パッケージエントリあり、実装は別途）
  - monitoring/ — 監視用 DB / ロギング（モジュール群）

---

## 設計上の注意点

- ルックアヘッドバイアス対策: すべての戦略・研究関数は target_date 時点で利用可能なデータのみを使用する方針です（fetched_at 等でトレーサビリティを担保）。
- 冪等性: データ保存は ON CONFLICT / RETURNING を活用し冪等に実行されます。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に行われます。自動ロードを停止する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB のファイルパスはデフォルトで `data/kabusys.duckdb`。初回 `init_schema()` 実行時に親ディレクトリが自動作成されます。

---

## 開発・貢献

- バグ報告や機能追加は Pull Request を歓迎します。設計原則（ルックアヘッド回避、冪等性、トレーサビリティ）を尊重してください。
- 大きな変更（DB スキーマ変更等）は DataSchema.md / StrategyModel.md 等の設計ドキュメントと合わせて提案してください。

---

README に記載の使い方はあくまで API の一例です。各関数には詳細なドキュメント文字列（docstring）が付与されていますので、より詳細な挙動や引数仕様はソースの docstring を参照してください。必要なら README にサンプルスクリプトや運用手順を追記します。