KabuSys — 日本株自動売買/データ基盤ライブラリ
====================================

概要
----
KabuSys は日本株向けのデータ収集・ETL・品質チェック・特徴量生成・AI を使ったニュースセンチメント評価、
および売買監査ログを備えた汎用ライブラリです。J-Quants API / DuckDB / OpenAI（gpt-4o-mini）などと連携し、
バックテスト・リサーチ・自動売買システムの基盤機能を提供します。

主な目的：
- J-Quants から株価・財務・カレンダーを差分取得して DuckDB に保存する日次 ETL
- ニュース収集・前処理と LLM を使った銘柄別ニュースセンチメントスコアリング
- 市場レジーム判定（ETF MA + マクロニュースの LLM スコア合成）
- 研究用のファクター計算・特徴量解析ユーティリティ
- 監査ログ（signal → order_request → execution）のスキーマ初期化と管理
- データ品質チェック（欠損・スパイク・重複・日付不整合）

機能一覧
--------
大まかな機能（抜粋）：

- 環境設定
  - .env または環境変数自動読み込み（プロジェクトルートを探索）
  - 必須キー未設定時のチェック

- Data / ETL
  - J-Quants API クライアント（差分取得、ページネーション、リトライ、レート制御）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - market_calendar の差分更新ジョブ
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- ニュース
  - RSS からニュース収集（SSRF対策、トラッキングパラメータ除去、前処理）
  - raw_news / news_symbols との連携

- AI（OpenAI）
  - ニュースセンチメント（銘柄別）: kabusys.ai.news_nlp.score_news
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュース LLM）: kabusys.ai.regime_detector.score_regime
  - LLM 呼び出しは堅牢なリトライ＋JSON バリデーション設計

- Research（研究用）
  - momentum / value / volatility 等のファクター計算
  - 将来リターン計算、IC（Spearman）やファクターの統計要約
  - zscore 正規化ユーティリティ

- Data 品質チェック
  - 欠損、スパイク（前日比閾値）、重複、日付整合性チェック
  - QualityIssue オブジェクトで報告（error / warning）

- 監査ログ（Audit）
  - 信号 → 発注要求 → 約定 の監査スキーマ初期化および専用 DB 初期化ユーティリティ
  - 冪等キーやインデックス設定済み

セットアップ手順
-------------
前提
- Python 3.10+（typing | union 型ヒントの使用を鑑みて）
- DuckDB、OpenAI SDK、defusedxml などを利用

開発環境例（推奨）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（最低限）
   - pip install duckdb openai defusedxml

   ※プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使用してください。

3. パッケージのインストール（編集可能な開発モード）
   - pip install -e .

環境変数 / .env
- プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env を置くと自動で読み込まれます。
  読み込み順: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト時等）。

主な必須環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants の refresh token（ETL 用）
- KABU_API_PASSWORD: kabuステーション API パスワード（注文連携がある場合）
- SLACK_BOT_TOKEN: Slack 通知（任意機能を使う場合）
- SLACK_CHANNEL_ID: Slack チャンネル ID
- OPENAI_API_KEY: OpenAI 呼び出しに使用（AI モジュールで未指定時に参照）
- KABUSYS_ENV: 環境（development / paper_trading / live）。未指定は development。
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- DUCKDB_PATH: DuckDB ファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（モニタリング）パス（例: data/monitoring.db）

例: .env（プロジェクトルート）
- JQUANTS_REFRESH_TOKEN=xxxx...
- OPENAI_API_KEY=sk-...
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C01234567
- KABUSYS_ENV=development
- DUCKDB_PATH=data/kabusys.duckdb

使い方（クイックスタート）
------------------------

基本的な DuckDB 接続の作成例：
- import duckdb
- conn = duckdb.connect(str(settings.duckdb_path))

