KabuSys — 日本株自動売買・データプラットフォーム（README）
=============================================================================

概要
----
KabuSys は日本株のデータ収集（J-Quants）、ニュース集約・NLP（OpenAI）、研究用ファクター計算、ETL、監査ログ（監査テーブル）などを備えた自動売買プラットフォーム向けのライブラリ群です。  
設計上、バックテストでのルックアヘッドバイアスを避ける実装や、API リトライ・レート制御・冪等保存など実運用を意識した堅牢性を重視しています。

主な機能
--------
- データ取得（J-Quants）
  - 株価日足（OHLCV）、財務データ、上場銘柄情報、JPX マーケットカレンダー
  - レート制限・リトライ・トークン自動更新対応
- ETL パイプライン
  - 差分取得、バックフィル、品質チェック（欠損・スパイク・重複・日付整合性）
  - ETL 実行結果を ETLResult オブジェクトで取得
- ニュース収集・NLP（OpenAI）
  - RSS 収集（SSRF/サイズ/トラッキング除去対策）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメント（score_news）
  - マクロニュース＋ETF MA200 乖離で市場レジーム判定（score_regime）
  - JSON Mode / 冪等性 / バッチ・リトライ制御を実装
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）、ファクター統計サマリ、Z スコア正規化
- 監査ログ（audit）
  - signal_events / order_requests / executions の監査スキーマ生成、DB 初期化ユーティリティ
- マーケットカレンダー管理
  - 営業日の判定、next/prev/get_trading_days、カレンダー更新ジョブ

セットアップ手順
----------------

前提
- Python 3.10 以上を推奨（型ヒントに union 型記法などを使用）
- DuckDB を利用（Python パッケージ duckdb）
- OpenAI API を利用する場合は OpenAI の API キーが必要
- J-Quants API を利用する場合はリフレッシュトークンが必要

1) 仮想環境作成（任意）
- Unix/macOS:
  - python -m venv .venv
  - source .venv/bin/activate
- Windows (PowerShell):
  - python -m venv .venv
  - .\.venv\Scripts\Activate.ps1

2) 必須パッケージのインストール（例）
- 最低限必要なパッケージ:
  - duckdb, openai, defusedxml
- 例:
  - pip install duckdb openai defusedxml

（注）実運用で Slack 連携や kabu ステーション連携を使う場合は別途 slack_sdk や requests 等が必要になる場合があります。

3) 環境変数の準備
- プロジェクトルートに .env または .env.local を作成すると、自動で読み込まれます（kabusys.config）。
- 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

代表的な環境変数（.env 例）
- JQUANTS_REFRESH_TOKEN=あなたの_jquants_refresh_token
- OPENAI_API_KEY=あなたの_openai_api_key
- KABU_API_PASSWORD=kabuステーション接続パスワード
- KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 必要に応じて
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C01234567
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development  # development | paper_trading | live
- LOG_LEVEL=INFO

使い方（コード例）
-----------------

以下は主なユースケースのサンプルです。実行前に .env に必要なキーを設定しておいてください。

- DuckDB 接続の作成（既存 DB を使う）
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

- ETL 日次実行（差分取得 + 品質チェック）
  - from kabusys.data.pipeline import run_daily_etl
  - from kabusys.config import settings
  - from datetime import date
  - conn = duckdb.connect(str(settings.duckdb_path))
  - result = run_daily_etl(conn, target_date=date.today())
  - print(result.to_dict())

- ニュースセンチメントを作成して ai_scores に書き込む
  - from kabusys.ai.news_nlp import score_news
  - from kabusys.config import settings
  - conn = duckdb.connect(str(settings.duckdb_path))
  - from datetime import date
  - written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None で env OPENAI_API_KEY を使用
  - print(f"書き込み銘柄数: {written}")

- 市場レジーム判定（ma200 + マクロニュース）
  - from kabusys.ai.regime_detector import score_regime
  - conn = duckdb.connect(str(settings.duckdb_path))
  - from datetime import date
  - score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 研究用ファクター計算
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  - conn = duckdb.connect(str(settings.duckdb_path))
  - records = calc_momentum(conn, target_date=date(2026,3,20))
  - # records は [{"date":..., "code":..., "mom_1m":..., ...}, ...]

- 監査 DB 初期化（監査用の独立 DB を作成）
  - from kabusys.data.audit import init_audit_db
  - conn_audit = init_audit_db("data/audit.duckdb")
  - # テーブルが作成され、UTC タイムゾーンが設定されます

重要な挙動メモ
- 環境変数の自動ロード
  - kabusys.config はプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に .env と .env.local を自動的に読み込みます。
  - 読み込み優先: OS 環境 > .env.local > .env
  - テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- OpenAI 呼び出し
  - news_nlp / regime_detector ともに OpenAI の Chat Completions を JSON Mode で利用します。API エラー時はフェイルセーフでスコア 0.0 を返すなどの設計です。
  - test 用に内部の _call_openai_api をモックできるように設計されています。
- J-Quants クライアント
  - レート制御（120 req/min）とリトライ、401 の自動トークンリフレッシュに対応しています。

ディレクトリ構成（抜粋）
---------------------
以下はリポジトリ内の主要ファイル/モジュール構成（src/kabusys 以下を中心に抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                     # 環境変数/設定管理
  - ai/
    - __init__.py
    - news_nlp.py                 # ニュースセンチメント生成
    - regime_detector.py          # 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py           # J-Quants API クライアント + 保存ロジック
    - pipeline.py                 # ETL パイプライン（run_daily_etl 等）
    - etl.py                      # ETLResult 再エクスポート
    - news_collector.py           # RSS 収集（SSRF 対策等）
    - calendar_management.py      # マーケットカレンダー管理
    - quality.py                  # 品質チェック
    - stats.py                    # 汎用統計ユーティリティ
    - audit.py                    # 監査スキーマ初期化
  - research/
    - __init__.py
    - factor_research.py          # ファクター計算（momentum/value/vol）
    - feature_exploration.py      # 将来リターン・IC・統計要約
  - ai/__init__.py
  - research/__init__.py

（開発時の補足ファイル）
- .env.example (プロジェクトルートに配置する想定)
- pyproject.toml / setup.cfg など（パッケージ配布がある場合）

開発・テストに関する注意点
-------------------------
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して環境依存を排除できます。
- OpenAI や J-Quants など外部 API を呼び出す部分は、内部の HTTP / OpenAI 呼び出し関数をモックして単体テストを行う設計です（_call_openai_api などを patch 可能）。
- DuckDB は単一ファイル DB なのでローカル開発でのデータ準備・再現が容易です。

ライセンス
---------
このリポジトリにライセンス情報が付随していない場合は、利用前にライセンスを明確にしてください。社内・商用で利用する場合は法務部門と相談の上、必要な許可を得てください。

最後に
------
この README はコードベースから抽出した仕様・使用法の概要です。実際の運用では .env の機密情報管理（Vault／Secrets 管理の利用）、API キーの権限管理、監査ログとバックアップポリシー、実行環境（paper/live）の安全対策などを必ず行ってください。運用やデプロイに関する具体的な手順や CI/CD の設定が必要であれば、続けてその内容を作成します。