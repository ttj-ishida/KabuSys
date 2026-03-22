# KabuSys

KabuSys は日本株向けの自動売買基盤ライブラリです。  
データ収集（J-Quants / RSS）、ETL、特徴量生成、シグナル生成、バックテスト、擬似約定シミュレータ、DuckDB スキーマ管理など、戦略検証から運用までの主要機能を備えています。

バージョン: 0.1.0

---

## 主な機能

- データ取得・保存
  - J-Quants API クライアント（株価日足、財務データ、マーケットカレンダー）
  - RSS ニュース収集（安全対策付き）と記事→銘柄紐付け
  - DuckDB への冪等保存（ON CONFLICT / トランザクション）
- ETL パイプライン
  - 差分取得 / バックフィル対応 / 品質チェックフレームワーク
- スキーマ管理
  - DuckDB 用のスキーマ初期化（raw / processed / feature / execution 層）
- ファクター計算・特徴量処理
  - Momentum / Volatility / Value 等のファクター算出
  - クロスセクション Z スコア正規化、ユニバースフィルタ
- シグナル生成
  - 正規化された特徴量＋AI スコアを統合して BUY/SELL シグナルを生成
  - Bear レジーム検知やエグジット条件（ストップロス等）実装
- バックテスト
  - インメモリでのバックテスト実行（擬似約定、スリッページ、手数料モデル）
  - 評価指標（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio）
- ニュース収集
  - RSS フィード取得、本文前処理、記事ID生成、raw_news/news_symbols 保存
  - SSRF 対策、サイズ上限、XML パース安全化（defusedxml）
- 小規模の実行層（execution）と監視（monitoring）向けの土台

---

## セットアップ手順

前提
- Python 3.9+
- duckdb
- ネットワークアクセス（J-Quants / RSS）

1. リポジトリをクローン（パッケージ開発時）
   - 開発環境であればプロジェクトルートに移動して pip editable install 等を行ってください。
   - 例:
     - git clone ...
     - cd <repo>
     - python -m venv .venv
     - source .venv/bin/activate

2. 必要パッケージをインストール
   - 最小例:
     - pip install duckdb defusedxml
   - プロジェクトに requirements.txt がある場合はそちらを使用してください。

3. 環境変数の設定
   - 必要な環境変数（主要なもの）
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID      : 通知先チャンネル ID（必須）
     - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH           : SQLite（監視用）パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV           : 実行環境 (development | paper_trading | live)（デフォルト: development）
     - LOG_LEVEL             : ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)（デフォルト: INFO）
   - .env / .env.local をプロジェクトルートに置くと自動で読み込まれます（kabusys.config の自動ロード）。
     - 読み込み優先順位: OS 環境変数 > .env.local > .env
     - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

4. DuckDB スキーマ初期化
   - Python REPL かスクリプトで:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")
     - conn.close()
   - ":memory:" を指定するとインメモリ DB が初期化されます（バックテスト用に利用可）。

---

## 使い方（簡易ガイド）

以下は主要な利用例です。各関数は duckdb 接続や日付を受け取り、冪等性を保つ設計です。

1. 設定取得（コード内で）
   - from kabusys.config import settings
   - token = settings.jquants_refresh_token

2. スキーマ初期化（1回だけ）
   - from kabusys.data.schema import init_schema
   - conn = init_schema("data/kabusys.duckdb")

3. データ取得（J-Quants）
   - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
   - records = fetch_daily_quotes(date_from=..., date_to=...)
   - saved = save_daily_quotes(conn, records)

4. ETL パイプライン（差分更新）
   - from kabusys.data.pipeline import run_prices_etl, ETLResult
   - result = run_prices_etl(conn, target_date=datetime.date.today())
   - ETLResult に品質チェックやエラー情報が含まれます

5. 特徴量構築（features テーブルへ書込む）
   - from kabusys.strategy import build_features
   - build_features(conn, target_date=some_date)  # DuckDB 接続と基準日を指定

6. シグナル生成
   - from kabusys.strategy import generate_signals
   - generate_signals(conn, target_date=some_date, threshold=0.6, weights=None)

7. ニュース収集ジョブ
   - from kabusys.data.news_collector import run_news_collection
   - results = run_news_collection(conn, sources=None, known_codes=set_of_codes)

8. バックテスト（CLI）
   - 付属のバックテストランナーを利用（DB は事前にデータを用意）
   - コマンド例:
     - python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db data/kabusys.duckdb
   - オプション: --cash, --slippage, --commission, --max-position-pct

9. バックテスト（プログラムから）
   - from kabusys.backtest.engine import run_backtest
   - result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
   - result.history / result.trades / result.metrics を利用

注意点:
- 各 ETL / ビルド / 生成処理は target_date 単位で日付を削除してから挿入する（冪等）。
- J-Quants API 呼び出しはレート制限・リトライ・401 自動刷新などを含む堅牢な実装です。
- news_collector は SSRF 対策、受信サイズ制限、XML の安全パースを行います。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
  - 環境変数 / .env 自動ロード / settings 提供
- data/
  - __init__.py
  - jquants_client.py         — J-Quants API クライアント、保存関数
  - news_collector.py        — RSS 取得・前処理・DB 保存
  - pipeline.py              — ETL パイプライン
  - schema.py                — DuckDB スキーマ定義と init_schema
  - stats.py                 — Zスコア等の統計ユーティリティ
- research/
  - __init__.py
  - factor_research.py       — Momentum/Value/Volatility ファクター
  - feature_exploration.py   — 将来リターン計算、IC、統計サマリ
- strategy/
  - __init__.py
  - feature_engineering.py   — features 作成フロー（正規化・ユニバースフィルタ）
  - signal_generator.py      — final_score 計算と BUY/SELL シグナル生成
- backtest/
  - __init__.py
  - engine.py                — run_backtest（インメモリコピー＋日次ループ）
  - simulator.py             — PortfolioSimulator（擬似約定、history/trades）
  - metrics.py               — バックテスト評価指標計算
  - clock.py                 — SimulatedClock（将来拡張用）
  - run.py                   — CLI エントリポイント（バックテスト実行）
- execution/                  — 発注/実行層のプレースホルダ（拡張用）
- monitoring/                 — 監視・メトリクス関連（拡張用）

ドキュメント（リポジトリ外想定）
- StrategyModel.md, DataPlatform.md, BacktestFramework.md, DataSchema.md 等の設計ドキュメントを参照することを想定しています。

---

## 補足 / ベストプラクティス

- 環境変数は .env.example を参考に .env を作成してください（settings._require は未設定で例外を投げます）。
- 開発中に .env の自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途）。
- DuckDB のファイルパスを変更する場合は settings.duckdb_path（環境変数 DUCKDB_PATH）を使って統一してください。
- ニュースの銘柄抽出は既知のコードセット（known_codes）を渡すことで誤抽出を抑制できます。
- generate_signals は weights に対して寛容な入力検証を行い、合計が 1 になるよう自動で正規化します。

---

もし README に追記したい具体的なコマンド例や、CI / デプロイ手順、テストの書き方などの要求があれば教えてください。必要に応じてサンプル .env.example も作成できます。