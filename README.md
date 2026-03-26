# KabuSys

日本株向けの自動売買 / 研究フレームワーク。  
ファクター計算・特徴量生成・シグナル生成・ポートフォリオ構築・バックテスト・データ収集（J-Quants / RSS）など、アルゴリズムトレーディングに必要な主要処理をモジュール化しています。

現在のバージョン: 0.1.0

---

## 主要機能（概要）

- 環境設定管理
  - .env または環境変数から設定を自動読み込み（自動ロードは無効化可）
- データ取得 / ETL
  - J-Quants API クライアント（株価、財務データ、マーケットカレンダー）
  - RSS ニュース収集（SSRF対策、トラッキングパラメータ除去、記事→銘柄紐付け）
  - DuckDB への冪等保存ユーティリティ
- 研究（research）
  - モメンタム / ボラティリティ / バリュー などのファクター計算
  - ファクターの探索用ユーティリティ（将来リターン、IC、要約統計）
- 特徴量エンジニアリング（strategy.feature_engineering）
  - research で計算した生ファクターを正規化・クリップし `features` テーブルへ UPSERT
- シグナル生成（strategy.signal_generator）
  - features / ai_scores を組み合わせて final_score を算出
  - BUY / SELL シグナル生成（Bear レジーム抑制、ストップロス等）
  - signals テーブルへの日次置換保存（冪等）
- ポートフォリオ構築（portfolio）
  - 候補選定（スコア順）
  - 重み付け（等金額 / スコア加重）
  - サイジング（risk-based をサポート、単元丸め、集約キャップ調整）
  - セクター集中制限、レジーム乗数（投下資金調整）
- バックテスト（backtest）
  - インメモリ DuckDB にデータをコピーして隔離したバックテスト実行
  - 擬似約定（スリッページ・手数料・部分約定処理）
  - 日次スナップショット記録・トレード履歴保存
  - メトリクス計算（CAGR, Sharpe, MaxDD, Win rate, Payoff）
  - CLI エントリポイントでの実行（python -m kabusys.backtest.run）
- 実行層の骨組み（execution / monitoring 等の名前空間はエクスポート済み）

---

## 動作環境 / 前提

- Python 3.10 以上（型注釈に Python 3.10 構文を使用）
- 必要パッケージ（主なもの）
  - duckdb
  - defusedxml
- その他（実行用途に応じて追加）
  - ネットワークアクセス（J-Quants API / RSS）
  - J-Quants のリフレッシュトークン、Slack トークン等の環境変数

requirements.txt はプロジェクトに含められていないため、上記ライブラリを手動でインストールしてください。

例:
pip install duckdb defusedxml

---

## セットアップ手順

1. リポジトリをクローン / ソースを取得
   - 例: git clone <repo-url>

2. Python 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクト固有の追加依存があれば別途インストール）

4. 環境変数 / .env の準備
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（デフォルト）。
   - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

   主な環境変数（必須となるもの）:
   - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD : kabuステーション API パスワード（実取引層で必須）
   - SLACK_BOT_TOKEN : Slack 通知用 Bot Token（必須）
   - SLACK_CHANNEL_ID : Slack チャンネル ID（必須）
   - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH : 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV : "development" / "paper_trading" / "live"（デフォルト "development"）
   - LOG_LEVEL : "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"（デフォルト "INFO"）

   例 .env：
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

5. データベーススキーマ初期化
   - プロジェクト内に `kabusys.data.schema.init_schema` 関数（スキーマ作成用）が用意されている前提です。
   - Python REPL で例:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()

   （init_schema 実装はプロジェクトに含まれている想定です。存在しない場合はスキーマ作成スクリプトを追加して下さい。）

---

## 使い方

以下は代表的なワークフローの例です。

1) J-Quants からデータ取得して DuckDB に保存（ETL）

Python スクリプト例:
from datetime import date
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
token = get_id_token()  # settings からリフレッシュトークンを使って取得
records = fetch_daily_quotes(id_token=token, date_from=date(2023,1,1), date_to=date.today())
save_daily_quotes(conn, records)
conn.close()

2) ニュース収集と銘柄紐付け

from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = set([r[0] for r in conn.execute("SELECT code FROM stocks").fetchall()])  # 例
res = run_news_collection(conn, known_codes=known_codes)
conn.close()

3) 特徴量構築（日次）

from datetime import date
import duckdb
from kabusys.strategy.feature_engineering import build_features
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2024,1,31))
conn.close()

