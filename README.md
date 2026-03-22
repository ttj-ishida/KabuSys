# KabuSys

KabuSys は日本株向けの自動売買基盤ライブラリです。データ取得（J-Quants）、ETL、特徴量エンジニアリング、シグナル生成、バックテスト、およびニュース収集までの主要コンポーネントを備え、DuckDB をデータ層に用いる設計になっています。

主な目的は研究〜本番運用に向けた一貫したワークフローを提供することです。ルックアヘッドバイアス回避・冪等性・堅牢なエラーハンドリングを重視して実装されています。

---

## 機能一覧

- データ取得 / 保存
  - J-Quants API クライアント（株価日足、財務データ、JPXカレンダー）
  - raw データの DuckDB への冪等保存（ON CONFLICT ベース）
- ETL
  - 差分取得・バックフィル対応の ETL パイプライン
  - 市場カレンダーの管理・営業日の調整
  - 品質チェックとの連携（quality モジュールを想定）
- ニュース収集
  - RSS フィードの収集、前処理、raw_news への冪等保存
  - 銘柄コード抽出と news_symbols への紐付け
  - SSRF / XML Bomb / レスポンスサイズ上限等の安全対策
- 特徴量（Feature）計算
  - momentum / volatility / value 等の定量ファクターを計算
  - Z スコア正規化（クロスセクション）
  - ユニバースフィルタ（最低株価・流動性）適用
- シグナル生成
  - 各コンポーネントスコアを重み付けして final_score を算出
  - Bear レジーム判定に基づく BUY 抑制
  - BUY / SELL シグナルの生成と signals テーブルへの保存（日付単位の置換で冪等）
- バックテスト
  - インメモリ DuckDB コピーによる安全なバックテスト実行
  - ポートフォリオシミュレータ（スリッページ・手数料モデル）
  - バックテスト結果（履歴 / 約定 / 各種メトリクス）の算出
- ユーティリティ
  - 汎用統計（Z スコア正規化、IC 計算、ファクターサマリ等）
  - DuckDB スキーマ初期化ユーティリティ

---

## セットアップ手順（開発用）

※具体的な requirements.txt は含まれていませんが、主要依存は以下を想定します：
- python 3.9+
- duckdb
- defusedxml

1. リポジトリを取得してワークディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して有効化（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール（例）
   ```
   pip install duckdb defusedxml
   ```
   その他、HTTP クライアントや logging 等は標準ライブラリで対応しています。プロジェクトに requirements.txt がある場合はそれを使ってください。

4. DuckDB スキーマ初期化
   Python REPL かスクリプトから schema.init_schema を呼び出します。例:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```
   デフォルトでは親ディレクトリが自動作成されます。

5. 環境変数（.env）
   - プロジェクトルートに `.env` / `.env.local` を置くと、自動でロードされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードは無効化されます）。
   - 必須環境変数（Settings 参照）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意（デフォルトあり）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_pass
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（主要ワークフロー例）

- DuckDB スキーマの初期化
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  conn.close()
  ```

- J-Quants から日次株価を取得して保存
  ```python
  from datetime import date
  import duckdb
  from kabusys.data import jquants_client as jq
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  # id_token を明示的に渡すことも、モジュールキャッシュに任せることも可能
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  conn.close()
  ```

- ニュース収集（RSS）
  ```python
  import duckdb
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = duckdb.connect("data/kabusys.duckdb")
  # known_codes を与えると本文から銘柄コードを抽出して紐付けます
  result = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
  conn.close()
  ```

- 特徴量（features）構築
  ```python
  from datetime import date
  import duckdb
  from kabusys.strategy import build_features

  conn = duckdb.connect("data/kabusys.duckdb")
  count = build_features(conn, target_date=date(2024,2,1))
  conn.close()
  ```

- シグナル生成
  ```python
  from datetime import date
  import duckdb
  from kabusys.strategy import generate_signals

  conn = duckdb.connect("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2024,2,1))
  conn.close()
  ```

