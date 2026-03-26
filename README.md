# KabuSys

日本株向けの自動売買／バックテスト基盤ライブラリ。価格・財務・ニュースなどのデータ取得、特徴量生成、シグナル生成、ポートフォリオ構築、バックテストシミュレータまでを含むモジュール群を提供します。

主な設計方針：
- Look‑ahead バイアスを避けるため「対象日」ベースの計算を徹底
- DuckDB を中心としたローカルデータストア（ETL → features → signals → execution）
- 冪等性・トランザクション制御・エラーハンドリングを重視
- 本番実行（live）／ペーパー取引（paper_trading）／開発（development）を環境変数で切替可能

---

## 機能一覧

- 環境変数・設定の自動読み込み（`.env` / `.env.local`）、必須設定チェック（kabusys.config）
- J-Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ付き）と DuckDB への保存（kabusys.data.jquants_client）
  - 株価日足、財務データ、上場銘柄一覧、マーケットカレンダー等の取得・保存
- ニュース収集（RSS）・正規化・DB 保存、記事から銘柄コード抽出（kabusys.data.news_collector）
- 研究用ファクター計算（モメンタム / バリュー / ボラティリティ / 流動性）と Z スコア正規化ユーティリティ（kabusys.research）
- 特徴量構築（feature_engineering） → features テーブルへの書込（kabusys.strategy.build_features）
- シグナル生成（signal_generator）: final_score 計算、BUY / SELL シグナルの生成と signals テーブルへの書込（kabusys.strategy.generate_signals）
- ポートフォリオ構築:
  - 候補選定・重み計算（等配分・スコア加重） (kabusys.portfolio.portfolio_builder)
  - リスク調整（セクター集中制限、レジーム乗数） (kabusys.portfolio.risk_adjustment)
  - ポジションサイジング（risk_based / equal / score）・単元丸め・aggregate cap 処理 (kabusys.portfolio.position_sizing)
- バックテストフレームワーク:
  - インメモリでのバックテスト用 DB 構築、ループ、シミュレータ、メトリクス (kabusys.backtest)
  - CLI からの実行スクリプト（python -m kabusys.backtest.run）
- バックテストシミュレータ（約定モデル、スリッページ・手数料・部分約定・マーク・トゥ・マーケット） (kabusys.backtest.simulator)
- バックテスト評価指標の計算（CAGR, Sharpe, MaxDD, Win rate, Payoff ratio）(kabusys.backtest.metrics)

---

## セットアップ手順

前提：Python 3.10+ を想定（コードに型ヒント | を使用）。

