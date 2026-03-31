プロジェクト名: KabuSys — 日本株自動売買 / データプラットフォームライブラリ

概要
- KabuSys は日本株の自動売買・データプラットフォーム向けに設計された Python ライブラリ群です。
- データ ETL（J-Quants 連携）、ニュース収集・NLP（OpenAI を使用したセンチメント分析）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（orders/executions）などを含みます。
- バックテストや本番実行のためのコア処理を DuckDB ベースで実装しており、外部 API（J-Quants, OpenAI, kabuステーション 等）との堅牢な連携を想定しています。

主な機能（抜粋）
- データ ETL
  - J-Quants API から株価日足 / 財務 / 上場情報 / 市場カレンダーを差分取得・保存（ページネーション・レート制御・リトライ実装）
  - 品質チェック（欠損、スパイク、重複、日付不整合）
- ニュース収集・NLP
  - RSS 収集（SSRF 対策、トラッキングパラメータ除去）→ raw_news へ保存
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント（score_news）
  - LLM 呼び出しは JSON モードで堅牢に扱う（リトライ・パース耐性）
- 市場レジーム判定
  - ETF (1321) の 200 日移動平均乖離とマクロニュースセンチメントを合成して日次レジーム判定（score_regime）
- リサーチ（factor / feature）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
- 監査ログ（audit）
  - signal_events / order_requests / executions を含む監査用スキーマ生成・初期化ユーティリティ
- 設定管理
  - .env ファイル or 環境変数から設定を自動読込（プロジェクトルート検索、.env と .env.local の優先順）
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD

前提 / 必要環境
- Python 3.10 以上（型ヒントのユニオン演算子 `|` を使用）
- 主要依存（例）
  - duckdb
  - openai (OpenAI SDK)
  - defusedxml
- ネットワークアクセス: J-Quants / OpenAI / 各 RSS ソース へ接続できること

セットアップ手順（ローカル開発）
1. リポジトリをクローン、プロジェクトルートへ移動
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）
   - pip install -e .    # setup.py / pyproject.toml がある場合の開発インストール
   - または個別に: pip install duckdb openai defusedxml
4. 環境変数の準備
   - プロジェクトルートに .env を作成（.env.example を参照）
   - 主要な環境変数例:
     - JQUANTS_REFRESH_TOKEN=...
     - OPENAI_API_KEY=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development|paper_trading|live
   - 自動ロードを無効化したい場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
5. DuckDB 用ディレクトリ作成（必要に応じて）
   - mkdir -p data

基本的な使い方（コード例）
- 設定の取得
  - from kabusys.config import settings
  - settings.jquants_refresh_token, settings.duckdb_path, settings.env などを利用

- DuckDB 接続の取得（例）
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

- ETL（日次）実行例
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn, target_date=<datetime.date>, id_token=None)
  - result は ETLResult オブジェクト（to_dict() で辞書化可）

- ニュースセンチメント解析（score_news）
  - from kabusys.ai.news_nlp import score_news
  - n = score_news(conn, target_date=<date>, api_key=None)  # api_key を渡す or 環境変数 OPENAI_API_KEY を使用
  - 戻り値: 書き込み銘柄数（int）

- 市場レジーム判定（score_regime）
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=<date>, api_key=None)
  - 内部で OpenAI を呼び、market_regime テーブルへ結果を保存

- 監査スキーマ初期化 / 監査 DB
  - from kabusys.data.audit import init_audit_db, init_audit_schema
  - conn_audit = init_audit_db("data/audit.duckdb")  # ファイル作成＋DDL 実行
  - 既存接続にスキーマを追加する場合:
    - init_audit_schema(conn, transactional=True)

注意点 / テスト向けヒント
- 自動環境変数読み込み:
  - kabusys.config はプロジェクトルート（.git または pyproject.toml）を探索して .env を自動で読み込みます。
  - テスト等で自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- OpenAI 呼び出しの差し替え:
  - テスト時は各モジュール内の _call_openai_api を unittest.mock.patch でモックできます（kabusys.ai.news_nlp._call_openai_api や kabusys.ai.regime_detector._call_openai_api）。
- リトライ・フォールバック:
  - LLM 失敗時はフェイルセーフでスコアを中立 0.0 にするなどの挙動があります（例: score_regime, score_news）。
- DuckDB executemany の仕様:
  - 一部コードは DuckDB の executemany が空リストを受け付けない点に対応しています（事前チェックを実施）。

ディレクトリ構成（主要ファイル概観）
- src/kabusys/
  - __init__.py                 : パッケージ定義、バージョン
  - config.py                   : 環境変数 / .env 読み込みと Settings
  - ai/
    - __init__.py
    - news_nlp.py               : ニュースセンチメント解析（score_news）
    - regime_detector.py        : 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py         : J-Quants API クライアント（取得・保存ユーティリティ）
    - pipeline.py               : ETL パイプライン（run_daily_etl 等）
    - etl.py                    : ETLResult の再エクスポート
    - quality.py                : データ品質チェック
    - news_collector.py         : RSS 収集・前処理
    - calendar_management.py    : 市場カレンダー管理（is_trading_day 等）
    - stats.py                  : 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                  : 監査ログスキーマ作成 / 初期化
  - research/
    - __init__.py
    - factor_research.py        : Momentum / Volatility / Value 等
    - feature_exploration.py    : 将来リターン・IC・統計サマリー等
  - ai、data、research 以下にビジネスロジック実装（DB 接続は duckdb.DuckDBPyConnection を前提）

運用上の推奨
- 本番環境（live）では KABUSYS_ENV=live を設定し、ログレベルやリスク管理ルールを厳格化してください。
- ID トークン / API キーは安全に管理し、.env ファイルはソース管理に含めないでください。
- DuckDB ファイルや監視 PID、SQLite の監視 DB などは settings でパスを設定できます（デフォルトは data/ 以下）。

ライセンス・貢献
- （この README ではライセンスファイルは含めていません。リポジトリの LICENSE を参照してください）
- バグ報告・機能提案は issue を通じてお願いします。

その他質問や README に含めてほしい詳細（例: CI 設定、例データ投入スクリプト、.env.example の中身等）があれば教えてください。README を補足して更新します。