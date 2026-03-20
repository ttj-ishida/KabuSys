# KabuSys

日本株向けの自動売買・データプラットフォームライブラリです。J-Quants API や RSS ニュースを取得して DuckDB に保存し、特徴量計算→シグナル生成→発注管理までのワークフローをサポートするモジュール群を含みます。

## プロジェクト概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API から株価・財務・市場カレンダーを取得して DuckDB に保存（ETL）
- RSS ソースからニュースを収集してテキスト前処理・銘柄紐付け
- 研究用に設計されたファクター計算（Momentum / Volatility / Value 等）
- ファクターの正規化（Z スコア）→ features テーブル保存
- features と AI スコアを統合して売買シグナルを生成（BUY / SELL）
- 実行・監視・監査用スキーマ（発注・約定・ポジション・監査ログ）を定義

設計方針として、ルックアヘッドバイアス防止、API 呼び出しのリトライ／レート制限、DB 操作の冪等性（ON CONFLICT）などを重視しています。

## 主な機能一覧

- 環境変数管理
  - .env / .env.local の自動読み込み（無効化可能）
- データ取得（J-Quants）
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - レートリミット・リトライ・トークン自動更新対応
- ETL パイプライン
  - run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl
  - 差分取得・バックフィル・品質チェック統合
- DuckDB スキーマ管理
  - init_schema(db_path) によるテーブル・インデックス作成
- 研究／戦略
  - calc_momentum, calc_volatility, calc_value（research/factor_research）
  - build_features（feature_engineering）: ファクターの正規化・features テーブル書込
  - generate_signals（signal_generator）: final_score 計算・BUY/SELL 判定・signals テーブル書込
- ニュース収集
  - RSS フィード取得（SSRF 対策、gzip 対応、サイズ制限）
  - raw_news 保存・news_symbols 紐付け
- データユーティリティ
  - zscore_normalize（data.stats）
  - カレンダー管理（next_trading_day / is_trading_day 等）
- 監査ログスキーマ
  - signal_events / order_requests / executions など

## セットアップ手順

前提:
- Python 3.9 以上（typing | annotations を利用しています）
- DuckDB ライブラリが必要: pip でインストールします

例（仮想環境推奨）:
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
2. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクト配布に requirements.txt がある場合は pip install -r requirements.txt）
3. 開発インストール（リポジトリ ルートに setup.cfg / pyproject.toml がある想定）
   - pip install -e .

環境変数
- プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- 主要な環境変数（例）:
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
  - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
  - SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
  - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
  - SQLITE_PATH: 監視用 SQLite パス（デフォルト `data/monitoring.db`）
  - KABUSYS_ENV: environment（development / paper_trading / live）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...）

例 .env（テンプレート）
  JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
  KABU_API_PASSWORD=your_kabu_password
  SLACK_BOT_TOKEN=xoxb-...
  SLACK_CHANNEL_ID=C01234567
  DUCKDB_PATH=data/kabusys.duckdb
  KABUSYS_ENV=development
  LOG_LEVEL=INFO

注意:
- .env のパースはシェル風の export KEY=val、引用符付き値、インラインコメント処理などに対応しています。

## 使い方（基本的な利用例）

以下は Python REPL / スクリプトからの基本的な流れ例です。

1) DuckDB の初期化（スキーマ作成）
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ":memory:" でインメモリ可
```

2) 日次 ETL の実行（J-Quants から差分取得して DB に保存）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

3) 特徴量構築（features テーブルの作成）
```python
from kabusys.strategy import build_features
from datetime import date
count = build_features(conn, target_date=date(2024, 1, 31))
print(f"features upserted: {count}")
```

4) シグナル生成（signals テーブルへ書き込み）
```python
from kabusys.strategy import generate_signals
from datetime import date
n = generate_signals(conn, target_date=date(2024, 1, 31))
print(f"signals generated: {n}")
```

5) ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES, extract_stock_codes
# known_codes は銘柄コードセット（例: set(["7203","6758"]))
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(res)
```

6) J-Quants API を直接使う（データ取得）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = save_daily_quotes(conn, records)
```

ログ・環境
- settings = kabusys.config.settings から設定を参照可能（例: settings.jquants_refresh_token）。
- 自動 .env ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください（テスト時などに有用）。

エラーハンドリング
- 多くの ETL / DB 操作はトランザクションで行われ、例外時はロールバックされます。
- run_daily_etl 等は内部でエラーを捕捉して ETLResult.errors に記録します（Fail-Fast しない設計）。

## ディレクトリ構成

リポジトリの主要ファイル構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                -- 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント（取得・保存）
    - news_collector.py      -- RSS ニュース収集・保存
    - schema.py              -- DuckDB スキーマ定義・初期化
    - stats.py               -- 統計ユーティリティ（zscore_normalize）
    - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
    - features.py            -- data の公開インターフェース（再エクスポート）
    - calendar_management.py -- 市場カレンダー管理（next_trading_day 等）
    - audit.py               -- 監査ログ（signal_events 等）
  - research/
    - __init__.py
    - factor_research.py     -- ファクター計算（momentum/volatility/value）
    - feature_exploration.py -- 研究用ユーティリティ（forward_returns, IC, summary）
  - strategy/
    - __init__.py
    - feature_engineering.py -- features 作成（正規化・フィルタ）
    - signal_generator.py    -- final_score 計算・signals 生成
  - execution/               -- 発注・execution 用パッケージ（未詳細実装ファイル含む）
  - monitoring/              -- 監視・モニタリング機能（DB/Slack 連携など想定）
- pyproject.toml / setup.cfg 等（パッケージメタ情報）

（上記はコードベースの抜粋に基づく）

## 追加情報・開発ノート

- テスト:
  - コアロジックは外部依存を最小化しているため、DuckDB のインメモリ ':memory:' を使った単体テストが容易です。
- 安全性:
  - RSS は SSRF 対策や gzip 上限、XML パーサの安全なラッパー（defusedxml）を使用しています。
  - J-Quants クライアントはレート制限とリトライ（指数バックオフ）を実装しています。
- 冪等性:
  - DuckDB への保存処理は ON CONFLICT / DO UPDATE / DO NOTHING を用いた冪等設計です。
- 実運用:
  - KABUSYS_ENV を "live" にした場合は実売買・発注ロジックの動作制御を厳格に行ってください（本コードベースでは execution 層の設定に従う）。

## よくある質問（FAQ）

Q: .env を読み込ませたくない / テスト時に上書きしたい  
A: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると自動ロードを無効化できます。手動で os.environ を設定してから settings を参照してください。

Q: DuckDB スキーマ初期化は何をする？  
A: init_schema(db_path) が全テーブル・インデックスを作成します（存在する場合はスキップ）。初回はこれを必ず実行してください。

Q: J-Quants の認証が失敗したら？  
A: jquants_client は 401 に対してリフレッシュトークンを用いたトークン更新を行い1回リトライします。リフレッシュトークンが無効な場合は settings.jquants_refresh_token を確認してください。

---

不明点や README に追記したい利用シナリオ（デプロイ例、Cron ジョブ設定、Slack 通知の使い方など）があれば教えてください。必要に応じてサンプル運用スクリプトや systemd / cron の設定例も用意します。