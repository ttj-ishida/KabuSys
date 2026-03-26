# KabuSys

日本株向けの自動売買 / 研究フレームワーク。データ収集（J-Quants / RSS）、ファクター計算、特徴量生成、シグナル生成、ポートフォリオ構築、バックテスト、ニュース収集などの機能をモジュール化して提供します。

主な設計方針
- ルックアヘッドバイアスを避ける（target_date 以前のデータのみ使用）
- DuckDB を中心としたローカルデータプラットフォーム
- バックテストはメモリ上で完結する（本番 DB を汚さないコピー戦略）
- 冪等性・エラー耐性を重視した実装（トランザクション、ON CONFLICT、リトライ等）

---

## 主な機能一覧

- データ取得 / ETL
  - J-Quants API クライアント（fetch / save: 日次株価、財務データ、上場情報、マーケットカレンダー）
  - RSS ベースのニュース収集（SSRF 対策、トラッキングパラメータ除去、記事→銘柄紐付け）
- 研究用ファクター計算
  - Momentum / Volatility / Value ファクター計算（DuckDB 上の SQL + Python）
  - ファクター探索・IC 計算・統計サマリー
- 特徴量エンジニアリング
  - 生ファクターのユニバースフィルタ、Z スコア正規化、features テーブルへの UPSERT
- シグナル生成
  - features + ai_scores を合成して final_score を算出、BUY/SELL シグナルを生成して signals テーブルへ保存
  - Bear レジーム抑制、SELL の優先ポリシー、エグジットルール（ストップロス等）
- ポートフォリオ構築 / サイジング
  - 候補選定、等金額／スコア加重／リスクベースのポジションサイズ算出
  - セクター集中制限、レジーム乗数の適用、単元株丸め、aggregate cap（現金上限）対応
- バックテスト
  - 市場カレンダーに沿った営業日ループ、擬似約定（スリッページ・手数料モデル）、ポートフォリオ状態管理
  - バックテスト用接続の構築（本番 DB から必要テーブルをコピー）
  - メトリクス（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio 等）
  - CLI エントリポイントを備えた実行可能スクリプト
- ユーティリティ
  - 環境設定読み込み（.env 自動読み込み / 必須環境変数チェック）
  - ログレベル・環境（development / paper_trading / live）判定

---

## セットアップ手順（開発環境向け・最小）

想定: Python 3.10+

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows (PowerShell / cmd)
   ```

3. 必要パッケージをインストール（プロジェクトに requirements.txt があることを想定）
   ```bash
   pip install -r requirements.txt
   ```
   requirements.txt がない場合、最低限必要なのは:
   - duckdb
   - defusedxml
   その他、分析や実行に必要なパッケージはプロジェクト固有で追加してください。

4. 環境変数の設定
   プロジェクトルート（.git または pyproject.toml を検出）を基準に `.env` / `.env.local` を自動で読み込みます（起動時）。自動ロードを無効化するには:
   ```bash
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```
   必須の環境変数（Settings から抽出）
   - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
   - KABU_API_PASSWORD — kabuステーション API パスワード
   - SLACK_BOT_TOKEN — Slack 通知用ボットトークン
   - SLACK_CHANNEL_ID — Slack チャンネル ID

   任意（デフォルトあり）
   - KABUSYS_ENV — development / paper_trading / live (default: development)
   - LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL (default: INFO)
   - KABU_API_BASE_URL — kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
   - SQLITE_PATH — 監視用 SQLite パス（default: data/monitoring.db）

---

## 使い方（代表的な例）

### DuckDB スキーマ初期化
（実装ファイルは `kabusys.data.schema` を参照するコードがあるため、そこにある `init_schema()` を使います）

例:
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# 以降 conn を使って ETL / 解析 / バックテスト 等を実行
```

### ファクター → features 作成
build_features を呼んで指定日付分の特徴量を作成して `features` テーブルへ書き込みます。
```python
from datetime import date
from kabusys.strategy.feature_engineering import build_features

count = build_features(conn, target_date=date(2024, 1, 4))
print(f"upserted {count} features")
```

### シグナル生成
features と ai_scores を参照して signals を生成します。
```python
from kabusys.strategy.signal_generator import generate_signals
from datetime import date

n = generate_signals(conn, target_date=date(2024, 1, 4), threshold=0.6)
print(f"generated {n} signals")
```

