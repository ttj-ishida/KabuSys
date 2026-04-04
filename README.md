KabuSys
=======

日本株向けのデータプラットフォーム兼自動売買（バックテスト／リサーチ／実行補助）ライブラリのコア部分です。  
本リポジトリは ETL（J-Quants → DuckDB）、ニュース収集・NLP（OpenAI を利用したセンチメント評価）、ファクター計算、監査ログ（発注→約定トレーサビリティ）などを含むモジュール群を提供します。

主な特徴
--------
- データ取得（J-Quants API）と差分ETL（DuckDB へ冪等保存）
- ニュース収集（RSS）と前処理、銘柄紐付け
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（銘柄別 / マクロ）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロセンチメントの合成）
- ファクター計算（Momentum / Value / Volatility 等）と研究用ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログスキーマ（signal → order_request → executions のトレーサビリティ）
- 環境変数ベースの設定管理（.env 自動ロード機能あり）

セットアップ
-----------

1. Python バージョン
   - Python 3.10 以上（型アノテーションで PEP 604 などを利用）

2. 必要パッケージ（例）
   - duckdb
   - openai
   - defusedxml
   - （その他依存があれば適宜追加）

   例:
   ```
   python -m pip install duckdb openai defusedxml
   ```

3. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env を置くと自動で読み込まれます。
     自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 主要な環境変数（一部、デフォルト値や必須のものを記載）:

     - JQUANTS_REFRESH_TOKEN (必須)
       - J-Quants のリフレッシュトークン（ETL 実行・データ取得に必要）
     - KABU_API_PASSWORD (必須)
       - kabuステーション API 用パスワード（発注連携に使用）
     - OPENAI_API_KEY
       - OpenAI API キー（news_nlp / regime_detector で必要）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID
       - LINE 通知用（任意）
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
       - DuckDB ファイルパス
     - SQLITE_PATH (デフォルト: data/monitoring.db)
       - 監視用 SQLite パス
     - PID_FILE_PATH / KILL_FLAG_PATH ...（監視用）
     - KABUSYS_ENV (development | paper_trading | live) (デフォルト: development)
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) (デフォルト: INFO)

   - .env の読み込み順:
     OS 環境変数 > .env.local > .env
     （OS 環境変数は上書き防止の保護対象になります）

使い方（主要 API 例）
--------------------

以下はモジュールを利用する際の簡単な Python スニペットです。実行前に必要な環境変数（JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY 等）を設定してください。

- DuckDB 接続の生成例:
  ```py
  import duckdb
  from kabusys.config import settings

  db_path = str(settings.duckdb_path)  # Path オブジェクトを文字列化して渡す
  conn = duckdb.connect(db_path)
  ```

- 日次 ETL の実行（J-Quants からの差分取得 + 品質チェック）:
  ```py
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # target_date を指定しない場合は今日が対象
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを計算して ai_scores に保存（OpenAI API キーが必要）:
  ```py
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print("scores written:", written)
  ```

- 市場レジーム判定（MA200 乖離 + マクロセンチメント）:
  ```py
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査用 DB 初期化（監査ログ専用 DB を作る）:
  ```py
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # または ":memory:" を指定してインメモリ DB
  ```

- ファクター計算・研究ユーティリティ:
  ```py
  from datetime import date
  from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize

  momentum = calc_momentum(conn, date(2026,3,20))
  volatility = calc_volatility(conn, date(2026,3,20))
  value = calc_value(conn, date(2026,3,20))

  # Z スコア正規化
  normed = zscore_normalize(momentum, ["mom_1m","mom_3m","mom_6m","ma200_dev"])
  ```

重要な実装上の注意
------------------
- OpenAI 呼び出しは gpt-4o-mini モデルを想定し、JSON Mode で厳格に JSON を返すようにプロンプトを設計しています。API が失敗した場合はフェイルセーフ（スコア 0.0 など）を採ります。
- ETL / データ保存は冪等（ON CONFLICT DO UPDATE）で実装されています。部分失敗時に既存データを不用意に消さない設計になっています。
- 日付処理では「ルックアヘッドバイアス防止」が意識されており、内部処理は target_date 以前のデータのみを参照します（datetime.today() などを直接参照しないモジュール設計）。
- ニュース収集では SSRF 対策、受信バイト制限、defusedxml による XML 脆弱性対策などを行っています。
- J-Quants API はレート制限（120 req/min）を守るため、内部で固定間隔の RateLimiter を用いています。401 発生時はトークン自動リフレッシュを行います。

プロジェクト構成（抜粋）
---------------------

src/kabusys/ 以下の主要ファイル / モジュール:

- __init__.py
- config.py
  - 環境変数の自動読み込み・Settings クラスを提供
- ai/
  - news_nlp.py        — ニュースを銘柄別にまとめて OpenAI でスコア化し ai_scores に保存
  - regime_detector.py — ETF(1321) の MA200 とマクロセンチメントを合成して market_regime に書き込む
- data/
  - jquants_client.py  — J-Quants API クライアント（取得＋DuckDB 保存ロジック）
  - pipeline.py        — ETL パイプラインと run_daily_etl エントリポイント
  - news_collector.py  — RSS 収集・前処理・raw_news への保存
  - quality.py         — データ品質チェック（欠損・重複・スパイク・日付不整合）
  - calendar_management.py — 市場カレンダー取得 / 営業日判定ユーティリティ
  - stats.py           — zscore_normalize 等の統計ユーティリティ
  - audit.py           — 監査ログ（signal/order_request/executions）スキーマ初期化
  - etl.py             — ETLResult の再エクスポート
- research/
  - factor_research.py     — Momentum / Value / Volatility 等のファクター計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー等
- research/__init__.py     — 主要研究関数の再エクスポート
- ai/__init__.py          — score_news の再エクスポート

（strategy / execution / monitoring などの上位モジュールはパッケージインターフェースに含まれますが、本リードミットのコード抜粋では詳細実装はありません）

環境変数の自動ロードについて
----------------------------
- .env / .env.local はプロジェクトルート（.git または pyproject.toml を探索して決定）から読み込まれます。
- 読み込み順は OS 環境 > .env.local > .env です（.env.local が .env を上書き）。
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 にしてください（テスト時などで便利です）。

貢献・拡張
----------
- ニュースソース追加、Prompts の改善、OpenAI のエラーハンドリング方針調整などは ai/news_nlp.py / ai/regime_detector.py を中心に行ってください。
- 発注実装（kabuステーション連携）や戦略（signal 生成）層は strategy / execution の下位モジュールとして追加できます。監査ログは init_audit_schema で初期化した上で利用してください。

この README はコードの一部から抽出した設計方針と使い方をまとめたものです。実際の運用では .env.example を参照して必須環境変数を設定し、まずはローカル DuckDB に対して ETL を実行してデータの整合性を確認してください。