# KabuSys

日本株向けの自動売買プラットフォーム（ライブラリ）です。  
データ取得（J‑Quants）、ニュース収集、ETLパイプライン、データ品質チェック、監査ログ（トレーサビリティ）など、アルゴリズム取引のバックエンド処理群を提供します。

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群を提供します。

- J‑Quants API からの株価・財務・マーケットカレンダー取得（レートリミット・リトライ対応）
- RSS フィードを用いたニュース収集と銘柄抽出（SSRF/XML脆弱性対策、受信サイズ制限）
- DuckDB を用いたスキーマ定義・永続化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）

設計上の特徴:
- API レート制限と指数バックオフによる堅牢な HTTP クライアント
- データ取得の冪等性（DuckDB への INSERT は ON CONFLICT で更新）
- ニュース収集における SSRF / XML Bomb / 圧縮爆弾対策
- ETL は差分更新（最終取得日を基準）・バックフィルをサポート
- すべての時刻は UTC ベースで扱うことを想定

---

## 機能一覧

- data.jquants_client
  - get_id_token / fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB への冪等保存）
  - レート制限、リトライ、401 時の自動トークンリフレッシュ、fetched_at の記録
- data.news_collector
  - RSS フィードの取得・解析・前処理（URL 除去・空白正規化）
  - 記事ID を正規化 URL の SHA‑256（先頭32文字）で生成し冪等性を確保
  - SSRF/リダイレクト検査、Content-Length やデコード後のサイズ制限、defusedxml による安全な XML パース
  - raw_news / news_symbols への保存ロジック（トランザクション、チャンク挿入、INSERT RETURNING）
- data.schema
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution 層）
  - init_schema(db_path) による初期化（":memory:" サポート）
- data.pipeline
  - run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl（差分取得 + 保存 + 品質チェック）
  - ETLResult による実行結果集約
- data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
  - QualityIssue による問題表現（severity: error|warning）
- data.audit
  - 監査テーブル（signal_events / order_requests / executions）定義と初期化
  - init_audit_schema / init_audit_db
- 設定管理 (config)
  - .env 自動読み込み（プロジェクトルートの .env / .env.local、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - Settings クラス経由で各種環境変数を取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_* 等）
  - KABUSYS_ENV（development|paper_trading|live）と LOG_LEVEL の検証

strategy / execution / monitoring パッケージはエントリ空間（将来的な戦略・発注・監視ロジック）を想定しています。

---

## 要件（依存ライブラリ）

最低限必要なパッケージ（抜粋）：
- Python 3.9+（型表記に | を使用しているため 3.10 以降を想定している箇所もあります）
- duckdb
- defusedxml

インストール例（仮）:
pip install duckdb defusedxml

（実際のプロジェクトでは requirements.txt / pyproject.toml を用意してください）

---

## セットアップ手順

1. リポジトリをクローン / チェックアウト

2. 仮想環境を作成して有効化（例）:
python -m venv .venv
source .venv/bin/activate  # Unix/macOS
.venv\Scripts\activate     # Windows

3. 必要パッケージをインストール:
pip install duckdb defusedxml

4. 環境変数設定:
プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

例 .env（サンプル）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO

5. DuckDB スキーマ初期化（例は後述の使い方参照）

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J‑Quants の refresh token（必須）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネルID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境 (development | paper_trading | live)、デフォルト development
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

注意: .env 自動読み込みはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に行います。CI/テスト等で自動読み込みを抑止する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（簡易チュートリアル）

以下はいくつかの典型的な利用例です。Python REPL やスクリプトで実行します。

1) DuckDB スキーマ初期化
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # ファイルがなければ作成、テーブルを生成

メモリ上 DB を使う場合:
conn = init_schema(":memory:")

2) J‑Quants の ID トークン取得（明示取得）
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用してトークンを取得

3) ETL（1日分のパイプライン）を実行
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # target_date を指定しなければ今日

result は ETLResult オブジェクトで、保存件数や品質チェック結果、エラーメッセージを含みます。
if result.has_errors:
    # ログやアラートを発報

