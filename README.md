KabuSys
=======

概要
----
KabuSys は日本株データ基盤・リサーチ・（将来的な）自動売買を支えるライブラリ群です。  
主に以下を提供します：

- J-Quants からのデータ取得（株価日足・財務・上場情報・市場カレンダー）
- DuckDB を用いた ETL パイプライン（差分取得・保存・品質チェック）
- ニュース収集・NLP（OpenAI を用いた銘柄ごとのニュースセンチメント）
- 市場レジーム判定（ETF + マクロニュースの合成）
- 研究用ファクター計算（モメンタム / バリュー / ボラティリティ 等）
- 監査ログスキーマ（シグナル→発注→約定のトレーサビリティ）
- 市場カレンダー管理・取引日判定ロジック

本 README はローカルでのセットアップ方法、主要な使い方、プロジェクト構成の概観をまとめたものです。

主な機能一覧
--------------
- data.jquants_client
  - J-Quants API との堅牢な通信（レートリミット・リトライ・401 自動リフレッシュ）
  - fetch / save の idempotent 実装（DuckDB への ON CONFLICT 処理）
  - 上場情報・日足・財務・カレンダー取得
- data.pipeline
  - 日次 ETL（run_daily_etl）: カレンダー→日足→財務→品質チェックの一連処理
  - 個別 ETL ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）
- data.news_collector
  - RSS 収集、URL 正規化、SSRF 対策、記事の前処理と raw_news への永続化
- data.quality
  - 欠損、スパイク、重複、日付整合性チェック。QualityIssue レポートを返す
- data.calendar_management
  - market_calendar を元に営業日/前後営業日取得などのユーティリティ
- data.audit
  - 監査ログ用テーブルとインデックスを初期化する機能（init_audit_schema / init_audit_db）
- ai.news_nlp
  - 銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）でセンチメントを付与して ai_scores に保存
- ai.regime_detector
  - ETF（1321）の MA200 乖離とマクロニュースセンチメントを合成し市場レジーム（bull/neutral/bear）を算出
- research
  - ファクター計算（モメンタム、ボラティリティ、バリュー）と特徴量探索（forward returns, IC 等）
- data.stats
  - zscore_normalize 等の汎用統計ユーティリティ

前提・依存
-----------
最低限必要となるパッケージ（代表例）：
- Python 3.10+
- duckdb
- openai (OpenAI SDK)
- defusedxml
- その他標準ライブラリ

（実際の requirements はリポジトリに requirements.txt / pyproject.toml があればそちらに従ってください）

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - またはリポジトリに requirements.txt / pyproject.toml がある場合はそれに従う

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env または .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須（最低限）環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API のパスワード（将来の実行モジュール用）
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack のチャンネル ID
   - OpenAI を使う機能を呼ぶ場合:
     - OPENAI_API_KEY または関数呼び出し時に api_key 引数を渡す
   - 任意:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
     - DUCKDB_PATH: デフォルト data/kabusys.duckdb
     - SQLITE_PATH: デフォルト data/monitoring.db

.env の読み込みルール:
- 読み込み優先順位: OS 環境変数 > .env.local > .env
- .env のパースはシェル風（export KEY=val, コメント, クォート）に対応

使い方（主要な操作例）
---------------------

注意: 以下はライブラリを直接インポートして使う方法の例です。実運用スクリプトや CLI を作成して実行することを推奨します。

1) DuckDB 接続を作る
- Python から:
  - import duckdb
  - from kabusys.config import settings
  - conn = duckdb.connect(str(settings.duckdb_path))

2) 日次 ETL を実行する
- from kabusys.data.pipeline import run_daily_etl
- result = run_daily_etl(conn, target_date=desired_date)
- result は ETLResult（取得件数、保存件数、quality_issues, errors 等を含む）

3) ニュースセンチメント（ai）をスコアリングして保存する
- from kabusys.ai.news_nlp import score_news
- from datetime import date
- count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None の場合は環境変数 OPENAI_API_KEY を使用
- 戻り値は書き込んだ銘柄数

4) 市場レジーム判定
- from kabusys.ai.regime_detector import score_regime
- score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

