# KabuSys

日本株向けの自動売買システム用ライブラリ／フレームワーク。データ収集（J-Quants）、特徴量算出、シグナル生成、ポートフォリオ構築、バックテスト、ニュース収集までのパイプラインを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は以下を主目的としたコンポーネント群を持ちます。

- J-Quants API からのデータ取得（株価日足、財務データ、上場情報、マーケットカレンダー）
- DuckDB を用いたデータ格納／分析
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- 特徴量エンジニアリングと正規化（Zスコア）
- シグナル生成（複数コンポーネントスコアの重み付け合算、Bear フィルタ、エグジット判定）
- ポートフォリオ構築（候補選別、重み計算、ポジションサイジング、セクター制限）
- バックテストエンジン（擬似約定・手数料/スリッページモデル・メトリクス算出）
- ニュース収集（RSS）と銘柄紐付け（SSRF防止・サイズ制限・トラッキングパラメタ除去）
- セットアップ/設定管理（.env 自動読み込み、必須環境変数の検査）

設計上は、Look-ahead bias を避けるため「対象日までに利用可能なデータのみ」を使う方針で実装されています。

---

## 主な機能一覧

- データ取得・保存
  - J-Quants クライアント（rate limit / retry / token refresh 対応）
  - raw_prices / raw_financials / market_calendar 等への保存関数
- 研究・特徴量
  - calc_momentum / calc_volatility / calc_value（research.factor_research）
  - zscore 正規化とクリップ（strategy.feature_engineering）
- シグナル生成
  - generate_signals: features + ai_scores を統合して BUY/SELL を生成（Bear フィルタ・エグジット判定含む）
- ポートフォリオ構築
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes（equal/score/risk_based、lot rounding、aggregate cap）
  - apply_sector_cap（セクター集中制限）、calc_regime_multiplier（レジーム乗数）
- バックテスト
  - run_backtest: データをインメモリにコピーして日次ループで疑似約定を実行
  - PortfolioSimulator, DailySnapshot, TradeRecord（擬似売買・MTM）
  - メトリクス算出（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff）
- ニュース収集
  - RSS 収集（fetch_rss）, 前処理, raw_news 保存、記事→銘柄の紐付け
  - SSRF 対策・受信サイズ制限・URL 正規化（utm 等除去）
- 設定管理
  - .env 自動読み込み（プロジェクトルート探索）, 必須環境変数チェック（Settings）

---

## 必要条件（推奨）

- Python 3.10+
- 依存ライブラリ（例、requirements.txt に記述する想定）
  - duckdb
  - defusedxml
  - （標準ライブラリ以外を使う箇所があれば追加してください）

※ 実行環境によっては追加でネットワークアクセス・J-Quants API トークン等が必要です。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .\.venv\Scripts\activate    # Windows
   ```

3. 依存パッケージをインストール
   - 例: requirements.txt を用意している場合
     ```
     pip install -r requirements.txt
     ```
   - 最小で duckdb, defusedxml が必要になります:
     ```
     pip install duckdb defusedxml
     ```

4. 環境変数（.env）を作成
   - プロジェクトルートに `.env` / `.env.local` を置くことで自動的に読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると自動読み込みを無効化できます）。
   - 必須キー（Settings が要求するもの）例:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabu API のパスワード（もし execution 層を使う場合）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知用
   - 任意（デフォルトあり）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
     - DUCKDB_PATH — デフォルト data/kabusys.duckdb
     - SQLITE_PATH — デフォルト data/monitoring.db

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. データベース初期化
   - 本リポジトリでは `kabusys.data.schema.init_schema` を通じて DuckDB スキーマ初期化を行う想定です（schema モジュールによりテーブル定義を作成して下さい）。
   - 例:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     # ETL / データ投入を実施
     conn.close()
     ```

---

## 使い方（主な例）

### バックテスト（CLI）

内蔵の CLI エントリポイントでバックテストを実行できます。

```
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --db data/kabusys.duckdb \
  --cash 10000000 \
  --allocation-method risk_based \
  --lot-size 100
```

出力例（簡易）:
- CAGR / Sharpe / Max Drawdown / Win Rate / Payoff Ratio / Total Trades が標準出力に表示されます。

### プログラムから利用する（簡易）

