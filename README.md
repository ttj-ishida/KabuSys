# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム用ライブラリです。データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、バックテスト、ニュース収集、簡易の発注/シミュレーション機能を含むモジュール群を提供します。本 README はコードベース（src/kabusys/**）の使い方と構成をまとめたものです。

> 注意: 本リポジトリは実運用前提で設計されたコンポーネントを含みます。実際に売買を行う場合は十分な検証と安全対策（APIキー管理・発注制御・リスク制御等）を行ってください。

---

## 特徴（プロジェクト概要）

- J-Quants API から株価・財務・マーケットカレンダーを安全に取得（レート制限・リトライ・トークン自動更新対応）
- DuckDB を用いたローカルデータストア（スキーマ定義・初期化ユーティリティ）
- 研究（research）で得た生ファクターを正規化して特徴量（features）を作成する特徴量エンジニアリング
- features / ai_scores を組み合わせて売買シグナル（BUY/SELL）を生成するシグナルジェネレータ
- ETL パイプライン（差分取得・保存・品質チェックのフレームワーク）
- RSS ベースのニュース収集、テキスト前処理、記事→銘柄紐付け
- バックテストフレームワーク（シミュレータ、メトリクス、エンジン、CLI）
- メモリ内シミュレータ（スリッページ・手数料考慮）とトレード履歴生成

---

## 機能一覧（主要機能）

- data/
  - jquants_client: J-Quants API クライアント（ページネーション・レート制御・リトライ）
  - schema: DuckDB のスキーマ定義・初期化（init_schema）
  - pipeline: ETL 実行ロジック（差分取得、保存、品質チェック）
  - news_collector: RSS 取得・前処理・保存・銘柄抽出
  - stats: Zスコア正規化などの統計ユーティリティ
- research/
  - factor_research: momentum / volatility / value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）や要約統計
- strategy/
  - feature_engineering: raw factor を統合し features テーブルへ保存
  - signal_generator: final_score を計算して signals テーブルへ書き込む（BUY/SELL 判定、Bear レジーム抑制、エグジット判定）
- backtest/
  - engine: run_backtest（DB をコピーして日次ループでシグナル生成→約定→時価評価を実行）
  - simulator: PortfolioSimulator（約定ロジック、スリッページ、手数料、マーク・トゥ・マーケット）
  - metrics: バックテスト評価指標（CAGR, Sharpe, MaxDD, Win Rate, Payoff Ratio）
  - run: CLI エントリポイント（python -m kabusys.backtest.run）
- config: 環境変数読み込み・設定管理（.env 自動読み込み、必須変数チェック）
- execution: 発注周り（将来的な実装領域、package を分離）

---

## 要求環境（推奨）

- Python 3.10+
- duckdb（DuckDB Python パッケージ）
- defusedxml（ニュースの XML パース安全化）
- （その他: 標準ライブラリを多用していますが、外部 API クライアントの利用には urllib を使用）

実装に合わせて requirements.txt / pyproject.toml を用意している場合はそれに従ってください。

---

## セットアップ手順

1. レポジトリをクローン（例）:
   ```
   git clone <repository-url>
   cd <repository>
   ```

2. 仮想環境を作成・有効化:
   ```
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

3. 必要パッケージをインストール（最低限: duckdb, defusedxml）:
   ```
   pip install duckdb defusedxml
   ```
   開発用に pip install -e . が用意されている場合はプロジェクトルートで:
   ```
   pip install -e .
   ```

4. 環境変数設定:
   - プロジェクトルートに `.env` と/または `.env.local` を置くと自動的に読み込まれます（config モジュールによる自動ロード）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須環境変数（config.Settings から）:
   - JQUANTS_REFRESH_TOKEN : J-Quants の refresh token
   - KABU_API_PASSWORD : kabu API（kabuステーション）パスワード
   - SLACK_BOT_TOKEN : Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID : Slack 通知先チャンネル ID

   任意 / デフォルト付き:
   - KABUSYS_ENV : development / paper_trading / live （デフォルト development）
   - LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
   - DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH : 監視用 SQLite（デフォルト data/monitoring.db）

   .env の書式は shell の export 形式やクォート・コメントをサポートします。

5. DuckDB スキーマ初期化:
   Python REPL またはスクリプトで:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # または ":memory:"（テスト用）
   conn.close()
   ```

