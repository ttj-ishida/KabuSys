# KabuSys

日本株向けの自動売買 / バックテスト / データ収集フレームワークです。  
ファクタ計算（モメンタム・ボラティリティ・バリュー等）、特徴量作成、シグナル生成、ポートフォリオ構築、バックテストシミュレーション、J-Quants / RSS ベースのニュース収集など、研究から本番までの主要コンポーネントを含みます。

---

## プロジェクト概要

KabuSys は次の目的を持つ Python パッケージです。

- DuckDB を用いた時系列データ管理・解析
- 研究フェーズでのファクター計算（prices_daily / raw_financials 等を参照）
- 正規化済み特徴量（features）と AI スコアを統合したシグナル生成（BUY / SELL）
- ポートフォリオ構築（候補選定、配分、リスク調整、サイジング）
- バックテスト（疑似約定・スリッページ・手数料モデルを含む）
- J-Quants API クライアント（価格・財務・マーケットカレンダー取得）
- RSS ベースのニュース収集と銘柄紐付け（raw_news / news_symbols）

設計方針として、ルックアヘッドバイアスの回避、冪等性（DB 操作の ON CONFLICT 等）、ネットワーク安全性（SSRF 等への配慮）を重視しています。

---

## 主な機能一覧

- データ取得・保存
  - J-Quants API クライアント（ページネーション・リトライ・トークン自動更新・レート制限）
  - RSS フィードからのニュース収集（SSRF対策、gzip 保護、トラッキングパラメータ除去）
  - DuckDB へ冪等保存（raw_prices / raw_financials / market_calendar / raw_news 等）

- 研究・特徴量
  - モメンタム / ボラティリティ / バリュー等のファクター計算（duckdb 経由）
  - Z スコア正規化、ユニバースフィルタ、features テーブルへの置換保存

- シグナル生成
  - 正規化特徴量と ai_scores を統合して final_score を計算
  - Bear レジーム抑制、BUY/SELL の生成と signals テーブルへの置換保存

- ポートフォリオ構築
  - 候補選定、等金額／スコア加重／リスクベースのサイジング
  - セクター集中制限、レジーム乗数

- バックテスト
  - インメモリ DuckDB を用いた安全なバックテスト実行（本番 DB を汚染しない）
  - 擬似約定（スリッページ・手数料・単元丸め）、日次マーク・トゥ・マーケット
  - 各種評価指標の計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio）

- その他
  - CLI エントリポイント（バックテスト実行用）
  - 設定管理（.env 自動読み込み、環境変数ラップ）

---

## 要件

- Python 3.10 以上（型ヒントに `X | Y` 等を使用）
- DuckDB（Python パッケージ: duckdb）
- defusedxml（ニュースパーシングの安全化）
- その他必要パッケージはプロジェクトの requirements.txt / pyproject.toml を参照してください（本コードベースでは明示的に duckdb / defusedxml を利用しています）。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   ```
   pip install -U pip
   pip install duckdb defusedxml
   # プロジェクトを editable install する場合
   pip install -e .
   ```

4. 環境変数 / .env の準備  
   プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

   主な必須環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必要な場合）
   - SLACK_BOT_TOKEN: Slack 通知用トークン（必要な場合）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必要な場合）

   オプション:
   - DUCKDB_PATH: デフォルト "data/kabusys.duckdb"
   - SQLITE_PATH: デフォルト "data/monitoring.db"
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG / INFO / ...（デフォルト: INFO）

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

5. DuckDB スキーマ初期化  
   コード内で `kabusys.data.schema.init_schema(path)` が利用されます。プロジェクトに schema 初期化スクリプトがある想定のため、`init_schema` を呼んで DB を作成してください（本 README のコードベースでは schema 実装参照箇所があります）。

---

## 使い方

以下は主要な利用例です。各関数は DuckDB の接続オブジェクト（kabusys.data.schema.init_schema の戻り値想定）と日付を受け取ります。

- バックテスト（CLI）

  DuckDB ファイルがあらかじめ必要なテーブル（prices_daily, features, ai_scores, market_regime, market_calendar, stocks 等）を持っていることが前提です。

  ```
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --cash 10000000 \
    --db path/to/kabusys.duckdb
  ```

  主なオプション:
  - --allocation-method: equal | score | risk_based
  - --slippage / --commission: スリッページ・手数料率
  - --max-positions / --max-utilization など

- 特徴量の作成（feature engineering）

  Python から直接呼ぶ例:
  ```python
  import duckdb
  from datetime import date
  from kabusys.strategy.feature_engineering import build_features
  from kabusys.data.schema import init_schema

  conn = init_schema("path/to/kabusys.duckdb")
  built = build_features(conn, target_date=date(2024, 1, 31))
  print(f"features upserted: {built}")
  conn.close()
  ```

- シグナル生成

  ```python
  from kabusys.strategy.signal_generator import generate_signals
  # conn は DuckDB 接続
  count = generate_signals(conn, target_date=date(2024, 1, 31), threshold=0.6)
  print(f"signals generated: {count}")
  ```

- ニュース収集（RSS）

  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import init_schema

  conn = init_schema("path/to/kabusys.duckdb")
  # known_codes は銘柄抽出に使う有効なコードの集合（例: stocks テーブルから取得）
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=None)
  print(results)
  conn.close()
  ```

- J-Quants から価格・財務データ取得

  fetch + save の流れ例:
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import init_schema

  conn = init_schema("path/to/kabusys.duckdb")
  records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = save_daily_quotes(conn, records)
  print(f"saved raw prices: {saved}")
  conn.close()
  ```

---

## 主要モジュール（簡易 API）

- kabusys.config.settings — 環境変数ラッパー
- kabusys.data.jquants_client — J-Quants API クライアント / 保存ユーティリティ
- kabusys.data.news_collector — RSS 取得 / raw_news の保存 / 銘柄抽出
- kabusys.research.* — ファクター計算・探索ユーティリティ（calc_momentum 等）
- kabusys.strategy.build_features / generate_signals — 特徴量作成、シグナル生成
- kabusys.portfolio.* — 候補選定、重み計算、サイジング、リスク調整
- kabusys.backtest.* — バックテストエンジン、シミュレータ、メトリクス、CLI

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - jquants_client.py
    - news_collector.py
    - (schema.py, calendar_management.py 等が参照されます)
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
    - run.py (CLI)
    - clock.py
  - execution/ (プレースホルダ / 実装次第)
  - monitoring/ (プレースホルダ / 実装次第)

---

## 開発・テストに関するヒント

- .env の自動ロードはデフォルトで有効。テストで無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB を in-memory でテストする際は `init_schema(":memory:")` を使用すると本番 DB を汚染せずに実行できます（engine._build_backtest_conn と同様の考え方）。
- RSS の外部通信はユニットテストではネットワークをモックしてください（news_collector._urlopen を差し替え可能）。

---

## 免責・注意点

- 本リポジトリは売買アルゴリズムの研究・実装を支援するツール群です。実際の資金を投入する前に十分なバックテスト・ペーパートレードを行ってください。
- レジーム判定／パラメータ等は戦略設計に依存します。デフォルト値は研究目的の一例です。
- J-Quants API 利用には利用規約・認証情報が必要です。トークンの取り扱いに注意してください。

---

必要であれば、README に含める具体的なコマンド一覧（DB 初期化、schema スクリプト例、よく使うユーティリティ関数の例）や、.env.example のテンプレートを追加で作成します。どの情報をより詳しく載せたいか教えてください。