5) 監査ログ DB を初期化
- from kabusys.data.audit import init_audit_db
- conn_audit = init_audit_db("data/audit.duckdb")
- もしくは init_audit_schema(conn) を既存接続に対して呼ぶ

6) 研究用ファクター計算
- from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
- records = calc_momentum(conn, target_date=date(2026,3,20))
- 結果は [{ "date": ..., "code": "...", "mom_1m": ..., ... }, ...]

7) カレンダー・営業日ユーティリティ
- from kabusys.data.calendar_management import is_trading_day, next_trading_day
- is_trading_day(conn, date(2026,3,20))
- next_trading_day(conn, date(2026,3,20))

ポイント・注意事項
------------------
- Look-ahead バイアス対策: 多くの関数は date.today()/datetime.today() を直接参照せず、明示的な target_date を引数として受け取る設計です。バックテスト等では target_date を適切に与えてください。
- OpenAI 呼び出しはレスポンス検証やリトライを実装していますが、API キー・コスト・レート制限に注意して運用してください。
- J-Quants API 呼び出しはレート制限（120 req/min）をモジュール内で制御しますが、複数プロセスから同時に叩く場合は別途配慮が必要です。
- DB 操作は基本的に DuckDB を想定しています（ファイルまたは :memory:）。ファイルの親ディレクトリがなければ自動作成されます。
- 本リポジトリはデータ基盤・研究用途を主目的とし、実際の取引発注（risk/実行）部分は慎重に扱ってください。実行モジュールを使う場合は安全策（paper_trading 環境、停止スイッチ、二重チェック）を必ず導入してください。

ディレクトリ構成
----------------
（ソースは src/kabusys 以下に配置されています。主要ファイルを抜粋）

- src/kabusys/
  - __init__.py               (パッケージのエクスポート)
  - config.py                 (環境変数・設定管理)
  - ai/
    - __init__.py
    - news_nlp.py             (ニュース NLP スコアリング)
    - regime_detector.py      (市場レジーム判定)
  - data/
    - __init__.py
    - jquants_client.py       (J-Quants API クライアント + save_* 実装)
    - pipeline.py             (ETL パイプライン, ETLResult)
    - etl.py                  (ETL の公開インターフェース)
    - news_collector.py       (RSS ニュース収集)
    - quality.py              (データ品質チェック)
    - calendar_management.py  (市場カレンダー管理)
    - audit.py                (監査ログスキーマ初期化)
    - stats.py                (統計ユーティリティ)
  - research/
    - __init__.py
    - factor_research.py      (モメンタム・バリュー・ボラティリティ)
    - feature_exploration.py  (forward returns, IC, summary, rank)
  - ai/, data/, research/ などがパッケージとして機能

- その他（プロジェクトルート）
  - .env.example (想定) — 環境変数サンプル（存在しない場合は .env を作ってください）
  - pyproject.toml / setup.cfg / requirements.txt 等（存在する場合はそれに従ってください）

よくある操作例（サンプル）
-------------------------
1) 簡易 ETL 実行（対話的に）
- python REPL:
  - >>> import duckdb
  - >>> from kabusys.config import settings
  - >>> from kabusys.data.pipeline import run_daily_etl
  - >>> conn = duckdb.connect(str(settings.duckdb_path))
  - >>> res = run_daily_etl(conn)
  - >>> print(res.to_dict())

2) OpenAI を使ったニューススコアリング
- 環境変数 OPENAI_API_KEY を設定してから:
  - >>> from kabusys.ai.news_nlp import score_news
  - >>> score_news(conn, target_date=date(2026,3,20))

3) 監査 DB 初期化
- >>> from kabusys.data.audit import init_audit_db
- >>> init_audit_db("data/audit.duckdb")

サポート / 貢献
----------------
- バグ報告や提案は Issue でお願いします。
- プルリクエストは小さな単位で、テストと説明を付けてください。

ライセンス
---------
リポジトリ付属の LICENSE を確認してください。

最後に
------
この README はコードベースの公開 API と内部設計に基づき作成しました。実際に運用する際は環境変数の管理、API キーの保護、バックテストとの分離（look-ahead を避ける設計）に十分注意してください。質問や補足があれば教えてください。