4) シグナル生成（日次）

from datetime import date
from kabusys.strategy.signal_generator import generate_signals
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
n = generate_signals(conn, target_date=date(2024,1,31))
conn.close()

5) バックテスト（CLI）

プロジェクトルートで例:
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2024-12-31 \
  --cash 10000000 \
  --db data/kabusys.duckdb

主要オプション:
- --start / --end : バックテスト期間（YYYY-MM-DD）
- --cash : 初期資金（JPY）
- --slippage / --commission : スリッページ・手数料率
- --allocation-method : equal | score | risk_based
- --max-positions : 最大保有銘柄数
- --lot-size : 単元株数（デフォルト 100）
- --db : DuckDB ファイルパス（必須）

6) Python API でのバックテスト呼び出し

from kabusys.data.schema import init_schema
from kabusys.backtest.engine import run_backtest
from datetime import date

conn = init_schema("data/kabusys.duckdb")
res = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2024,12,31))
# res.history, res.trades, res.metrics に結果が入る
conn.close()

---

## 主要モジュール / API（抜粋）

- kabusys.config
  - settings — 環境変数を読み込むための Settings オブジェクト
- kabusys.data.jquants_client
  - get_id_token, fetch_daily_quotes, save_daily_quotes, fetch_financial_statements, save_financial_statements, fetch_market_calendar, save_market_calendar, fetch_listed_info
- kabusys.data.news_collector
  - fetch_rss, save_raw_news, run_news_collection, extract_stock_codes
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold=..., weights=...)
- kabusys.portfolio
  - select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
- kabusys.backtest
  - run_backtest(conn, start_date, end_date, ...), BacktestResult, DailySnapshot, TradeRecord, BacktestMetrics
- kabusys.backtest.run
  - CLI エントリポイント（python -m kabusys.backtest.run）

---

## 注意点 / 実運用時の留意事項

- Look-ahead バイアス防止:
  - 特徴量・シグナル生成・バックテストは「target_date 時点で利用可能なデータのみ」を用いる設計になっています。外部からデータ投入する際は取得日時とデータの可視化時間に注意してください（例: fetched_at の記録）。
- Bear レジーム:
  - signal_generator は Bear レジーム検出時に BUY シグナルを抑制します（設定により調整可能）。
- 自動 .env 読み込み:
  - プロジェクトルート（.git または pyproject.toml を起点）から `.env` / `.env.local` を自動読み込みします。テスト等で自動機能を無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- API レート制限 / リトライ:
  - J-Quants クライアントは内部でレート制御・リトライ・トークン自動更新を実装していますが、実際の運用ではレート制限や API 利用規約を守ってください。
- データベーススキーマ:
  - 本 README の例は `kabusys.data.schema.init_schema` によりスキーマ初期化が行えることを前提としています。schema 実装が別途必要です。

---

## ディレクトリ構成

（ソースに含まれているファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数管理（.env 自動ロード、Settings）
  - data/
    - jquants_client.py — J-Quants API クライアント + DuckDB 保存ユーティリティ
    - news_collector.py — RSS 収集・記事正規化・DB 保存・銘柄抽出
    - (schema.py 等がプロジェクトにある前提)
  - research/
    - factor_research.py — momentum/volatility/value の計算
    - feature_exploration.py — IC・forward returns・統計
  - strategy/
    - feature_engineering.py — features の構築（正規化・UPSERT）
    - signal_generator.py — final_score 計算と signals 生成
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み付け
    - position_sizing.py — 発注株数計算（risk_based / equal / score）
    - risk_adjustment.py — セクターキャップ / レジーム乗数
  - backtest/
    - engine.py — バックテストループ、データコピー、サイジング統合
    - simulator.py — 擬似約定 / ポートフォリオ管理
    - metrics.py — バックテスト評価指標
    - run.py — CLI エントリポイント
    - clock.py — SimulatedClock（将来拡張用）
  - execution/ (プレースホルダ)
  - monitoring/ (プレースホルダ)

---

## ライセンス / 貢献

この README はリポジトリ内のコードに基づく概要と使い方のサマリです。ライセンスや貢献ガイドラインはプロジェクトルートの LICENSE / CONTRIBUTING.md を参照してください（存在する場合）。

---

疑問点や README に追加したい具体的な使用例（SQL スキーマや init_schema の内容、CI セットアップ、依存リストの固定化など）があれば教えてください。README をより実運用向けに拡充できます。