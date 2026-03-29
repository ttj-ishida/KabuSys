# KabuSys

日本株向けの自動売買・データ基盤ライブラリセットです。ETL（J-Quants）→ データ品質チェック → 研究用ファクター計算 → ニュースNLP（OpenAI） → 市場レジーム判定 → 監査ログ（注文／約定トレーサビリティ）までのワークフローを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システム向けに設計されたモジュール群です。主に以下の責務を持ちます。

- J-Quants API からのデータ取得（株価、財務、JPX カレンダー等）
- DuckDB を使ったローカルデータストアへの ETL（差分取得・冪等保存）
- データ品質チェック（欠損・重複・日付不整合・スパイク）
- ニュース収集（RSS）とニュースの NLP（OpenAI）による銘柄センチメント評価
- 市場レジーム判定（ETF MA とマクロニュースセンチメントの合成）
- 研究用のファクター計算 / 特徴量解析ユーティリティ
- 監査ログ（signal / order_request / execution）用のスキーマ初期化ユーティリティ
- 環境変数 / .env の管理ユーティリティ

設計方針として、バックテストでのルックアヘッドバイアス回避、API 呼び出しのフェイルセーフ化（失敗時のフォールバック）、DuckDB を利用した高効率な SQL ベース処理を重視しています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（認証、ページネーション、リトライ、rate limiting、DuckDB への保存）
  - pipeline / etl: 日次 ETL パイプライン（prices / financials / calendar）と ETL 結果管理（ETLResult）
  - quality: データ品質チェック（欠損、重複、スパイク、日付不整合）
  - calendar_management: JPX カレンダー管理、営業日判定ユーティリティ
  - news_collector: RSS 収集（SSRF 対策、トラッキング除去、前処理）
  - audit: 監査ログテーブルの DDL と初期化ユーティリティ
  - stats: 汎用統計ユーティリティ（Zスコア正規化等）
- ai/
  - news_nlp.score_news: ニュース記事を銘柄毎にまとめて OpenAI に投げ、ai_scores テーブルに書き込む
  - regime_detector.score_regime: ETF（1321）の200日MA乖離とマクロニュースセンチメントを合成して market_regime テーブルへ書き込む
- research/
  - factor_research: momentum / value / volatility 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman rank）計算、統計サマリ等
- config:
  - 環境変数と .env の自動読み込み / 必須設定取得（settings オブジェクト）

---

## 前提 / 必要環境

- Python（互換性は本リポジトリ内で明示されていませんが、typing 機能を多用しているため Python 3.10+ を推奨）
- 必須ライブラリ（例）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI）

※ 実行環境に応じて requirements.txt を用意して pip によるインストールを行ってください。

例:
pip install duckdb openai defusedxml

---

## 環境変数 / .env

KabuSys は .env ファイル（プロジェクトルートの .git または pyproject.toml を探索）と OS 環境変数を統合して設定を読み込みます。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime に渡すか環境で設定）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite (monitoring) のパス（デフォルト data/monitoring.db）
- KABUSYS_ENV: 環境 ('development' | 'paper_trading' | 'live')（デフォルト development）
- LOG_LEVEL: ログレベル ('DEBUG','INFO','WARNING','ERROR','CRITICAL')

settings オブジェクトからプログラム内でアクセス可能:
from kabusys.config import settings
settings.jquants_refresh_token
settings.duckdb_path
etc.

---

## セットアップ手順（ローカルでの開始例）

1. リポジトリをクローン / 作業ディレクトリへ移動
2. 仮想環境を作成して有効化
   python -m venv .venv
   source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   pip install duckdb openai defusedxml
   （プロジェクトに requirements.txt があれば pip install -r requirements.txt を利用）
4. .env を作成（または環境変数を設定）
   例 .env:
     JQUANTS_REFRESH_TOKEN=xxxxx
     OPENAI_API_KEY=sk-xxxx
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
5. データベース用ディレクトリを作成（必要なら）
   mkdir -p data
