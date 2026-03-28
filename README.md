# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ（モジュール群）。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、監査ログなどを提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム・研究プラットフォーム向けの共通ライブラリ群です。  
主な目的は次の通りです。

- J-Quants API を使った市場データ（株価・財務・市場カレンダー）取得と DuckDB への冪等保存
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI を用いたニュースセンチメント分析（銘柄単位）およびマクロセンチメントと価格指標の合成による市場レジーム判定
- データ品質チェック（欠損、スパイク、重複、日付整合性）
- ファクター計算（モメンタム / バリュー / ボラティリティ等）と特徴量探索ユーティリティ
- 発注〜約定までの監査ログ（監査テーブル、初期化ユーティリティ）

設計方針として、ルックアヘッドバイアス回避（内部で date.today()/datetime.today() を直接参照しない設計）、冪等処理、外部APIのレート制御・リトライ、テスト容易性を重視しています。

---

## 主な機能一覧

- 環境変数/設定管理（kabusys.config）
  - .env / .env.local 自動読み込み（プロジェクトルート検出）、必須値チェック
- データ取得・ETL（kabusys.data.jquants_client / kabusys.data.pipeline）
  - J-Quants から日足・財務・カレンダーをページネーション対応で取得
  - DuckDB へ ON CONFLICT DO UPDATE による冪等保存
  - run_daily_etl() による一括ETL + 品質チェック
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合を検出し QualityIssue を返却
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、次営業日／前営業日取得、カレンダー更新ジョブ
- ニュース収集（kabusys.data.news_collector）
  - RSS 収集、URL 正規化、トラッキング除去、SSRF 対策、raw_news への保存想定
- ニュースNLP / レジーム判定（kabusys.ai.news_nlp, kabusys.ai.regime_detector）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメント（ai_scores）とマクロセンチメントによる市場レジーム判定
  - レスポンスのバリデーション、リトライ、フォールバック（失敗時はスコア 0.0）
- 研究用ユーティリティ（kabusys.research）
  - モメンタム・ボラティリティ・バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、Zスコア正規化
- 監査ログ（kabusys.data.audit）
  - シグナル → 発注要求 → 約定 をトレースするテーブル定義と初期化ユーティリティ

---

## 必要条件

- Python 3.10 以上（typing の「|」表記を使用）
- 主要依存ライブラリ（例）
  - duckdb
  - openai (または openai SDK に相当するパッケージ)
  - defusedxml
- ネットワーク接続（J-Quants / OpenAI / RSS フィード）

（実際の配布パッケージでは requirements.txt / pyproject.toml を参照してください）

---

## セットアップ手順（開発向け）

1. リポジトリをクローンし、開発環境を作成
   - git clone ...
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 例:
     - pip install duckdb openai defusedxml

   - 開発インストール（パッケージ化されている場合）:
     - pip install -e .

3. 環境変数の設定 (.env)
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env を置くと自動で読み込まれます。
   - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 必須の環境変数（例）
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
     - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime のデフォルト参照先）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — （通知用途）
     - KABUS_API_PASSWORD — kabuステーションのパスワード
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - KABUSYS_ENV — development / paper_trading / live
     - LOG_LEVEL — DEBUG/INFO/...
   - .env のフォーマットは shell の KEY=VALUE 形式を想定します（export プレフィックス、クォート、コメント対応）。

4. データベース初期化
   - DuckDB ファイルを利用する場合は、親ディレクトリが作成されることを確認してください（kabusys.data.audit.init_audit_db などは自動で作成します）。

---

## 使い方：主要な例

以下は Python REPL やスクリプト内での利用例。実行前に環境変数（OPENAI_API_KEY など）を設定してください。

- DuckDB 接続を用意する（共通）
  - import duckdb
  - from kabusys.config import settings
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する（市場データの取得・保存・品質チェック）
  - from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニュースセンチメントを計算して ai_scores に保存する
  - from datetime import date
    from kabusys.ai.news_nlp import score_news
    # api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定
    n_written = score_news(conn, target_date=date(2026, 3, 20))
    print("書き込み銘柄数:", n_written)

- 市場レジーム判定（ma200 と マクロセンチメントの合成）
  - from datetime import date
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026, 3, 20))

- ファクター計算（研究）
  - from datetime import date
    from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
    mom = calc_momentum(conn, date(2026, 3, 20))
    val = calc_value(conn, date(2026, 3, 20))
    vol = calc_volatility(conn, date(2026, 3, 20))

- 将来リターンや IC 計算
  - from kabusys.research.feature_exploration import calc_forward_returns, calc_ic
    fwd = calc_forward_returns(conn, date(2026, 3, 20), horizons=[1,5,21])
    ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")

- 監査ログ用 DB の初期化
  - from kabusys.data.audit import init_audit_db
    audit_conn = init_audit_db("data/audit.duckdb")
    # init_audit_db は transactional=True でDDLを実行します

- カレンダー関連ユーティリティ
  - from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days
    is_trading = is_trading_day(conn, date(2026,3,20))

注意点：
- OpenAI 呼び出しはネットワーク/レート/課金を伴います。テスト時はモック化が用意しやすいよう設計されています（各モジュールの _call_openai_api 等を patch 可能）。
- J-Quants API 呼び出しはレート制御・リトライ・401 リフレッシュをサポートしています。get_id_token() や fetch_* 関数を利用してください。

---

## 環境変数（主なキー）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- OPENAI_API_KEY — OpenAI API キー（score_news / regime_detector が参照）
- KABU_API_PASSWORD — kabu ステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知設定
- DUCKDB_PATH — DuckDB ファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH — sqlite3（監視用）パス（例: data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — DEBUG/INFO/...
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動読み込みを無効化

.env の自動読み込みはプロジェクトルート（.git または pyproject.toml の存在）から行われ、.env → .env.local の順で読み込みます（.env.local が優先）。


---

## ディレクトリ構成（抜粋）

以下は主要なファイル／モジュールのツリー（src 配下）です。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/*（その他ユーティリティ）

上記のモジュールは機能ごとに責務が分離されており、DuckDB 接続や API キーは呼び出し側で注入可能になっています。

---

## 開発・テストについて

- OpenAI / J-Quants の外部 API 呼び出しはテストでモック化しやすいよう関数が分離されています（例: news_nlp._call_openai_api, regime_detector._call_openai_api, news_collector._urlopen などを patch）。
- ETL や保存関数は DuckDB への接続（:memory: も可）でローカルにテスト可能です。
- .env 自動読み込みをテストから無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## 補足 / 注意事項

- 本ライブラリは「データ収集・研究・監査」機能を中心に提供しており、実際のブローカー発注ロジック（kabuステーション等）や戦略の自動売買ポジション管理は別モジュールで実装する想定です。
- API キーやトークン取り扱いは慎重に行ってください。ログに機密情報を書き出さないよう運用を工夫してください。
- DuckDB のバージョン差異により executemany の挙動に注意した実装（空リスト禁止対応など）があります。

---

必要に応じて README をより詳細化（例: API レスポンススキーマ、SQL スキーマ定義、実運用のワークフロー例、CI 設定）できます。追加で記載したい内容があれば教えてください。