1) 日次 ETL を実行する
- from kabusys.data.pipeline import run_daily_etl
- from kabusys.config import settings
- import duckdb, datetime
- conn = duckdb.connect(str(settings.duckdb_path))
- result = run_daily_etl(conn, target_date=datetime.date(2026,3,20))
- print(result.to_dict())

2) ニュースセンチメント（銘柄別）をスコアする
- from kabusys.ai.news_nlp import score_news
- from kabusys.config import settings
- import duckdb, datetime
- conn = duckdb.connect(str(settings.duckdb_path))
- n_written = score_news(conn, target_date=datetime.date(2026,3,20), api_key=None)  # OPENAI_API_KEY を使う

3) 市場レジーム判定
- from kabusys.ai.regime_detector import score_regime
- conn = duckdb.connect(str(settings.duckdb_path))
- score_regime(conn, target_date=datetime.date(2026,3,20), api_key=None)

4) 監査ログ DB を初期化する
- from kabusys.data.audit import init_audit_db
- conn_audit = init_audit_db("data/audit.duckdb")  # ":memory:" も可

5) 研究用ファクター計算
- from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
- results = calc_momentum(conn, target_date=datetime.date(2026,3,20))
- normalized = zscore_normalize(results, ["mom_1m", "mom_3m", "ma200_dev"])

注意点（設計上の留意）
- 多くの関数は datetime.today() や date.today() を参照しない設計です（バックテストでのルックアヘッドバイアス回避）。
- OpenAI 呼び出しは API レートやエラーに対してリトライとフォールバックを持ちます。API キーは関数引数で渡すか環境変数 OPENAI_API_KEY を使います。
- DuckDB に対する executemany は空リストを渡すと例外になるバージョンがあるため、該当コードは空チェックを行っています。
- .env の読み込みはプロジェクトルート検出に依存します。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を使って無効化できます。

ディレクトリ構成
----------------
以下は主要なパッケージ構成（src/kabusys 内）と役割の要約です。

- src/kabusys/
  - __init__.py                : パッケージ初期化（__version__ 等）
  - config.py                  : 環境変数 / 設定管理（.env 自動読み込み・Settings）
  - ai/
    - __init__.py
    - news_nlp.py              : ニュースセンチメント（銘柄別）処理、LLM 呼び出しのラップ
    - regime_detector.py       : 市場レジーム判定（ETF MA + マクロニュース LLM）
  - data/
    - __init__.py
    - jquants_client.py        : J-Quants API クライアント（取得・保存・リトライ・レート制御）
    - pipeline.py              : ETL パイプライン（run_daily_etl 等）
    - etl.py                   : ETL 結果の公開（ETLResult）
    - quality.py               : データ品質チェック
    - news_collector.py        : RSS 収集・前処理・SSRF 対策
    - calendar_management.py   : 市場カレンダー管理（営業日判定等）
    - stats.py                 : 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                 : 監査ログスキーマ定義と初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py       : ファクター計算（momentum / value / volatility）
    - feature_exploration.py   : 将来リターン計算、IC、統計サマリー 等

追加情報 / 開発
----------------
- ログレベルは環境変数 LOG_LEVEL で制御できます（デフォルト INFO）。
- KABUSYS_ENV は development / paper_trading / live のいずれかを指定します（安全のためバリデーションあり）。
- テストを実行する場合は外部 API 呼び出し（OpenAI / J-Quants / RSS）をモックしてください。多くの内部関数はモック差し替えを想定した設計になっています。
- セキュリティ注意点：RSS の取得は SSRF や XML 攻撃に対処する実装（ホスト検証、defusedxml、受信サイズ制限）を備えていますが、運用時のネットワークポリシーも併せて検討してください。

ライセンス・貢献
----------------
この README に示した手順はリポジトリの現状を基にまとめたものです。実運用・配布時は LICENSE / CONTRIBUTING の方針に従ってください。

質問・要望
---------
使い方のサンプルコードや .env.example のテンプレートが必要であれば、用途（ETL 実行／AI スコアリング／監査DB 初期化 など）を指定して教えてください。具体例を作成します。