6. 必要に応じて監査用 DB を初期化
   python -c "from kabusys.data.audit import init_audit_db; init_audit_db('data/audit.duckdb')"

---

## 使い方（主要 API の例）

以下は Python REPL やスクリプトからの呼び出し例です。

- DuckDB 接続
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行（run_daily_etl は ETLResult を返す）
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())

- ニュース NLP（OpenAI を使って銘柄別スコアを ai_scores に書き込む）
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  # api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定
  n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)

- 市場レジーム判定（ETF 1321 の MA とマクロニュースを合成）
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026,3,20), api_key=None)

- ファクター計算（研究用途）
  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
  from datetime import date
  momentum = calc_momentum(conn, target_date=date(2026,3,20))
  volatility = calc_volatility(conn, target_date=date(2026,3,20))
  value = calc_value(conn, target_date=date(2026,3,20))

- 研究用ユーティリティ（将来リターン・IC）
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic
  fwd = calc_forward_returns(conn, target_date=date(2026,3,20), horizons=[1,5,21])
  ic = calc_ic(momentum, fwd, factor_col="mom_1m", return_col="fwd_1d")

- 監査スキーマの初期化（既存の DuckDB 接続にテーブルを作成）
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)

注意:
- score_news / score_regime は OpenAI API 呼び出しを行います。テスト時は内部の _call_openai_api をモックできます。
- ETL / 保存は冪等（ON CONFLICT DO UPDATE）で設計されています。

---

## ディレクトリ構成（主要ファイル）

（リポジトリの src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py  (パッケージ初期化、__version__=0.1.0)
  - config.py    (環境変数 / .env ロード、settings オブジェクト)
  - ai/
    - __init__.py
    - news_nlp.py         (ニュース NLP スコアリング)
    - regime_detector.py  (市場レジーム判定)
  - data/
    - __init__.py
    - jquants_client.py   (J-Quants API クライアント + DuckDB 保存)
    - pipeline.py         (ETL パイプライン / run_daily_etl / ETLResult)
    - etl.py              (ETLResult 再エクスポート)
    - news_collector.py   (RSS 収集・前処理)
    - calendar_management.py (マーケットカレンダー管理)
    - quality.py          (データ品質チェック)
    - stats.py            (統計ユーティリティ)
    - audit.py            (監査ログスキーマ / 初期化)
  - research/
    - __init__.py
    - factor_research.py  (Momentum / Value / Volatility 等)
    - feature_exploration.py (将来リターン / IC / 統計サマリ)
  - research/*, ai/*, data/* の各モジュールは互いに適切に分離され、バックテストでのルックアヘッド回避や副作用の最小化に配慮されています。

---

## 注意点 / 運用上のヒント

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。CI やテストで自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しは外部 API のためコスト／レート制限に注意してください。モジュールはリトライとバックオフを実装していますが、利用量は管理してください。
- J-Quants API のレート制限（120 req/min）に合わせた RateLimiter を実装しています。大量処理時は十分な間隔を保ってください。
- ETL は冪等設計になっていますが、DuckDB のバージョンによる細かい挙動（executemany の空パラメータなど）に注意しています。運用環境でテストを行ってください。
- production 環境（KABUSYS_ENV=live）は安全対策（実際の発注や機密情報管理）を厳格に行ってください。

---

## 貢献 / テスト

- 各モジュール内はテストしやすい設計（依存注入、内部 API 呼び出しのモックポイント）がなされています。
- OpenAI / ネットワーク呼び出し箇所は unittest.mock で _call_openai_api / _urlopen 等を差し替えられます。
- .env.example を用意して運用ドキュメントを整備すると導入が容易になります。

---

この README はコードベースの概要と主要な使い方を簡潔に示したものです。各モジュールの詳細な使用方法やパラメータは該当ソースファイルの docstring を参照してください。必要であればサンプルスクリプトや CI 用設定、requirements.txt のテンプレートを追記します。