- バックテスト（CLI）
  リポジトリのバックテスト実行スクリプトを使います。DB は事前に prices_daily / features / ai_scores / market_regime / market_calendar を含むよう準備してください。
  ```
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --cash 10000000 --db data/kabusys.duckdb
  ```

- バックテストを Python から呼び出す
  ```python
  from datetime import date
  from kabusys.backtest.engine import run_backtest
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
  conn.close()

  print(result.metrics)
  ```

- ETL（差分更新）パターン
  data.pipeline モジュールの run_prices_etl / run_prices_etl 等の関数で差分取得・保存・品質チェックを行う設計です。各関数は DuckDB 接続と日付を受け取ります（詳細はコード内ドキュメントを参照ください）。

---

## 主要モジュールと責務

- kabusys.config
  - 環境変数を読み込み、Settings オブジェクトでアクセスする
  - プロジェクトルートの .env / .env.local を自動読み込み（無効化可能）
- kabusys.data.*
  - jquants_client: J-Quants API の取得・リトライ・レート制御、DuckDB への保存関数
  - news_collector: RSS 取得・前処理・DB 保存・銘柄抽出
  - schema: DuckDB スキーマ定義・初期化
  - stats: Z スコア正規化などの統計ユーティリティ
  - pipeline: 差分 ETL / カレンダー管理 等
- kabusys.research.*
  - factor_research: momentum / volatility / value 等のファクター計算
  - feature_exploration: 将来リターン計算・IC 計算・ファクターサマリ
- kabusys.strategy.*
  - feature_engineering: raw ファクターの統合・正規化・features テーブルへの保存
  - signal_generator: final_score 算出と BUY/SELL シグナル生成
- kabusys.backtest.*
  - simulator: 擬似約定とポートフォリオ状態管理
  - engine: 日次ループ・インメモリコピー・シミュレーションフロー
  - metrics: バックテスト評価指標計算
  - run: CLI エントリポイント

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイル群は以下のようなツリー構成です（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - stats.py
    - pipeline.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - backtest/
    - __init__.py
    - engine.py
    - simulator.py
    - metrics.py
    - clock.py
    - run.py
  - execution/  (発注関連は将来実装想定)
  - monitoring/ (監視・通知関連は将来実装想定)

---

## 実装上の注意点・設計ポリシー

- 冪等性: DB への保存処理は ON CONFLICT や INSERT ... DO NOTHING を多用し、再実行での上書き/重複を防止しています。
- ルックアヘッドバイアス対策: 戦略・研究処理はいずれも target_date 時点までの情報のみを参照するよう設計されています。
- レート制御と堅牢性: J-Quants クライアントは固定間隔のスロットリング、リトライ、401 リフレッシュ処理を実装しています。
- セキュリティ / 安全対策: RSS 収集は SSRF 対策、XML パーサーの安全ライブラリ(defusedxml)、レスポンス上限、リダイレクト検査等を行います。
- テスト容易性: API トークンの注入や一部関数のインタフェース設計によりモック/単体テストが行いやすいよう配慮されています。

---

## よくある質問

- Q: .env を自動ロードしたくない場合は？
  - A: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを抑止できます。

- Q: DuckDB スキーマをローカルで初期化したい
  - A: kabusys.data.schema.init_schema("path/to/db") を呼んでください。":memory:" を渡すことでインメモリ DB になります。

- Q: バックテストで外部 DB を汚したくない
  - A: run_backtest は source_conn からインメモリの DuckDB に必要なテーブルをコピーして実行するため、元の DB を汚しません（ただし事前に適切なデータが必要です）。

---

README はここまでです。必要であれば次の内容を追加できます：
- 具体的な .env.example ファイル
- requirements.txt の推奨パッケージ一覧
- よく使う SQL サンプル（テーブルのクエリ例）
- 各モジュールの API 使用例（関数別の詳細スニペット）