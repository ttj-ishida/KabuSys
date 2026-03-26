# KabuSys

日本株向けの自動売買／バックテスト基盤ライブラリ。  
DuckDB をデータ層に用い、ファクター計算・シグナル生成・ポートフォリオ構築・バックテスト・ニュース収集などの機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の機能を持つモジュール群から構成される研究〜バックテスト〜実運用支援用のコードベースです。

- データ取得・ETL（J-Quants API 経由の株価/財務/カレンダー取得）
- ニュース収集（RSS）
- ファクター計算（モメンタム／ボラティリティ／バリュー等）
- 特徴量構築（正規化・クリップ・features テーブルへの保存）
- シグナル生成（ファクター＋AIスコアの統合、BUY/SELL 判定）
- ポートフォリオ構築（候補選定・重み付け・サイジング・セクター制限）
- バックテスト実行（擬似約定モデル、メトリクス算出）

設計上のポイント:
- DuckDB を用いたデータ永続化（軽量で高速）
- ルックアヘッドバイアス回避への配慮（取得時刻の記録 / target_date に基づく計算）
- 冪等性（DB への upsert / ON CONFLICT ハンドリング）
- ネットワークリクエストへのリトライ・レート制御・SSRF 対策

---

## 主な機能一覧

- データ取得
  - J-Quants API クライアント（jquants_client）
  - 株価日足 / 財務 / 上場情報 / カレンダー取得（ページネーション / トークン自動リフレッシュ / レート制限対応）
- ニュース収集
  - RSS 取得・前処理・記事保存（news_collector）
  - 銘柄コード抽出と紐付け（news_symbols）
- 研究用ユーティリティ
  - ファクター計算（momentum / volatility / value）
  - ファクター探索（forward returns / IC / summary）
  - Z スコア正規化ユーティリティ
- 戦略パイプライン
  - 特徴量構築（build_features）
  - シグナル生成（generate_signals）
- ポートフォリオ構築
  - 候補選定、等金額/スコア加重、リスクベースサイジング、セクターキャップ、レジーム乗数
- バックテスト
  - 擬似約定（スリッページ・手数料モデル）、日次スナップショット、トレード記録
  - メトリクス（CAGR, Sharpe, MaxDD, WinRate, PayoffRatio）
  - CLI 実行エントリポイント（python -m kabusys.backtest.run）

---

## 前提 / 要件

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml
  - （その他：標準ライブラリのみで実装されている箇所が多いですが、実行環境に応じて追加が必要な場合があります）

例（pip）:
```
pip install duckdb defusedxml
```

パッケージの開発セットアップ:
```
pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン／配置
2. Python 仮想環境を用意して依存をインストール
3. .env を作成して必須環境変数を設定
4. DuckDB スキーマを初期化（schema 初期化用関数を利用）

例: .env（プロジェクトルートに配置）
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_refresh_token_here

# kabu API (kabuステーション)
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789

# DB paths (任意)
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると config モジュールの自動 .env ロードを無効化できます（テスト用）。

DuckDB スキーマ初期化（例）:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # 既存DBがなければ初期テーブル作成
conn.close()
```

（schema モジュールはコードベースに含まれている想定です。初期テーブル定義に従って prices_daily / features / signals / positions / raw_* 等のテーブルが作成されます）

---

## 使い方

### バックテスト（CLI）

DuckDB ファイルを用意（prices_daily / features / ai_scores / market_regime / market_calendar 等が整っていることが前提）。

実行例:
```
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --db data/kabusys.duckdb \
  --cash 10000000 \
  --allocation-method risk_based \
  --lot-size 100
```

出力: バックテストメトリクス（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, Total Trades）を標準出力に表示します。

### 特徴量構築（プログラムから）

DuckDB コネクションを作成し、build_features を呼び出します。
```python
import duckdb
from datetime import date
from kabusys.strategy import build_features

conn = duckdb.connect("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2024, 1, 31))
print(f"features upserted: {n}")
conn.close()
```

### シグナル生成（プログラムから）

features / ai_scores / positions を参照して signals テーブルへ出力します。
```python
from datetime import date
from kabusys.strategy import generate_signals

conn = duckdb.connect("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2024,1,31))
print(f"signals written: {count}")
conn.close()
```

### データ取得 / 保存（J-Quants）

J-Quants からの取得例:
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
records = fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,12,31))
saved = save_daily_quotes(conn, records)
print(f"saved raw prices: {saved}")
conn.close()
```

注意:
- J-Quants は API レート制限 (120 req/min) を持ち、クライアントは固定間隔レートリミッタとリトライを備えています。
- get_id_token() は settings.jquants_refresh_token を使います。環境変数に設定してください。

### ニュース収集（RSS）

news_collector.run_news_collection を呼び出して RSS を取得・保存できます。known_codes を渡すと記事 → 銘柄紐付けも行います。

```python
from kabusys.data.news_collector import run_news_collection
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
results = run_news_collection(conn, sources=None, known_codes=set(["7203","6758"]))
print(results)
conn.close()
```

セキュリティ・堅牢性:
- RSS 取得は SSRF 対策・gzip サイズ検査・XML パースの安全化（defusedxml）等を備えています。

---

## ディレクトリ構成（主なファイル・モジュール）

src/kabusys/
- __init__.py — パッケージ定義
- config.py — 環境変数 / 設定管理
- data/
  - jquants_client.py — J-Quants API クライアント & DuckDB 保存ユーティリティ
  - news_collector.py — RSS 取得・記事保存・銘柄抽出
  - (schema, calendar_management, stats 等は別ファイルで想定)
- research/
  - factor_research.py — momentum / volatility / value の計算
  - feature_exploration.py — forward returns / IC / summary（研究用）
- strategy/
  - feature_engineering.py — features テーブル構築（正規化・クリップ・UPSERT）
  - signal_generator.py — final_score 計算 & BUY/SELL 判定 & signals テーブル保存
- portfolio/
  - portfolio_builder.py — 候補選定・重み付け（等金額/スコア）
  - position_sizing.py — 株数計算・リスクベース算出・単元丸め・aggregate cap
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- backtest/
  - engine.py — バックテストの全体ループ（run_backtest）
  - simulator.py — 擬似約定・ポートフォリオ状態・マークツーマーケット
  - metrics.py — バックテスト評価指標の計算
  - run.py — CLI エントリポイント
  - clock.py — 模擬時計（将来用）
- portfolio/ などと連携してバックテストを実行

（上記は本リポジトリ内の主な実装ファイルを抜粋したものです）

---

## 開発・貢献

- コードはドメイン（研究 / データ / 戦略 / 実行 / モニタリング）毎に分割されています。新機能追加は該当モジュールに機能を追加してください。
- テストは単体関数が純粋関数であることを想定して容易にモック可能です（DuckDB 接続部分はインメモリ DB を使うと便利です）。
- 環境変数の自動ロードは config._find_project_root() で .git / pyproject.toml を探索します。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。

---

## 注意事項

- 本リポジトリは実運用を想定した設計・実装ガイドラインに沿っていますが、実際のライブトレードを行う場合は入念な検証・ログ監査・安全対策が必要です。
- J-Quants / kabu ステーション等の外部 API 情報は個人情報やキーを扱うため、.env を漏洩しないよう管理してください。
- DuckDB のスキーマ（テーブル定義）は schema モジュールに依存します。バックテスト / シグナル生成に必要なテーブルが整っていることを事前に確認してください。

---

必要に応じて README をプロジェクトの実ファイル（schema, requirements 等）に合わせて更新できます。追加で「環境の初期データ投入方法」や「CI でのバックテスト実行手順」などを追記したい場合は指示してください。