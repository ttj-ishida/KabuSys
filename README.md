# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL、ニュースNLP、マーケットレジーム判定、ファクター計算、監査ログなどのユーティリティを提供します。

---

## プロジェクト概要
KabuSys は日本株の自動売買システムやリサーチ環境向けに設計された Python モジュール群です。主に以下を提供します。

- J-Quants API を用いたデータ取得（株価、財務、JPX カレンダー）
- ETL パイプライン（差分取得・保存・品質チェック）
- ニュース収集・NLP スコアリング（OpenAI を用いたセンチメント評価）
- 市場レジーム判定（ETF とマクロニュースを合成）
- ファクター計算・特徴量探索（モメンタム、ボラティリティ、バリュー等）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- データ品質チェック、マーケットカレンダー管理 等

設計方針として、ルックアヘッドバイアス回避、冪等操作、堅牢な API リトライやフェイルセーフ、DuckDB を使ったローカル保存が採用されています。

---

## 主な機能一覧
- data
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save）
  - カレンダー管理（is_trading_day, next_trading_day, get_trading_days 等）
  - ニュース収集（RSS 取得、前処理、安全対策付き）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（score_news：銘柄ごとにセンチメントを算出）
  - レジーム判定（score_regime：ETF MA とマクロセンチメントを合成）
- research
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - 環境変数・設定管理（Settings）

---

## 要件（推奨）
- Python 3.10+
- 必要パッケージ（代表例）:
  - duckdb
  - openai
  - defusedxml
  - （その他：標準ライブラリのみで実装されている部分多数）
- J-Quants API のリフレッシュトークン
- OpenAI API キー（ニュースNLP / レジーム判定で使用）
- 必要に応じて kabuステーション API パスワード、Slack トークン 等

依存関係はプロジェクトの packaging / requirements を参照してください。ローカルで利用する際は少なくとも上のライブラリを pip でインストールしてください。

例:
pip install duckdb openai defusedxml

開発パッケージを editable インストールする例:
pip install -e .

---

## セットアップ手順

1. リポジトリをクローン / 取得
   - 任意の取得方法でプロジェクトをローカルに置いてください。

2. Python 環境準備
   - Python 3.10+ の仮想環境を作成しアクティベートしてください。
   - 例:
     python -m venv .venv
     source .venv/bin/activate  # macOS / Linux
     .venv\Scripts\activate     # Windows

3. 必要パッケージのインストール
   - 例:
     pip install duckdb openai defusedxml

   - 開発インストール:
     pip install -e .

4. 環境変数（.env）を用意
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）が検出されると、自動的に `.env` と `.env.local` が読み込まれます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すれば自動ロードを無効化可能）。
   - 最低限設定が必要な環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
     - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 使用時に必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（発注を行う場合）
     - SLACK_BOT_TOKEN — Slack 通知に使用する Bot トークン
     - SLACK_CHANNEL_ID — 通知先チャンネル ID
   - オプション（デフォルトが設定されている場合あり）:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト development）
     - LOG_LEVEL — DEBUG / INFO / ...（デフォルト INFO）
     - DUCKDB_PATH — デフォルト data/kabusys.duckdb
     - SQLITE_PATH — デフォルト data/monitoring.db

   - 例 `.env`（一例）:
     JQUANTS_REFRESH_TOKEN=xxxxx
     OPENAI_API_KEY=sk-xxxxx
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-xxxxx
     SLACK_CHANNEL_ID=C01234567

5. データベース・スキーマ初期化（監査ログ等）
   - 監査ログ用 DB を初期化する例:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
   - または既存の DuckDB 接続を渡して init_audit_schema を呼ぶこともできます。

---

## 使い方（簡単な例）

以下は Python REPL / スクリプトからの利用例です。すべての呼び出しはルックアヘッドバイアスを避けるため明示的な target_date を受け取ります。

- DuckDB 接続と Settings の利用
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026,3,29))
  print(result.to_dict())

- ニュース NLP スコアを算出（ai_score を ai_scores テーブルへ保存）
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  n = score_news(conn, target_date=date(2026,3,29))
  print(f"scored {n} symbols")

  注意: OpenAI API キーは環境変数 OPENAI_API_KEY、または api_key 引数で渡せます。

- 市場レジーム判定を実行する
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026,3,29))

- ファクター計算（例: モメンタム）
  from kabusys.research.factor_research import calc_momentum
  from datetime import date
  recs = calc_momentum(conn, target_date=date(2026,3,29))
  # recs は各銘柄に対する dict のリスト

- 監査ログスキーマ初期化（既存接続に対して）
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)

- カレンダーの判定ユーティリティ
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  from datetime import date
  is_trading_day(conn, date(2026,3,29))
  next_trading_day(conn, date(2026,3,29))

---

## 設定と挙動に関するメモ

- 環境変数自動ロード
  - プロジェクトルートが特定できれば `.env` → `.env.local` の順で自動読み込みします（OS 環境変数が優先されます）。
  - テスト等で自動ロードを無効にする場合:
    KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- OpenAI 呼び出し
  - gpt-4o-mini（JSON Mode）を利用する設計になっています。OpenAI SDK の例外に対してリトライやフェイルセーフが実装されています。
  - OpenAI API キーは OPENAI_API_KEY で渡してください（関数引数で上書き可能）。

- J-Quants API
  - get_id_token によりリフレッシュトークンから id_token を取得し、ページネーションや保存処理を行います。
  - レート制御（120req/min）やリトライが組み込まれています。

- ルックアヘッドバイアス対策
  - 多くの関数は date を明示的に受け取り、内部で datetime.today()/date.today() を参照しない実装を心掛けています。

---

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 以下の主要モジュール構成です（抜粋）。実際のリポジトリにはさらに詳細なファイルやユーティリティがあります。

- src/kabusys/
  - __init__.py
  - config.py                — 環境設定 / Settings
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント（score_news）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント / 保存関数
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult エクスポート
    - calendar_management.py — マーケットカレンダー管理
    - news_collector.py      — RSS 収集・前処理
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py     — ファクター計算（モメンタム等）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー

---

## 開発・デバッグのヒント
- テストや CI 環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して環境を明示的に管理すると安定します。
- OpenAI / J-Quants 呼び出し部分は内部で retry/backoff を行いますが、API キーやトークンが正しいか事前に確認してください。
- DuckDB のバージョンによっては executemany の空リスト扱いなどの違いがあるため、ETL の挙動に不整合が出た場合は DuckDB バージョンを確認してください。

---

README の内容はコードの docstring / コメントを元に作成しています。実運用やデプロイ時は各所の設定値（API キー、DB パス、環境区分）を適切に管理し、テスト環境と本番環境で変数を分離してください。質問や追加で記載したい使い方があれば教えてください。