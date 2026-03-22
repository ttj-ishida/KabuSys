# KabuSys

日本株向けの自動売買 / 研究プラットフォーム用ライブラリです。  
データ収集（J-Quants）、ETL、特徴量生成、シグナル生成、バックテスト、ニュース収集、バックエンド（DuckDB）スキーマなどを含んだモジュール群を提供します。

---

## プロジェクト概要

KabuSys は以下のレイヤーで構成されています。

- Data Layer: J-Quants からのデータ取得クライアント、RSS ニュース収集、DuckDB スキーマ定義、ETL パイプライン
- Research Layer: ファクター計算・特徴量探索（ルックアヘッドバイアスを避ける設計）
- Strategy Layer: 特徴量を正規化しシグナル（BUY/SELL）を生成
- Backtest Layer: 日次シミュレータ、約定モデル、メトリクス計算、バックテスト実行 CLI
- Execution / Monitoring 層: 実運用向け（API 呼び出し・監視）用のプレースホルダ（将来的な拡張）

設計方針の要点:
- ルックアヘッドバイアス回避（target_date 時点のデータのみ使用）
- DuckDB を中心としたローカル DB（インメモリも可）
- 冪等性（DB への保存は ON CONFLICT 等で重複防止）
- ネットワーク処理に対する堅牢性（リトライ、レート制限、SSRF対策 等）

---

## 主な機能一覧

- jquants_client
  - J-Quants API から株価・財務・市場カレンダーを取得（ページネーション、トークン自動更新、リトライ、レート制御）
  - DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）
- data.pipeline
  - 差分更新ベースの ETL（backfill 対応、品質チェックフック）
- data.news_collector
  - RSS フィード収集、URL 正規化、記事 ID 生成（SHA-256）、SSRF 対策、raw_news / news_symbols への冪等保存
- data.schema
  - DuckDB のスキーマ定義と初期化（raw / processed / feature / execution 層）
- research.factor_research / feature_exploration
  - Momentum / Volatility / Value 等のファクター計算、Forward return、IC 計算、統計サマリー
- strategy.feature_engineering
  - 研究で得た raw factor を結合・ユニバースフィルタ・Z スコア正規化して features テーブルへ保存
- strategy.signal_generator
  - features と ai_scores を統合し最終スコアを算出、BUY/SELL シグナルを signals テーブルへ保存
- backtest
  - PortfolioSimulator（擬似約定、スリッページ・手数料モデル）、run_backtest（DB をコピーして日次ループでシミュレーション）、評価指標計算

---

## セットアップ手順

前提
- Python 3.9+（typing 機能や一部の型記述を考慮）
- DuckDB（Python パッケージ）
- defusedxml（RSS パースの安全化）

推奨インストール例（仮に requirements.txt が無い場合）:
pip install duckdb defusedxml

（必要に応じて他パッケージを追加してください）

環境変数
- 必須（Settings で _require されるもの）
  - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD — kabu API を使用する場合のパスワード
  - SLACK_BOT_TOKEN — Slack 通知を使う場合
  - SLACK_CHANNEL_ID — Slack 通知先チャネル
- 任意
  - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL — DEBUG/INFO/...（デフォルト: INFO）
  - DUCKDB_PATH — デフォルト data/kabusys.duckdb
  - SQLITE_PATH — 監視用 DB（デフォルト data/monitoring.db）

.env ファイル
プロジェクトルートに `.env` / `.env.local` を置くと自動でロードされます（CWD ではなくパッケージ位置から .git または pyproject.toml を基準に探索）。自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

サンプル .env（例）
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb

DuckDB スキーマ初期化
Python REPL またはスクリプトで実行:
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")

---

## 使い方（主な操作・例）

1) DuckDB スキーマ初期化
python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

2) J-Quants からデータを取得して保存（ETL の一部を手動で呼ぶ例）
from datetime import date
import duckdb
from kabusys.data.schema import init_schema
from kabusys.data import jquants_client as jq

