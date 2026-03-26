# KabuSys

日本株向けのアルゴリズム自動売買フレームワーク（研究・データパイプライン・バックテスト・実行層の基盤）

このリポジトリは、J-Quants 等からのデータ収集、ファクター計算、シグナル生成、ポートフォリオ構築、バックテスト、ニュース収集などを統合した日本株自動売買システムのコアモジュール群を提供します。

---

## 主な特徴（機能一覧）

- データ取得・保存
  - J-Quants API クライアント（レートリミット対応、トークン自動リフレッシュ、リトライ付き）
  - 株価日足・財務データ・マーケットカレンダー等の取得と DuckDB への冪等保存
- 研究用ファクター群
  - Momentum / Volatility / Value 等のファクター計算（DuckDB ベース）
  - Z スコア正規化ユーティリティ
- 特徴量エンジニアリング
  - ユニバースフィルタ（株価・流動性）・Z スコア正規化・±3 クリップ・features テーブルへの UPSERT
- シグナル生成
  - ファクターと AI スコアを統合して final_score を算出
  - Bear レジーム抑制、BUY/SELL シグナルの生成と signals テーブルへの冪等書込
- ポートフォリオ構築
  - 候補選定、等配分 / スコア配分、リスクベースのポジションサイジング
  - セクター集中制限、レジーム乗数適用
- バックテストフレームワーク
  - 日次ループによる擬似約定（スリッページ・手数料モデル）、ポートフォリオ履歴・取引記録の生成
  - 指標計算（CAGR、Sharpe、最大ドローダウン、勝率、Payoff ratio）
  - CLI エントリポイント（python -m kabusys.backtest.run）
- ニュース収集
  - RSS フィード収集、正規化、raw_news 保存、銘柄抽出・紐付け（SSRF 対策、gzip 上限、XML セーフパーサ使用）

---

## 動作要件（主な依存）

- Python 3.10+
- duckdb
- defusedxml
- （標準ライブラリで多くを実装しているため外部依存は最小限）

推奨インストール（例）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# パッケージをローカルで編集しながら使う場合
pip install -e .
```

※ requirements.txt がある場合はそちらを参照してください。

---

## セットアップ手順

1. リポジトリをクローン／配置
2. Python 仮想環境を作成して依存をインストール（上記参照）
3. DuckDB スキーマ初期化（スキーマ初期化関数は kabusys.data.schema.init_schema を使用）
   - 例: Python REPL やスクリプトで init_schema("data/kabusys.duckdb")
4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を配置すると自動で読み込まれます
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください

推奨 .env（例）:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx

# kabuステーション API
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789

# DB パス（デフォルト値）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境
KABUSYS_ENV=development    # development | paper_trading | live
LOG_LEVEL=INFO
```

必須環境変数（Settings で _require されるもの）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

設定は `kabusys.config.settings` からアクセスできます。

自動 .env 読み込みの挙動:
- プロジェクトルートはこのファイル（config.py）を起点に `.git` または `pyproject.toml` を探索して決定
- 読み込み順序: OS 環境変数 > .env.local > .env
- OS 側の環境変数は保護され、.env の override を防止（必要に応じて .env.local で上書き可）

---

## 使い方（主な例）

### DB スキーマ初期化
（プロジェクトに schema モジュールがある想定）
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# conn は duckdb.DuckDBPyConnection
```

### 特徴量作成（build_features）
features の計算は DuckDB 接続と基準日を渡して呼び出します。
```python
from datetime import date
from kabusys.strategy import build_features

count = build_features(conn, target_date=date(2024, 01, 31))
print(f"features upserted: {count}")
```

### シグナル生成（generate_signals）
features / ai_scores / positions を参照して signals テーブルを書き換えます。
```python
from datetime import date
from kabusys.strategy import generate_signals

num = generate_signals(conn, target_date=date(2024, 01, 31), threshold=0.6)
print(f"signals written: {num}")
```

### バックテスト（run_backtest）
高水準 API を使ってバックテストを実行できます。
```python
from datetime import date
from kabusys.backtest.engine import run_backtest

