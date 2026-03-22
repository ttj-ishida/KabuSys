# KabuSys

日本株向けの自動売買フレームワーク（ライブラリ）。データ取得・ETL、特徴量計算、シグナル生成、バックテスト、ニュース収集、バックエンド用の DuckDB スキーマなどを提供します。

主な目的は、ルックアヘッドバイアスを避けつつ研究→運用への橋渡しを行うことです（データ取得は J-Quants、発注は kabuステーション を想定）。

## 特徴（機能一覧）

- データ取得
  - J-Quants API クライアント（差分取得・ページネーション・トークン自動リフレッシュ・レート制限・リトライ）
  - JPX マーケットカレンダー、株価（OHLCV）、財務データの取得と DuckDB への保存
- ETL パイプライン
  - 差分更新、バックフィル（後出し修正吸収）、品質チェック連携
- ニュース収集
  - RSS フィード取得、前処理、記事保存、記事→銘柄の紐付け（SSRF対策、gzip/サイズ制限、トラッキング除去）
- ファクター設計・特徴量生成（research / strategy 層）
  - Momentum / Volatility / Value ファクター計算
  - クロスセクション Z スコア正規化（外れ値クリップ）
  - features テーブルへの冪等保存
- シグナル生成（strategy）
  - ファクター＋AIスコア統合による final_score 計算
  - Bear レジーム抑制、BUY/SELL シグナルの生成と signals テーブルへの冪等書き込み
- バックテストフレームワーク
  - DuckDB を用いたインメモリコピーでのシミュレーション
  - 約定・スリッページ・手数料モデルを持つポートフォリオシミュレータ
  - メトリクス（CAGR、Sharpe、Max Drawdown、勝率、Payoff 等）
  - CLI エントリーポイント（python -m kabusys.backtest.run）
- DB スキーマ（DuckDB）
  - Raw / Processed / Feature / Execution 層を含むスキーマ定義と初期化ユーティリティ

---

## 要件（Prerequisites）

- Python 3.10+
- 必須ライブラリ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード 等）
- J-Quants リフレッシュトークン、kabu API パスワード、Slack トークン等の環境変数（下記参照）

インストール（例）
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# 開発中でパッケージ化済みなら:
# pip install -e .
```

---

## 環境変数（.env）

プロジェクトはルートの `.env` / `.env.local` を自動で読み込みます（CWD ではなくパッケージ位置からプロジェクトルートを検出）。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主に使用される環境変数（config.Settings で参照）:
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（省略可、デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN（必須）
- SLACK_CHANNEL_ID（必須）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用 DB、デフォルト: data/monitoring.db）
- KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

README に含める .env.example（例）
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン
2. 仮想環境を作成して有効化
3. 依存パッケージをインストール（上記参照）
4. DuckDB スキーマを初期化
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```
5. .env を編集して必要な環境変数を設定（J-Quants トークン等）

---

## 使い方（主要な例）

- DuckDB スキーマ初期化（プログラム）:
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可
  ```

- J-Quants からデータ取得して保存（例）:
  ```python
  from kabusys.data import jquants_client as jq
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=..., date_to=...)
  saved = jq.save_daily_quotes(conn, records)
  conn.close()
  ```

- ETL（パイプライン）を呼ぶ（例）:
  ```python
  from kabusys.data.pipeline import run_prices_etl, ETLResult
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  result = run_prices_etl(conn, target_date=date.today())
  # result は (fetched_count, saved_count) などを返す実装になっています
  conn.close()
  ```

- 特徴量ビルド / シグナル生成（プログラム）:
  ```python
  import duckdb
  from kabusys.strategy import build_features, generate_signals
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  build_features(conn, target_date=date(2024, 1, 1))
  generate_signals(conn, target_date=date(2024, 1, 1))
  conn.close()
  ```

- バックテスト実行（CLI）:
  ```
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --cash 10000000 --db data/kabusys.duckdb
  ```
  実行後に CAGR、Sharpe、MaxDD、勝率 等が出力されます。

- ニュース収集ジョブ（RSS）:
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", ...}  # 抽出対象の有効銘柄コードセット
  res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  conn.close()
  ```

---

## 主要モジュール / ディレクトリ構成

リポジトリは Python パッケージ `kabusys`（src 配下）として構成されています。主なファイルと機能は次の通りです。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み、Settings クラス（J-Quants トークン、kabu API、Slack、DB パス、実行環境判定等）
  - data/
    - __init__.py
    - jquants_client.py: J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py: RSS 収集 & raw_news/news_symbols への保存
    - pipeline.py: ETL パイプライン（差分取得・品質チェック連携）
    - schema.py: DuckDB スキーマの定義と init_schema
    - stats.py: Z スコア等の統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py: Momentum / Volatility / Value ファクター計算
    - feature_exploration.py: 将来リターン、IC、統計サマリー等の研究用ユーティリティ
  - strategy/
    - __init__.py
    - feature_engineering.py: ファクター正規化・features テーブルへの書込
    - signal_generator.py: final_score 計算、BUY/SELL シグナル生成、signals テーブルへの保存
  - backtest/
    - __init__.py
    - engine.py: バックテストループ（インメモリ DB コピー・シミュレーション実行）
    - simulator.py: ポートフォリオシミュレータ（約定・マーケット評価・トレード履歴）
    - metrics.py: バックテスト評価指標計算（CAGR, Sharpe など）
    - run.py: CLI エントリポイント（python -m kabusys.backtest.run）
    - clock.py: 将来用の模擬時計
  - execution/
    - (発注 / 実行関連のエントリポイント・ラッパー等。実装は環境依存)
  - monitoring/
    - (監視用 DB / Slack 通知などを想定するモジュール群)

---

## 開発・テスト上の注意

- type ヒントや一部の構文により Python 3.10 以降を想定しています（| 型記法など）。
- config モジュールはプロジェクトルート（.git または pyproject.toml）を基に .env を自動読み込みします。テスト時に自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB のバージョンによっては制約や外部キーの挙動が異なる場合があります（schema.py のコメント参照）。
- ネットワーク呼び出しを伴う部分（J-Quants、RSS）は単体テストではモック化することを推奨します。

---

## 参考・補足

- 設計文書（StrategyModel.md、DataPlatform.md、BacktestFramework.md 等）を参照することで詳細な仕様（重み付け、閾値、ETL 戦略など）を把握できます（本リポジトリに含まれる想定仕様に基づいた実装が多数あります）。
- 追加の CLI、運用スクリプト、Slack 通知などは本パッケージをベースに自由に作成してください。

---

必要であれば、README にサンプル .env.example やよくあるトラブルシュート（例: J-Quants 401 エラー時の対処、DuckDB ロック、RSS の SSRF エラー対策）を追記します。どの項目を詳しく載せたいか教えてください。