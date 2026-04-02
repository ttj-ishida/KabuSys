KabuSys — 日本株自動売買 / データ基盤ライブラリ
=================================================

概要
----
KabuSys は日本株向けのデータパイプライン、機械学習支援（ニュース NLP / レジーム判定）、ファクター計算、監査ログなどを提供するライブラリ群です。J-Quants API や RSS、OpenAI（gpt-4o-mini など）など外部サービスと連携して日次 ETL、ニュースセンチメント評価、ファクター解析、監査記録の初期化を行えるよう設計されています。

主な特徴
--------
- データ ETL（J-Quants からの株価・財務・カレンダー取得、DuckDB への冪等的保存）
- ニュース収集（RSS）、前処理、LLM による銘柄別センチメント評価（ai.news_nlp）
- 市場レジーム判定（ETF 1321 の 200 日 MA とマクロニュースの LLM 結果を合成）
- ファクター計算（モメンタム / ボラティリティ / バリュー 等）および研究用統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ（signal → order_request → executions のトレーサビリティ）を DuckDB に初期化
- 設定は .env または環境変数で管理（自動ロード機能あり。テスト時は無効化可能）

動作要件（推奨）
----------------
- Python 3.10 以上（型アノテーションで | 演算子を使用）
- 必要な Python パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - （必要に応じて他の HTTP / Slack 等のクライアント）

インストール（開発環境）
-----------------------
例（仮想環境を使う場合）:

1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージのインストール（プロジェクトに requirements.txt があればそちらを利用）
   - pip install duckdb openai defusedxml

3. （任意）パッケージを編集可能モードでインストール
   - pip install -e .

環境変数（必須 / 推奨）
----------------------
主に以下の環境変数が使用されます。プロジェクトルートの .env / .env.local に記載して利用します（config モジュールが自動で読み込みます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

必須（ライブラリの多くの機能で必要）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（get_id_token に使用）
- SLACK_BOT_TOKEN       : Slack 通知を利用する場合の Bot トークン
- SLACK_CHANNEL_ID      : Slack チャンネル ID

Kabu/API 関連
- KABU_API_PASSWORD     : kabuステーション API のパスワード
- KABU_API_BASE_URL     : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）

データベース / ファイルパス（任意: デフォルト有り）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH         : 実行 PID ファイルパス（デフォルト: data/execution.pid）

OpenAI
- OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime の引数としても渡せる）

システム / ログ
- KABUSYS_ENV           : development / paper_trading / live（デフォルト development）
- LOG_LEVEL             : DEBUG / INFO / ...（デフォルト INFO）

セットアップのポイント
----------------------
1. プロジェクトルートに .env を作成して上記の必須キーを記載します（.env.example を参考にしてください）。
2. DuckDB のデータベースファイルはデフォルトで data/kabusys.duckdb に保存されます。parent ディレクトリがない場合は適宜作成してください。
3. テスト環境では自動的に .env を読み込む処理を無効化できます:
   - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な使い方（コード例）
-----------------------

- DuckDB 接続の準備（監査 DB 初期化例）
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # これで監査ログ用テーブルが作成されます（UTC タイムゾーン固定）

- 日次 ETL 実行（J-Quants からの株価/財務/カレンダー取得）
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニューススコア算出（LLM を用いた銘柄ごとのスコア付与）
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"scored {count} codes")

- 市場レジーム判定（ETF 1321 の MA とマクロニュースを合成）
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")

- ファクター計算（研究用）
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))
  val = calc_value(conn, date(2026,3,20))

- データ品質チェック
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i)

注意点 / 設計ポリシー
--------------------
- 多くの処理はルックアヘッドバイアスを避けるため、内部で datetime.today() や date.today() を参照せず、呼び出し側から target_date を渡す設計になっています。バックテストや再現性のために明示的な target_date を指定してください。
- DuckDB への保存は基本的に冪等（ON CONFLICT DO UPDATE / DO NOTHING）で行われ、部分失敗時でも既存データを極力保護する実装方針です。
- OpenAI や外部 API 呼び出しにはリトライ・バックオフ・フェイルセーフが実装されており、API 失敗時はスコアを 0.0 として続行する等の安全措置があります。
- RSS フェッチ周りでは SSRF 対策、受信サイズ制限、XML パースの安全化（defusedxml）などを行っています。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                       — 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py                    — ニュースセンチメント生成（OpenAI 連携）
  - regime_detector.py             — 市場レジーム判定（MA + マクロニュース）
- data/
  - __init__.py
  - calendar_management.py         — 市場カレンダー管理・営業日判定
  - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
  - etl.py                         — ETL 結果 ETLResult の再エクスポート
  - jquants_client.py              — J-Quants API クライアント（取得 + DuckDB 保存）
  - news_collector.py              — RSS 収集・前処理
  - quality.py                     — データ品質チェック
  - stats.py                       — 統計ユーティリティ（zscore_normalize 等）
  - audit.py                       — 監査ログスキーマ初期化 / init_audit_db
- research/
  - __init__.py
  - factor_research.py             — モメンタム / バリュー / ボラティリティ等
  - feature_exploration.py         — 将来リターン計算 / IC / 統計サマリー
- ai / data / research 以下の他ユーティリティ多数（詳細はソース参照）

よくある質問（FAQ）
------------------
Q: 環境変数の自動ロードを抑止したい
A: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると config モジュールの .env 自動ロードを無効化できます。テストで環境を独自にセットアップする際に有用です。

Q: OpenAI キーをコード内で直接渡したい
A: score_news / score_regime など多くの関数は api_key 引数を受け付けます。None の場合は環境変数 OPENAI_API_KEY を参照します。

Q: DuckDB の初期スキーマはどこで定義される？
A: 各機能（raw_prices, raw_financials, market_calendar, ai_scores, market_regime, audit テーブル等）はプロジェクト内の別モジュールで作成されます。監査ログは kabusys.data.audit.init_audit_schema / init_audit_db で初期化できます。その他テーブルの初期化スクリプトはプロジェクトに合わせて用意してください。

貢献 / 開発
------------
- コーディング規約に従い、ユニットテストを追加してください。
- 外部 API との呼び出しはモック可能なように実装されています（テストで _call_openai_api などを patch する想定）。
- .env.example を用意して必須環境変数をドキュメント化してください。

ライセンス
---------
プロジェクト内で別途指定がない場合はリポジトリの LICENSE を参照してください。

---
この README はリポジトリの主要モジュールと基本的な使い方・セットアップ手順をまとめたものです。詳細な内部実装や追加機能（Slack 通知、kabu API 実行ロジック等）は該当ソースファイルを参照してください。必要であればサンプルスクリプトや .env.example のテンプレートも作成します。