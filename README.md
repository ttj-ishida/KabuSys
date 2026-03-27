# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
データ収集（J-Quants）、ETL、ニュースNLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（DuckDB）などを含むモジュール群を提供します。

主な用途例：
- 日次 ETL（株価・財務・カレンダー）の自動実行
- RSS ニュースの収集と銘柄ごとの LLM センチメント評価
- マクロ + テクニカルを組み合わせた市場レジーム判定
- 研究用ファクター計算・特徴量解析
- 発注・約定に対する監査ログ（DuckDB）初期化

---

## 機能一覧

- 環境設定管理（.env の自動読み込み / 必須チェック）
- J-Quants API クライアント
  - 株価日足取得 / 保存（差分・ページネーション対応）
  - 財務データ取得 / 保存
  - JPX マーケットカレンダー取得 / 保存
  - レート制御・リトライ・トークン自動リフレッシュ対応
- ETL パイプライン（差分取得・保存・品質チェックの一連処理）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（RSS）と前処理（SSRF対策・サイズ上限・トラッキング除去）
- ニュース NLP（OpenAI）による銘柄センチメント算出（バッチ処理・リトライ）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュース LLM）
- 研究モジュール（モメンタム/バリュー/ボラティリティ等のファクター計算、IC/統計解析）
- 監査ログスキーマ初期化（signal_events / order_requests / executions）と専用 DB 初期化

---

## セットアップ

前提
- Python 3.10+
- DuckDB、OpenAI SDK、defusedxml 等が必要（下記は代表的な依存）

推奨インストール（ローカル開発時）:
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージをインストール（プロジェクト配布形態により調整）
   - 開発中のローカルパッケージとして: pip install -e .
   - 必要パッケージ（例）:
     pip install duckdb openai defusedxml

3. 環境変数を設定
   - ルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます。
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須（主な）環境変数
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- SLACK_BOT_TOKEN        : Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID       : Slack 通知先チャネル ID
- KABU_API_PASSWORD      : kabuステーション API パスワード（発注等で利用）
- OPENAI_API_KEY         : OpenAI API キー（news scoring / regime scoring）

その他オプション
- KABUSYS_ENV : development | paper_trading | live（デフォルト: development）
- LOG_LEVEL : DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH : SQLite パス（監視用など、デフォルト data/monitoring.db）

例（.env）
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（簡易サンプル）

以下はライブラリの代表的な呼び出し例です。実行前に必須環境変数を設定し、DuckDB ファイルの配置先（DUCKDB_PATH）等を確認してください。

- DuckDB 接続の作成例
  from datetime import date
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL を実行（株価・財務・カレンダー取得 + 品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(res.to_dict())  # ETLResult の概要

- ニュースセンチメントスコアを算出して ai_scores に書き込む
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込み銘柄数:", n_written)

- 市場レジーム判定（1321 の MA200 乖離とマクロニュース）
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20))  # market_regime テーブルに書き込まれる

- 監査ログ用 DuckDB を初期化する
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit_kabusys.duckdb")
  # これで signal_events / order_requests / executions テーブルが作成される

- .env の自動読み込みについて
  パッケージインポート時にプロジェクトルート（.git または pyproject.toml を探索）を見つけると、
  .env → .env.local の順で環境変数を読み込みます。.env.local は上書き可能。

注意点
- LLM 呼び出し（OpenAI）はレスポンスの失敗やレート制限を想定してフォールバックが組まれています（失敗時は 0.0 を返す等）。
- 日付の扱いはルックアヘッドバイアスを避ける設計（関数内で datetime.today() を参照しない）になっています。
- DuckDB に対する executemany の空リストは一部バージョンでエラーになるため、関数側でチェックしてから実行しています。

---

## 主要 API（モジュール別）

- kabusys.config
  - settings: 環境変数アクセス用（settings.jquants_refresh_token 等）
  - .env 自動読み込み（プロジェクトルート検出、.env, .env.local）

- kabusys.data
  - pipeline.run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - jquants_client: fetch_*/save_*（J-Quants API の取得・DuckDB 保存）
  - quality: データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
  - news_collector: RSS 収集（fetch_rss）と前処理
  - calendar_management: 営業日判定・next_trading_day 等、calendar_update_job
  - audit: 監査ログスキーマ初期化（init_audit_schema, init_audit_db）

- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントスコア算出（OpenAI）
  - regime_detector.score_regime: MA200 とマクロニュースを組み合わせた市場レジーム判定

- kabusys.research
  - factor_research.calc_momentum / calc_value / calc_volatility
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats.zscore_normalize（研究用ユーティリティ）

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py                - パッケージ初期化、バージョン定義
- config.py                  - 環境変数 / .env 読込 / settings
- ai/
  - __init__.py
  - news_nlp.py              - ニュースセンチメント算出（OpenAI）
  - regime_detector.py       - 市場レジーム判定（MA200 + マクロLLM）
- data/
  - __init__.py
  - jquants_client.py        - J-Quants API クライアント（取得・保存）
  - pipeline.py              - ETL パイプライン（run_daily_etl など）
  - etl.py                   - ETLResult の公開（再エクスポート）
  - quality.py               - データ品質チェック
  - news_collector.py        - RSS 収集と前処理
  - calendar_management.py   - 市場カレンダー管理（営業日判定・更新ジョブ）
  - stats.py                 - 統計ユーティリティ（zscore_normalize）
  - audit.py                 - 監査ログスキーマ定義 / 初期化
- research/
  - __init__.py
  - factor_research.py       - ファクター計算（Momentum/Value/Volatility）
  - feature_exploration.py   - 将来リターン / IC / 統計サマリー
- monitoring/ (※実装ファイルがあれば監視系モジュール)
- execution/, strategy/ 等（プロジェクト全体のインターフェース実装想定）

各ファイルには詳細なドキュメント文字列（docstring）があり、関数の目的、引数、返り値、設計上の注意点が記載されています。

---

## 運用上の注意

- 本ライブラリには実際の発注・本番口座操作に用いるモジュール群が想定されています。live 環境での運用時は十分なログ・監査・リスク制御を実装してください（KABUSYS_ENV を適切に設定）。
- OpenAI / J-Quants API キーは秘匿情報です。`.env` をリポジトリに含めないでください。
- DuckDB を複数プロセスで同時に書き込む運用は注意が必要です。運用設計に応じて排他制御・接続ポリシーを検討してください。
- テスト時は環境変数自動読み込みを無効化できる（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）ので、ユニットテストで外部依存を制御しやすくなっています。

---

もし README に追加したい使い方の具体例（例: Cron ジョブ設定、Airflow / Prefect の統合サンプル、Slack 通知のサンプル）や、依存関係一覧（requirements.txt 形式）が必要であれば教えてください。必要に応じて追記します。