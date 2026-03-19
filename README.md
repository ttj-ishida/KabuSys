# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ群（モジュール群と ETL / Data / Research / Audit 機能群）です。  
本リポジトリはデータ取得（J-Quants 等）→ DuckDB に格納 → 品質チェック → 特徴量生成 → 研究・戦略開発 → 発注・監査ログ、までの基盤処理を想定しています。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の責務を持つモジュール群を備えたライブラリです。

- データ取得（J-Quants API）と ETL（差分取得・バックフィル）
- DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース（RSS）収集、前処理、記事と銘柄の紐付け
- 研究用のファクター計算（モメンタム・ボラティリティ・バリュー等）および IC/統計
- 発注・監視・監査ログのためのスキーマ準備（監査DB初期化）

設計方針の一部：
- DuckDB を中心に冪等的（ON CONFLICT）にデータ保存
- J-Quants の API レート制御・リトライ・トークン自動更新を実装
- 外部依存を最小化した純粋 Python 実装（ただし DuckDB / defusedxml 等は使用）
- Research / Strategy モジュールは本番取引 API へはアクセスしない（安全設計）

---

## 主な機能一覧

- データ取得 / 保存
  - J-Quants から日足・財務・マーケットカレンダーを取得（pagination 対応）
  - raw_prices / raw_financials / market_calendar などへの冪等保存
- ETL / パイプライン
  - 差分更新（最終取得日からの差分を自動検出）
  - 日次 ETL エントリポイント（run_daily_etl）
  - カレンダー更新ジョブ（calendar_update_job）
- 品質チェック
  - 欠損データ、主キー重複、スパイク（前日比閾値）、日付不整合の検出
- ニュース収集
  - RSS フィードの収集、XML の安全パース、URL 正規化、記事ID生成（SHA256）
  - raw_news / news_symbols への保存と銘柄コード抽出
- 研究（Research）
  - ファクター計算: calc_momentum, calc_volatility, calc_value
  - 将来リターン計算: calc_forward_returns
  - IC（スピアマン）計算: calc_ic
  - ファクター統計サマリ: factor_summary
  - Zスコア正規化ユーティリティ
- スキーマ・監査
  - DuckDB の全テーブル DDL を定義して初期化（init_schema）
  - 監査ログ専用スキーマ（signal_events / order_requests / executions）と初期化ユーティリティ

---

## セットアップ手順

前提:
- Python 3.10 以上（typing 用の表記に依存）
- DuckDB を使用（Python パッケージ duckdb）
- RSS XML 安全パースに defusedxml

1. 仮想環境作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb defusedxml

   （プロジェクト配布に pyproject.toml / requirements.txt があれば pip install -e . または pip install -r requirements.txt を使用）

3. 環境変数設定
   - プロジェクトルートに `.env`（および開発用に `.env.local`）を置くと自動ロードされます。
     自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 必要な主要環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN: Slack ボットトークン（必須）
     - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG/INFO/...（デフォルト INFO）

   - .env のパースはシェル風の export / quotes / コメントを考慮した実装になっています。

4. DuckDB スキーマ初期化（Python REPL やスクリプトで）
   - 例:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

   - 監査ログ専用 DB を別ファイルで用意する場合:
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（実例）

以下は主要ユースケースのサンプルです。

1) 日次 ETL を実行して DuckDB にデータを投入する
   - Python 例:
     from datetime import date
     import duckdb
     from kabusys.data.schema import init_schema
     from kabusys.data.pipeline import run_daily_etl

     conn = init_schema("data/kabusys.duckdb")
     result = run_daily_etl(conn, target_date=date.today())
     print(result.to_dict())

2) ニュース収集ジョブを実行する
   - Python 例:
     from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
     conn = duckdb.connect("data/kabusys.duckdb")
     known_codes = {"7203", "6758", "9984"}  # 事前に有効銘柄セットを準備
     res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
     print(res)

