KabuSys — 日本株自動売買プラットフォーム
=================================

バージョン: 0.1.0

概要
----
KabuSys は日本株のデータプラットフォーム、リサーチ、ニュースNLP、レジーム判定、ETL、監査ログ等を含むライブラリ群です。DuckDB をデータ層に使い、J-Quants からのデータ取得、OpenAI（gpt-4o-mini）によるニュースセンチメント評価などを行い、戦略・研究・実行層の基盤機能を提供します。

主な特徴
--------
- データ取得 / ETL:
  - J-Quants API から株価（日足）、財務、マーケットカレンダーを差分取得して DuckDB に保存
  - 差分更新・バックフィル・ページネーション・レート制御・トークン自動リフレッシュを実装
- データ品質管理:
  - 欠損、重複、スパイク、日付不整合の検出と QualityIssue レポート
- ニュース収集 / 前処理:
  - RSS フィード取得（SSRF対策、追跡パラメータ除去、サイズ上限）
  - raw_news / news_symbols との紐付け（冪等保存設計）
- ニュースNLP:
  - OpenAI を用いた銘柄毎のニュースセンチメント算出（JSON Mode, バッチ・リトライ対応）
- レジーム判定:
  - ETF 1321（225連動）の 200 日MA乖離とマクロニュースセンチメントを合成して市場レジーム（bull/neutral/bear）判定
- 研究ユーティリティ:
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン・IC（スピアマン）・ファクター統計サマリー
- 監査ログ:
  - シグナル→発注→約定までの監査テーブルとインデックス、DB初期化ユーティリティ
- 設定管理:
  - .env 自動ロード（プロジェクトルート検出）と Settings クラスによる環境変数アクセス

必要な環境・依存
----------------
- Python 3.9+ 推奨
- 主要依存（例）:
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ（urllib, json, datetime, logging, 等）
（プロジェクトに requirements.txt があればそちらを使ってください。なければ必要なパッケージを pip でインストールしてください。）

セットアップ手順
---------------
1. リポジトリをクローン／配置
   - pip editable インストールを想定:
     - python -m pip install -e .

2. 必要パッケージをインストール
   - 例:
     - pip install duckdb openai defusedxml

3. 環境変数 / .env を準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env を配置すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主な必須キー（例）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - KABU_API_PASSWORD=your_kabu_api_password
     - SLACK_BOT_TOKEN=your_slack_token
     - SLACK_CHANNEL_ID=your_slack_channel
     - OPENAI_API_KEY=your_openai_api_key
   - オプション:
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PID_FILE_PATH=data/execution.pid
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO|DEBUG|...
   - .env の例:
     - # .env
       JQUANTS_REFRESH_TOKEN=xxxxxxxx
       OPENAI_API_KEY=sk-...
       KABU_API_PASSWORD=...
       SLACK_BOT_TOKEN=xoxb-...
       SLACK_CHANNEL_ID=C01234567
       DUCKDB_PATH=data/kabusys.duckdb

4. データディレクトリ作成
   - DUCKDB_PATH 等の親ディレクトリを作成しておきます（多くの初期化関数は自動作成しますが事前準備推奨）。
     - mkdir -p data

基本的な使い方
--------------
以下は主要機能を Python REPL などから呼ぶ際の例（duckdb を使用する想定）。

1. DuckDB 接続作成
   - import duckdb
   - conn = duckdb.connect("data/kabusys.duckdb")

2. 日次 ETL 実行
   - from kabusys.data.pipeline import run_daily_etl
   - from datetime import date
   - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   - result は ETLResult オブジェクト（取得件数・保存件数・品質問題・エラー情報を含む）

3. ニュースセンチメントの算出
   - from kabusys.ai.news_nlp import score_news
   - from datetime import date
   - # OPENAI_API_KEY を環境変数でセットしているか、api_key を渡す
   - n = score_news(conn, date(2026, 3, 20))
   - n は書き込んだ銘柄数を返す（ai_scores テーブルへ保存）

4. 市場レジーム判定
   - from kabusys.ai.regime_detector import score_regime
   - score_regime(conn, date(2026, 3, 20))  # OpenAI API key は環境変数か引数で渡す