### ニュース収集（RSS）
RSS を取得して raw_news / news_symbols に保存する統合ジョブ:
```python
from kabusys.data.news_collector import run_news_collection

res = run_news_collection(conn, sources=None, known_codes=set_of_codes)
# res: {source_name: saved_count}
```

### バックテスト（CLI）
リポジトリに含まれる CLI エントリポイントを使ってバックテストを実行できます（`kabusys.backtest.run`）。
```bash
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 --db data/kabusys.duckdb \
  --allocation-method risk_based --max-positions 10
```
出力にバックテストメトリクス（CAGR, Sharpe 等）が表示されます。

### バックテストを Python API から実行
```python
from kabusys.data.schema import init_schema
from kabusys.backtest.engine import run_backtest

conn = init_schema("data/kabusys.duckdb")
result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
# result.history, result.trades, result.metrics を利用
```

---

## 主要モジュール / ディレクトリ構成

（src/kabusys 以下の主要ファイルと簡単な説明）

- kabusys/
  - __init__.py — パッケージ初期化（version 等）
  - config.py — 環境設定の読み込み・管理（.env 自動ロード、必須チェック）
  - data/
    - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ、リトライ・レート制御）
    - news_collector.py — RSS ニュース収集・前処理・DB 保存・銘柄抽出
    - (schema.py 等が参照されるがここに含まれる想定)
  - research/
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py — 将来リターン計算・IC 計算・統計サマリ
  - strategy/
    - feature_engineering.py — 正規化・ユニバースフィルタ・features テーブルへの書き込み
    - signal_generator.py — final_score 計算・BUY/SELL シグナル生成・signals への書き込み
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算（等金額 / スコア）
    - position_sizing.py — 発注株数算出（risk-based / equal / score）
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - backtest/
    - engine.py — バックテストのメインループ、データコピー、日次処理の統合
    - simulator.py — 擬似約定（PortfolioSimulator）、DailySnapshot, TradeRecord
    - metrics.py — バックテスト評価指標の計算
    - run.py — CLI エントリポイント
    - clock.py — 将来拡張用の模擬時計クラス
  - execution/ — 実取引層（現状モジュール空、実装拡張用）
  - monitoring/ — 監視・アラート関連（実装箇所ありうる）

各ファイルには詳細な docstring があり、想定されるアルゴリズム仕様や制約が記載されています。

---

## 環境変数（主な一覧）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意、デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live、デフォルト: development)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL、デフォルト: INFO)

注: .env / .env.local はプロジェクトルート（.git または pyproject.toml の所在）を検出して自動読み込みされます。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 開発のヒント / 注意点

- Python の型ヒント（| 型や型エイリアス）を多用しているため、Python 3.10 以上を推奨します。
- DuckDB 接続はプロジェクト全体で広く使われます。`init_schema()`（data.schema）でスキーマ初期化を行ってから処理してください。
- J-Quants の API レート制限・401 トークンリフレッシュ等はクライアント実装側で扱っていますが、実運用ではトークン管理に注意してください。
- バックテストは本番データベースを変更しないよう、エンジン内部でコピー（インメモリ DuckDB）を作成して実行します。
- News Collector は SSRF 対策や受信サイズ制限、XML パース対策（defusedxml）を含むため、安全性が考慮されています。外部ソース追加時はその点を尊重してください。

---

## 参考: よく使う API（関数）

- Data
  - kabusys.data.jquants_client.fetch_daily_quotes(...)
  - kabusys.data.jquants_client.save_daily_quotes(conn, records)
  - kabusys.data.news_collector.fetch_rss(url, source)
  - kabusys.data.news_collector.run_news_collection(conn, sources, known_codes)
- Research / Strategy
  - kabusys.research.calc_momentum(conn, date)
  - kabusys.research.calc_volatility(conn, date)
  - kabusys.research.calc_value(conn, date)
  - kabusys.strategy.build_features(conn, date)
  - kabusys.strategy.generate_signals(conn, date)
- Portfolio / Backtest
  - kabusys.portfolio.select_candidates(...)
  - kabusys.portfolio.calc_position_sizes(...)
  - kabusys.backtest.run_backtest(conn, start_date, end_date, ...)

---

README の内容はコードベース（src/kabusys）から抽出した情報に基づき作成しています。実際に運用する際は、プロジェクト固有の依存ファイル（requirements.txt / schema 初期化スクリプト / データ投入手順）を確認してください。必要であれば README にそれらの詳細（requirements, schema 定義、サンプル .env.example）を追加して整備できます。