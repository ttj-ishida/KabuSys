# KabuSys

日本株向けの自動売買・リサーチ用ライブラリ群です。データ収集（J-Quants）、特徴量生成、シグナル生成、ポートフォリオ構築、バックテスト、ニュース収集などの機能を備えたモジュール群で構成されています。

---

## プロジェクト概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API 等からの市場データ取得と DuckDB への保存（etL）
- 研究用ファクター計算（momentum / volatility / value 等）
- 特徴量エンジニアリング（正規化・ユニバースフィルタリング）
- シグナル生成（複数コンポーネントの重み合算、Bear レジーム抑制、エグジット判定）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイジング、セクター上限）
- バックテストエンジン（擬似約定、スリッページ・手数料モデル、メトリクス計算）
- ニュース収集・記事と銘柄の紐付け（RSS ベース）

設計方針として、ルックアヘッドバイアスの防止、冪等性、明示的な DB トランザクション、外部 API のレート制御やリトライ等に配慮しています。

---

## 主な機能一覧

- data
  - J-Quants API クライアント（fetch / save）
  - RSS ニュース収集・前処理・DB保存（SSRF 対策、gzip 制限、トラッキング除去）
- research
  - ファクター計算: calc_momentum, calc_volatility, calc_value
  - 解析: forward returns, IC（Spearman）、factor summary
- strategy
  - build_features(conn, target_date): 特徴量の計算と features テーブルへの保存
  - generate_signals(conn, target_date): features / ai_scores を元に BUY/SELL シグナルを作成・保存
- portfolio
  - 候補選定: select_candidates
  - 重み計算: calc_equal_weights, calc_score_weights
  - サイジング: calc_position_sizes（risk_based / equal / score）
  - リスク調整: apply_sector_cap, calc_regime_multiplier
- backtest
  - run_backtest(conn, start_date, end_date, ...): データをインメモリにコピーしてバックテスト実行
  - PortfolioSimulator: 擬似約定・履歴管理
  - metrics: CAGR / Sharpe / Max DD / Win Rate / Payoff Ratio
  - CLI エントリポイント: python -m kabusys.backtest.run
- その他
  - 設定管理: 環境変数と .env 自動読み込み（kabusys.config）
  - news_collector: RSS 取得→raw_news 保存→銘柄抽出→news_symbols 登録

---

## セットアップ手順

前提: Python 3.10 以上を推奨（PEP 604 の型記法などを使用）。

1. リポジトリをクローン（あるいはソースを準備）
2. 仮想環境の作成と有効化
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```
3. 依存パッケージをインストール
   - 必要な主なパッケージ（例）:
     ```
     pip install duckdb defusedxml
     ```
   - 開発インストール（setup.py/pyproject がある場合）:
     ```
     pip install -e .
     ```
   - 必要に応じて logging 等の標準ライブラリ以外を追加でインストールしてください。

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を用意することで自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（kabusys.config.Settings 参照）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabu ステーション API パスワード（API 実行時）
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
   - 任意 / デフォルトあり:
     - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/...（デフォルト: INFO）

   - .env の例:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

5. DB スキーマ初期化
   - パッケージ内の schema 初期化関数を使用します（実装ファイル: kabusys.data.schema）。
   - 例:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - （schema 実装に従いテーブルが作成されます。init_schema は既存 DB を開く挙動を持つことが期待されます。）

---

## 使い方（主なユースケース）

### バックテスト（CLI）

プロジェクトはバックテスト用の CLI を提供します。事前に DuckDB に必要なテーブル（prices_daily, features, ai_scores, market_regime, market_calendar, stocks など）が整っている必要があります。

例:
```
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2024-12-31 \
  --cash 10000000 --db data/kabusys.duckdb \
  --allocation-method risk_based --max-positions 10
```

表示される結果には CAGR / Sharpe / Max Drawdown / Win Rate / Payoff Ratio / Total Trades が含まれます。

### バックテスト（プログラムから呼び出す）

```python
from kabusys.data.schema import init_schema
from kabusys.backtest import run_backtest

