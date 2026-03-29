# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ群です。  
ETL、ニュース収集・NLP、ファクター計算、監査ログ、J-Quants クライアントなどを含み、バックテスト・研究・本番運用の基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は下記の目的で設計された Python パッケージです。

- J-Quants API から株価・財務・カレンダー等を安全に取得して DuckDB に格納する ETL パイプライン
- RSS を用いたニュース収集と前処理、LLM を用いたニュースセンチメント評価（銘柄単位）
- 市場レジーム判定（ETF の移動平均乖離 + マクロニュースの LLM センチメントを合成）
- 研究用のファクター計算・特徴量解析ユーティリティ（モメンタム、ボラティリティ、バリュー等）
- データ品質チェック・監査ログ（signal → order → execution）用スキーマと初期化ユーティリティ
- 設定は環境変数 / .env ファイルで管理（自動読み込み機能あり）

設計方針の例:
- ルックアヘッドバイアス防止（内部で datetime.today() を使わない等）
- API 呼び出しに対する堅牢なリトライ・フェイルセーフ
- 冪等（idempotent）なデータ保存

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（fetch / save 関数、トークン自動リフレッシュ、レートリミット制御）
  - ニュース収集（RSS の正規化、SSRF 対策、重複防止）
  - マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログスキーマ初期化（signal_events, order_requests, executions）
  - 統計ユーティリティ（zscore_normalize など）
- ai
  - ニュース NLP（銘柄ごとのセンチメントを LLM で評価：score_news）
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成：score_regime）
- research
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 特徴量探索・IC 計算・サマリー（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - 環境変数の読み込み・管理（.env 自動ロード、Settings クラス）

---

## セットアップ手順

前提: Python 3.9+（typing 表記に依存するため）を想定しています。

1. リポジトリをチェックアウト／インストール
   - 開発中はソース直下で直接利用できます。パッケージ化する場合は通常通り setuptools/poetry 等でインストールしてください。

2. 必要パッケージをインストール（例）
   - pip を使用する例:
     pip install duckdb openai defusedxml

   - 実運用ではその他ログ周りや HTTP ライブラリ等が必要になる可能性があります。requirements.txt がある場合はそちらを参照してください。

3. 環境変数（.env）を準備
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（config.py の自動ロード）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テストで便利）。

   必須の環境変数例（.env の最小例）:
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - KABU_API_PASSWORD=your_kabu_api_password
   - SLACK_BOT_TOKEN=xoxb-...
   - SLACK_CHANNEL_ID=C12345678
   - OPENAI_API_KEY=sk-...
   - （任意）KABUSYS_ENV=development|paper_trading|live
   - （任意）LOG_LEVEL=INFO|DEBUG

   さらにデータベースパス（デフォルト）:
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db

4. DB 初期化（監査ログ用など）
   - 監査ログ用 DB を初期化するには:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

   - ETL で使う DuckDB ファイルを準備する（設定に合わせて path を変更）

---

## 使い方（簡単なサンプル）

以下は主要な操作例です。実行前に .env（または環境変数）で必要なキーを設定してください。

- DuckDB 接続の作成:
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行:
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメント（LLM）による銘柄スコア付け:
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {n_written}")

- 市場レジーム判定（LLM + MA200）:
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログスキーマ初期化（既存接続に追加）:
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)

- 監査専用 DB を作成:
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")

注意点:
- LLM（OpenAI）を使う関数は `OPENAI_API_KEY` でキーを解決します。引数で api_key を渡すことも可能です。
- J-Quants API 利用は `JQUANTS_REFRESH_TOKEN` が必須です。
- ETL / API 呼び出しはネットワーク・API レート制限に依存するため、実行環境で適切にキーとネットワークを設定してください。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD : kabuステーション API パスワード（必須）
- KABU_API_BASE_URL : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY : OpenAI の API キー（LLM 関連で使用）
- SLACK_BOT_TOKEN : Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID : Slack 通知先チャンネルID（必須）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH : sqlite（モニタリング用）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV : environment（development / paper_trading / live）
- LOG_LEVEL : ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定すると .env 自動読み込みを無効化

config.Settings を通じて型安全に取得できます（例: settings.jquants_refresh_token）。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内部の主要モジュール構成です（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数管理 / Settings
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP（score_news）
    - regime_detector.py      — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（fetch / save / auth / rate limit）
    - pipeline.py             — ETL パイプライン（run_daily_etl など）、ETLResult
    - etl.py                  — ETLResult 再エクスポート
    - news_collector.py       — RSS 取得・前処理・保存
    - calendar_management.py  — 市場カレンダー管理（営業日判定等）
    - quality.py              — データ品質チェック
    - stats.py                — 統計ユーティリティ（zscore_normalize）
    - audit.py                — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py      — ファクター計算（momentum, volatility, value）
    - feature_exploration.py  — 特徴量解析・IC・サマリー
  - research/...              — 研究用ユーティリティ群

（実行時に利用するテーブル名の例）
- raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, prices_daily, market_regime, signal_events, order_requests, executions など

---

## 開発 / テストに関するメモ

- config.py はプロジェクトルート（.git または pyproject.toml がある親ディレクトリ）を探索して `.env` / `.env.local` を自動的に読み込みます。テスト時には `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動読み込みを止めてください。
- LLM / 外部 API 呼び出し部分は内部で分離されており、ユニットテストでは _call_openai_api や _urlopen などをモックしてテスト可能です（ソースに注釈あり）。
- DuckDB を用いるためテストでは `:memory:` を利用してインメモリ DB を作ることができます（例: init_audit_db(":memory:")）。

---

## 参考（実運用での注意点）

- 本ライブラリは実際の発注処理を担うものではありません（発注 API は別途実装が必要）。監査ログや order_requests テーブルは発注処理と連携するためのスキーマを提供します。
- 本番（live）運用時は config.Settings の env を "live" に設定し、ログレベルやキー管理に注意してください。
- LLM（OpenAI）に渡すデータやレスポンス取り扱いには料金・プライバシーの考慮が必要です。

---

必要であれば README に以下を追加できます:
- 具体的な .env.example（テンプレート）
- CI / デプロイ手順
- 詳細な DB スキーマ（各テーブル列の説明）
- よくあるトラブルシュート（API トークン更新、レート制限エラー、DuckDB バージョン互換性 など）

必要な追加内容があれば教えてください。