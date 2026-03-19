# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）。  
J-Quants / JPX をデータソースとし、DuckDB を永続化層に使う ETL、データ品質チェック、特徴量生成、ニュース収集、監査ログ等のユーティリティを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを支えるデータ基盤と研究／戦略用ユーティリティ群をまとめたパッケージです。主な目的は以下：

- J-Quants API からの株価・財務・マーケットカレンダー取得（レート制限・リトライ・トークン自動リフレッシュ対応）
- DuckDB を用いた冪等（idempotent）なデータ保存スキーマ
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース（RSS）収集と銘柄抽出
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）と共通統計ユーティリティ
- 発注／監査用のスキーマ（監査ログ、order_requests、executions 等）

設計方針として、本番口座・発注 API には直接アクセスしないモジュール（data/research 系）と、発注管理・監査を扱うスキーマが明確に分離されています。

---

## 主な機能一覧

- data.jquants_client
  - J-Quants API の呼び出し（ページネーション対応、レート制限、リトライ、401トークン自動更新）
  - fetch / save 関数: 株価（日足）、財務データ、マーケットカレンダーの取得・DuckDB 保存
- data.schema / data.audit
  - DuckDB 用の完全なスキーマ定義（Raw / Processed / Feature / Execution / Audit 層）
  - スキーマ初期化ユーティリティ（init_schema、init_audit_schema、init_audit_db）
- data.pipeline
  - 日次 ETL パイプライン（run_daily_etl）: カレンダー → 日足 → 財務 → 品質チェック
- data.quality
  - 欠損・重複・スパイク・日付不整合検出（QualityIssue オブジェクトで返却）
- data.news_collector
  - RSS 取得、XML 安全パース、URL 正規化、記事ID生成、raw_news / news_symbols への保存、SSRF 対策、受信サイズ制限
- research.factor_research / research.feature_exploration
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearmanランク相関）計算、ファクター統計サマリ
- data.stats / data.features
  - Zスコア正規化等の共通統計ユーティリティ

---

## セットアップ手順

前提
- Python 3.9+（typing の一部記述や Path 型互換を想定）
- DuckDB を使用（duckdb Python パッケージ）
- defusedxml（RSS パースの安全化）

1. リポジトリを取得し、パッケージをインストール
   - 開発時:
     - pip install -e .
   - または必要パッケージを個別にインストール:
     - pip install duckdb defusedxml

2. 環境変数 / .env の準備
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必須環境変数（少なくとも下記は設定が必要です）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
     - SLACK_BOT_TOKEN — Slack 通知用ボットトークン（必須、使用しない場合でも一部コードが参照する可能性あり）
     - SLACK_CHANNEL_ID — Slack チャネル ID（同上）
     - KABU_API_PASSWORD — kabuステーション API パスワード（発注周りを使う場合）
   - 任意 / デフォルト:
     - KABUSYS_ENV — `development`（default）, `paper_trading`, `live`
     - LOG_LEVEL — `INFO`（default）
     - KABUS_API_BASE_URL — `http://localhost:18080/kabusapi`（kabu station 用）
     - DUCKDB_PATH — `data/kabusys.duckdb`（DuckDB ファイル）
     - SQLITE_PATH — `data/monitoring.db`（SQLite 監視 DB）

3. DuckDB スキーマ初期化（例）
   - Python REPL またはスクリプトで:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")
   - 監査ログを別DBに分ける場合:
     - from kabusys.data.audit import init_audit_db
     - audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   - 既存接続に監査テーブルを追加する場合:
     - from kabusys.data.audit import init_audit_schema
     - init_audit_schema(conn)  # conn は init_schema で得た接続

---

## 使い方（よく使う例）

以下は代表的な呼び出し例です。適宜ログ設定やエラーハンドリングを追加してください。

- 日次 ETL 実行（DB 初期化済みと想定）
  - from kabusys.data.schema import get_connection, init_schema
  - from kabusys.data.pipeline import run_daily_etl
  - conn = init_schema("data/kabusys.duckdb")
  - result = run_daily_etl(conn)  # デフォルトで今日を処理、品質チェックあり
  - result.to_dict()  # 実行結果と品質問題一覧を確認