5. 研究用ファクター計算
   - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
   - mom = calc_momentum(conn, date(2026, 3, 20))
   - vol = calc_volatility(conn, date(2026, 3, 20))
   - val = calc_value(conn, date(2026, 3, 20))

6. 監査ログ DB 初期化
   - from kabusys.data.audit import init_audit_db
   - audit_conn = init_audit_db("data/audit.duckdb")
   - この関数は TimeZone を UTC に固定してテーブルを作成します。

7. J-Quants クライアント
   - from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
   - token = get_id_token()  # settings.jquants_refresh_token を使用
   - rows = fetch_daily_quotes(id_token=token, date_from=date(2026,3,1), date_to=date(2026,3,20))

注意点 / 運用上のポイント
-----------------------
- Look-ahead bias 対策:
  - 多くの関数は datetime.today() / date.today() を直接参照せず、必ず target_date を明示して呼ぶ設計です。バックテスト時は target_date を正しく指定してください。
- OpenAI 呼び出し:
  - API レートや失敗時のリトライ・フェイルセーフ（スコア 0.0 で継続）などが実装されていますが、API コスト・レートには注意してください。
- .env 自動読み込み:
  - プロジェクトルートの検出は __file__ から親ディレクトリを探索します。テスト時に自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB executemany の制約:
  - 一部の保存処理は DuckDB の executemany に空リストを渡せない点に配慮して実装されています（空チェックあり）。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                      — 環境設定と .env 自動読み込み / Settings クラス
- ai/
  - __init__.py                   — score_news のエクスポート
  - news_nlp.py                   — ニュース NLP（銘柄別センチメント算出）
  - regime_detector.py            — 市場レジーム判定（ma200 + マクロニュース）
- data/
  - __init__.py
  - jquants_client.py             — J-Quants API クライアント（取得・保存・認証）
  - pipeline.py                   — 日次 ETL パイプライン（run_daily_etl 等）
  - etl.py                        — ETLResult の公開
  - stats.py                      — Zスコア正規化などの統計ユーティリティ
  - quality.py                    — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management.py        — マーケットカレンダー管理・営業日判定
  - news_collector.py             — RSS 収集（SSRF防御、正規化、前処理）
  - audit.py                      — 監査ログテーブル定義・初期化ユーティリティ
- research/
  - __init__.py
  - factor_research.py            — Momentum/Value/Volatility ファクター計算
  - feature_exploration.py        — 将来リターン、IC、統計サマリー、rank 等
- data/（他のモジュールは上記参照）

各モジュールの責務
-----------------
- config: 環境変数管理、Settings によるアプリ設定取得
- data.jquants_client: J-Quants からの取得・DuckDB への冪等保存
- data.pipeline: ETL ワークフローのオーケストレーションと結果集約
- data.quality: ETL 後のデータ品質チェック
- data.news_collector: RSS 取得と前処理（raw_news への保存ロジック含む）
- ai.news_nlp: ニュースをまとめて LLM に投げ、銘柄ごとのスコアを ai_scores に書き込む
- ai.regime_detector: MA とマクロニュースを合成して market_regime を更新
- research.*: バックテスト／研究で使うファクター生成・統計分析ユーティリティ
- data.audit: シグナル→発注→約定の監査テーブル（DDL・初期化）

貢献・拡張のヒント
------------------
- 新しいデータソースや RSS フィードを追加する場合は news_collector を拡張し、news_symbols テーブルとの紐付けロジックを実装してください。
- OpenAI モデルを切り替える場合は ai.news_nlp / ai.regime_detector の _MODEL 定数を更新し、レスポンスのバリデーションを再確認してください。
- DuckDB スキーマ変更時は data.audit.init_audit_schema 等のDDLを更新してください。

ライセンス
---------
（このリポジトリに LICENSE ファイルがあればその内容に従ってください。本 README には特定のライセンス情報を含めていません。）

問い合わせ
----------
実装や使い方に関する質問はリポジトリの issue を立てるか、開発チームにお問い合わせください。

以上。必要であれば README にサンプル .env.example や具体的な CLI 起動例、より詳細な API 使用例を追加します。どの情報を追記しますか？