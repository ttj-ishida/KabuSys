KabuSys
=======

概要
----
KabuSys は日本株のデータ収集・品質管理・リサーチ・ニュースNLP・市場レジーム判定・監査ログなどを備えた日本株自動売買プラットフォームのライブラリ群です。主に以下用途を想定しています：

- J-Quants API からのデータ ETL（株価・財務・マーケットカレンダー）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- ニュースの収集・NLP（OpenAI を用いた銘柄別センチメント）
- 市場レジーム判定（MA200 とマクロニュースの混合）
- 研究用ファクター計算（モメンタム／ボラティリティ／バリュー等）
- 監査トレース（シグナル→発注→約定を追跡する監査テーブル）

主要機能
--------
- ETL パイプライン（kabusys.data.pipeline.run_daily_etl）
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 差分取得・ページネーション・トークン自動リフレッシュ・レート制御・保存（DuckDB）
- データ品質チェック（kabusys.data.quality）
- ニュース収集（RSS）と保存（kabusys.data.news_collector）
- OpenAI を使ったニュースセンチメント（kabusys.ai.news_nlp）
- マクロ＋価格指標を使った市場レジーム判定（kabusys.ai.regime_detector）
- 研究用分析（kabusys.research.*）
- 監査ログ（証跡）用スキーマ初期化とユーティリティ（kabusys.data.audit）
- 汎用統計ユーティリティ（kabusys.data.stats）
- 環境設定管理（kabusys.config）: .env / .env.local の自動読み込みに対応

前提条件 / 依存
--------------
- Python >= 3.10
- パッケージ依存（主なもの）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / OpenAI / RSS）
- J-Quants のリフレッシュトークン、OpenAI API キー 等の環境変数

環境変数（主なもの）
-------------------
以下は必須またはよく使われる環境変数です（.env に記載して管理することを想定）。

必須:
- JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン
- SLACK_BOT_TOKEN        — Slack 通知用トークン（本プロジェクトで通知機能を利用する場合）
- SLACK_CHANNEL_ID       — Slack 通知先チャンネルID
- KABU_API_PASSWORD      — kabuステーション等の API パスワード（使用する場合）
- OPENAI_API_KEY         — OpenAI API キー（ai モジュールを使う場合は必須）

任意（デフォルトあり）:
- KABUSYS_ENV            — 実行環境: development / paper_trading / live（デフォルト development）
- LOG_LEVEL              — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- DUCKDB_PATH            — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH            — 監視用 sqlite パス（デフォルト data/monitoring.db）
- PID_FILE_PATH          — 実行監視用 PID ファイル（デフォルト data/execution.pid）
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視閾値

自動 .env ロードについて:
- プロジェクトルート（.git または pyproject.toml を含む親ディレクトリ）から .env と .env.local を自動で読み込みます。
- 読み込み順: OS 環境 > .env.local > .env
- テスト等で自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

セットアップ手順
---------------
1. リポジトリをクローン:
   - git clone <repo-url>

2. Python 環境の準備（仮想環境推奨）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール:
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）

4. パッケージをインストール（開発モード）:
   - pip install -e .

5. .env を作成:
   - プロジェクトルートに .env を置き、必要な環境変数を設定します（上記参照）。
   - 例:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567

使い方（主要な呼び出し例）
------------------------

注意: 多くの関数は duckdb.DuckDBPyConnection を受け取るため、まず接続を作成します。

基本的な DuckDB 接続例:
- Python REPL で:
  >>> import duckdb
  >>> conn = duckdb.connect("data/kabusys.duckdb")

ETL（日次パイプライン）を実行する:
- run_daily_etl は市場カレンダー → 株価 → 財務 → 品質チェックを順に実行します。

  >>> from datetime import date
  >>> from kabusys.data.pipeline import run_daily_etl
  >>> result = run_daily_etl(conn, target_date=date(2026,3,20))
  >>> print(result.to_dict())

