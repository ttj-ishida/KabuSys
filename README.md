# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。データ収集（J‑Quants）、ETL、データ品質チェック、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、監査ログ（発注／約定トレーサビリティ）など、量的運用と研究用途に必要な機能群を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要APIの例）
- 環境変数（主な設定）
- ディレクトリ構成

---

プロジェクト概要
- 日本株のデータプラットフォームと自動売買に必要な共通機能を集約したライブラリです。
- J-Quants API からの株価／財務／カレンダー取得、DuckDB への保存（冪等保存）、品質チェック、ニュースRSS収集と前処理、OpenAI を用いたニュースセンチメント評価、ETFベースの市場レジーム判定、研究用ファクター計算、監査ログ（signal → order_request → execution）のスキーマ初期化などを備えます。
- ルックアヘッドバイアス回避やフェイルセーフ設計（API障害時のフォールバック）を考慮した実装方針になっています。

機能一覧
- 環境設定管理（.env 自動読み込み・保護）
- J-Quants API クライアント（取得／ページネーション／認証リフレッシュ／レートリミット／保存関数）
- ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS、SSRF対策、正規化、raw_news / news_symbols への保存設計）
- ニュースNLP（OpenAI を利用した銘柄別センチメント付与、batch処理、堅牢なレスポンス検証）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM センチメントを合成）
- 研究モジュール（モメンタム / バリュー / ボラティリティ 等のファクター計算、forward returns、IC、統計サマリー）
- 監査ログ（signal_events / order_requests / executions テーブル）と初期化ユーティリティ
- 汎用統計ユーティリティ（Zスコア正規化 等）

セットアップ手順（開発環境・実行環境の準備例）
1. Python の準備
   - Python 3.10+ を推奨（型注釈の Union | 等を利用しています）。
2. リポジトリを取得して editable インストール（例）
   - git clone <repo>
   - cd <repo>
   - pip install -r requirements.txt
     - 主要依存例: duckdb, openai, defusedxml
     - （このリポジトリに requirements.txt がない場合は上記パッケージを個別にインストールしてください）
   - または開発中は: pip install -e .
3. データディレクトリ作成
   - デフォルトの DuckDB パスは data/kabusys.duckdb（設定で変更可）
   - mkdir -p data
4. 環境変数の設定
   - .env をプロジェクトルートに作成（.env.local もサポート）。自動読み込みはデフォルトで有効。
   - 必須項目や推奨項目は下記「環境変数」参照。
   - 自動読み込みを無効化したい場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
5. DuckDB 初期化（監査DB など）
   - 監査用DB初期化はコードから実行します（後述例参照）。

使い方（主要APIの例）

- 簡単な DuckDB 接続
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL 実行（市場カレンダー・株価・財務・品質チェックを順次実行）
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn, target_date=None, id_token=None)
  - print(result.to_dict())

- 個別 ETL（株価・財務）
  - from kabusys.data.pipeline import run_prices_etl, run_financials_etl
  - fetched, saved = run_prices_etl(conn, target_date=date(2026,3,20))
  - fetched_f, saved_f = run_financials_etl(conn, target_date=date(2026,3,20))

- ニュースセンチメント（銘柄別）を生成
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - n = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key None → 環境変数 OPENAI_API_KEY を参照
  - print(f"scored {n} codes")

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=date(2026,3,20), api_key=None)

- 監査DB初期化（signal/order/execution テーブルを作成）
  - from kabusys.data.audit import init_audit_db, init_audit_schema
  - conn_audit = init_audit_db("data/audit.duckdb")
  - # または既存 DuckDB 接続にスキーマを付加:
  - from kabusys.data.audit import init_audit_schema
  - init_audit_schema(conn, transactional=True)

- 研究モジュール例
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  - mom = calc_momentum(conn, target_date=date(2026,3,20))
  - vals = calc_value(conn, target_date=date(2026,3,20))

環境変数（主な設定）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須：J-Quants API を使う場合）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須：kabu連携がある場合）
- KABU_API_BASE_URL: kabu API のベースURL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須：Slack 通知を使う場合）
- SLACK_CHANNEL_ID: Slack チャンネルID（必須：Slack 通知を使う場合）
- OPENAI_API_KEY: OpenAI API キー（必須：AI モジュールを利用する場合。score_news, score_regime など）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（モニタリングDB）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development, paper_trading, live のいずれか。デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL。デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env の自動読み込みを無効化

.env ファイルの読み込み
- プロジェクトルートは __file__ を起点に .git または pyproject.toml を探して決定します（カレントワークディレクトリに依存しません）。
- 自動的に .env → .env.local の順で読み込み、.env.local は上書き可能（OS 環境変数は保護）。
- 必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを停止できます（テスト等で有用）。

実装上の注意 / 設計方針（抜粋）
- ルックアヘッドバイアス防止: 各モジュールは date / target_date を明示的に受け、内部で datetime.today() 等に依存しない設計です。バックテスト用途でも安全に使える設計配慮があります。
- フェイルセーフ: 外部API失敗時はゼロスコアやスキップして継続する箇所が多く、システム全体の頑健性を高める実装になっています。
- 冪等性: DuckDB への保存は ON CONFLICT DO UPDATE や PK によるスキップ等で冪等化しています。
- セキュリティ: RSS 収集では SSRF 対策、XML の defusedxml 利用、レスポンスサイズチェック等を行います。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                          （環境変数・設定管理）
  - ai/
    - __init__.py
    - news_nlp.py                       （ニュースNLP、OpenAI 呼び出し、バッチ処理）
    - regime_detector.py                （市場レジーム判定）
  - data/
    - __init__.py
    - jquants_client.py                 （J‑Quants API クライアント、保存関数）
    - pipeline.py                       （ETL パイプライン）
    - etl.py                            （ETL インターフェース - ETLResult 再エクスポート）
    - stats.py                          （統計ユーティリティ）
    - quality.py                        （データ品質チェック）
    - news_collector.py                 （RSS 収集・前処理）
    - calendar_management.py            （市場カレンダー管理）
    - audit.py                          （監査ログスキーマ初期化）
  - research/
    - __init__.py
    - factor_research.py                （モメンタム／ボラティリティ／バリュー）
    - feature_exploration.py            （forward returns / IC / summary）
  - research/... (その他の研究ユーティリティ)

補足
- OpenAI との連携は OpenAI Python SDK（Chat Completions + JSON Mode 向け）を利用する前提です。API レスポンスの堅牢な検証や再試行ロジックが組まれています。API キーは環境変数 OPENAI_API_KEY で指定してください。
- J-Quants 周りは rate limit（120 req/min）やトークン自動リフレッシュ、ページネーション対応などを内蔵しています。JQUANTS_REFRESH_TOKEN の設定が必要です。
- DuckDB をデータレイヤーとして使用します。ファイルパスは設定で変更可能です。

お問い合わせ・開発メモ
- この README はコードベース（src/kabusys）から抜粋した設計意図・使い方を記載しています。具体的な運用（cron / Airflow / Kubernetes など）やテスト、CI/CD に関してはプロジェクトの運用ガイドに従ってください。

以上。必要であれば「.env.example のテンプレート」「起動スクリプト例（systemd / cron / docker-compose）」や「典型的な ETL スケジュール例」「よくある障害と対応方法」を追加で作成します。どれを追加しますか？