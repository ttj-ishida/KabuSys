# KabuSys

日本株向け自動売買システム用ライブラリ（モジュール群）。  
データ収集・ETL、特徴量計算、ファクター研究、ニュース収集、マーケットカレンダー管理、監査ログなど、戦略実行に必要な基盤機能を提供します。

主な設計方針：
- DuckDB を中心としたローカルデータプラットフォーム
- J-Quants API 経由で市場データ・財務データを取得（レート制御・リトライ・トークン自動更新対応）
- RSS ベースのニュース収集（SSRF / XML 脆弱性対策済み）
- ETL は差分・バックフィル対応、品質チェックを含む
- 研究用モジュールは外部APIにアクセスせず DuckDB のテーブルのみ参照

バージョン: 0.1.0

---

## 機能一覧

- 環境変数 / .env の自動読み込み（プロジェクトルート検出）
- J-Quants API クライアント
  - 日足（OHLCV）・財務（四半期）・マーケットカレンダー取得（ページネーション対応）
  - レート制御（120 req/min）、リトライ、401 時のトークン自動リフレッシュ
  - DuckDB への冪等保存ユーティリティ
- ETL パイプライン
  - 市場カレンダー・日足・財務の差分取得と保存
  - 品質チェック（欠損・重複・スパイク・日付不整合）
- DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit 層）
- ニュース収集（RSS）
  - URL 正規化・トラッキング除去、記事ID は正規化URLの SHA-256（先頭32文字）
  - SSRF対策、gzip上限、XMLの安全パース（defusedxml）
  - raw_news / news_symbols への冪等保存
- 研究用ファクター計算
  - Momentum / Volatility / Value 等のファクター
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
  - Zスコア正規化ユーティリティ（data.stats.zscore_normalize）
- 監査ログ（信号→発注→約定のトレーサビリティ）用 DDL と初期化ユーティリティ
- マーケットカレンダー管理（営業日判定・next/prev/trading days 等）

---

## 要求環境 / 依存

- Python 3.10+
- 主要依存ライブラリ（例）:
  - duckdb
  - defusedxml

最小インストール例:
```bash
python -m pip install "duckdb" "defusedxml"
```

プロジェクト内に requirements.txt を用意する場合はそちらを参照してください。

---

## 環境変数

自動読み込み順序: OS 環境変数 > .env.local > .env  
（プロジェクトルートは .git または pyproject.toml を探索して決定）

自動ロードを無効化する:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数（必須は README 内で明記）:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API 用パスワード
- KABU_API_BASE_URL (任意) — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

設定参照例:
```python
from kabusys.config import settings
token = settings.jquants_refresh_token
```

---

## セットアップ手順

1. リポジトリをチェックアウト
2. Python 仮想環境を作成・有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```
3. 依存ライブラリをインストール
   ```bash
   pip install duckdb defusedxml
   ```
4. 環境変数を設定（.env をプロジェクトルートに作成）
   例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=yyyyy
   SLACK_BOT_TOKEN=xxxxx
   SLACK_CHANNEL_ID=XXXXX
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```
5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
     ```
   - 監査 DB を別ファイルで用意する場合:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/kabusys_audit.duckdb")
     conn.close()
     ```

---

## 使い方（基本例）

いくつかの典型的なユースケース例を示します。

- 日次 ETL（市場カレンダー・日足・財務の差分取得と品質チェック）:
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
conn.close()
```

- ニュース収集（RSS）を実行して DB に保存:
```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)
conn.close()
```

- J-Quants から日足を直接取得・保存:
```python
from datetime import date
import duckdb
from kabusys.data import jquants_client as jq

records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
conn = duckdb.connect(":memory:")
# 事前に raw_prices テーブルを作成しておくか、init_schema を使う
# jq.save_daily_quotes(conn, records)
```

- ファクター計算（研究用）:
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic

conn = init_schema("data/kabusys.duckdb")
target = date(2024, 1, 31)
factors = calc_momentum(conn, target)
fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
ic = calc_ic(factors, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
conn.close()
```

- Zスコア正規化:
```python
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(records=factors, columns=["mom_1m", "ma200_dev"])
```

---

## 主要 API（モジュールと役割）

- kabusys.config
  - 環境変数読み込み・Settings オブジェクト（settings）を提供
- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token（トークン取得）
- kabusys.data.schema
  - init_schema / get_connection（DuckDB スキーマ定義と初期化）
- kabusys.data.pipeline
  - run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl
- kabusys.data.news_collector
  - fetch_rss / save_raw_news / run_news_collection / extract_stock_codes
- kabusys.data.quality
  - run_all_checks（品質チェック）
- kabusys.research
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.data.stats
  - zscore_normalize
- kabusys.data.audit
  - init_audit_schema / init_audit_db（監査ログテーブル初期化）

---

## ディレクトリ構成

リポジトリの主要ファイル配置（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/                (発注関連モジュール用フォルダ、現在は空 __init__)
    - strategy/                 (戦略モジュール用フォルダ、現在は空 __init__)
    - monitoring/               (監視関連、現在は空 __init__)
    - data/
      - __init__.py
      - jquants_client.py       (J-Quants API クライアント)
      - news_collector.py       (RSS ニュース収集)
      - schema.py               (DuckDB スキーマと初期化)
      - stats.py                (統計ユーティリティ)
      - pipeline.py             (ETL パイプライン)
      - features.py             (特徴量インターフェース)
      - calendar_management.py  (マーケットカレンダー管理)
      - audit.py                (監査ログ初期化)
      - etl.py                  (ETL 公開インターフェース)
      - quality.py              (品質チェック)
    - research/
      - __init__.py
      - feature_exploration.py  (将来リターン/IC/要約)
      - factor_research.py      (Momentum/Value/Volatility 計算)
    - execution/                (発注実装用 placeholder)
    - strategy/                 (戦略実装用 placeholder)

---

## 運用上の注意

- settings.is_live / is_paper / is_dev により実行環境を区別できます。発注処理を行うコードはこれを参照して本番口座への送信を制御してください。
- DuckDB のタイムゾーンや TIMESTAMP の扱いに注意（audit.init_audit_schema は UTC を設定します）。
- J-Quants API のレート制限（120 req/min）はクライアント実装で保護されていますが、大量の並列処理時は追加の調整が必要です。
- ニュース収集では SSRF や XML 外部実行攻撃対策（defusedxml、リダイレクト検査、プライベートIP拒否等）を実装しています。外部からのフィード URL は慎重に管理してください。

---

必要であれば README にサンプル .env.example、より詳細な API 使用例、CI / デプロイ手順、運用ガイド（バックアップ・マイグレーション等）を追加します。どのドキュメントを優先して追加しますか？