- ファイル構成や DuckDB 接続が整っている前提で、特徴量作成やシグナル生成、バックテストを API レベルで呼べます。

特徴量作成:
```python
from datetime import date
import duckdb
from kabusys.strategy import build_features
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2023, 12, 31))
print(f"built features: {n}")
conn.close()
```

シグナル生成:
```python
from datetime import date
import duckdb
from kabusys.strategy import generate_signals
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2023, 12, 31))
print(f"signals written: {count}")
conn.close()
```

バックテスト実行（プログラム）:
```python
from datetime import date
from kabusys.backtest.engine import run_backtest
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_backtest(conn, start_date=date(2022,1,1), end_date=date(2022,12,31))
print(result.metrics)
conn.close()
```

### ニュース収集（RSS）

RSS フィードから記事を取得して DB に保存する簡易例:
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9432"}  # stocks テーブルと一致させる
results = run_news_collection(conn, known_codes=known_codes)
print(results)
conn.close()
```

### J-Quants からの取得と保存（例）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
records = fetch_daily_quotes(date_from=..., date_to=..., id_token=None)
saved = save_daily_quotes(conn, records)
conn.close()
```
- fetch 系関数は自動でトークンをキャッシュ・リフレッシュします（Settings に JQUANTS_REFRESH_TOKEN が必要）。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API パスワード（実行時に使用する場合）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行モード: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）

自動 .env 読み込み:
- パッケージ初期化時にプロジェクトルート（.git または pyproject.toml を基準）から `.env` と `.env.local` を読み込みます。
- OS 環境変数が優先され、`.env.local` は `.env` を上書きします。
- 自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

.env のパースルール:
- export KEY=val 形式に対応
- シングル/ダブルクォートで囲まれた値はエスケープを解釈して読み込み
- コメント（#）は適切に無視されます（実装済みのパーサを使用）

---

## ディレクトリ構成（抜粋）

プロジェクト内の主なファイル／モジュール:

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数設定管理（Settings）
  - data/
    - jquants_client.py               — J-Quants API クライアント / 保存関数
    - news_collector.py               — RSS ニュース収集・保存・銘柄抽出
    - (schema.py)                     — DuckDB スキーマ初期化（参照実装あり）
    - calendar_management.py          — 取引日管理（参照される）
    - stats.py                         — zscore_normalize 等（参照）
  - research/
    - factor_research.py              — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py          — IC, forward returns 等の分析ユーティリティ
  - strategy/
    - feature_engineering.py          — features テーブル構築
    - signal_generator.py             — generate_signals 実装
  - portfolio/
    - portfolio_builder.py            — 候補選定・重み計算
    - position_sizing.py              — 株数算出・aggregate cap
    - risk_adjustment.py              — セクター上限・レジーム乗数
  - backtest/
    - engine.py                       — run_backtest 実装（主要ループ）
    - simulator.py                    — PortfolioSimulator（疑似約定）
    - metrics.py                      — バックテスト指標計算
    - run.py                          — CLI エントリポイント
  - execution/                         — 発注/実行層（空のパッケージ/拡張点）
  - monitoring/                        — 監視・メトリクス（拡張点）

各モジュールは「DB を読む／書く関数」と「純粋関数（DB参照なしの計算ロジック）」が分離されており、単体テストと再利用がしやすい設計です。

---

## 開発者向けメモ / 注意点

- Look-ahead bias 対策: 多くの関数は target_date 以前のデータのみを参照するよう設計されています。バックテスト/研究時はこの方針を守ってください。
- J-Quants API 呼び出しはレート制限（120 req/min）に対する固定間隔スロットリングと再試行ロジックが組み込まれています。大量取得時は時間を設けて実行してください。
- news_collector は SSRF 対策、レスポンスサイズ制限、gzip 検査等の防御を実装しています。RSS フィードは外部入力なので堅牢性に注意してください。
- バックテスト用に run_backtest は本番 DB を変更しないようインメモリ接続にデータをコピーして実行します。ただし schema/init の実装次第では差分が発生する可能性があるため注意してください。
- settings.env の値が不正な場合 ValueError を投げます（早期失敗が好ましいため）。

---

問題・追加機能や README の補足を希望する場合は、どの部分を詳しく記載したいか（例: schema の定義、requirements.txt、運用手順など）を教えてください。