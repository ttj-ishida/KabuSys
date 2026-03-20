# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）。データ収集（J‑Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、カレンダー管理、監査ログなどを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム構築を支援するライブラリ群です。主な目的は次のとおりです。

- J‑Quants API からの市場データ・財務データ・マーケットカレンダー取得（レートリミット・リトライ・トークン自動更新対応）
- DuckDB によるデータ格納（Raw / Processed / Feature / Execution の多層スキーマ）
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- 研究（research）向けのファクター計算・特徴量探索ユーティリティ
- 戦略層の特徴量正規化（feature_engineering）とシグナル生成（signal_generator）
- RSS を用いたニュース収集と銘柄抽出（SSRF対策・トラッキングパラメータ除去）
- 発注・約定・ポジションの監査ログ管理

設計上のポイント：
- ルックアヘッドバイアスを防ぐため「target_date 時点のデータのみ」を参照する方針
- DuckDB を用いた冪等保存（ON CONFLICT）、トランザクション保護
- 外部依存を最小化（可能な限り標準ライブラリ）、だが DuckDB / defusedxml 等は使用

---

## 機能一覧

- data
  - J‑Quants API クライアント（取得・保存・ページネーション・リトライ・トークン刷新）
  - DuckDB スキーマ定義 / 初期化（init_schema）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - ニュース収集（RSS 取得、前処理、DB 保存、銘柄抽出）
  - カレンダー管理（is_trading_day / next_trading_day / get_trading_days / calendar_update_job）
  - 統計ユーティリティ（zscore_normalize）
- research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman）計算、ファクター要約
- strategy
  - 特徴量ビルド（build_features）
  - シグナル生成（generate_signals） — momentum/value/volatility/liquidity/news を統合
- execution / monitoring / audit
  - テーブル設計と監査ログ（signal_events, order_requests, executions など）
- config
  - 環境変数管理（.env 自動読み込み、必須チェック、KABUSYS_ENV / LOG_LEVEL 等）

---

## セットアップ手順

前提
- Python 3.9+（コードは型注釈で演算子オーバーロード等を使用）
- duckdb パッケージ
- defusedxml（ニュース RSS パース用）
- （必要に応じて）その他環境に合わせたパッケージ

例：仮想環境作成と依存インストール（pip）
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# パッケージをローカル開発インストールする場合
# pip install -e .
```

環境変数（最低限設定が必要なもの）
- JQUANTS_REFRESH_TOKEN  — J‑Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD      — kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN        — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID       — Slack チャンネル ID（必須）
- KABUSYS_ENV            — development / paper_trading / live（省略時 development）
- LOG_LEVEL              — DEBUG / INFO / WARNING / ERROR / CRITICAL（省略時 INFO）
- DUCKDB_PATH            — DuckDB ファイルパス（省略時 data/kabusys.duckdb）
- SQLITE_PATH            — 監視用 SQLite のパス（省略時 data/monitoring.db）

例 .env（リポジトリルートに配置）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

自動で .env を読み込む仕組み：
- パッケージはプロジェクトルート（.git または pyproject.toml を探索）から .env/.env.local を自動読み込みします。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利）。

---

## 使い方（代表的なワークフロー）

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ":memory:" でインメモリ可
```

2) 日次 ETL 実行（J‑Quants から差分取得して保存）
```python
from kabusys.data.pipeline import run_daily_etl, get_last_price_date
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
res = run_daily_etl(conn, target_date=date.today())
print(res.to_dict())
```

3) 特徴量をビルド（strategy.feature_engineering.build_features）
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

4) シグナル生成（strategy.signal_generator.generate_signals）
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
signals_written = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {signals_written}")
```

5) ニュース収集ジョブ（RSS から raw_news に保存・銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes: 銘柄抽出に使用する有効なコード集合（例: prices_daily の code を集める等）
saved_by_source = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(saved_by_source)
```

6) カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

補足：
- J‑Quants への API コールは内部でレート制御（120 req/min）・リトライ・401 時のトークン自動リフレッシュを実行します。
- ETL は品質チェック（quality モジュール）を呼び出します。品質問題は収集を止めずに収集結果へ報告されます。
- strategy モジュールは発注 API には依存せず、シグナルを生成して signals テーブルへ冪等に保存します。execution 層で実際の発注処理を組み合わせてください。

---

## 主要 API（抜粋）

- kabusys.config.settings
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.kabu_api_base_url, settings.slack_bot_token, settings.duckdb_path, settings.env, settings.log_level, settings.is_live 等

- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)

- kabusys.data.jquants_client
  - fetch_daily_quotes(...), save_daily_quotes(...)
  - fetch_financial_statements(...), save_financial_statements(...)
  - fetch_market_calendar(...), save_market_calendar(...)

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, ...)
  - run_prices_etl / run_financials_etl / run_calendar_etl

- kabusys.data.news_collector
  - fetch_rss(url, source), save_raw_news(conn, articles), run_news_collection(...)

- kabusys.research
  - calc_momentum(conn, date), calc_volatility(...), calc_value(...), calc_forward_returns(...), calc_ic(...)

- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold, weights)

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                      — 環境変数・設定管理
- data/
  - __init__.py
  - jquants_client.py            — J‑Quants API クライアント（取得/保存）
  - news_collector.py            — RSS ニュース収集・前処理・DB保存
  - schema.py                    — DuckDB スキーマ定義・初期化
  - pipeline.py                  — ETL パイプライン（差分更新・日次ETL）
  - calendar_management.py       — マーケットカレンダー管理・ジョブ
  - features.py                  — 統計ユーティリティ公開（zscore_normalize）
  - stats.py                     — 統計ユーティリティ（Z スコア正規化）
  - audit.py                     — 監査ログスキーマ（signal_events, order_requests, executions）
- research/
  - __init__.py
  - factor_research.py           — momentum/value/volatility 計算
  - feature_exploration.py       — 将来リターン/IC/summary 等
- strategy/
  - __init__.py
  - feature_engineering.py       — features テーブル構築（正規化・フィルタ）
  - signal_generator.py          — final_score 計算・BUY/SELL 生成
- execution/                      — 発注・実行関連（骨組み）
- monitoring/                     — 監視・メトリクス（骨組み）

テスト用や docs は含まれていません（リポジトリの構成次第で追加）。

---

## 注意事項・運用上のポイント

- 本ライブラリは「戦略の計算・シグナル生成」を提供しますが、実際の発注（証券会社 API）・リスク管理・資金管理は別レイヤーで実装してください。
- DuckDB のファイルパス（DUCKDB_PATH）は設定ファイル/環境変数で管理し、バックアップやローテーションを計画してください。
- ニュース収集では外部 RSS をダウンロードします。SSRF 対策やレスポンスサイズ制限が組み込まれていますが、運用時は信頼できるソースを選択してください。
- 本番環境（live）では KABUSYS_ENV=live を設定し、log レベルやテストフラグに注意してください。

---

## 貢献・拡張のヒント

- 新しいファクターを追加する場合は `kabusys.research.factor_research` に実装し、`kabusys.strategy.feature_engineering` の正規化対象に追加してください。
- 発注ロジック（execution 層）は監査ログと signal_queue / orders / trades のスキーマに基づいて実装できます。
- DuckDB のスキーマに変更を加える場合は `data/schema.py` の DDL を更新し、マイグレーション手順を別途用意してください。

---

必要であれば README に具体的なサンプルワークフロー（cron/job 定義、systemd unit、Dockerfile、CI スクリプト等）を追加します。どの部分を詳しく追記しましょうか？