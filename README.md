# KabuSys

日本株向けの自動売買 / 研究フレームワーク。  
DuckDB をデータストアとして用い、ファクター計算 → 特徴量生成 → シグナル生成 → 発注（本番/バックテスト）までのパイプラインと、ニュース収集や J‑Quants API クライアント等を備えます。

---

## 概要

KabuSys は次の目的で設計された Python パッケージです。

- 研究フェーズでのファクター計算・探索（DuckDB ベース）
- 特徴量エンジニアリングとシグナル生成（ルックアヘッドバイアスに配慮）
- ポートフォリオ構築（候補選定、重み算出、ポジションサイジング、セクター制限）
- バックテストエンジン（擬似約定・スリッページ/手数料モデル付き）
- データ取得モジュール（J‑Quants API クライアント）
- ニュース収集（RSS）と銘柄抽出

設計方針として、DB 参照箇所を明確に分離し、バックテストや研究処理は再現性・冪等性を重視して実装されています。

---

## 機能一覧

主な機能（モジュール単位）

- kabusys.config
  - .env / 環境変数の自動読込み（.env.local 上書き）
  - 必須設定の検証（Settings クラス）
- kabusys.data
  - J‑Quants API クライアント（レート制限・リトライ・トークン自動リフレッシュ）
  - DuckDB へ取り込み用の保存関数（raw_prices / raw_financials / market_calendar 等）
  - ニュース収集（RSS 取得、前処理、raw_news 保存、銘柄抽出）
- kabusys.research
  - ファクター計算（momentum / volatility / value）
  - ファクター探索・IC 計算・統計サマリ
- kabusys.strategy
  - 特徴量作成（features テーブル） build_features
  - シグナル生成（features + ai_scores → signals） generate_signals
- kabusys.portfolio
  - 候補選定、配分重み（等配分 / スコア加重）
  - ポジションサイズ計算（risk_based / equal / score）
  - セクター集中制限、レジーム乗数
- kabusys.backtest
  - バックテストエンジン（run_backtest）
  - 擬似約定シミュレータ（PortfolioSimulator）
  - メトリクス計算（CAGR, Sharpe, MaxDD, WinRate, Payoff など）
  - CLI ランナー（python -m kabusys.backtest.run）
- その他
  - news_collector: RSS 取得・前処理・DB保存（SSRF 等のセキュリティ対策あり）
  - jquants_client: ページネーション・保存ロジック付き API クライアント

---

## セットアップ

前提
- Python 3.10+（型アノテーションや分岐で Python 3.10 構文を使用）
- DuckDB を使います（pip install duckdb）
- RSS XML パースに defusedxml を使用（pip install defusedxml）

推奨手順（プロジェクトルートで実行）:

1. リポジトリをクローン（例）
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成・有効化
   - macOS/Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 開発インストール（パッケージを editable にインストール）
   ```
   pip install -e .
   ```

4. 依存パッケージ（必要に応じて）
   ```
   pip install duckdb defusedxml
   ```

5. 環境変数の設定
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を作成してください。
   - 自動読込はデフォルトで有効。テスト等で無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須の環境変数（settings 参照）
- JQUANTS_REFRESH_TOKEN — J‑Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

推奨 / 任意
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 sqlite ファイル（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development | paper_trading | live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト INFO）

.env の優先度:
- OS 環境変数 > .env.local > .env
- プロジェクトルートの検出には .git または pyproject.toml を使用します

（.env.example をプロジェクトに置いてある想定なので、それを参考に .env を作成してください）

---

## 使い方 / 例

いくつかの典型的な利用例を示します。

- バックテスト（CLI）
  ```
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --cash 10000000 \
    --db path/to/kabusys.duckdb
  ```
  注意: 指定の DuckDB ファイルは prices_daily, features, ai_scores, market_regime, market_calendar 等の必要なテーブルが事前に準備されている必要があります。

- バックテスト（プログラムから）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.schema import init_schema  # schema モジュールで接続を作成する想定
  from kabusys.backtest.engine import run_backtest

  conn = init_schema("path/to/kabusys.duckdb")
  result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
  conn.close()

  # 結果
  print(result.metrics)
  ```

- 特徴量構築
  ```python
  import duckdb
  from datetime import date
  from kabusys.strategy.feature_engineering import build_features

  conn = duckdb.connect("path/to/kabusys.duckdb")
  inserted = build_features(conn, target_date=date(2024,1,31))
  print("upserted features:", inserted)
  conn.close()
  ```

- シグナル生成
  ```python
  from kabusys.strategy.signal_generator import generate_signals
  import duckdb
  from datetime import date

  conn = duckdb.connect("path/to/kabusys.duckdb")
  count = generate_signals(conn, target_date=date(2024,1,31))
  print("signals written:", count)
  conn.close()
  ```

- ニュース収集（RSS）と保存
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import init_schema

  conn = init_schema("path/to/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 例: 有効銘柄セット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  conn.close()
  ```

- J‑Quants から日足取得・保存
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import init_schema

  conn = init_schema("path/to/kabusys.duckdb")
  records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = save_daily_quotes(conn, records)
  print("saved rows:", saved)
  conn.close()
  ```

---

## 注意点 / 運用上のポイント

- ルックアヘッドバイアス対策
  - 研究 / シグナル生成 / バックテストでは「target_date 時点の情報のみ」を使用する設計になっています。データ取得時に fetched_at を記録し、いつそのデータが利用可能になったかを追跡することが推奨されます。

- .env 読込
  - パッケージの config モジュールは自動的にプロジェクトルートの .env/.env.local を読み込みます。テストや特殊初期化の際は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動読込を無効化できます。

- バックテスト用 DB 構築
  - run_backtest CLI は事前に prices_daily / features / ai_scores / market_regime / market_calendar 等が揃っている DuckDB を期待しています。データ ETL は jquants_client と独自の ETL スクリプトで行ってください。

- エラーハンドリング / 冪等性
  - 多くの保存関数は ON CONFLICT（アップサート）やトランザクションを使って冪等性を確保しています。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 配下の主なファイル・モジュール構成です（本 README 作成時点の抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - execution/ (将来の execution 層)
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - backtest/
    - __init__.py
    - engine.py
    - simulator.py
    - metrics.py
    - clock.py
    - run.py  (CLI エントリポイント)
  - data/
    - jquants_client.py
    - news_collector.py
    - (schema.py, calendar_management.py 等の補助モジュールを想定)
  - monitoring/ (監視・アラート関連: placeholder)
  - portfolio/ (先述)
  - その他: research/*, data/*

注: 実際のリポジトリにはさらに schema.py、calendar_management.py、data/stocks マスタや DB 初期化コードが含まれる想定です（バックテストや ETL に必須）。

---

## 開発・貢献

- コーディング規約: Type hints を利用し、関数はできるだけ純粋関数として副作用を限定しています。
- テスト: 各モジュールはユニットテストを書きやすいように DB 接続やネットワーク処理を分離しています。ユニットテストでは外部通信やファイルIO をモックすることを推奨します。

---

## ライセンス / 免責

- 本プロジェクトは学術・研究用の参照実装です。実際の資金運用に用いる場合は十分な検証とリスク管理を行ってください。誤った設定・バグにより金銭的損失が生じても作者は責任を負いません。

---

README に不足している点や、実際の運用手順（ETL パイプライン、schema 定義、kabu ステーション連携など）について詳しく記載してほしい場合は、目的に応じて追加ドキュメントを作成します。どのトピックに重点を置きたいか教えてください。