result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
print(result.metrics)
```

または CLI:
```
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 --db data/kabusys.duckdb \
  --allocation-method risk_based --max-positions 10
```

CLI の主なオプション:
- --start / --end : 日付
- --db : DuckDB ファイルパス（必須）
- --cash, --slippage, --commission, --allocation-method, --max-positions, --lot-size など多数

### データ収集（J-Quants）
J-Quants からの取得・保存関数:
- fetch_daily_quotes / save_daily_quotes
- fetch_financial_statements / save_financial_statements
- fetch_market_calendar / save_market_calendar
- fetch_listed_info

使用例（簡略）:
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = save_daily_quotes(conn, records)
print(f"saved {saved} raw price records")
```
注意: API は 120 req/min のレート制限、401 発生時は自動でリフレッシュして再試行します。リトライは最大 3 回。

### ニュース収集
RSS フィードから記事を収集して DB に保存します（SSRF 対策済）。
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

result = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set(["7203","6758"]))
print(result)
```

---

## 主要モジュール概要（簡潔）

- kabusys.config
  - Settings（環境変数管理・自動 .env ロード）
- kabusys.data
  - jquants_client.py（API クライアント、保存関数）
  - news_collector.py（RSS 収集・前処理・保存）
  - schema.py（DB スキーマ初期化） — 実装はプロジェクトに依存
- kabusys.research
  - factor_research.py（momentum, volatility, value 等）
  - feature_exploration.py（IC / forward returns / summary）
- kabusys.strategy
  - feature_engineering.py（features 作成）
  - signal_generator.py（final_score 計算、BUY/SELL 生成）
- kabusys.portfolio
  - portfolio_builder.py（候補選定、重み計算）
  - position_sizing.py（株数算出、aggregate cap）
  - risk_adjustment.py（sector cap、regime multiplier）
- kabusys.backtest
  - engine.py（バックテストループ）
  - simulator.py（擬似約定、ポートフォリオ管理）
  - metrics.py（評価指標）
  - run.py（CLI エントリポイント）

---

## ディレクトリ構成

プロジェクトの主要ファイル（抜粋）:
```
src/
  kabusys/
    __init__.py
    config.py
    data/
      jquants_client.py
      news_collector.py
      schema.py         # ※スキーマ定義・init_schema 実装がある想定
      ...
    research/
      factor_research.py
      feature_exploration.py
      ...
    strategy/
      feature_engineering.py
      signal_generator.py
      ...
    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
      __init__.py
    backtest/
      engine.py
      simulator.py
      metrics.py
      run.py
    execution/
      __init__.py
    monitoring/
      ...
    backtest/
      ...
```

各ファイルの責務は、ソース内の docstring に詳述されています。README は概観のための要約です。

---

## 注意事項 / 実運用上のポイント

- Look-ahead バイアスに注意
  - features / signals / prices といったデータは「その時点で利用可能な情報のみ」を用いるよう設計されています。バックテストで正しいデータを使う場合は、事前に適切な時点のデータを DB に格納してください。
- セキュリティ
  - news_collector は SSRF 対策、defusedxml を使用した XML パース、レスポンスサイズ上限などを実装済みですが、外部公開環境では更なる監査を推奨します。
- 設定
  - KABUSYS_ENV は development / paper_trading / live のいずれか。live の場合は実行前に十分な確認を行ってください。
- テスト
  - 単体テストや統合テスト用に KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動 .env ロードを抑止できます。

---

## 開発・貢献

バグ修正や機能拡張の PR を歓迎します。コード内のドキュメント（docstring）を優先して実装の意図を確認してください。

---

以上。必要であれば README に含めるサンプル .env.example、依存一覧（requirements.txt）、schema の初期化手順（init_schema の具体的なスキーマ）などを追記できます。どの内容を追加しますか？