KabuSys
=======

概要
----
KabuSys は日本株のデータ収集・品質管理・リサーチ・AI ベースのニュースセンチメント評価・市場レジーム判定・監査ログ管理を目的としたライブラリです。J-Quants API からの日次データ ETL、RSS ニュース収集、OpenAI を使ったニュース NLP（銘柄別スコア付与）、ETF を用いた市場レジーム判定、ファクター計算・特徴量探索、データ品質チェック、監査ログ（発注・約定トレース）などの機能を提供します。

主な機能
--------
- ETL パイプライン
  - run_daily_etl による市場カレンダー / 株価（日次） / 財務データの差分取得・保存・品質チェック
  - J-Quants API クライアント（ページネーション・リトライ・トークン自動更新・レート制御）
- データ管理
  - DuckDB を使ったデータ保存・冪等保存（ON CONFLICT で上書き）
  - market_calendar, raw_prices, raw_financials, raw_news, ai_scores 等を想定
- ニュース収集
  - RSS からの収集（トラッキングパラメータ除去、記事 ID は正規化 URL の SHA-256）と SSRF 対策
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースセンチメントを gpt-4o-mini（JSON Mode）で評価し ai_scores に保存
  - バッチ・リトライ・レスポンス検証を搭載
- 市場レジーム判定
  - ETF 1321 の 200 日移動平均乖離とマクロニュース LLM センチメントを合成して daily regime 判定
- 研究用途（research）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリー
  - zscore 正規化ユーティリティ
- データ品質チェック
  - 欠損、スパイク（前日比）、重複、日付不整合の検出
- 監査ログ（audit）
  - signal_events / order_requests / executions 等、トレーサビリティのためのスキーマ定義・初期化ユーティリティ
- 設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）と Settings API

セットアップ手順
---------------
1. 必要環境
   - Python 3.10 以上（typing | 標準的な近年バージョンを想定）
   - ネットワークアクセス（J-Quants / OpenAI / RSS）
   - 推奨パッケージ（最低限）:
     - duckdb
     - openai
     - defusedxml
   - 開発環境により追加で requests 等が必要になる場合があります。

2. インストール（ローカル開発）
   - 仮想環境を作成して有効化した後、必要パッケージをインストールしてください。
     例:
       python -m venv .venv
       source .venv/bin/activate   # Windows: .venv\Scripts\activate
       pip install duckdb openai defusedxml
   - パッケージ化されている場合は:
       pip install -e .

3. 環境変数 / .env
   - プロジェクトルート（.git or pyproject.toml がある階層）に .env / .env.local を置くことで自動読み込みされます。
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 主な必須環境変数:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - OPENAI_API_KEY : OpenAI API キー（score_news / score_regime で参照）
     - KABU_API_PASSWORD : kabu ステーション API のパスワード（発注系で使用）
     - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID : Slack 通知に使用
   - その他:
     - KABUSYS_ENV（development / paper_trading / live）
     - LOG_LEVEL（DEBUG/INFO/...）
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視用 DB、デフォルト data/monitoring.db）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

使い方（基本例）
----------------

- DuckDB 接続の例:
  from datetime import date
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行:
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメント（単日）を取得して ai_scores に保存:
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  n = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY は環境変数か引数で指定可能

- 市場レジーム判定:
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を参照

- 監査 DB 初期化（監査専用 DB ファイルを作る）:
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit_duckdb.db")

- 研究系（例: モメンタム計算）:
  from kabusys.research import calc_momentum
  from datetime import date

  mom = calc_momentum(conn, target_date=date(2026,3,20))
  # mom は辞書のリスト

- テスト時の注入ポイント
  - OpenAI 呼び出し部分は内部でラップしており、ユニットテストでは kabusys.ai.news_nlp._call_openai_api や kabusys.ai.regime_detector._call_openai_api を patch して差し替え可能です。
  - 自動 .env ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

注意点・設計方針（抜粋）
-----------------------
- ルックアヘッドバイアス対策: ほとんどの処理（news window, ma 計算, ETL など）は datetime.today()/date.today() を無秩序に参照せず、target_date を明示的に引数として受け取る設計です。
- 冪等性: J-Quants から取得したデータは save_* 関数で ON CONFLICT DO UPDATE を利用して冪等保存します。
- ネットワーク堅牢性: J-Quants クライアントおよび OpenAI 呼び出しはリトライ・バックオフ・レート制御を組み込んでいます。
- セキュリティ: news_collector は SSRF 対策・受信サイズ制限・defusedxml による XML パース保護等を実装しています。
- テスト容易性: API キーや HTTP 呼び出しは引数で注入可／モック化しやすいように設計されています。

ディレクトリ構成（概略）
----------------------
src/kabusys/
- __init__.py                     : パッケージ定義、バージョン
- config.py                       : 環境変数 / Settings 管理（.env 自動ロード含む）
- ai/
  - __init__.py                   : score_news の公開など
  - news_nlp.py                   : ニュース NLP（銘柄別スコアリング）
  - regime_detector.py            : 市場レジーム判定
- data/
  - __init__.py
  - pipeline.py                   : ETL パイプライン（run_daily_etl 等）
  - etl.py                        : ETLResult 再エクスポート
  - jquants_client.py             : J-Quants API クライアント（fetch/save）
  - news_collector.py             : RSS ニュース収集
  - calendar_management.py        : market_calendar 管理・営業日ユーティリティ
  - stats.py                      : zscore_normalize 等の統計ユーティリティ
  - quality.py                    : データ品質チェック
  - audit.py                      : 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py            : Momentum/Volatility/Value 等
  - feature_exploration.py        : forward returns / IC / summary / rank
- ai/（上記同様）
- その他モジュール...
（上記は主要ファイルの抜粋です）

よくある質問（FAQ）
------------------
Q: OpenAI API キーはどのように指定しますか？
A: 環境変数 OPENAI_API_KEY を設定するか、score_news / score_regime の api_key 引数に直接渡してください。

Q: .env はどこから読み込まれますか？
A: ライブラリ import 時にプロジェクトルート（.git または pyproject.toml がある階層）を基準に .env と .env.local を順に読み込みます。OS 環境変数が優先され、.env.local は .env を上書きします。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

Q: テスト時の外部 API 呼び出しはどうしますか？
A: jquants_client の HTTP 呼び出しや OpenAI 呼び出しは個別にモックできます（モジュール内のヘルパー関数にパッチを当てる設計）。

開発・寄稿
----------
- バグ報告・機能要望は Issue を立ててください。
- コントリビュート時はユニットテスト・型チェック・ドキュメントの更新をお願いします。

ライセンス
---------
（このテンプレートにはライセンス情報は含まれていません。プロジェクトルートに LICENSE を追加してください。）

以上が KabuSys の概要と基本的な使い方です。必要であれば、具体的なサンプルスクリプト（ETL バッチやニューススコアリングのサンプル）を作成しますので知らせてください。