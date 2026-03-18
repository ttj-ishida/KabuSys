# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
DuckDB をデータレイクとして利用し、J-Quants からの市場データ取得、ETL、データ品質チェック、特徴量計算、ニュース収集、監査ログ等の機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下のような機能群を想定したモジュール群を提供します。

- データ取得・保存（J-Quants API クライアント、ニュース RSS 収集）
- DuckDB を用いたスキーマ定義・初期化
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC 計算、Z-score 正規化）
- 監査ログ（シグナル → 発注 → 約定のトレース用テーブル）
- 発注 / 戦略 / 監視のための名前空間（実装は各モジュールで管理）

設計方針の要点：
- DuckDB を中心に、冪等性（ON CONFLICT）を意識した保存
- Look-ahead bias 防止のため取得日時（fetched_at）を記録
- API レート制御、リトライ、トークン自動リフレッシュ
- XML/ネットワーク周りのセキュリティ対策（SSRF 対策・defusedxml・サイズ制限）

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（ページネーション、トークンリフレッシュ、レート制限、リトライ）
  - fetch/save の冪等関数: fetch_daily_quotes / save_daily_quotes / fetch_financial_statements / save_financial_statements / fetch_market_calendar / save_market_calendar
- data/schema.py
  - DuckDB のフルスキーマ定義（Raw / Processed / Feature / Execution / Audit 用テーブル）と init_schema/get_connection
- data/pipeline.py
  - run_daily_etl: 市場カレンダー → 株価 → 財務の差分 ETL と品質チェックを一括実行
  - run_prices_etl / run_financials_etl / run_calendar_etl: 個別 ETL ジョブ
- data/quality.py
  - check_missing_data / check_duplicates / check_spike / check_date_consistency / run_all_checks
  - QualityIssue クラスを返却
- data/news_collector.py
  - RSS フィード取得（SSRF 対策、gzip 対応、トラッキングパラメータ除去）、記事の前処理、raw_news への冪等保存、銘柄抽出
- data/etl.py, data/features.py, data/stats.py
  - ETLResult、zscore_normalize 等のユーティリティ公開
- research/factor_research.py, research/feature_exploration.py
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman ρ）計算、factor_summary、rank
- audit モジュール（data.audit.py）
  - signal_events / order_requests / executions テーブルと初期化ユーティリティ（監査ログ）
- 設定管理（config.py）
  - .env 自動読み込み（プロジェクトルート検出）、必須環境変数チェック、設定アクセス用 Settings オブジェクト

---

## セットアップ手順

前提
- Python 3.9+（コードは型ヒントに Union 演算子等を使用）
- DuckDB を利用（pip で導入）
- インターネット接続（J-Quants API / RSS）

推奨手順例:

1. リポジトリをチェックアウト / コピー
   - 例: git clone <repo>

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - 必須: duckdb, defusedxml
   - 例:
     - pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使ってください）

4. 環境変数の準備
   - プロジェクトルートに .env（または .env.local）を置くと、自動でロードされます（config.py の自動ロード機構）。自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 必須変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意 / デフォルトあり:
     - KABUSYS_ENV (development / paper_trading / live) — デフォルト: development
     - LOG_LEVEL (DEBUG / INFO / ...) — デフォルト: INFO
     - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db

   例 .env（参考）
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=xxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. DuckDB スキーマ初期化
   - Python REPL / スクリプトで以下を実行:
     ```python
     from kabusys.config import settings
     from kabusys.data.schema import init_schema

     conn = init_schema(settings.duckdb_path)  # データベースファイルを作成しスキーマを初期化
     ```
   - 監査ログ専用 DB を初期化する場合:
     ```python
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")
     ```

---

## 使い方（代表的な例）

以下は代表的な呼び出し例です。詳細は各モジュールの docstring を参照してください。

1) 日次 ETL の実行（市場カレンダー / 株価 / 財務 / 品質チェック）
```python
from datetime import date
import duckdb

from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

# 初期化済みの DB 接続を取得（既に init_schema を実行済みであることが前提でも可）
conn = init_schema(settings.duckdb_path)

# 基準日を指定して ETL 実行（省略時は今日）
result = run_daily_etl(conn, target_date=date.today())

print(result.to_dict())
```

