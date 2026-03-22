# KabuSys

バージョン: 0.1.0

KabuSys は日本株のデータ取得、特徴量生成、シグナル生成、バックテスト、ETL、ニュース収集などを備えた自動売買システムのライブラリ群です。DuckDB をデータ層に使用し、J-Quants API や RSS などからデータを取り込み、研究（research）→ 特徴量（feature）→ 戦略（strategy）→ 発注（execution）というワークフローを想定しています。

---

## 主な特徴（機能一覧）

- データ取得 / 保存
  - J-Quants API クライアント（株価日足、財務、マーケットカレンダー）
  - RSS ニュース収集（トラッキングパラメータ除去・SSRF 対策・gzip 対応）
  - DuckDB に対する冪等保存（ON CONFLICT 処理）
- データスキーマ管理
  - DuckDB スキーマ初期化（init_schema）
  - 生データ / 整形済み / 特徴量 / 実行レイヤーを含む多層スキーマ
- 特徴量・研究
  - momentum / volatility / value 等のファクター計算（research モジュール）
  - クロスセクション Z スコア正規化ユーティリティ
  - ファクター探索（IC, forward returns, 統計サマリ）
- 戦略（シグナル生成）
  - 正規化済み特徴量と AI スコアを統合した final_score に基づく BUY/SELL シグナル生成
  - Bear レジームによる BUY 抑制・エグジット判定（ストップロス等）
- バックテスト
  - ポートフォリオシミュレータ（スリッページ・手数料モデル、約定シミュレーション）
  - 日次スナップショット記録、トレード記録
  - メトリクス計算（CAGR、Sharpe、MaxDD、勝率、Payoff）
  - CLI からのバックテスト実行（python -m kabusys.backtest.run）
- ETL パイプライン
  - 差分更新、バックフィル、品質チェックの骨格
- 安全設計
  - API レート制御、リトライ、トークン自動リフレッシュ
  - RSS の XML/SSRF 対策、受信サイズ制限

---

## 必要条件 / 依存関係

主な依存パッケージ（プロジェクトに合わせて pyproject.toml / requirements.txt を参照してください）：
- Python 3.9+
- duckdb
- defusedxml

その他、標準ライブラリのみで多くの処理が実装されていますが、実行環境に合わせた追加パッケージが必要な場合があります。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ... （適宜）

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - （パッケージ化されている場合は）pip install -e .

4. 環境変数の準備
   - プロジェクトルートに .env/.env.local を作成すると自動で読み込まれます（自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須環境変数（少なくとも以下を用意してください）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabu ステーション API のパスワード
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID
   - 任意 / デフォルトがあるもの:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると .env の自動ロードを無効化
     - KABUSYS_ENV により is_live / is_paper / is_dev の判定に影響する

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-xxxxx
   SLACK_CHANNEL_ID=CXXXXXXXX
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプト内で:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
   - デフォルトのデータベースパスは設定で DUCKDB_PATH を参照できます（settings.duckdb_path）。

---

## 使い方（代表的な操作例）

- DuckDB スキーマを初期化する
  ```
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  conn.close()
  ```

- J-Quants から株価を取得して保存する（簡易例）
  ```
  from kabusys.data import jquants_client as jq
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,12,31))
  saved = jq.save_daily_quotes(conn, records)
  conn.close()
  ```

- ニュース収集ジョブを実行する
  ```
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={'7203','6758'})
  conn.close()
  ```

- 特徴量の構築（features テーブルへの保存）
  ```
  from datetime import date
  import duckdb
  from kabusys.strategy import build_features

  conn = duckdb.connect("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2024,3,31))
  ```

- シグナル生成
  ```
  from datetime import date
  import duckdb
  from kabusys.strategy import generate_signals

  conn = duckdb.connect("data/kabusys.duckdb")
  count = generate_signals(conn, target_date=date(2024,3,31))
  ```

- バックテスト（Python API）
  ```
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.backtest.engine import run_backtest

  conn = init_schema("data/kabusys.duckdb")
  result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
  conn.close()

  # 結果を表示
  metrics = result.metrics
  print(metrics)
  ```

- バックテスト（CLI）
  ```
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --cash 10000000 --db data/kabusys.duckdb
  ```

- ETL（パイプライン）骨格
  - data.pipeline モジュールには差分更新や get_last_price_date / run_prices_etl 等の関数があり、ETL ジョブの実装と運用に使えます（詳細はコードコメント参照）。

---

## 重要な設定項目（settings）

settings は kabusys.config.Settings で管理され、環境変数から取得されます。主なプロパティ:

- jquants_refresh_token: JQUANTS_REFRESH_TOKEN（必須）
- kabu_api_password: KABU_API_PASSWORD（必須）
- kabu_api_base_url: KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- slack_bot_token: SLACK_BOT_TOKEN（必須）
- slack_channel_id: SLACK_CHANNEL_ID（必須）
- duckdb_path: DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- sqlite_path: SQLITE_PATH（デフォルト: data/monitoring.db）
- env: KABUSYS_ENV（development/paper_trading/live）
- log_level: LOG_LEVEL

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml を基準）にある .env / .env.local を実行時に自動で読み込みます。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## ディレクトリ構成（抜粋）

src/kabusys/
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
- execution/
  - __init__.py
- monitoring/ (存在は __all__ にあるが実装は別ファイルで管理)

（実際のリポジトリには README、pyproject.toml 等のトップレベルファイルがある想定です）

---

## 開発・拡張のポイント

- DuckDB スキーマは init_schema() で自動作成されるため、初期データのロード前に呼び出してください。
- ETL は差分取得を前提に設計されています。run_prices_etl 等は backfill をサポートします（pipeline.py を参照）。
- シグナル生成・特徴量計算は「ルックアヘッドバイアスの回避」を明確に意識しています。target_date 時点までのデータのみを使用します。
- news_collector は SSRF / XML 攻撃 / 大容量レスポンス対策を行っています。テスト時は _urlopen をモックしてください。
- J-Quants クライアントは固定間隔スロットリング＋リトライ＋トークン自動更新を実装しています。API レート制限に注意してください。

---

## ライセンス / 責任範囲

- 本リポジトリは研究・開発用のフレームワークです。実運用にあたっては注文周り（kabu API）やリスク管理・監査・法令順守が必要です。
- 各種パラメータ（手数料、スリッページ、閾値等）はサンプル実装であり、実資金運用前に十分な検証を行ってください。

---

必要であれば、README に含めるコマンドの詳細、.env.example の完全なテンプレート、または各モジュールの API リファレンス（関数引数や戻り値の詳細）を出力できます。どの情報を優先して追加しますか？