3) ファクター計算・研究用関数の利用
   - Python 例:
     from datetime import date
     from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
     conn = duckdb.connect("data/kabusys.duckdb")
     td = date(2025, 1, 15)
     mom = calc_momentum(conn, td)
     vol = calc_volatility(conn, td)
     val = calc_value(conn, td)
     fwds = calc_forward_returns(conn, td, horizons=[1,5,21])
     # 例: mom と fwd_1d の IC を計算
     ic = calc_ic(mom, fwds, factor_col="mom_1m", return_col="fwd_1d")
     print("IC:", ic)

4) J-Quants から日足を直接取得して保存（テスト用）
   - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
     conn = duckdb.connect("data/kabusys.duckdb")
     recs = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
     saved = save_daily_quotes(conn, recs)

注意:
- 各 API 呼び出しは内部でレート制御・リトライを実施します。
- Research 系関数は prices_daily や raw_financials を前提にしており、本番 API に注文等は送信しません。

---

## 環境変数と設定

- 自動 .env ロード
  - パッケージロード時にプロジェクトルート（.git または pyproject.toml を探索）を検出できる場合、`.env` → `.env.local` の順に自動で環境変数を読み込みます。
  - OS 環境変数は上書きされません。.env.local は override=True のため .env より優先して上書き可能です。
  - 自動ロードを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- Settings で参照するキー（一部）
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (省略可)
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (必須)
  - DUCKDB_PATH, SQLITE_PATH
  - KABUSYS_ENV: development | paper_trading | live
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

settings オブジェクトは kabusys.config.settings として利用できます。

---

## ディレクトリ構成

リポジトリ（src/kabusys 以下）の主要ファイルおよびモジュール:

- src/kabusys/
  - __init__.py
  - config.py              — 環境変数・設定管理（自動 .env ロード含む）
  - data/
    - __init__.py
    - jquants_client.py    — J-Quants API クライアント（取得・保存）
    - news_collector.py    — RSS 収集・前処理・DB保存
    - schema.py            — DuckDB スキーマ定義と init_schema
    - stats.py             — 汎用統計ユーティリティ（zscore_normalize 等）
    - pipeline.py          — ETL パイプライン（run_daily_etl 等）
    - features.py          — features の公開インターフェース
    - calendar_management.py — market_calendar 管理・営業日関連ユーティリティ
    - audit.py             — 監査ログスキーマ & 初期化
    - etl.py               — ETLResult の再エクスポート
    - quality.py           — データ品質チェック
  - research/
    - __init__.py
    - factor_research.py   — momentum / volatility / value の計算
    - feature_exploration.py — forward returns / IC / factor summary
  - strategy/              — 戦略層（雛形）
  - execution/             — 発注実行層（雛形）
  - monitoring/            — モニタリング層（雛形）

各モジュールは docstring と関数レベルのコメントで利用方法や設計方針が明記されています。

---

## 開発・運用上の注意点

- DuckDB の SQL 実行はパラメータバインド（?）を使っており、SQL インジェクションリスクを低減しています。
- J-Quants API はレート制限（120 req/min）に従うため、fetch 系は内部でスロットリングとリトライを行います。短時間に大量リクエストを投げないでください。
- News Collector は SSRF 対策、サイズ上限、defusedxml の使用など安全措置を講じていますが、外部フィードを取り込む際は運用上の監視を推奨します。
- 本番発注を行うコードを追加する際は audit / order_requests / executions の監査スキーマを正しく使い、冪等キー（order_request_id）で二重発注を防止してください。
- KABUSYS_ENV によって本番（live）/ ペーパー / 開発挙動を分岐できます。発注実装を行う際はこのフラグを尊重してください。

---

## ライセンス・貢献

（プロジェクトのライセンスや貢献手順があればここに記載してください）

---

必要であれば README に以下を追加できます：
- CI / テスト実行方法
- pyproject.toml / packaging / リリース手順
- 詳細な API 使用例（jquants_client の各エンドポイント）
- Strategy / Execution の具体的な実装テンプレート

追加の要望があれば知らせてください。