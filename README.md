# KabuSys

日本株自動売買プラットフォームのコアライブラリ（ライブラリ風のコードベース）。  
データ収集（J-Quants）、ETL、データ品質チェック、ニュースNLP（OpenAI）、市場レジーム判定、リサーチ（ファクター計算）、監査ログ（約定トレーサビリティ）などを含みます。

## プロジェクト概要
KabuSys は日本株向けのデータプラットフォームと研究／実行基盤のコアロジックを提供するモジュール群です。  
主に以下を目的としています。

- J-Quants API からの株価・財務・市場カレンダーの差分取得と DuckDB への保存（ETL）
- ニュース収集・前処理・LLM を用いたニュースセンチメントスコアリング
- 市場レジーム判定（ETF MA とマクロニュースの組合せ）
- ファクター（モメンタム・ボラティリティ・バリュー等）の計算と統計ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログスキーマ（signal → order_request → execution のトレーサビリティ）
- 設定は環境変数または .env ファイルで管理

## 主な機能一覧
- data
  - ETL パイプライン（run_daily_etl、run_prices_etl、run_financials_etl、run_calendar_etl）
  - J-Quants クライアント（トークン管理、ページネーション、レート制限、リトライ）
  - market_calendar（営業日の判定、next/prev/get_trading_days）
  - News collector（RSS 取得、前処理、SSRF 対策）
  - データ品質チェック（missing/duplicates/spike/date_consistency）
  - audit（監査ログスキーマ初期化、監査 DB 初期化ユーティリティ）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - news_nlp.score_news: ニュースを LLM でスコアリングし ai_scores テーブルへ書き込む
  - regime_detector.score_regime: ETF（1321）の MA200 とニュースセンチメントから市場レジーム判定
- research
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - Settings クラス: 環境変数を体系的に取得（自動で .env/.env.local をプロジェクトルートからロード）

## 要件
- Python 3.10+
- 必要なパッケージ（最低限の例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI）

インストールはプロジェクトに依存するため、実際の requirements.txt / pyproject.toml に従ってください。上記は本 README の説明用。

## セットアップ手順（開発・実行環境例）
1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトの pyproject.toml / requirements.txt があればそちらを使用）

4. 環境変数の設定
   - プロジェクトルートに `.env`（または `.env.local`）を作成すると、自動で読み込まれます。
   - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. 必須の環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
   - OPENAI_API_KEY: OpenAI 呼び出しに必要（ai.score_news / regime_detector 等を使う場合）
   - （任意）
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_FILL_MODE（paper_trading 用: instant|partial|never|reject、デフォルト "instant"）
     - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
     - PID_FILE_PATH / KILL_FLAG_PATH / その他監視パラメータ

6. データディレクトリ作成（必要に応じて）
   - mkdir -p data

注: config.Settings は .env.example を参照する旨のエラーメッセージを出す箇所があります。実際のプロジェクトでは `.env.example` を用意しておくことを推奨します。

## 使い方（コード例）
以下はライブラリ関数をインポートして利用する簡単な例です。例では DuckDB を直接接続して使用します。

- ETL（毎日実行する想定）
  - Python REPL / スクリプト例:
    from datetime import date
    import duckdb
    from kabusys.config import settings
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date.today())
    print(result.to_dict())

- ニュース NLP スコアリング（OpenAI 必須）
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使う

- 市場レジーム判定（OpenAI 必須）
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY を利用

- 監査ログ DB の初期化
    import duckdb
    from kabusys.data.audit import init_audit_db

    conn = init_audit_db("data/audit.duckdb")
    # conn をアプリケーションの監査用接続として使用

- J-Quants の id token を取得（手動）
    from kabusys.data.jquants_client import get_id_token
    token = get_id_token()  # settings.jquants_refresh_token を使用

ログレベルやその他設定は環境変数（LOG_LEVEL / KABUSYS_ENV など）で制御できます。

## 注意事項 / 設計上のポイント
- look-ahead bias を防ぐため、各モジュールは target_date を明示的に受け取り、内部で datetime.today() を参照しない設計がされています（ETL / scoring / research 関数）。
- OpenAI への呼び出しはリトライやフェイルセーフ（API 失敗時は中立スコアで継続）を備えています。
- J-Quants API 呼び出しはレート制限とリトライ、401 時のトークンリフレッシュ対応が実装されています。
- News collector では SSRF や XML 攻撃対策（defusedxml、ホストチェック、リダイレクト検査、受信サイズ制限）を行っています。
- DuckDB への保存は基本的に冪等（ON CONFLICT / DO UPDATE）で実装されています。

## ディレクトリ構成（主要ファイル）
（src/kabusys をルートとする主要モジュール一覧）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数/設定管理
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP スコアリング（score_news）
    - regime_detector.py      — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得・保存）
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - etl.py                  — ETL 型の再エクスポート（ETLResult）
    - calendar_management.py  — 市場カレンダー・営業日ロジック
    - news_collector.py       — RSS 取得・前処理・保存
    - quality.py              — データ品質チェック
    - audit.py                — 監査ログスキーマ初期化 / init_audit_db
    - stats.py                — 統計ユーティリティ（zscore_normalize）
  - research/
    - __init__.py
    - factor_research.py      — ファクター計算（momentum/value/volatility）
    - feature_exploration.py  — 特徴量探索（forward returns, IC, summary）
  - research/...              — その他研究ユーティリティ

（テスト、ドキュメント、CLI などは別途実装）

## 環境変数（主な一覧）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API パスワード
- OPENAI_API_KEY — OpenAI API キー（ai モジュールで使用）
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_FILL_MODE — paper trading の fill モード（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH — paper trading 用 SQLite（デフォルト data/paper_trading.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定で .env 自動ロードを無効化

設定は `.env` / `.env.local` に記述しておくと、config モジュールがプロジェクトルートから自動読み込みします（CWD ではなくファイル位置を元にルート判定）。

## ログと監視
- config.Settings で LOG_LEVEL を設定できます。
- 実行プロセスの監視用に pid ファイル / kill flag の設定が可能です（Settings 内でパスを指定）。

## 開発・拡張のヒント
- OpenAI 呼び出し部分はテスト容易性を考慮して内部呼び出し関数をモック可能な設計になっています（例: kabusys.ai.news_nlp._call_openai_api を patch）。
- DuckDB による SQL 実行は SQL を文字列埋め込みで行っている箇所があるため（パラメータバインドは使われていますが）、拡張時は SQL の安全性に留意してください。
- ETL や calendar 判定は冪等設計を念頭に置いています。外部 API の仕様変更があれば jquants_client 側を更新してください。

---

本 README はコードベースの主要点をまとめた簡易ドキュメントです。詳細な設計参照（StrategyModel.md / DataPlatform.md 等）は別ドキュメントにまとめている想定です。必要であれば各モジュールの関数ごとの使い方・引数仕様の追記を行います。