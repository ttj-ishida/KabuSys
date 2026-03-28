KabuSys — 日本株自動売買プラットフォーム（README 日本語版）
================================================================================

概要
----
KabuSys は日本株向けのデータプラットフォーム・リサーチ・自動売買基盤の骨格を提供する Python パッケージです。  
主に次の責務を持ちます。

- J-Quants API からのデータ ETL（株価、財務、マーケットカレンダー）
- ニュース収集・前処理（RSS）と LLM を用いたニュースセンチメント評価
- 市場レジーム判定（ETF MA とマクロニュースの統合）
- ファクター計算・特徴量探索（モメンタム・バリュー・ボラティリティ等）
- データ品質チェック、監査（トレーサビリティ）用の監査テーブル初期化ユーティリティ

本 README はリポジトリ内の主要モジュールをもとに、セットアップ・基本的な使い方・ディレクトリ構成を説明します。

主な機能一覧
----------------
- data/
  - ETL パイプライン（差分取得・保存・品質チェック）: run_daily_etl 等
  - J-Quants API クライアント（ページネーション・レート制御・トークンリフレッシュ）
  - ニュース収集（RSS）と前処理（SSRF 対策、トラッキングパラメータ除去）
  - マーケットカレンダー管理（営業日判定、next/prev trading day）
  - 監査ログスキーマ初期化（signal / order_request / executions）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 汎用統計ユーティリティ（Zスコア正規化）
- ai/
  - news_nlp: ニュース記事を LLM（gpt-4o-mini）でスコア化し ai_scores に保存する機能
  - regime_detector: ETF（1321）200 日 MA とマクロニュースセンチメントを統合して市場レジーム判定
- research/
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算
  - feature_exploration: 将来リターン計算・IC（Information Coefficient）・統計サマリー
- config: 環境変数の管理・自動 .env 読み込みロジック（.env, .env.local の読み込み順序）
- audit: 監査（トレーサビリティ）用の DDL と初期化ユーティリティ

必要条件
---------
- Python 3.10 以上（型アノテーションで | 演算子を使用）
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - その他（urllib 等標準ライブラリを利用）

インストール（開発と実行の基本）
--------------------------------
1. リポジトリをクローン：
   git clone <repo-url>
2. 仮想環境を作成・有効化（任意）:
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
3. 依存をインストール（プロジェクトに requirements.txt / pyproject.toml があればそちらを使ってください）:
   pip install duckdb openai defusedxml
   # または:
   # pip install -r requirements.txt
   # または poetry/pipenv を利用
4. 開発インストール（任意）:
   pip install -e .

環境変数 / 設定
----------------
config.Settings から多くの設定を取得します。必須の環境変数は以下の通りです。

- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 等で使用）
- （任意）KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB の DB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト development）
- LOG_LEVEL: ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)

自動 .env 読み込み
- パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml を探索）を見つけると、
  OS 環境 > .env.local > .env の順で自動的に読み込みます。
- 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- .env の構文は export プレフィックス・クォート・インラインコメント等に対応しています。

基本的な使い方（コード例）
-------------------------

- DuckDB 接続の用意（例: settings.duckdb_path を使用）
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  # target_date を指定しなければ今日が対象（内部では trading day に調整されます）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースのスコア付け（LLM を使う）
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  # OPENAI_API_KEY が環境変数に設定されているか、api_key 引数に渡す
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み済み銘柄数: {n_written}")

- 市場レジーム判定
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは環境変数または api_key 引数

- 監査データベースの初期化（監査専用 DB）
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # または既存の DuckDB 接続にスキーマだけ追加:
  # from kabusys.data.audit import init_audit_schema
  # init_audit_schema(conn, transactional=True)

使い方の注意点
--------------
- ルックアヘッドバイアス対策:
  - 多くの関数は内部で date.today() を直接使わず、明示的な target_date 引数を受け取ります。バックテスト等では必ず過去日を指定してください。
- API 呼び出し:
  - OpenAI/J-Quants 呼び出しはリトライやバックオフを実装していますが、API キーやレート制限に注意してください。
- データベース操作:
  - DuckDB に対してはエラー発生時に ROLLBACK を行う処理が実装されている箇所が多いですが、運用スクリプトではトランザクションの取り扱いに注意してください。

テスト / 開発ヘルパ
--------------------
- テスト時に自動 .env ロードを無効化する:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI 呼び出しやネットワーク I/O 部分は内部で分離されており、unittest.mock で差し替え可能になっています（例: kabusys.ai.news_nlp._call_openai_api をモック）。

主要ディレクトリ構成
---------------------
（提供コードに基づく抜粋）

src/kabusys/
- __init__.py                (パッケージ初期化)
- config.py                  (環境変数 / .env 管理)
- ai/
  - __init__.py
  - news_nlp.py              (ニュースセンチメント評価 / score_news)
  - regime_detector.py       (市場レジーム判定 / score_regime)
- data/
  - __init__.py
  - jquants_client.py        (J-Quants API クライアント、保存関数)
  - pipeline.py              (ETL パイプライン run_daily_etl 等)
  - etl.py                   (ETL インターフェース再エクスポート)
  - news_collector.py        (RSS 収集・前処理)
  - calendar_management.py   (マーケットカレンダー管理)
  - stats.py                 (統計ユーティリティ)
  - quality.py               (データ品質チェック)
  - audit.py                 (監査テーブル DDL / 初期化)
- research/
  - __init__.py
  - factor_research.py       (ファクター計算)
  - feature_exploration.py   (将来リターン・IC・統計サマリ)
- (その他) strategy/ execution/ monitoring 等のサブパッケージが想定される（この README は提供されたコードベースに基づき記載）

開発・運用上の設計方針（要点）
-----------------------------
- データ取得は差分・バックフィル方式で実装されており、ETL は idempotent（重複挿入防止）を基本とする。
- 外部 API 呼び出しはレート制御・リトライ・トークンリフレッシュを備え、フェイルセーフ（API 失敗時に処理継続）を優先する箇所がある。
- LLM とのインタラクションは JSON Mode（厳密な JSON 出力を期待）かつ応答検証を行うことでパースの堅牢性を高めている。
- 監査ログはトレーサビリティを重視し、削除しない設計・UTC タイムスタンプ保存を採用している。

付録: よく使うプログラム例（要約）
--------------------------------
- ETL 実行（簡易）
  from kabusys.config import settings
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  conn = duckdb.connect(str(settings.duckdb_path))
  res = run_daily_etl(conn)
  print(res.to_dict())

- ニューススコア（簡易）
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  score_news(conn, date(2026, 3, 20))

- レジーム判定（簡易）
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, date(2026, 3, 20))

問い合わせ / 貢献
------------------
- バグ報告・機能要望は issue を作成してください。Pull Request は歓迎します。大きな設計変更や互換性に関わる変更は事前に Issue で相談してください。

以上が本リポジトリの概要・セットアップ・基本的な使い方になります。必要であれば、具体的な運用手順（cron ジョブ例、Docker 化、CI 設定、マイグレーション手順など）も作成しますので教えてください。