conn = init_schema("data/kabusys.duckdb")
result = run_backtest(
    conn=conn,
    start_date=date(2023,1,1),
    end_date=date(2023,12,31),
    initial_cash=10_000_000,
    allocation_method="risk_based",
)
# result.history, result.trades, result.metrics を利用
conn.close()
```

### 特徴量構築 / シグナル生成（DuckDB 接続を与えて実行）

feature_engineering.build_features と strategy.signal_generator.generate_signals を使用します。

```python
from kabusys.strategy import build_features, generate_signals
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2024,1,31))
print(f"features upserted: {n}")

m = generate_signals(conn, target_date=date(2024,1,31), threshold=0.6)
print(f"signals generated: {m}")
conn.close()
```

### J-Quants データ取得と保存

J-Quants クライアントは自動でトークンをリフレッシュし、ページネーション・レート制御・リトライを扱います。

```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = save_daily_quotes(conn, records)
print(f"saved {saved} price records")
conn.close()
```

### ニュース収集

RSS フィードを取得して raw_news に保存、記事と銘柄の紐付けを行います。

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES, fetch_rss
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes: 抽出に使う有効コード集合（stocks テーブルなどから取得）
known_codes = {"7203","6758","9984"}
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
conn.close()
```

---

## 主要モジュールと責務（ディレクトリ構成）

プロジェクトの主なファイル/ディレクトリ（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
    - .env 自動読み込み、Settings クラス（環境変数定義）
  - data/
    - jquants_client.py — J-Quants API クライアント（fetch / save）
    - news_collector.py — RSS 収集、前処理、DB 保存、銘柄抽出
    - (その他: schema.py, calendar_management.py, stats.py 等を想定)
  - research/
    - factor_research.py — calc_momentum, calc_volatility, calc_value
    - feature_exploration.py — forward returns, calc_ic, factor_summary, rank
  - strategy/
    - feature_engineering.py — build_features (Zスコア正規化・ユニバースフィルタ)
    - signal_generator.py — generate_signals (final_score 計算・BUY/SELL ロジック)
  - portfolio/
    - portfolio_builder.py — select_candidates, calc_equal_weights, calc_score_weights
    - position_sizing.py — calc_position_sizes（risk_based, equal, score）
    - risk_adjustment.py — apply_sector_cap, calc_regime_multiplier
  - backtest/
    - engine.py — run_backtest（バックテスト全体ループ）
    - simulator.py — PortfolioSimulator（擬似約定）
    - metrics.py — バックテスト指標計算
    - run.py — CLI エントリポイント
    - clock.py — SimulatedClock（将来拡張用）
  - portfolio/ (パッケージ化済み)
  - execution/ — 実際の発注ロジック（プレースホルダ）
  - monitoring/ — 監視・通知関連（プレースホルダ）

（実際の repo では更に細かいファイルが含まれる可能性があります。）

---

## 注意事項 / 運用メモ

- DuckDB のスキーマ（tables）や初期データ準備は必須です。schema 初期化関数（kabusys.data.schema.init_schema）を確認してください。
- バックテストを行う際は、Look-ahead Bias を避けるために使用するデータがバックテスト期間より「過去」に存在していることを確認してください（fetch 時刻や fetched_at を管理する設計になっています）。
- J-Quants API はレート制限があるため、fetch の呼び出し間隔やページネーションでの制御に注意してください（クライアントは固定間隔レートリミッタを持ちます）。
- ニュース収集は外部 RSS を扱うため SSRF 対策やレスポンスサイズ/圧縮の検査を行っています。カスタムソースを追加する際は URL の信頼性を検討してください。
- 本番運用（live）時は KABUSYS_ENV を `live` に設定してください。`paper_trading` はペーパートレード用の運用モードです。

---

## さらに詳しく / 貢献

- 各モジュール内に詳細な docstring / 設計注記（例: StrategyModel.md / PortfolioConstruction.md 参照の旨）が含まれています。機能拡張やバグ修正時は個別モジュールの docstring を参照してください。
- PR / Issue での機能提案やバグ報告を歓迎します。コードスタイルやテストカバレッジを保ちながら変更を行ってください。

---

この README はコードベースの現状（主要モジュール・API・挙動）を要約したものです。実運用前に各設定や DB スキーマ、周辺ツールのドキュメントを必ず確認してください。