# KabuSys

バージョン: 0.1.0

日本株向けの自動売買 / データプラットフォームライブラリです。J-Quants API からのデータ取得（株価・財務・市場カレンダー）、DuckDB を用いた永続化、ニュースの収集・NLP スコアリング（OpenAI を利用）、市場レジーム判定、研究用ファクター計算、データ品質チェック、監査ログ（発注→約定のトレーサビリティ）などを提供します。

---

## 主な機能一覧

- データ取得・ETL
  - J-Quants API から株価日足、財務データ、JPX カレンダーを差分取得して DuckDB に保存（冪等）
  - 日次 ETL パイプライン（run_daily_etl）
- ニュース収集・NLP
  - RSS からニュースを収集（SSRF 対策・トラッキング除去・前処理）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント集約（score_news）
- 市場レジーム判定
  - ETF（1321）の 200 日移動平均乖離とマクロニュースセンチメントを合成して日次レジームを判定（score_regime）
- リサーチ / ファクター計算
  - Momentum / Volatility / Value などのファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計要約
  - z-score 正規化ユーティリティ
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合の検出（run_all_checks）
- 監査ログ・トレーサビリティ
  - signal_events / order_requests / executions テーブルを初期化するユーティリティ（init_audit_schema / init_audit_db）
- 環境設定管理
  - .env / .env.local 自動読込（プロジェクトルート基準、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - Settings オブジェクトで環境変数を型安全に取得

---

## セットアップ手順

動作には Python 3.10+ を推奨します（型ヒントに union 型表現などを使用しています）。

1. レポジトリを取得する
   - 例: git clone ...

2. 仮想環境を作成して有効化
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 依存パッケージをインストール
   - 最低限必要な主なライブラリ:
     - duckdb
     - openai
     - defusedxml
   - 開発／利用環境に応じて追加ライブラリが必要になる場合があります。簡易的にインストールする例:
     ```
     pip install duckdb openai defusedxml
     ```
   - パッケージを編集・利用する場合はソースを editable install:
     ```
     pip install -e .
     ```

4. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD を設定している場合は無効）。
   - 必須の環境変数（代表例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（ETL 用）
     - KABU_API_PASSWORD: kabu ステーション API のパスワード（注文連携用）
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack チャネル ID
     - OPENAI_API_KEY: OpenAI を使う処理（score_news / score_regime）で必要（関数呼び出しで api_key を渡すことも可能）
   - ログレベル・環境:
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
     - KABUSYS_ENV: development|paper_trading|live（デフォルト development）
   - 環境変数の例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-xxxx
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-xxxx
     SLACK_CHANNEL_ID=C0123456789
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     KABUSYS_ENV=development
     ```

---

## 使い方（コード例）

以下はライブラリ API の代表的な使い方例です。いずれも duckdb の接続オブジェクトを渡して呼び出します。

- DuckDB 接続を作って日次 ETL を実行する例:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのスコアリング（OpenAI を使用）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY を環境変数に設定していれば api_key を省略可
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {n_written}")
  ```

- 市場レジーム判定:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DB を初期化する:
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可能
  ```

- 研究用関数の利用例（ファクター計算→IC）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

  conn = duckdb.connect("data/kabusys.duckdb")
  target = date(2026, 3, 20)
  factors = calc_momentum(conn, target)
  fwd = calc_forward_returns(conn, target, horizons=[1])
  ic = calc_ic(factors, fwd, factor_col="mom_1m", return_col="fwd_1d")
  print("IC:", ic)
  ```

ログや例外は適宜出力されるため、アプリ側でログ設定を調整してください（LOG_LEVEL 環境変数や標準 logging の設定を利用）。

---

## ディレクトリ構成（主なファイル/モジュール）

（パッケージルート: src/kabusys）

- __init__.py
  - パッケージバージョン定義（0.1.0）およびエクスポート一覧

- config.py
  - .env / 環境変数の自動読み込み、Settings クラス（アプリ設定の取得）

- ai/
  - news_nlp.py
    - ニュースの OpenAI を使ったセンチメントスコアリング（score_news）
  - regime_detector.py
    - ETF の MA200 とマクロニュースで市場レジームを判定（score_regime）

- data/
  - pipeline.py
    - ETL のメイン処理（run_daily_etl、個別 ETL ジョブ）
    - ETLResult データクラス
  - jquants_client.py
    - J-Quants API クライアント（取得・保存・認証・レートリミット・リトライ）
  - news_collector.py
    - RSS フィード収集・前処理・DB 保存（SSRF 対策、トラッキング除去）
  - calendar_management.py
    - 市場カレンダー管理・営業日判定・calendar_update_job
  - stats.py
    - z-score 等の共通統計ユーティリティ
  - quality.py
    - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py
    - 監査ログテーブル定義と初期化（init_audit_schema / init_audit_db）
  - etl.py
    - pipeline.ETLResult の再エクスポート

- research/
  - factor_research.py
    - Momentum / Volatility / Value ファクター計算
  - feature_exploration.py
    - 将来リターン計算、IC、統計サマリー、ランク化ユーティリティ
  - __init__.py
    - 研究用ユーティリティのエクスポート

---

## 注意点・設計上のポイント

- Look-ahead bias を避けるため、多くの関数は内部で date.today() や datetime.now() を直接参照せず、target_date を外部から明示的に渡す設計です。バックテスト用途では過去の target_date を使って再現性を確保してください。
- OpenAI 呼び出しは外部 API 依存であり、ネットワーク障害やレート制限を考慮したリトライ・フォールバックロジックを内蔵しています。API キーは環境変数 OPENAI_API_KEY または関数引数で提供できます。
- .env の自動ロードはプロジェクトルートを .git または pyproject.toml により検出します。自動読み込みが不要な場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API 連携ではレート制限を厳守する実装（120 req/min）およびトークン自動リフレッシュを備えています。
- DuckDB への挿入は基本的に冪等（ON CONFLICT DO UPDATE / DO NOTHING）で設計されています。

---

## ライセンス・貢献

このプロジェクトのライセンスはリポジトリ内の LICENSE ファイルを参照してください。バグ報告・機能要望・プルリクエストはリポジトリの issue / PR で受け付けてください。

---

README に記載のないユーティリティ関数や内部設計の詳細はソースコード内の docstring に豊富に記載されています。まずは ETL（run_daily_etl）→ニューススコアリング（score_news）→レジーム判定（score_regime）を順に試してみることを推奨します。