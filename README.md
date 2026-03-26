# KabuSys

KabuSys は日本株向けの自動売買（データ取得・特徴量生成・シグナル生成・バックテスト・ニュース収集など）を支援するライブラリ群です。DuckDB を利用したデータパイプラインや、J-Quants API / RSS ニュース収集、バックテストエンジン、ポートフォリオ構築ロジックなどを含みます。

## 概要

主な設計方針・特徴：
- 研究（research）と実運用（engine）の分離：データ取得・特徴量計算・シグナル生成は発注ロジックと依存分離されています。
- DuckDB を中心としたオンプレ/ローカル DB を想定（軽量な分析とバックテストに最適）。
- J-Quants API クライアント（レートリミット・リトライ・トークン自動更新対応）。
- RSS ニュース収集（SSRF対策・トラッキングパラメータ除去・記事IDは正規化URLの SHA-256 を利用）。
- バックテストフレームワーク（擬似約定、スリッページ・手数料モデル、評価指標）。

バージョン: 0.1.0（src/kabusys/__init__.py）

## 主な機能一覧

- データ取得 / ETL
  - J-Quants API クライアント（jquants_client）
    - 日次株価、財務データ、上場銘柄一覧、マーケットカレンダー取得
    - レートリミット制御、リトライ、トークン自動リフレッシュ
  - ニュース収集（news_collector）
    - RSS 取得、記事前処理、記事保存、銘柄コード抽出

- 研究・特徴量
  - ファクター計算（research/factor_research.py）
    - Momentum / Volatility / Value / Liquidity 等の定量ファクター
  - 特徴量作成（strategy/feature_engineering.py）
    - ユニバースフィルタ、Zスコア正規化、features テーブルへの UPSERT

- シグナル生成（strategy/signal_generator.py）
  - 特徴量 + AI スコア統合 → final_score 算出
  - Bear レジーム抑制、BUY/SELL シグナル生成、signals テーブル更新

- ポートフォリオ構築（portfolio/*.py）
  - 候補選定（select_candidates）
  - 重み計算（等配分 / スコア加重）
  - リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイジング（risk_based / equal / score）

- バックテスト（backtest/*.py）
  - run_backtest: データのコピー → 日次ループ → 約定シミュレーション → 指標計算
  - PortfolioSimulator: 擬似約定・時価評価・トレード記録
  - 評価指標（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio）

- 設定管理（config.py）
  - .env または環境変数から設定を自動ロード（プロジェクトルート検出）
  - 必須設定の検証、環境種別（development / paper_trading / live）とログレベル検査

## セットアップ手順（開発 / 実行）

以下は一般的なローカル開発手順の例です。プロジェクト固有の requirements.txt / pyproject.toml がある場合はそちらを参照してください。

1. Python 環境（推奨: 3.10+）を用意
2. リポジトリをクローンしてパッケージを編集可能モードでインストール
   - git clone ...
   - pip install -e .
3. 依存パッケージ（最低限）
   - duckdb
   - defusedxml
   - （必要に応じて）その他 HTTP / logging の補助ライブラリ
   例:
   ```
   pip install duckdb defusedxml
   ```
4. 環境変数 / .env を準備
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（読み込み優先度: OS 環境変数 > .env.local > .env）。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 必要なキー（例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須：実運用時）
     - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: 通知用 Slack の情報
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG/INFO/...
   - 例 .env:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

5. DuckDB スキーマ初期化
   - このコードベースはスキーマ初期化関数（kabusys.data.schema.init_schema）を利用します。初期化スクリプトや migrate が提供されている場合はそちらを実行してください（本リポジトリに schema 実装が含まれている想定）。
   - 例（仮）:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
     ```

## 使い方（代表的なコマンド・サンプル）

- バックテスト CLI（推奨）
  ```
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --cash 10000000 --db data/kabusys.duckdb
  ```
  オプションで slippage / commission / allocation-method / lot-size などを指定できます。バックテスト実行には事前に DuckDB に prices_daily / features / ai_scores / market_regime / market_calendar 等のデータが入っている必要があります。

- 特徴量を生成して features テーブルへ書き込む（プログラムから）
  ```python
  import duckdb
  from datetime import date
  from kabusys.strategy.feature_engineering import build_features
  conn = duckdb.connect("data/kabusys.duckdb")
  count = build_features(conn, target_date=date(2024, 1, 31))
  print("upserted:", count)
  conn.close()
  ```

- シグナル生成（programmatically）
  ```python
  from datetime import date
  import duckdb
  from kabusys.strategy.signal_generator import generate_signals
  conn = duckdb.connect("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2024,1,31))
  print("signals generated:", total)
  conn.close()
  ```

- ニュース収集ジョブの実行（RSS）
  ```python
  import duckdb
  from kabusys.data.news_collector import run_news_collection
  conn = duckdb.connect("data/kabusys.duckdb")
  # known_codes は銘柄コード抽出に使う set（省略可）
  res = run_news_collection(conn, sources=None, known_codes=None)
  print(res)
  conn.close()
  ```
  run_news_collection は各ソースごとの新規保存件数を辞書で返します。

- J-Quants から日次株価を取得して保存する（例）
  ```python
  import duckdb
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  conn = duckdb.connect("data/kabusys.duckdb")
  recs = fetch_daily_quotes(date_from=None, date_to=None)  # 全銘柄・期間を指定可能
  saved = save_daily_quotes(conn, recs)
  print("saved rows:", saved)
  conn.close()
  ```

## 設定（重要な環境変数 / 設定項目）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (kabu API を使う場合は必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID (通知用)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development / paper_trading / live)
- LOG_LEVEL (DEBUG/INFO/...)

設定は .env/.env.local の自動読み込み（プロジェクトルート検出）または OS 環境変数で行います。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能です。

## ディレクトリ構成（抜粋）

以下はリポジトリ内の主要なモジュールとファイルの一覧（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - jquants_client.py
    - news_collector.py
    - (schema.py などの DB スキーマ周りの実装を想定)
  - research/
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - feature_engineering.py
    - signal_generator.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - backtest/
    - engine.py
    - simulator.py
    - metrics.py
    - run.py
    - clock.py
  - execution/           # （パッケージエクスポート用に空 __init__ が存在）
  - monitoring/          # （監視モジュールを想定）
  - portfolio/           # 上記
  - research/            # 上記

ファイルはそれぞれドキュメント文字列と実装コメントを含み、設計仕様（StrategyModel.md / PortfolioConstruction.md / BacktestFramework.md 等）に準拠する実装方針が各所に記載されています。

## 開発メモ / 注意事項

- Look-ahead bias の回避設計が随所に組み込まれています。バックテストでデータを投入する際は、対象期間に対する「知り得るデータのみ」を保存することが重要です（例: stocks / raw_financials / prices の時点制約）。
- J-Quants クライアントはレート制限とトークン更新に対応していますが、実運用では API の利用規約・レート制限に注意してください。
- news_collector は SSRF 対策・受信サイズ制限・XML デコーディングに注意した実装になっています。HTTP リクエストのタイムアウトや例外処理を適切に設定して運用してください。
- 実運用（live）では KABUSYS_ENV=live を設定し、kabu API（約定）や Slack 通知などの連携を十分にテストしてから稼働してください。

---

README の内容はコードベースから抽出した情報に基づいて作成しています。実際の運用や導入にあたっては、プロジェクト内の追加ドキュメント（md ファイル）や schema / migration スクリプト、requirements/pyproject を必ず参照してください。必要であれば、README に追記する実行例や schema 初期化手順、CI 設定のテンプレートを作成します。どの情報をさらに詳しく載せたいか教えてください。