- 市場カレンダー更新ジョブ
  - from kabusys.data.calendar_management import calendar_update_job
  - conn = init_schema("data/kabusys.duckdb")
  - saved = calendar_update_job(conn)

- ニュース収集（RSS）と銘柄紐付け
  - from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  - conn = init_schema("data/kabusys.duckdb")
  - known_codes = {"7203","6758", ...}  # 既知銘柄コードのセット
  - res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)

- 研究用ファクター計算（例: モメンタム / IC 計算）
  - from kabusys.data.schema import get_connection, init_schema
  - from kabusys.research import calc_momentum, calc_forward_returns, calc_ic, zscore_normalize
  - conn = init_schema("data/kabusys.duckdb")
  - date0 = date(2024, 1, 31)
  - factors = calc_momentum(conn, date0)
  - fwd = calc_forward_returns(conn, date0, horizons=[1,5,21])
  - ic = calc_ic(factors, fwd, factor_col="mom_1m", return_col="fwd_1d")

- J-Quants から生データを直接取得して保存
  - from kabusys.data import jquants_client as jq
  - conn = init_schema("data/kabusys.duckdb")
  - records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  - saved = jq.save_daily_quotes(conn, records)

注意点:
- jquants_client はレート制限（120 req/min）・リトライ・401 リフレッシュを内包しています。`settings.jquants_refresh_token` が必須です。
- news_collector は defusedxml を用いて XML の脆弱性を回避し、SSRF 対策・受信サイズ上限を持ちます。
- ETL は各ステップでエラーハンドリングを行い、品質チェックで検出された問題は QualityIssue として返却されます。致命的エラーの有無は ETLResult を参照してください。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (発注周りで必須)
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須：Slack 通知を使う場合)
- SLACK_CHANNEL_ID (必須：Slack 通知を使う場合)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- KABUSYS_ENV (valid: development, paper_trading, live) — デフォルト development
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL) — デフォルト INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — 自動 .env ロードを無効化

settings オブジェクト経由でコードから参照できます:
- from kabusys.config import settings
- settings.jquants_refresh_token, settings.duckdb_path, settings.env など

---

## ディレクトリ構成（主要ファイル・モジュール）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数/設定管理
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（fetch/save）
    - news_collector.py       — RSS 取得・前処理・DB保存
    - schema.py               — DuckDB スキーマ定義・初期化
    - stats.py                — 統計ユーティリティ（zscore_normalize）
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - features.py             — public re-export（zscore_normalize）
    - calendar_management.py  — market calendar ユーティリティ / 更新ジョブ
    - audit.py                — 監査ログスキーマと初期化ユーティリティ
    - etl.py                  — ETLResult のエクスポート
    - quality.py              — データ品質チェック
  - research/
    - __init__.py             — 研究用ヘルパーのエクスポート
    - factor_research.py      — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py  — 将来リターン / IC / サマリー計算
  - strategy/                  — 戦略実装用プレースホルダ（将来拡張）
  - execution/                 — 発注・実行ロジック（将来拡張）
  - monitoring/                — 監視用モジュール（プレースホルダ）

---

## 開発・運用上の注意

- DuckDB の SQL は多くの場所でパラメータバインド（`?`）を使っています。SQLインジェクション対策済みですが、直接文字列埋め込みには注意してください。
- RSS のパースは defusedxml を使っており、gzip 対応・最大受信バイト制限など DoS 攻撃対策を入れています。
- J-Quants の API 呼び出しはリトライ／バックオフ／429 の Retry-After 考慮／401 の自動トークン更新を行いますが、運用時は API レートやトークン管理を監視してください。
- 本パッケージは研究・データ基盤の実装を中心としており、実際の発注ロジックやブローカー連携は別モジュール（execution 等）で実装する想定です。実運用の前に十分なテストと監査を行ってください。

---

疑問点や追加してほしいセクション（例：具体的なスクリプト例、CI 設定、テスト手順など）があれば教えてください。README を用途に合わせて拡張します。