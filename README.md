# KabuSys

日本株向けの自動売買 / 研究プラットフォーム。データ収集（J-Quants）、ETL、ファクター計算、特徴量生成、シグナル生成、バックテスト、ニュース収集、擬似約定シミュレータなどを含むモジュール群から構成されています。

主な設計方針：
- ルックアヘッドバイアス回避（ターゲット日以前のデータのみを使用）
- DuckDB をデータレイヤに採用（ローカルファイルおよびインメモリ）
- 冪等性を意識した保存（ON CONFLICT / DO UPDATE 等）
- 外部依存は最小限（標準ライブラリ＋ duckdb, defusedxml 等）

---

## 機能一覧

- データ取得
  - J-Quants API クライアント（株価日足 / 財務 / マーケットカレンダー）
  - RSS からのニュース収集（SSRF対策・トラッキング除去・前処理）
- ETL / パイプライン
  - 差分取得・バックフィル機能・品質チェック接続口
- スキマティックなデータスキーマ
  - raw / processed / feature / execution 層の DuckDB スキーマ定義と初期化
- 研究・ファクター
  - Momentum / Volatility / Value 等のファクター計算
  - 特徴量の Z スコア正規化
  - ファクター探索（IC、forward returns、summary）
- 戦略
  - 特徴量合成（features テーブル生成）
  - シグナル生成（final_score・BUY/SELL 判定）
- バックテスト
  - 日次ループによるポートフォリオシミュレーション（スリッページ・手数料モデル）
  - バックテスト用インメモリ DB 作成（本番 DB の一部をコピー）
  - 成績指標計算（CAGR, Sharpe, MaxDD, Win rate, Payoff ratio）
  - CLI エントリポイント（python -m kabusys.backtest.run）
- 実行（execution）層のスケルトン（orders, trades, positions 等のスキーマ）

---

## 動作要件

- Python 3.10+
  - typing の `X | Y` などを使用しているため Python 3.10 以上を想定しています。
- 必要パッケージ（最低限）
  - duckdb
  - defusedxml
- 推奨：仮想環境での実行

インストール例（最低限）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# パッケージとしてローカルインストールする場合
pip install -e .
```

（実プロジェクトでは requirements.txt / pyproject.toml を用意してください）

---

## 環境変数

自動でプロジェクトルートにある `.env` / `.env.local` を読み込みます（優先順: OS > .env.local > .env）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD      : kabuステーション API パスワード（必須）
- KABU_API_BASE_URL     : kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN       : Slack 通知用 bot トークン（必須）
- SLACK_CHANNEL_ID      : Slack チャンネル ID（必須）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV           : environment (development | paper_trading | live)（デフォルト development）
- LOG_LEVEL             : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

サンプル `.env`:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXX
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成と依存インストール
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb defusedxml
   # あるいはプロジェクトの依存定義があれば pip install -r requirements.txt
   ```

3. 環境変数設定
   - プロジェクトルートに `.env` を作成する（上記参照）。
   - または OS 環境変数として設定。

4. DuckDB スキーマ初期化
   Python REPL / スクリプトで:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```
   :memory: を指定するとインメモリ DB が作成されます（バックテスト等で使用）。

---

## 使い方（代表的な操作例）

- バックテスト CLI
  ```
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --cash 10000000 --db data/kabusys.duckdb
  ```
  必要なテーブル（prices_daily, features, ai_scores, market_regime, market_calendar）が事前に格納されている必要があります。

- スキーマ初期化（プログラムから）
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 特徴量構築（features テーブル作成）
  ```python
  import duckdb
  from datetime import date
  from kabusys.strategy import build_features

  conn = duckdb.connect("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2024, 1, 31))
  print(f"upserted features: {n}")
  conn.close()
  ```

- シグナル生成
  ```python
  import duckdb
  from datetime import date
  from kabusys.strategy import generate_signals

  conn = duckdb.connect("data/kabusys.duckdb")
  count = generate_signals(conn, target_date=date(2024, 1, 31), threshold=0.6)
  print(f"signals generated: {count}")
  conn.close()
  ```

- ETL（株価取得 / 保存 等）
  - モジュールは `kabusys.data.pipeline` と `kabusys.data.jquants_client` を提供します。実際の ETL 実行スクリプトはプロジェクトの運用ワークフローに合わせて実装してください。
  - 例（概念）:
    ```python
    from kabusys.data.schema import init_schema
    from kabusys.data import jquants_client as jq

    conn = init_schema("data/kabusys.duckdb")
    records = jq.fetch_daily_quotes(date_from=..., date_to=...)
    jq.save_daily_quotes(conn, records)
    conn.close()
    ```

- ニュース収集
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
  print(results)
  conn.close()
  ```

---

## 注意点 / 実装上のポイント

- 多くの DB 書き込みはトランザクションでラップされ、冪等性を保つため ON CONFLICT や RETURNING を利用しています。
- J-Quants クライアントはレートリミットとリトライ（指数バックオフ）を実装。401 はリフレッシュトークンで自動更新します。
- RSS 収集は SSRF や XML Bomb を意識した実装になっています（スキーム検証、プライベートアドレスチェック、defusedxml 等）。
- 環境変数読み込みはプロジェクトルートを .git / pyproject.toml を基準に探索します（CWD 非依存）。
- Python の型アノテーションと docstring により使用法を追いやすくしています。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント、保存関数
    - news_collector.py — RSS 取得・保存ロジック
    - schema.py — DuckDB スキーマ定義 & init_schema
    - stats.py — zscore 正規化等のユーティリティ
    - pipeline.py — ETL パイプライン（差分更新等）
  - research/
    - __init__.py
    - factor_research.py — Momentum/Volatility/Value 計算
    - feature_exploration.py — forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py — features 作成（正規化・フィルタ）
    - signal_generator.py — final_score 計算・BUY/SELL 生成
  - backtest/
    - __init__.py
    - engine.py — run_backtest の実装（インメモリ DB コピー含む）
    - simulator.py — PortfolioSimulator（擬似約定・履歴）
    - metrics.py — バックテスト指標計算
    - clock.py — SimulatedClock（将来拡張用）
    - run.py — バックテスト CLI エントリポイント
  - execution/ — 実行関連のプレースホルダ（将来の発注フロー）
  - monitoring/ — 監視用コード（SQLite など）（未列挙の可能性あり）

各モジュールは docstring とコメントで設計仕様（StrategyModel.md、DataPlatform.md、BacktestFramework.md 等）に準拠することを前提に実装されています。

---

必要があれば README に以下を追記できます：
- 具体的な ETL 実行例（run_prices_etl 等の引数例）
- CI / テスト実行方法
- デプロイ / 運用手順（kabuステーション連携・Slack 通知設定）
- 依存関係の完全な一覧（requirements.txt / pyproject.toml）