ニュースセンチメント（銘柄別 ai_scores 生成）:
- OpenAI API キーは環境変数 OPENAI_API_KEY に設定しておくか、api_key 引数で渡します。

  >>> from kabusys.ai.news_nlp import score_news
  >>> from datetime import date
  >>> n_written = score_news(conn, target_date=date(2026,3,20))
  >>> print("書込み銘柄数:", n_written)

市場レジーム判定:
  >>> from kabusys.ai.regime_detector import score_regime
  >>> from datetime import date
  >>> score_regime(conn, target_date=date(2026,3,20))

監査スキーマ初期化（監査DB単体を作る例）:
  >>> from kabusys.data.audit import init_audit_db
  >>> audit_conn = init_audit_db("data/audit.duckdb")  # :memory: も可

研究用ファクター計算（例: モメンタム）:
  >>> from kabusys.research.factor_research import calc_momentum
  >>> from datetime import date
  >>> records = calc_momentum(conn, target_date=date(2026,3,20))
  >>> print(len(records))

設定・挙動のポイント
-------------------
- OpenAI 呼び出しは gpt-4o-mini を想定し、JSON mode（response_format）でレスポンスを期待しています。テスト時はモック可能です（モジュール内の _call_openai_api を patch）。
- J-Quants クライアントは ID トークンを自動取得・キャッシュし、401 時に自動リフレッシュします。レート制御（120 req/min）とリトライ処理を内蔵しています。
- ETL は差分更新とバックフィル（既存最終日から数日前まで再取得）を行い、保存は冪等（ON CONFLICT DO UPDATE）です。
- 日付処理はルックアヘッドバイアスを避けるため、内部で date.today() を直接参照しない方針の関数が多くあります（target_date を明示的に渡すことが推奨されます）。
- ニュース収集は SSRF 対策・トラッキングパラメータ除去・受信サイズ制限等の安全対策を実装しています。

ディレクトリ構成（主要ファイル）
------------------------------
以下はこのリポジトリ内の主なモジュールとファイルの一覧（抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数・設定管理（.env 自動ロード含む）
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュースのセンチメント解析 / ai_scores 書込み
    - regime_detector.py             — 市場レジーム判定（MA200 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（fetch/save）
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - etl.py                         — ETLResult の再エクスポート
    - news_collector.py              — RSS 収集・前処理・保存
    - quality.py                     — データ品質チェック
    - calendar_management.py         — マーケットカレンダー管理 / 営業日ヘルパ
    - stats.py                       — 統計ユーティリティ（zscore_normalize）
    - audit.py                       — 監査ログスキーマ初期化・ユーティリティ
  - research/
    - __init__.py
    - factor_research.py             — モメンタム・ボラティリティ・バリュー等
    - feature_exploration.py         — 将来リターン・IC・統計サマリー 等

補足 / 注意事項
---------------
- DuckDB スキーマ（テーブル名やカラム）は ETL 側および保存関数（jquants_client.save_*）と整合している必要があります。初回はスキーマ作成用の SQL / スクリプトを用意しておくことを推奨します（このリポジトリでは監査スキーマを init_audit_schema で作成できます）。
- OpenAI 呼び出しにはコストとレート制限が伴います。バッチサイズやリトライの設定は各モジュール内の定数で調整可能です。
- production（live）実行時は KABUSYS_ENV=live を設定し、ログレベルなどを適切に管理してください。
- 自動ロードされる .env の取り扱いに注意してください（機密情報の取り扱い・バージョン管理除外等）。

ライセンス・貢献
----------------
- （ここにプロジェクトのライセンスと貢献方法を追記してください）

お問い合わせ
------------
- Issue を通じてバグ報告や改善提案をお願いします。

以上が基本的な README 内容です。必要であれば、セットアップ用のスクリプト例（Dockerfile、systemd unit、cron ジョブ）や、DuckDB スキーマ定義 SQL、.env.example の具体例を追加で作成します。どれを追加しますか？