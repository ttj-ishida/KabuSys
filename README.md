# KabuSys — 日本株自動売買プラットフォーム（README）

概要
---
KabuSys は日本株向けのデータパイプライン、ニュースNLP、市場レジーム判定、リサーチ（ファクター計算）および監査（オーダートレース）を含む自動売買基盤のコアライブラリです。  
主に以下を提供します。

- J-Quants API 経由のデータ ETL（株価日足・財務・取引カレンダー）
- RSS ベースのニュース収集と OpenAI を用いた銘柄別センチメント（ai_score）算出
- ETF とマクロニュースを組み合わせた市場レジーム判定
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量解析ユーティリティ
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ初期化・操作
- データ品質チェック（欠損・スパイク・重複・日付不整合検出）

主な機能一覧
---
- data/jquants_client.py
  - J-Quants API からのデータ取得（株価日足・財務・上場情報・カレンダー）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - レートリミッタ / リトライ / トークン自動リフレッシュ実装

- data/pipeline.py
  - 差分取得に基づく日次 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - ETL 実行結果を表す ETLResult

- data/news_collector.py
  - RSS フィード収集、前処理、raw_news への冪等保存
  - SSRF 対策やサイズ上限、トラッキングパラメータ除去

- ai/news_nlp.py
  - 銘柄ごとのニュース集約 → OpenAI（gpt-4o-mini）でセンチメント算出 → ai_scores へ保存
  - バッチ・リトライ・レスポンス検証を実装

- ai/regime_detector.py
  - ETF（1321）の 200 日 MA 乖離とマクロニュースセンチメントを合成して market_regime を算出・保存

- research/
  - factor_research.py: Momentum / Value / Volatility 等のファクター算出
  - feature_exploration.py: 将来リターン計算、IC（Spearman）計算、統計サマリー等

- data/quality.py
  - 欠損、スパイク、重複、日付不整合を検出する品質チェック群

- data/audit.py
  - 監査ログ用テーブル定義・初期化（signal_events / order_requests / executions 等）
  - init_audit_db により監査専用 DuckDB DB を初期化可能

セットアップ手順
---
1. 推奨: Python 仮想環境を作成して有効化する
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要ライブラリをインストール
   - 必須パッケージ（代表例）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   ※ プロジェクトとして packaging（pyproject.toml / setup.py）がある場合は
   - pip install -e .

3. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml のある階層）に .env または .env.local を配置すると自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 最低限必要な環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN=...
     - OPENAI_API_KEY=...
     - KABU_API_PASSWORD=...          # kabuステーション連携がある場合
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

4. データベース用ディレクトリを作成（必要に応じて）
   - mkdir -p data

使い方（簡単な例）
---
以下は Python REPL やスクリプトでの利用例です。

- DuckDB 接続を作り ETL を実行
  ```
  import duckdb, datetime
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=datetime.date(2026,3,20))
  print(result.to_dict())
  ```

- ニュースのセンチメントスコアを算出（OpenAI API キーは環境変数か api_key 引数で指定）
  ```
  from kabusys.ai.news_nlp import score_news
  import duckdb, datetime

  conn = duckdb.connect("data/kabusys.duckdb")
  n = score_news(conn, datetime.date(2026,3,20), api_key="sk-...")
  print("scored:", n)
  ```

- 市場レジームをスコアリングして保存
  ```
  from kabusys.ai.regime_detector import score_regime
  import duckdb, datetime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, datetime.date(2026,3,20), api_key="sk-...")
  ```

- 監査ログ DB 初期化（監査専用 DB）
  ```
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # この conn に対して order/event の挿入やクエリを行う
  ```

- ファクター計算・研究用ユーティリティ
  ```
  from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize
  import duckdb, datetime

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, datetime.date(2026,3,20))
  normalized = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])
  ```

環境変数の自動読み込み挙動
---
- パッケージロード時にプロジェクトルート（.git または pyproject.toml）を探索し、.env を自動で読み込みます。
- 読み込み順序（優先度高 → 低）:
  - OS 環境変数
  - .env.local（override=True）
  - .env（override=False）
- 自動読み込みを無効化するには:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

ディレクトリ構成（主要ファイル説明）
---
- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定管理（Settings クラス）
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュース集約 → OpenAI で銘柄別スコア算出 → ai_scores へ保存
    - regime_detector.py
      - ETF（1321）の MA 乖離 + マクロニュース LLM スコアで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存・認証・レート制御）
    - pipeline.py
      - ETL パイプライン（run_daily_etl 等）と ETLResult
    - etl.py
      - ETLResult の再エクスポート
    - calendar_management.py
      - 市場カレンダー管理・営業日判定ユーティリティ
    - news_collector.py
      - RSS 収集・前処理・保存
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - quality.py
      - データ品質チェック
    - audit.py
      - 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py
      - Momentum / Value / Volatility 等の計算
    - feature_exploration.py
      - 将来リターン, IC, 統計サマリー 等

運用上の注意・トラブルシューティング
---
- J-Quants API:
  - レート制限（120 req/min）に注意。jquants_client は固定間隔スロットリングを実装しています。
  - トークン(Refresh Token)から ID トークンを取得する際、id_token は自動キャッシュ・リフレッシュされます。

- OpenAI:
  - news_nlp / regime_detector は OpenAI の Chat Completions（gpt-4o-mini など）を想定。API 呼び出しの失敗や不正レスポンスはフェイルセーフ（スコア 0.0 やスキップ）を基本方針としていますが、API キー未設定時は ValueError を送出します。
  - テスト時は内部の _call_openai_api をモック可能です。

- DuckDB:
  - executemany に空リストを渡すとエラーになるバージョンがあるため、コード内で空リストチェックが実装されています。

- ニュース収集:
  - RSS の URL 正規化・SSRF 保護・最大受信サイズなどの安全対策を実装しています。外部 RSS を追加する際は既知の信頼できるソースを指定してください。

テスト / 開発ヒント
---
- 自動 .env ロードを無効化して、テスト用の環境変数をプログラム内で注入する:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI 呼び出しや HTTP 処理は関数単位でモック可能（テスト用フックが各モジュールに用意されています）。
- DuckDB の一時インメモリ DB を使う:
  - duckdb.connect(":memory:")

ライセンス・貢献
---
- 本 README にライセンス情報は含めていません。リポジトリに LICENSE ファイルがある場合はそちらを参照してください。  
- バグ報告・機能提案・PR を歓迎します。コードスタイルやテスト追加の際は既存の実装方針（ルックアヘッドバイアス回避、冪等保存、フェイルセーフ）に従ってください。

その他
---
- README に書かれている CLI ツールやエントリポイントはこのコードベースからは明示されていません。運用用のスクリプト（ETL スケジューラ、監視サービス、発注実行器等）は別途用意してこのライブラリを呼び出す想定です。

必要であれば:
- .env.example のテンプレートを生成
- 実行スクリプト（例: scripts/run_etl.py / scripts/score_news.py）のサンプルを追加
- requirements.txt / pyproject.toml の雛形作成

ご希望があれば、上記のうちどれを README に追記するか（.env.example、実行スクリプト、CI/テスト手順など）を教えてください。