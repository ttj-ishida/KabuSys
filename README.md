# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買プラットフォームの基盤ライブラリです。データ取得（J-Quants）、ETL、データ品質チェック、特徴量計算、ニュース収集、監査ログなどを備え、戦略開発（Research）と実行（Execution）を支援するためのモジュール群を提供します。

---

## 主要機能（概要）

- J-Quants API クライアント
  - 日足（OHLCV）・財務データ・JPX カレンダーのページネーション対応取得
  - レートリミット順守、リトライ（指数バックオフ）、401時のトークン自動リフレッシュ
  - DuckDB へ冪等保存（ON CONFLICT / DO UPDATE）

- ETL パイプライン
  - 差分取得（バックフィル対応）、market calendar の先読み
  - 保存・品質チェック（欠損・スパイク・重複・日付不整合）
  - ETL 実行結果を表す ETLResult データクラス

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution の多層スキーマ定義と初期化
  - 監査ログ用スキーマ（signal / order_request / executions 等）初期化ユーティリティ

- ニュース収集
  - RSS フィードの取得・正規化・前処理・ID生成（URL 正規化 + SHA-256）
  - SSRF 対策、gzip / レスポンスサイズ制限、XML 攻撃対策（defusedxml）
  - raw_news / news_symbols への冪等保存

- 研究用ユーティリティ（Research）
  - Momentum / Volatility / Value 等ファクター計算
  - 将来リターン計算（forward returns）、IC（Spearman）計算、ファクター統計サマリー
  - Z スコア正規化ユーティリティ（data.stats.zscore_normalize）

- データ品質チェック
  - 欠損データ、スパイク検出、重複、日付整合性チェックを SQL ベースで実行

- 設定管理
  - .env / .env.local / OS 環境変数の自動ロード（プロジェクトルート検出）
  - 必須の環境変数取得時に明快なエラー提示
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化

---

## 依存関係（最小）

- Python 3.9+
- duckdb
- defusedxml

（その他は標準ライブラリで実装されています。実際の運用では Slack 等と連携するためのクライアントが別途必要になる場合があります）

例（pip）:
```
pip install duckdb defusedxml
```

プロジェクトには requirements.txt は含まれていませんが、上記を少なくともインストールしてください。

---

## セットアップ手順

1. リポジトリをチェックアウト / クローン

2. Python 仮想環境を作成して有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 依存ライブラリをインストール
   ```
   pip install duckdb defusedxml
   ```

4. 環境変数の設定
   - 必須:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意（デフォルトあり）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG|INFO|...) — デフォルト: INFO
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db

   簡易例（プロジェクトルートに `.env` を作る）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   ```

   補足:
   - パッケージ起動時に自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（`.git` または `pyproject.toml` を基準）。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 初期化（DuckDB スキーマ）

Python REPL またはスクリプトから DuckDB スキーマを初期化します。

例:
```python
from kabusys.data import schema

# ファイル DB を初期化
conn = schema.init_schema("data/kabusys.duckdb")

# またはインメモリ
# conn = schema.init_schema(":memory:")
```

監査ログ専用 DB を初期化する場合:
```python
from kabusys.data import audit
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
audit.init_audit_schema(conn)  # または audit.init_audit_db("data/audit.duckdb")
```

---

## ETL 実行例

日次 ETL（市場カレンダー・価格・財務データ取得 + 品質チェック）を実行します。

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())

# 結果
print(result.to_dict())
```

個別ジョブ:
- run_prices_etl / run_financials_etl / run_calendar_etl を直接呼べます（テスト用に id_token を注入可能）。

---

## ニュース収集の使い方

RSS フィードを収集して DB に保存します。

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 有効銘柄コードセット（例）

results = run_news_collection(conn, sources=None, known_codes=known_codes)
print(results)  # {source_name: saved_count, ...}
```

備考:
- デフォルト RSS ソースは `DEFAULT_RSS_SOURCES` に定義されています（例: Yahoo Finance のカテゴリ RSS）。
- 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成され、冪等性を保証します。
- SSRF や XML Bomb、gzip bomb、レスポンスサイズ上限などへの防御が組み込まれています。

---

## 研究（Research）モジュールの利用例

特徴量計算（モメンタム・ボラティリティ・バリュー等）や将来リターン、IC 計算、Zスコア正規化などが利用できます。

例: モメンタム計算
```python
from datetime import date
from kabusys.research import calc_momentum
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2024, 1, 31))
# records: list of dict with keys: date, code, mom_1m, mom_3m, mom_6m, ma200_dev
```

将来リターンの計算と IC（Spearman）:
```python
from kabusys.research import calc_forward_returns, calc_ic

fwd = calc_forward_returns(conn, target_date=date(2024,1,31), horizons=[1,5,21])
# factor_records は別途 calc_momentum 等で得たファクター
ic = calc_ic(factor_records, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

Z スコア正規化:
```python
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(records, columns=["mom_1m", "ma200_dev"])
```

---

## J-Quants クライアント（データ取得）

主要 API:
- fetch_daily_quotes(...)
- fetch_financial_statements(...)
- fetch_market_calendar(...)

保存ユーティリティ:
- save_daily_quotes(conn, records)
- save_financial_statements(conn, records)
- save_market_calendar(conn, records)

注意:
- get_id_token() は `JQUANTS_REFRESH_TOKEN` を使用して ID トークンを取得します（settings 経由）。
- API 呼び出しは内部でレート制御とリトライを行います。

---

## ディレクトリ構成（抜粋）

以下はこの README に含まれるコードベースの主要ファイルとモジュール配置の抜粋です。

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - pipeline.py
    - etl.py
    - quality.py
    - stats.py
    - calendar_management.py
    - audit.py
    - features.py
  - research/
    - __init__.py
    - feature_exploration.py
    - factor_research.py
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

主要な責務:
- kabusys.config: 環境変数・設定読み込み
- kabusys.data: データ取得/保存/ETL/スキーマ/品質チェック
- kabusys.research: 特徴量 / 解析ユーティリティ
- kabusys.strategy / execution / monitoring: 戦略・発注・監視ロジックの配置場所（拡張用）

---

## 環境変数一覧（要設定）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意（デフォルトあり）:
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で .env の自動ロードを無効化

---

## 実運用上の注意点

- 本ライブラリはデータ取得・特徴量作成・監査ログなど基盤機能を提供します。実際の発注ロジック・証券会社 API との連携は execution / strategy 層の実装が必要です。
- DuckDB の SQL 実行では SQL インジェクション対策としてパラメータバインド（?）を利用していますが、外部入力の取り扱いは運用側でも注意してください。
- J-Quants の API レート制限（120 req/min）や認証トークンの扱いに注意して運用してください。
- ニュース収集は外部 URL にアクセスするため、ネットワークセキュリティ・SSRF 対策を行っていますが、運用ネットワークのポリシーに従ってください。

---

## 貢献 / 追加情報

- README の内容はコード内の docstring と実装からまとめています。機能追加や API 変更時は README の更新をお願いします。
- より詳細な設計（DataPlatform.md, StrategyModel.md 等）に基づく実装設計ノートが別途存在する想定です。必要に応じて参照して下さい。

---

問題や使い方に関する具体的な実例（スクリプト等）が必要であれば、あなたの利用シナリオ（例: ETL を一日一回 cron で回す、研究用に特定日の特徴量を出す等）を教えてください。適切な例を追記します。