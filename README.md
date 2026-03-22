# KabuSys

日本株向けの自動売買システムのコンポーネント群をまとめたライブラリです。データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、バックテストフレームワーク、ニュース収集などを含み、研究→本番運用のワークフローを想定して設計されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を提供します。

- 市場データ・財務データ・ニュースの取得と DuckDB への保存（idempotent）
- 研究用ファクター計算と特徴量エンジニアリング（ルックアヘッド回避を重視）
- 正規化済み特徴量と AI スコアの統合によるシグナル生成（BUY / SELL）
- 日次バックテストエンジン（擬似約定、スリッページ/手数料モデル、ポートフォリオ管理）
- ニュース収集・記事処理・銘柄抽出
- 各種ユーティリティ（統計、スキーマ初期化、ETL パイプライン）

設計方針の一部：
- ルックアヘッドバイアスを防ぐため、各日付の「当日までに利用可能な情報」のみを使用することを前提に実装。
- DuckDB を中心にデータを保持し、INSERT は ON CONFLICT を使うなど冪等性を確保。
- 外部依存は最小限（標準ライブラリ + duckdb + defusedxml 等）。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション・レート制限・リトライ・トークンリフレッシュ）
  - news_collector: RSS 取得・記事前処理・DB 保存・銘柄抽出
  - schema: DuckDB スキーマの定義と初期化（raw / processed / feature / execution 層）
  - pipeline: 差分ETL処理（差分取得・保存・品質チェック）
  - stats: 汎用統計ユーティリティ（クロスセクションZスコア正規化等）
- research/
  - factor_research: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）や統計サマリ
- strategy/
  - feature_engineering: ファクターの正規化・ユニバースフィルタ・features テーブルへの保存
  - signal_generator: features と ai_scores を統合して final_score を計算、BUY/SELL シグナルを生成して signals テーブルへ保存
- backtest/
  - engine: 日次バックテストの全体ループ（インメモリ DB にデータをコピーして実行）
  - simulator: 擬似約定ロジック（スリッページ・手数料）、ポートフォリオ状態管理、スナップショット/約定記録
  - metrics: バックテスト評価指標（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff 等）
  - run: CLI エントリポイント（python -m kabusys.backtest.run）
- config.py: 環境変数ベースの設定管理（.env の自動ロード、必須キー検査、切替フラグ）

---

## 要件 / 事前準備

- Python 3.10 以上（PEP 604 の型ヒント表記等を使用）
- 必要なライブラリ（例）:
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS フィード）を行う場合は外向き通信が必要

推奨: 仮想環境を作成してお使いください。

---

## セットアップ手順（例）

1. リポジトリをクローン
   ```
   git clone <リポジトリURL>
   cd <リポジトリ>
   ```

2. 仮想環境作成（例）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   - requirements.txt があれば:
     ```
     pip install -r requirements.txt
     ```
   - 無ければ最低限:
     ```
     pip install duckdb defusedxml
     ```

4. （任意）パッケージとしてインストール
   ```
   pip install -e .
   ```

5. 環境変数設定
   プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   必須環境変数（コードで _require が呼ばれるもの）：
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

   その他（デフォルトあり）:
   - KABUSYS_ENV (development | paper_trading | live) デフォルト: development
   - LOG_LEVEL (DEBUG|INFO|...) デフォルト: INFO
   - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH（監視用、デフォルト data/monitoring.db）

   .env の簡単な例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

6. DuckDB スキーマ初期化
   Python REPL やスクリプト内で:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```

---

## 使い方（主なユースケース）

以下は代表的な利用例です。

1. バックテスト（CLI）
   - 準備: DuckDB に prices_daily, features, ai_scores, market_regime, market_calendar が必要です。
   - 実行例:
     ```
     python -m kabusys.backtest.run --start 2023-01-01 --end 2024-12-31 --db data/kabusys.duckdb
     ```
   - オプションで初期資金、スリッページ、手数料、最大ポジション比率を指定可能。

2. ファイルから DB 初期化・ETL 実行（プログラム例）
   - DuckDB 初期化:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - ETL（株価差分取得）:
     ```python
     from kabusys.data.pipeline import run_prices_etl
     from datetime import date
     res = run_prices_etl(conn, target_date=date.today())
     print(res)  # ETLResult 相当
     ```
     （run_prices_etl は差分取得、保存、品質確認を行います）

3. 特徴量構築（features テーブルへ保存）
   ```python
   from kabusys.strategy import build_features
   from kabusys.data.schema import get_connection  # もしくは init_schema
   import duckdb
   from datetime import date

   conn = duckdb.connect("data/kabusys.duckdb")
   count = build_features(conn, target_date=date(2024, 2, 1))
   print(f"features upserted: {count}")
   conn.close()
   ```

4. シグナル生成（signals テーブルへ保存）
   ```python
   from kabusys.strategy import generate_signals
   import duckdb
   from datetime import date

   conn = duckdb.connect("data/kabusys.duckdb")
   n = generate_signals(conn, target_date=date(2024, 2, 1))
   print(f"signals written: {n}")
   conn.close()
   ```

5. ニュース収集ジョブ
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   from kabusys.data.schema import get_connection
   conn = get_connection("data/kabusys.duckdb")
   # known_codes を渡すと抽出・紐付けまで行う
   known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
   res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(res)
   conn.close()
   ```

6. J-Quants からのデータ取得と保存
   ```python
   from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
   import duckdb
   from kabusys.data.schema import get_connection
   from datetime import date

   conn = get_connection("data/kabusys.duckdb")
   records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
   n = save_daily_quotes(conn, records)
   print(f"saved {n} rows")
   conn.close()
   ```

7. 研究用ユーティリティ
   - IC 計算、将来リターン、factor_summary 等は kabusys.research 以下にまとまっています。
   - 例: calc_forward_returns, calc_ic, factor_summary

---

## 設計上の注意点（運用時のポイント）

- 自動で .env をプロジェクトルートから読み込みます（プロジェクトルートは .git または pyproject.toml を基準）。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の初期化は一度行えば良いですが、バックテストは本番 DB を汚染しないためにインメモリ DB にデータをコピーして実行します。
- J-Quants API 呼び出し等で 401 が返った場合、自動でリフレッシュトークンから id_token を更新して再試行します（1 回）。
- ETL・ニュース収集は各ソースでエラーハンドリングを行い、1 ソース失敗でも他を続行する設計です。
- features / signals / positions 等は「日付単位で削除して再挿入（置換）」することで冪等性を保証します。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - pipeline.py
    - schema.py
    - stats.py
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
    - run.py
    - clock.py
  - execution/  (発注/実行関連のモジュール群のためのパッケージプレースホルダ)
  - monitoring/  (監視・アラート用のモジュールを想定)

ファイルごとの責務は各モジュール冒頭の docstring に詳述されています。まずは data/schema.init_schema() で DB を用意し、ETL → features → signals → (バックテスト/実運用) の順でワークフローを動かすのが基本です。

---

必要であれば README に以下を追加できます：
- 詳細な .env.example（全環境変数の一覧と説明）
- デプロイ手順（systemd / cron / Airflow などでの定期ジョブ化）
- 既知の制限事項・ TODO リスト
ご希望があれば追記します。