conn = init_schema("data/kabusys.duckdb")
# fetch & save 例（必要に応じて id_token を取得して渡す）
recs = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
jq.save_daily_quotes(conn, recs)

3) ETL の差分処理（pipeline モジュール）
from datetime import date
from kabusys.data.pipeline import run_prices_etl
# conn は init_schema で作成した接続
result = run_prices_etl(conn, target_date=date.today())

4) 特徴量の構築（feature_engineering）
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import build_features

conn = init_schema("data/kabusys.duckdb")
cnt = build_features(conn, target_date=date(2024,1,31))
print(f"features upserted: {cnt}")

5) シグナル生成
from kabusys.strategy import generate_signals
generate_signals(conn, target_date=date(2024,1,31))

6) バックテスト（CLI）
python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db data/kabusys.duckdb
（オプション: --cash, --slippage, --commission, --max-position-pct）

7) バックテストを Python から呼ぶ
from kabusys.backtest.engine import run_backtest
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_backtest(conn, start_date=date(2023,1,4), end_date=date(2023,12,29))
# result.history, result.trades, result.metrics を参照

8) ニュース収集（RSS）
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={'7203','6758'})

注意点
- ETL / データ取得は API のレート制限やリトライ挙動に準拠しているため、大量取得時は時間を要します。
- run_backtest は本番 DB から必要なテーブルをインメモリ DB にコピーして実行するため、本番テーブルを汚しません。
- .env の自動ロードはプロジェクトルート検出に依存します（.git または pyproject.toml）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
  - 環境変数読み込み / Settings クラス（JQUANTS_REFRESH_TOKEN など）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存）
  - news_collector.py — RSS 取得と raw_news / news_symbols 保存
  - schema.py — DuckDB スキーマ定義と init_schema()
  - stats.py — zscore_normalize 等の汎用統計関数
  - pipeline.py — ETL パイプライン（差分更新等）
- research/
  - __init__.py
  - factor_research.py — momentum / value / volatility の計算
  - feature_exploration.py — forward returns / IC / factor summary
- strategy/
  - __init__.py
  - feature_engineering.py — features テーブル生成（正規化・ユニバースフィルタ）
  - signal_generator.py — final_score 計算と signals テーブル書込
- backtest/
  - __init__.py
  - engine.py — run_backtest（インメモリコピー & 日次ループ）
  - simulator.py — PortfolioSimulator（擬似約定）
  - metrics.py — バックテスト評価指標
  - run.py — CLI エントリポイント（python -m kabusys.backtest.run）
  - clock.py — 将来拡張用の模擬時計
- execution/ (未実装プレースホルダ)
- monitoring/ (未実装プレースホルダ)

その他
- data/ 以下に保存されるデフォルト DB: data/kabusys.duckdb, data/monitoring.db

---

## 追加情報 / 開発メモ

- 自動 .env 読み込みはプロジェクトルートを .git または pyproject.toml で探します。CI・テストで自動ロードを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- news_collector は SSRF を防ぐためリダイレクト先検査やホストプライベート判定、受信サイズ上限、defusedxml を利用した安全な XML パースを行います。
- jquants_client は API レート制限（120 req/min）に合わせた固定間隔スロットリングと、401 時のトークン自動リフレッシュ、408/429/5xx のリトライ処理を備えています。
- スキーマやデータ形式は DataSchema.md / StrategyModel.md / BacktestFramework.md（設計ドキュメント）に基づく想定。実運用ではこれら設計文書に合わせたデータ投入が必要です。

---

問題点・拡張アイデア（運用時に検討すべき点）
- positions テーブルに peak_price / entry_date 等を保存するとトレーリングストップ等の戦略強化が容易になります（現状は未実装）。
- ai_scores の更新フロー（外部 AI サービス連携）を用意するとニュース・センチメントを戦略に組み込みやすくなります。
- 実運用での発注（kabu API）・監視（Slack 通知）機能を execution / monitoring 層で実装する必要があります。

---

必要であれば、README を英語版に翻訳したり、セットアップ用の requirements.txt / docker-compose 例、CI 用の簡易ワークフローを追記します。どれを優先しますか？