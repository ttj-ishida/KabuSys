# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター算出、データ品質チェック、監査ログ（発注→約定のトレーサビリティ）など、取引システムと研究用パイプラインの基盤機能を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 環境変数（.env）と自動読み込み
- 使い方（主要 API の例）
- ディレクトリ構成

---

プロジェクト概要
- J-Quants API を用いた株価・財務・カレンダー等の ETL
- RSS ベースのニュース収集と OpenAI を使った銘柄別・マクロセンチメント評価
- 市場レジーム判定（ETF とマクロニュースの重み付け合成による daily regime）
- ファクター計算（モメンタム / ボラティリティ / バリュー 等）と特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用の DuckDB スキーマ初期化・管理

主な機能（抜粋）
- data.pipeline.run_daily_etl: 日次 ETL（calendar, prices, financials）＋品質チェック
- data.jquants_client: J-Quants API クライアント（認証 / ページネーション / 保存）
- data.news_collector.fetch_rss: RSS 取得 + 前処理 + DB保存（冪等設計）
- ai.news_nlp.score_news: OpenAI で銘柄別ニュースセンチメントを算出し ai_scores に保存
- ai.regime_detector.score_regime: ETF（1321）MA200 乖離とマクロニュースで市場レジームを算出し market_regime に保存
- research.* : ファクター計算（momentum/volatility/value）や特徴量解析（forward returns / IC 等）
- data.quality.run_all_checks: 品質チェック実行
- data.audit.init_audit_db / init_audit_schema: 監査ログ用スキーマ初期化

セットアップ手順（開発・実行）
1. Python 環境（推奨: 3.10+）を準備
   - 例:
     python3 -m venv .venv
     source .venv/bin/activate

2. 必要ライブラリをインストール（最低限）
   - 代表的に必要なパッケージ:
     pip install duckdb openai defusedxml
   - 追加で Slack 連携等を使う場合は該当ライブラリを追加してください。

3. パッケージを開発モードでインストール（リポジトリルートに pyproject.toml がある前提）
   - pip install -e .

4. 環境変数設定
   - リポジトリルートの .env / .env.local を使うことを想定しています（自動読み込みあり、後述）。
   - 必須環境変数（最小）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知を使う場合
     - KABU_API_PASSWORD: kabu API を使う場合
     - OPENAI_API_KEY: OpenAI 呼び出しを行う場合（score_news/score_regime 実行時に引数として渡すことも可能）
   - データベースパス等は以下で上書き可能:
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）
   - システム動作モード:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

環境変数の自動読み込みについて
- パッケージ import 時に、プロジェクトルート（.git または pyproject.toml を探索）を特定し、.env を読み込み（既存 OS 環境変数を上書きしない）、.env.local を読み込み（上書きあり）します。
- 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等向け）。
- .env のパースはシェル形式をサポート（export KEY=val、クォート、コメント処理など）。

使い方（主要 API の例）

- DuckDB 接続の準備例:
  from pathlib import Path
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行例:
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())

- OpenAI を使ったニューススコアリング（ai.news_nlp.score_news）:
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  # api_key を引数で渡すか環境変数 OPENAI_API_KEY を設定
  n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
  print(f"書き込み銘柄数: {n_written}")

- 市場レジーム判定（ai.regime_detector.score_regime）:
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
  # market_regime テーブルに結果を書き込みます

- 監査ログ DB 初期化:
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  # 必要に応じて audit_conn を保存して利用

- J-Quants ID トークン取得（テストや手動実行向け）:
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # JQUANTS_REFRESH_TOKEN を参照して取得

注意点・設計方針（抜粋）
- ルックアヘッドバイアス回避: モジュールの多くは date.today() 等を内部で参照せず、target_date を明示的に渡す設計です。バックテストや再現性の高い処理のために target_date を外から指定してください。
- 冪等性: DB への保存は可能な箇所で ON CONFLICT 処理や既存削除→挿入の方式で冪等にしています。
- API 呼び出し: J-Quants や OpenAI の呼び出しにはリトライ・バックオフのロジックが組み込まれています。OpenAI の API キーを引数で渡せる関数もあり、テスト用に差し替えが可能な点を考慮しています。
- データ品質: quality モジュールで ETL 後に一連のチェックを実行し、QualityIssue オブジェクトで問題を報告します。

サンプル .env.example（プロジェクトルート）
- 下記を .env（.env.local）にコピーして必要な値を設定してください。
  JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
  OPENAI_API_KEY=your_openai_api_key
  KABU_API_PASSWORD=your_kabu_api_password
  SLACK_BOT_TOKEN=your_slack_bot_token
  SLACK_CHANNEL_ID=your_slack_channel_id
  DUCKDB_PATH=data/kabusys.duckdb
  SQLITE_PATH=data/monitoring.db
  KABUSYS_ENV=development
  LOG_LEVEL=INFO

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                      （環境設定・.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py                   （ニュース NLP -> ai_scores）
    - regime_detector.py            （市場レジーム判定 -> market_regime）
  - data/
    - __init__.py
    - calendar_management.py        （市場カレンダー管理・営業日判定）
    - pipeline.py                   （ETL パイプライン / run_daily_etl 等）
    - jquants_client.py             （J-Quants API クライアント / 保存関数）
    - news_collector.py             （RSS ニュース収集）
    - quality.py                    （データ品質チェック）
    - stats.py                      （統計ユーティリティ / zscore_normalize）
    - audit.py                      （監査ログスキーマ初期化）
    - etl.py                        （ETLResult 再エクスポート）
  - research/
    - __init__.py
    - factor_research.py            （momentum/value/volatility 計算）
    - feature_exploration.py         （forward returns / IC / summary / rank）
  - research/*（他ユーティリティ）
- その他:
  - pyproject.toml（存在すればプロジェクトルート判定に使用）
  - .git/（存在すればプロジェクトルート判定に使用）

開発・テストに関するヒント
- OpenAI / J-Quants など外部 API 呼び出しはモック可能なように実装されています（内部の呼び出し関数を patch してテストしてください）。
- DuckDB を使っているためローカルでファイル DB を作成して簡単に状態を再現できます。テスト時は ":memory:" を使用できます。
- .env の自動ロードは import 時に行われます。テストで環境を独立させたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

ライセンス・貢献
- 本リポジトリにライセンス情報があればそれに従ってください。貢献の際は issue / pull request を通じて提案してください。

お問い合わせ
- 実行や拡張に関する質問は README をアップデートする形でドキュメント化してください。機能追加や外部連携（ブローカー接続や Slack 通知等）については設計方針に従い冪等性とトレーサビリティを維持することを推奨します。

--- 

必要であれば、以下を追加で用意できます:
- requirements.txt / poetry / pyproject.toml の依存リスト例
- よくある実行コマンド集（ETL を cron や CI で回す例）
- .env.example の完全版（コメント付き）
ご希望があれば作成します。