---

## 使い方（代表的なワークフロー）

以下は主要 API の簡単な例です。

- J-Quants から日足取得して保存:
  ```python
  from datetime import date
  import duckdb
  from kabusys.data import jquants_client as jq
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  # 例: 取得
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,12,31))
  saved = jq.save_daily_quotes(conn, records)
  print("saved", saved)
  conn.close()
  ```

- ETL（パイプライン）実行（株価差分ETL の例）:
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_prices_etl
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  ```

- 特徴量作成（features テーブルへの書き込み）:
  ```python
  import duckdb
  from kabusys.strategy import build_features
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2024,3,1))
  print("features upserted:", n)
  conn.close()
  ```

- シグナル生成:
  ```python
  from kabusys.strategy import generate_signals
  from datetime import date
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2024,3,1))
  print("signals written:", total)
  conn.close()
  ```

- バックテスト（プログラムから）:
  ```python
  from kabusys.backtest.engine import run_backtest
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
  print(result.metrics)
  conn.close()
  ```

- バックテスト（CLI）:
  ```
  python -m kabusys.backtest.run \
      --start 2023-01-01 --end 2023-12-31 \
      --db data/kabusys.duckdb \
      --cash 10000000
  ```

- ニュース収集（RSS）実行:
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
  print(results)
  conn.close()
  ```

---

## 設定（環境変数の詳細）

主な環境変数（config.Settings に基づく）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live, デフォルト development)
- LOG_LEVEL (DEBUG|INFO|..., デフォルト INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化

.env ファイルの書式や自動読み込みの挙動は src/kabusys/config.py を参照してください（コメント行や export 形式をサポート）。

---

## ディレクトリ構成（主要ファイルと目的）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定管理（.env 自動ロード／必須チェック）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py — RSS 収集・前処理・DB 保存・銘柄抽出
    - pipeline.py — ETL 管理・差分更新ロジック
    - schema.py — DuckDB スキーマ定義・init_schema / get_connection
    - stats.py — zscore_normalize 等の統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — momentum/volatility/value 等のファクター計算
    - feature_exploration.py — 将来リターン計算 / IC / 統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py — ファクター統合・Z スコア正規化・features への UPSERT
    - signal_generator.py — final_score 計算、BUY/SELL シグナル生成、signals 書き込み
  - backtest/
    - __init__.py
    - engine.py — run_backtest（DB コピー→ループ→シミュレーション）
    - simulator.py — PortfolioSimulator（約定モデル、mark_to_market）
    - metrics.py — バックテスト評価指標
    - clock.py — SimulatedClock（将来拡張用）
    - run.py — CLI エントリポイント（python -m kabusys.backtest.run）
  - execution/ — 発注周り（空のパッケージ、将来の実装領域）
  - monitoring/ — 監視関連（別途実装想定）
  - backtest/**, data/** 等のファイル群が実装の中心

---

## 注意点 / 実装上の設計方針メモ

- 多くの処理は「ルックアヘッドバイアス」を避けるために target_date 以前のデータのみを使用する設計になっています（features/シグナル生成/バックテスト）。
- DuckDB に対する挿入は冪等性（ON CONFLICT）を考慮しているため、再実行可能です。
- J-Quants API はレート制限（120 req/min）や 401 自動リフレッシュ、429/5xx でのリトライを組み込んでいます。
- ニュース収集は SSRF 対策・大きなレスポンスの切り捨て・XML パースの安全化（defusedxml）などを考慮しています。
- config はプロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動ロードします（テスト等では無効化可能）。

---

## 貢献 / 拡張

- execution 層（実際の発注・注文管理）の具体実装（kabu ステーション接続など）
- Slack 通知・監視ダッシュボードの具体化
- モデル（AI スコア）連携と学習パイプラインの追加
- 分単位のバックテスト・高頻度戦略向け模擬時計の実装

---

質問や README の追記希望（例: 履歴の出力サンプル、より詳細な ETL 実行手順など）があれば教えてください。README のサンプル .env.example や requirements ファイルの追加も支援できます。