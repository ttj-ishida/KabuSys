# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログなどを含むモジュール群を提供します。

- パッケージ名: kabusys
- バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（簡単な例）
- 環境変数一覧
- ディレクトリ構成
- 設計上の注意点

---

プロジェクト概要
----------------
KabuSys は日本株のデータ基盤とリサーチ／自動売買関連の共通ユーティリティをまとめた Python パッケージです。主な目的は以下です。

- J-Quants API からの株価・財務・カレンダー取得と DuckDB への冪等保存（ETL）
- RSS ニュース収集と前処理、ニュース→銘柄の紐付け
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント評価（AI スコア）
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量解析ユーティリティ
- 市場レジーム判定（ETF + マクロニュース）
- データ品質チェック、監査ログ（約定・発注のトレーサビリティ）
- DuckDB ベースでのオフライン処理設計（ルックアヘッド対策・冪等性・リトライ）

主な機能
--------
- data.jquants_client: J-Quants API クライアント（ページネーション、レート制御、リトライ、トークン自動更新）
- data.pipeline/run_daily_etl: 日次 ETL パイプライン（市場カレンダー・株価・財務・品質チェック）
- data.news_collector: RSS 収集・前処理（SSRF 対策、トラッキング除去、サイズ制限）
- ai.news_nlp.score_news: ニュースを銘柄別にまとめて LLM でセンチメント評価、ai_scores へ保存
- ai.regime_detector.score_regime: ETF (1321) の MA とマクロニュース LLM を合成して市場レジーム判定
- research.*: ファクター計算（モメンタム / ボラティリティ / バリュー）と特徴量解析ユーティリティ（forward returns, IC, summary）
- data.quality: データ品質チェック（欠損、重複、スパイク、日付不整合）
- data.audit: 監査ログスキーマ定義と初期化ユーティリティ（監査テーブル・インデックス）
- data.stats: クロスセクションの Z スコア正規化ユーティリティ

セットアップ手順
----------------

前提:
- Python 3.10+（typing の新構文、Union 表記などを使用）
- ネットワークアクセス（J-Quants / OpenAI / RSS ソース等）
- DuckDB を使用（pip でインストール）

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. 依存関係インストール
   pip install -U pip
   pip install duckdb openai defusedxml

   （プロジェクト化している場合は setup/pyproject の指示に従って pip install -e .）

4. 環境変数の設定
   - .env または .env.local に必要な環境変数を設定してください。
   - 自動で .env をロードする仕組みがあり、プロジェクトルート（.git または pyproject.toml）から .env と .env.local を順に読み込みます。
   - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

必須環境変数 (最小構成)
- JQUANTS_REFRESH_TOKEN  : J-Quants のリフレッシュトークン（ETL 用）
- OPENAI_API_KEY          : OpenAI API キー（AI モジュール利用時）
- SLACK_BOT_TOKEN         : Slack 通知を使う場合
- SLACK_CHANNEL_ID        : Slack チャンネル ID（通知先）
- KABU_API_PASSWORD       : kabu ステーション API のパスワード（発注等を行う場合）

オプション（デフォルトあり）
- KABUSYS_ENV             : development / paper_trading / live（デフォルト: development）
- LOG_LEVEL               : ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 にすると自動 .env 読み込みを無効化
- DUCKDB_PATH             : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH             : 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABU_API_BASE_URL       : kabu API base URL（デフォルト http://localhost:18080/kabusapi）

使い方（簡単な例）
------------------

Python スクリプト例:

- DuckDB 接続を作って日次 ETL を実行する:

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニューススコア（OpenAI 必須）:

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-xxxx")
  print(f"書き込み銘柄数: {written}")

- 市場レジーム判定:

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-xxxx")

- 監査ログ DB 初期化:

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn を使って order/exec の記録が行えるようになります

環境変数の自動ロード
-------------------
- パッケージロード時にプロジェクトルートの .env → .env.local を自動で読み込みます（OS 環境変数を上書きしない挙動）。
- テストなどで自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成
----------------

（主要ファイルのみ抜粋）

src/
  kabusys/
    __init__.py
    config.py                      # 環境変数管理（.env 自動ロード・設定アクセス）
    ai/
      __init__.py
      news_nlp.py                  # ニュースセンチメントの LLM 呼び出し・バッチ処理
      regime_detector.py           # ETF MA + マクロニュースで市場レジーム判定
    data/
      __init__.py
      jquants_client.py            # J-Quants API クライアント（取得＋DuckDB 保存）
      pipeline.py                  # ETL パイプライン（run_daily_etl など）
      etl.py                       # ETL 公開インターフェース（ETLResult）
      news_collector.py            # RSS 収集 & 前処理
      calendar_management.py       # 市場カレンダー、営業日判定
      quality.py                   # データ品質チェック
      stats.py                     # 統計ユーティリティ（zscore等）
      audit.py                     # 監査ログスキーマ初期化
    research/
      __init__.py
      factor_research.py           # モメンタム / バリュー / ボラティリティ
      feature_exploration.py       # forward_returns, IC, rank, summary
    research/...                    # 研究用ユーティリティ
    monitoring/ (将来的な監視モジュール)  # （snapshot: 一部機能は未提示）

設計上の注意点
--------------
- ルックアヘッドバイアス対策:
  - 多くの関数（ETL、ニュース・レジーム、リサーチ）は内部で date を明示的に受け取り、datetime.today() などを直接参照しません。バックテストでの正確性を意識しています。
- 冪等性:
  - DuckDB への保存は ON CONFLICT / DO UPDATE を使って再実行可能にしています。
- フォールバック / フェイルセーフ:
  - OpenAI 等の外部 API が失敗した場合、多くの箇所で安全にフォールバック（スコア 0 やスキップ）する設計です。ログに警告を出します。
- セキュリティ:
  - ニュース収集では SSRF 防止、XML パースは defusedxml を使用、RSS レスポンスサイズ上限などを実装しています。
- レート制御:
  - J-Quants クライアントは内部で固定間隔のスロットリングを行い API レートを守るようになっています。

よくあるトラブルシューティング
-------------------------------
- .env が読み込まれない:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないか、リポジトリのルートに .git または pyproject.toml が存在するか確認してください。自動読み込みはプロジェクトルート探索に依存します。
- OpenAI 呼び出しで JSON パースエラーが出る:
  - LLM の応答は JSON に制約していますが稀にプレーンテキストが混ざることがあります。現行実装は冗長な応答を拾うための復元ロジックやパース失敗時のフォールバックを持っていますが、プロンプトや API バージョンを確認してください。
- DuckDB テーブルが存在しない:
  - 初回はスキーマ初期化を行うユーティリティや migration を実行してテーブルを作成してください（例: audit.init_audit_db は監査スキーマのみ初期化します）。ETL を実行する前に必要なテーブル群があることを確認してください。

ライセンス・貢献
----------------
（リポジトリの LICENSE ファイルに従ってください）

---

その他
-----
README に記載のないユーティリティや追加の CLI、テスト、CI 設定などはリポジトリ内の別ファイルを参照してください。詳細な設計方針は各モジュールの docstring（ソース内コメント）に記載されています。何か特定の使い方（例: kabu 発注連携、Slack 通知設定、監査ログの運用）についてのサンプルが必要であれば教えてください。