4) ニュース収集ジョブ（RSS）
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)
# sources を省略すると DEFAULT_RSS_SOURCES を使用
results = run_news_collection(conn, known_codes={"7203", "6758"})  # known_codes は既知銘柄セット

results は {source_name: 新規保存件数} の辞書

5) 監査ログ（Audit）初期化
from kabusys.data.schema import init_schema
from kabusys.data.audit import init_audit_schema

conn = init_schema(settings.duckdb_path)
init_audit_schema(conn)  # 監査系テーブルを追加で作成

---

## 主要モジュールの設計ノート（要点）

- jquants_client
  - レート制限（120 req/min）を固定間隔スロットリングで実装
  - リトライ: 408/429/5xx に対して指数バックオフ（最大 3 回）
  - 401 はトークン自動再取得して 1 回だけ再試行
  - 取得時刻（fetched_at）を UTC で記録して Look‑ahead Bias を防止
  - DuckDB への保存は ON CONFLICT DO UPDATE で冪等性を確保

- news_collector
  - defusedxml で安全に XML をパース
  - URL 正規化（utm_* 等のトラッキングパラメータを除去）→ SHA‑256（先頭32文字）を記事IDに
  - SSRF 対策: スキーム検証、DNS 解決してプライベート IP を拒否、リダイレクト先の検査
  - レスポンスサイズ上限と gzip 解凍後の再チェック（Gzip bomb 対策）
  - DB 保存はトランザクション・チャンク挿入で効率化

- pipeline / quality
  - 差分取得（DB の最終日を参照）＋ backfill による後出し修正吸収
  - 品質チェックは全チェックを実行して結果を集約（Fail‑Fast ではない）
  - QualityIssue に詳細（サンプル行等）を含めて返す

- schema / audit
  - データ層を Raw / Processed / Feature / Execution / Audit に分離
  - 生成される各テーブルに制約（CHECK・PRIMARY KEY・FOREIGN KEY）を設け、データ一貫性を担保
  - 監査ログは削除しない前提および UTC タイムゾーン固定を推奨

---

## ディレクトリ構成

リポジトリの主要ファイル/ディレクトリ（抜粋）:

src/
  kabusys/
    __init__.py                 -- パッケージ定義（version など）
    config.py                   -- 環境変数・設定管理（.env 自動読み込み）
    data/
      __init__.py
      jquants_client.py         -- J‑Quants API クライアント（取得・保存ロジック）
      news_collector.py         -- RSS ニュース収集・前処理・DB 保存
      schema.py                 -- DuckDB スキーマ定義・初期化
      pipeline.py               -- ETL パイプライン（差分更新・品質チェック含む）
      audit.py                  -- 監査ログ（signal / order_requests / executions）
      quality.py                -- データ品質チェック
    strategy/
      __init__.py               -- 戦略層（将来の拡張点）
    execution/
      __init__.py               -- 発注・ブローカー連携（将来の拡張点）
    monitoring/
      __init__.py               -- 監視/アラート（将来の拡張点）

その他:
  README.md                     -- （本ファイル）
  .env.example (推奨)           -- 環境変数のテンプレート（プロジェクトに合わせて配置）

---

## 注意事項 / 運用上のヒント

- 本ライブラリは、実際の発注・運用時には十分な安全検証（テストネット／ペーパートレード環境）を行ってください。
- J‑Quants や証券会社 API のレート制限、利用規約を順守してください。
- .env.local は .env より優先して上書きされます（OS 環境変数はさらに優先）。
- ETL 実行はスケジューラ（cron、Airflow など）で定期的に行うことを想定しています。run_daily_etl は idempotent に近い挙動を持ちますが、運用ではバックアップや監査ログを併用してください。
- DuckDB のデータファイルはバックアップ（スナップショット）を推奨します。

---

必要に応じて README を拡張して、CI 設定、テスト実行方法、開発フロー、実運用時のチェックリストなどを追加できます。追加で欲しいサンプルやコマンド（例: 実行スクリプト、systemd ユニット、Dockerfile など）があれば教えてください。