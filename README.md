# KabuSys

日本株向け自動売買 / データ基盤ライブラリ

KabuSys は日本株のデータ取得（J-Quants 等）・ETL、ニュース収集・NLP、ファクター研究、監査ログ、マーケットレジーム判定などを行うコンポーネント群を提供するパッケージです。バックテストや自動売買プラットフォームの基盤機能を段階的に実装することを目的としています。

バージョン: 0.1.0

---

主な特徴
- J-Quants API クライアント（株価日足、財務、マーケットカレンダー）の取得と DuckDB への冪等保存
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース収集（RSS）とニュース NLP（OpenAI を利用した銘柄別センチメント）
- 市場レジーム判定（ETF MA200 とマクロニュースセンチメントを合成）
- 研究用ファクター群（Momentum / Volatility / Value 等）と特徴量解析ユーティリティ
- 監査ログ（signal → order_request → execution）テーブルの初期化ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）

---

必要条件
- Python 3.10 以上（構文に | 型ヒント等を使用）
- 推奨ライブラリ（最低限）:
  - duckdb
  - openai
  - defusedxml

（プロジェクトで追加のパッケージが必要になる可能性があります。実行時に ImportError が出た場合は適宜インストールしてください。）

インストール（開発環境例）
1. リポジトリをクローン
   git clone <repo-url>
2. 仮想環境を作成して有効化
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
3. 必要パッケージをインストール
   pip install duckdb openai defusedxml
   # （必要に応じて他のパッケージを追加）

（パッケージ化されている場合は pip install -e . を推奨）

環境変数（.env）
KabuSys はプロジェクトルートにある `.env` / `.env.local` を自動的に読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可能）。実行に必要な主な環境変数:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注等に必要）
- SLACK_BOT_TOKEN: Slack ボットトークン（通知）
- SLACK_CHANNEL_ID: Slack チャンネル ID（通知先）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- DUCKDB_PATH (任意): デフォルト data/kabusys.duckdb
- SQLITE_PATH (任意): デフォルト data/monitoring.db
- KABUSYS_ENV (任意): development / paper_trading / live
- LOG_LEVEL (任意): DEBUG/INFO/WARNING/ERROR/CRITICAL

.env.example（例）
（プロジェクトルートに .env を作成して利用してください）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=your_slack_bot_token
SLACK_CHANNEL_ID=your_slack_channel_id
DUCKDB_PATH=data/kabusys.duckdb

設定管理
- kabusys.config.settings: 設定アクセサ。必要な環境変数はここから取得します。
  例: from kabusys.config import settings; token = settings.jquants_refresh_token
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml がある）を基準に行われます。

基本的な使い方（例）
以下は各主要機能の簡単な利用例です。実行前に環境変数（上記）を設定してください。

- DuckDB 接続を作る
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメント（銘柄別）をスコアリングする
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None → 環境変数 OPENAI_API_KEY を使用

- 市場レジームを判定して保存する
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 研究用ファクター計算
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date
  mom = calc_momentum(conn, target_date=date(2026, 3, 20))
  vol = calc_volatility(conn, target_date=date(2026, 3, 20))
  val = calc_value(conn, target_date=date(2026, 3, 20))

- 監査ログスキーマの初期化（監査専用 DB を生成）
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")

注意事項 / トラブルシューティング
- OpenAI 関連の関数（score_news, score_regime）は API 呼び出しが失敗した場合、フォールバック（多くは 0.0 を返す・もしくは処理をスキップ）する設計です。ただし API キーが未設定だと ValueError を投げます。
- J-Quants へのリクエストはレートリミット（120 req/min）を守り、内部でリトライやトークン自動リフレッシュを行います。refresh token が無いと get_id_token が失敗します。
- news_collector は外部 RSS を取得する際に SSRF/ファイルスキーム対策、サイズ上限、gzip 解凍チェックなどの安全対策を行っています。RSS の取得失敗は警告ログになります。
- DuckDB の executemany 等はバージョン差異による制約（空リストの扱い等）を考慮した実装が各所にあります。DuckDB のバージョンは互換性の高い最新版を使ってください。
- 自動 .env ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時の isolation 用）。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                : 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py            : ニュース NLP スコアリング（OpenAI 連携）
    - regime_detector.py     : マーケットレジーム判定（ETF MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py      : J-Quants API クライアント（取得 + 保存）
    - pipeline.py            : ETL パイプライン（run_daily_etl 等）
    - etl.py                 : ETL インタフェース再エクスポート
    - news_collector.py      : RSS ニュース収集
    - quality.py             : データ品質チェック
    - calendar_management.py : マーケットカレンダー管理（営業日判定等）
    - stats.py               : 汎用統計ユーティリティ（zscore 正規化等）
    - audit.py               : 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py     : Momentum / Value / Volatility ファクター
    - feature_exploration.py : 将来リターン・IC・統計サマリー等
  - ai/__init__.py
  - research/__init__.py
  - data/__init__.py

詳細設計や仕様（参考）
- news_nlp: ニュースの時間ウィンドウ設定、OpenAI へのバッチ送信・レスポンス検証・クリップ処理を実装
- regime_detector: ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して regime_label を決定
- jquants_client: レートリミット、リトライ、トークン自動リフレッシュ、DuckDB への冪等保存（ON CONFLICT）を実装
- data.pipeline.run_daily_etl: カレンダー・株価・財務の差分 ETL と品質チェックを一括実行

貢献
- バグ報告や機能提案は Issue へお願いします。プルリクエストは歓迎します。

ライセンス
- 本リポジトリにライセンスファイルが含まれていればそれに従ってください。

以上がこのコードベースの概要と使い方のまとめです。特定の機能（例: ETL のカスタム設定、news_nlp のプロンプト調整、監査 DB の運用方法）についてもっと詳しいドキュメントやサンプルが必要であれば教えてください。