2) J-Quants から日足を直接取得して保存する（テスト用途）
```python
from kabusys.config import settings
from kabusys.data import jquants_client as jq
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)

# 全銘柄の 2024-01-01〜2024-03-31 の日足を取得して保存
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,3,31))
saved = jq.save_daily_quotes(conn, records)
print("saved:", saved)
```

3) ニュース収集ジョブの実行
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# known_codes を与えると記事と銘柄の紐付けを行う（銘柄セットは別途用意）
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

4) 研究用ファクター計算と IC（Information Coefficient）計算
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

conn = init_schema("data/kabusys.duckdb")
target = date(2024, 1, 31)

mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)

forward = calc_forward_returns(conn, target_date=target, horizons=[1,5,21])

# 例: mom_1m と fwd_1d の IC を計算
ic = calc_ic(mom, forward, factor_col="mom_1m", return_col="fwd_1d")
print("IC (mom_1m vs fwd_1d):", ic)
```

5) Z-score 正規化（クロスセクション）
```python
from kabusys.data.stats import zscore_normalize

# records は [{"code": "...", "momentum": 0.1, ...}, ...]
normalized = zscore_normalize(records, ["momentum", "volatility"])
```

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
- KABUSYS_ENV — 実行環境 (development / paper_trading / live)（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/…）デフォルト INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する（任意）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）

config.Settings を通じて settings.<property> でアクセスできます。必須変数が未設定の場合は ValueError が発生します。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要なソース配置（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント & 保存ロジック
    - news_collector.py            — RSS ニュース収集・保存・銘柄抽出
    - schema.py                    — DuckDB スキーマ定義 / init_schema / get_connection
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - quality.py                   — データ品質チェック
    - stats.py                     — zscore_normalize 等ユーティリティ
    - features.py                  — 特徴量ユーティリティの公開（再エクスポート）
    - etl.py                       — ETLResult の公開（再エクスポート）
    - calendar_management.py       — カレンダー管理ユーティリティ
    - audit.py                     — 監査ログ用スキーマと初期化
  - research/
    - __init__.py
    - factor_research.py           — Momentum/Value/Volatility 等のファクター算出
    - feature_exploration.py       — 将来リターン・IC・summary 等
  - strategy/
    - __init__.py                  — 戦略関連名前空間（実装のエントリ）
  - execution/
    - __init__.py                  — 発注 / 約定管理名前空間（実装のエントリ）
  - monitoring/
    - __init__.py                  — 監視・メトリクス関連（実装のエントリ）

（上記はリポジトリ内の主要ファイルを抜粋した構成です）

---

## 運用上の注意

- 自動取得モジュールは J-Quants のレート制限 120 req/min を尊守する実装になっていますが、運用時はさらにバースティング対策・スロットリングを検討してください。
- ETL は差分更新・バックフィルを行いますが、DB 破損・不整合を避けるため定期的なバックアップ・監査を推奨します。
- ニュース収集では外部の RSS を解析するため、feed の多様性や XML の形式差異により未対応ケースが出る可能性があります。実運用ではソースごとの正規化設定を検討してください。
- 本システムは実際の発注・資金管理については別途リスク管理と監査が必須です（本番口座連携は十分なテストを経て行ってください）。

---

## 開発者向け

- テスト時に環境の自動 .env 読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB 接続は init_schema() で作成すると必要な全テーブルが初期化されます。unit test では ":memory:" を使用してインメモリ DB を使うことができます。
- 各モジュールの docstring に使用上の注意や設計方針が記載されています。まずはそれらを参照してください。

---

もし README の出力形式（英語版の追加、より詳細なサンプルスクリプト、CI/テスト手順、requirements.txt 例など）の追加や、特定の利用シナリオ（paper_trading 環境での運用手順など）を希望される場合は教えてください。必要に応じて追記します。