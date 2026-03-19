# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、ETL、スキーマ管理、ニュース収集、品質チェック、ファクター計算（リサーチ）、監査ログなど、自動売買システムに必要な基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

このリポジトリは以下の目的を持つモジュール群で構成されています。

- J-Quants API からの株価・財務・カレンダーデータ取得と DuckDB への保存（冪等）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- ニュース（RSS）収集と記事 → 銘柄紐付け
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ファクター計算（Momentum/Value/Volatility 等）と特徴量探索（将来リターン・IC 等）
- 監査ログ（シグナル → 発注 → 約定 のトレーサビリティ）
- 統計ユーティリティ（Zスコア正規化など）

設計方針として、DuckDB を中核に据え、外部 API 呼び出しはデータ取得層に限定し、リサーチ・戦略処理は DB のみ参照することで安全性と再現性を担保します。

---

## 機能一覧

主な提供機能（モジュール別）

- kabusys.config
  - .env 自動ロード（プロジェクトルート検出）
  - 必須設定の取得（例: JQUANTS_REFRESH_TOKEN）
  - 環境切替（development / paper_trading / live）とログレベル検証
- kabusys.data.jquants_client
  - J-Quants API クライアント（ページネーション、リトライ、トークン自動リフレッシュ、レートリミット制御）
  - fetch / save 用関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, save_* 系
- kabusys.data.schema
  - DuckDB スキーマ定義と init_schema(db_path)
  - スキーマは Raw / Processed / Feature / Execution 層に分離
- kabusys.data.pipeline / etl
  - 差分 ETL（run_prices_etl, run_financials_etl, run_calendar_etl）
  - 日次パイプライン run_daily_etl（品質チェック含む）
- kabusys.data.news_collector
  - RSS 取得（SSRF 対策、gzip/サイズ制限、XML 安全パース）
  - 記事正規化・ID生成・raw_news 保存・銘柄抽出と紐付け
- kabusys.data.quality
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
- kabusys.data.calendar_management
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- kabusys.research
  - ファクター計算: calc_momentum, calc_volatility, calc_value
  - 特徴量探索: calc_forward_returns, calc_ic, factor_summary, rank
  - 統計ユーティリティ再エクスポート: zscore_normalize
- kabusys.data.audit
  - 監査ログ（signal_events, order_requests, executions）の定義と初期化

また、strategy/execution/monitoring 用のパッケージエントリを用意しています（将来的な戦略エンジン・発注実装向け）。

---

## セットアップ手順

前提
- Python 3.10 以上（ソース内での型注釈 Path | None 等を使用）
- ネットワークアクセス（J-Quants API 等）
- DuckDB を利用（ローカルファイルまたは :memory:）

1. リポジトリをクローンして仮想環境を作成
   ```
   git clone <repo-url>
   cd <repo-dir>
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. 依存パッケージをインストール（最低限）
   ```
   pip install duckdb defusedxml
   ```
   ※ 実行環境に応じて追加ライブラリが必要になる場合があります。

3. 環境変数の設定
   - プロジェクトルートに `.env` を置くと自動的に読み込まれます（config.py の自動ロード）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   重要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - KABU_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - DUCKDB_PATH: デフォルト DB パス（例: data/kabusys.duckdb）
   - SQLITE_PATH: モニタリング用 SQLite パス（例: data/monitoring.db）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. スキーマ初期化（DuckDB）
   Python REPL またはスクリプトで:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```
   これで必要なテーブルとインデックスが作成されます。

---

## 使い方（代表的な例）

以下は主要ユースケースの簡単な利用例です。

1) 日次 ETL を実行する
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)
print(result.to_dict())
```

2) J-Quants から日足をフェッチして保存
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = save_daily_quotes(conn, records)
print(f"Saved {saved} rows")
```

3) ニュース収集ジョブを実行する
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes はテキストから抽出する有効な銘柄コードの集合
known_codes = {"7203", "6758", "9984"}
result = run_news_collection(conn, known_codes=known_codes)
print(result)  # {source_name: saved_count}
```

4) ファクター計算・リサーチ
```python
from kabusys.data.schema import get_connection
from kabusys.research import (
    calc_momentum, calc_volatility, calc_value,
    calc_forward_returns, calc_ic, factor_summary, zscore_normalize
)
from datetime import date

conn = get_connection("data/kabusys.duckdb")
target = date(2024, 1, 31)

mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)

fwd = calc_forward_returns(conn, target, horizons=[1,5])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
summary = factor_summary(mom, ["mom_1m", "mom_3m", "ma200_dev"])
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

5) スキーマの監査ログ初期化（監査専用 DB）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/kabusys_audit.duckdb")
```

---

## 設定 (環境変数の一覧)

主要な環境変数（config.Settings が参照するもの）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API パスワード
- KABU_API_BASE_URL — kabu API ベース URL (デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須) — Slack Bot token
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH — SQLite（監視用）パス (デフォルト: data/monitoring.db)
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）

注意: config モジュールはプロジェクトルート（.git または pyproject.toml を含む親ディレクトリ）から .env/.env.local を自動読み込みします。テストなどで自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成

主要なファイル/モジュール一覧（抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数/設定管理
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch/save）
    - news_collector.py — RSS ニュース収集 / 前処理 / DB 保存
    - schema.py — DuckDB スキーマ定義 & init_schema / get_connection
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — マーケットカレンダー管理
    - audit.py — 監査ログ用スキーマ初期化
    - quality.py — データ品質チェック
    - features.py — 特徴量ユーティリティ（再エクスポート）
    - etl.py — ETL 関連の公開型エクスポート
  - research/
    - __init__.py — 研究用 API の再エクスポート
    - feature_exploration.py — 将来リターン / IC / summary
    - factor_research.py — Momentum / Value / Volatility 計算
  - strategy/
    - __init__.py — 戦略層エントリ（将来的に実装）
  - execution/
    - __init__.py — 発注実装エントリ（将来的に実装）
  - monitoring/
    - __init__.py — 監視/メトリクス用（将来的に実装）

---

## 追加メモ / 運用上の注意

- DuckDB ファイルの親ディレクトリは init_schema / init_audit_db が自動作成します。
- J-Quants API はレート制限があります（モジュール内で制御）。高頻度での大量取得は避けてください。
- news_collector は外部 RSS をパースするため、XML 攻撃（XML bomb 等）を想定して defusedxml を使用し安全対策を講じています。RSS の URL は http/https のみ許可し、SSRF 防止のためプライベートアドレスへのアクセスは拒否します。
- run_daily_etl 等の ETL は各ステップで例外処理を行い、可能な限り他処理を継続する設計です。結果は ETLResult で確認してください。
- 本番発注（live）環境では十分なテスト・監査を行ったうえで使用してください（本コードベースはデータ取得・調査・監査の基盤を提供しますが、実際の発注モジュールは別途実装が必要です）。

---

もし README に追加したいサンプルスクリプト、CI/デプロイ手順、テストケースや依存関係の固定（requirements.txt / pyproject.toml）などがあれば、要件を教えてください。README をそれに合わせて拡張します。