1. リポジトリをクローン／配置し、仮想環境を作成：
   ```
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

2. パッケージインストール（プロジェクトの requirements.txt / pyproject.toml がある場合はそれに従う）。
   主要依存例：
   ```
   pip install duckdb defusedxml
   ```
   （必要に応じて duckdb‑python やその他の依存を追加してください）

   開発時にパッケージを編集しながら使う場合：
   ```
   pip install -e .
   ```

3. 環境変数（`.env`）を準備：
   プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただしテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   最低限設定すべき環境変数例：
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD : kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN : Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID : Slack 通知先チャンネル ID（必須）
   - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH : 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV : development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL : DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=./data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

4. DB スキーマ初期化：
   コード中で `kabusys.data.schema.init_schema` を参照する場所があります（プロジェクトに schema 定義がある想定）。DuckDB ファイルを初期化するユーティリティが提供されている場合はそれを利用してください。
   例:
   ```py
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```

5. データ取得（例）：
   - J-Quants から日足や財務データを取得して DuckDB に保存するには `kabusys.data.jquants_client.fetch_*` と `save_*` を組み合わせます。
   - ニュース収集は `kabusys.data.news_collector.run_news_collection(conn)` を呼ぶことで RSS 収集 → 保存 → 銘柄紐付けを行います。

---

## 使い方

いくつか代表的な使い方を示します。

- バックテスト CLI（推奨）：
  ```
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --cash 10000000 --db path/to/kabusys.duckdb
  ```
  オプションで slippage, commission, allocation-method, max-positions, lot-size 等を指定できます。DB は事前に prices_daily, features, ai_scores, market_regime, market_calendar を用意しておいてください。

- Python からバックテストを実行：
  ```py
  from datetime import date
  import duckdb
  from kabusys.backtest.engine import run_backtest
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
  conn.close()

  print(result.metrics)
  ```

- 特徴量構築（features テーブルへ書き込む）：
  ```py
  from datetime import date
  import duckdb
  from kabusys.strategy.feature_engineering import build_features
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2024,1,31))
  print(f"upserted features: {n}")
  conn.close()
  ```

- シグナル生成（signals テーブルへ書き込む）：
  ```py
  from datetime import date
  import duckdb
  from kabusys.strategy.signal_generator import generate_signals
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  count = generate_signals(conn, target_date=date(2024,1,31))
  print(f"signals written: {count}")
  conn.close()
  ```

- J-Quants データ取得・保存の例：
  ```py
  import duckdb
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  token = get_id_token()  # settings.jquants_refresh_token を使用
  records = fetch_daily_quotes(id_token=token, date_from=date(2023,1,1), date_to=date(2023,12,31))
  saved = save_daily_quotes(conn, records)
  conn.close()
  print(f"saved: {saved}")
  ```

- ニュース収集ジョブ（RSS）：
  ```py
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  res = run_news_collection(conn)
  print(res)
  conn.close()
  ```

注意事項：
- 各 ETL / 生成処理は「対象日」を明示して実行することで過去データのみを参照するよう設計されています（ルックアヘッド防止）。
- generate_signals は market_regime（当日のレジーム）や ai_scores を参照します。Bear 相場では BUY シグナルを抑制するロジックがあります。

---

## 主な環境変数（まとめ）

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID

- 推奨 / オプション:
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
  - LOG_LEVEL (INFO 等)

自動ロード無効化:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env ファイルの自動読み込みを無効化します（ユニットテスト等で有用）。

---

## ディレクトリ構成（主なファイル）

（リポジトリの `src/kabusys/` を抜粋）

- kabusys/
  - __init__.py
  - config.py — 環境変数と設定管理（.env 自動読み込み）
  - data/
    - jquants_client.py — J-Quants API クライアント & DuckDB への保存
    - news_collector.py — RSS ニュース収集・前処理・DB 保存・銘柄抽出
    - (schema.py, calendar_management などがプロジェクト内に存在する想定)
  - research/
    - factor_research.py — momentum, value, volatility の計算
    - feature_exploration.py — IC / forward returns / statistics 等の探索用関数
  - strategy/
    - feature_engineering.py — feature テーブル作成（正規化・フィルタ）
    - signal_generator.py — final_score 計算、BUY/SELL 判定、signals テーブル書込
  - portfolio/
    - portfolio_builder.py — 候補選定、重み計算
    - position_sizing.py — 株数決定・aggregate cap・単元丸め
    - risk_adjustment.py — セクターキャップ、レジーム乗数
  - backtest/
    - engine.py — run_backtest（メインループ、DB コピー、発注ロジック）
    - simulator.py — PortfolioSimulator（約定モデル・history/trades）
    - metrics.py — バックテスト評価指標計算
    - run.py — CLI entry point for backtest
    - clock.py — SimulatedClock（将来拡張用）
  - execution/ (プレースホルダ)
  - monitoring/ (プレースホルダ)

---

## 開発・運用上の注意点

- データの取得・保存処理は外部 API 呼び出しやネットワーク I/O を伴います。実行時は API レート制御やトークンの管理に注意してください（jquants_client に RateLimiter とリトライ実装あり）。
- バックテストを行う場合、事前に DuckDB に prices_daily / features / ai_scores / market_regime / market_calendar が揃っている必要があります。ETL パイプラインでこれらを用意してください。
- 本番運用（live）では KABUSYS_ENV を `live` に設定し、API キーやパスワード管理は安全な方法（Secrets manager 等）を推奨します。
- 単体テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を使うと .env 自動読み込みを抑制できます。

---

この README はコードベース（src/kabusys 以下）に基づいて作成しています。追加のユーティリティや schema/実運用スクリプトが別ファイルとして存在する場合は、そちらの README やドキュメントに従って環境を整備してください。必要であればサンプル .env.example や DB 初期化スクリプトのテンプレートも作成できます — その場合はどういったフォーマットがよいか教えてください。