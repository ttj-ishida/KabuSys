# KabuSys

KabuSys は日本株向けの自動売買システム向けライブラリです。データ収集（J-Quants）、データスキーマ（DuckDB）、特徴量作成、シグナル生成、バックテストおよび簡易な実行/ニュース収集機能を含むモジュール群を提供します。

このリポジトリはコアライブラリとして以下を想定しています：
- データレイヤ（J-Quants クライアント、RSS ニュース収集、ETL パイプライン）
- 特徴量計算 / 研究用ユーティリティ
- シグナル生成ロジック（ルール＋AIスコア統合）
- バックテストフレームワーク（シミュレータ・メトリクス）
- DuckDB スキーマ管理（初期化 / 接続）

---

## 主な機能

- J-Quants API クライアント
  - 株価（OHLCV）、財務データ、JPX マーケットカレンダー取得
  - レートリミット、リトライ、トークン自動リフレッシュ対応
  - DuckDB への冪等保存（ON CONFLICT）

- ETL / パイプライン
  - 差分取得（バックフィル対応）、品質チェック（設計）
  - raw → processed → feature 層へのデータ保存設計

- ニュース収集
  - RSS 収集（SSRF 対策・サイズ制限・トラッキングパラメータ除去）
  - 記事IDの冪等生成、記事と銘柄コードの紐付け

- 研究用ファクター計算
  - Momentum / Volatility / Value 等のファクター算出
  - forward return / IC / ファクター統計サマリー

- 特徴量エンジニアリング（戦略用）
  - ユニバースフィルタ、Zスコア正規化、features テーブルへの UPSERT

- シグナル生成
  - ファクター + AI スコア統合による final_score 計算
  - Bear レジーム時の BUY 抑制、SELL（エグジット）ロジック
  - signals テーブルへの冪等書き込み

- バックテストフレームワーク
  - インメモリ DuckDB コピーによる安全なバックテスト
  - 約定シミュレータ（スリッページ、手数料モデル）
  - 評価指標（CAGR / Sharpe / MaxDrawdown / WinRate / PayoffRatio）
  - CLI 実行エントリポイントあり

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化関数

---

## セットアップ

前提: Python 3.10+（ typing の一部記法に依存 ）と pip が利用可能であることを想定します。

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (macOS / Linux)
   - .venv\Scripts\activate (Windows)

2. 必要なパッケージ（最小）
   - duckdb
   - defusedxml

   例:
   ```bash
   pip install duckdb defusedxml
   ```

   （開発時は logging 等の標準ライブラリのみで大部分が動きますが、DuckDB と defusedxml は必須です。
   実運用では J-Quants 用に追加 HTTP ライブラリや Slack クライアントを導入することがあるかもしれません。）

3. パッケージをプロジェクトに追加（編集開発時）
   ```bash
   pip install -e .
   ```

4. 環境変数 / .env
   - プロジェクトはルート（.git または pyproject.toml のあるディレクトリ）を探索して `.env` / `.env.local` を自動ロードします（ただしテストや特殊用途で無効化可）。
   - 自動ロードを無効にする場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

   主に必要な環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャネル ID（必須）
   - DUCKDB_PATH: デフォルト DB パス（例: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（例: data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password_here
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（代表例）

- DuckDB スキーマの初期化
  ```python
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  # 作業が終わったら
  conn.close()
  ```

- J-Quants から株価を取得して保存（例）
  ```python
  import duckdb
  from kabusys.data import jquants_client as jq

  conn = duckdb.connect("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=...)
  saved = jq.save_daily_quotes(conn, records)
  conn.close()
  ```

- 特徴量（features）構築
  ```python
  import duckdb
  from datetime import date
  from kabusys.strategy import build_features

  conn = duckdb.connect("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2024, 1, 31))
  conn.close()
  ```

- シグナル生成
  ```python
  import duckdb
  from datetime import date
  from kabusys.strategy import generate_signals

  conn = duckdb.connect("data/kabusys.duckdb")
  total_signals = generate_signals(conn, target_date=date(2024, 1, 31))
  conn.close()
  ```

- バックテスト（CLI）
  ローカルに作成済みの DuckDB を用いてバックテストを実行します（DB 内に prices_daily, features, ai_scores, market_regime, market_calendar が存在する必要あり）。
  ```bash
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2024-12-31 \
    --cash 10000000 \
    --slippage 0.001 \
    --commission 0.00055 \
    --max-position-pct 0.20 \
    --db data/kabusys.duckdb
  ```

  実行後にコンソールへバックテスト結果（CAGR/Sharpe/MaxDD/WinRate/PayoffRatio/TotalTrades）が出力されます。

- バックテストをプログラムから利用する
  ```python
  import duckdb
  from datetime import date
  from kabusys.backtest.engine import run_backtest

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
  print(result.metrics.cagr, result.metrics.sharpe_ratio)
  conn.close()
  ```

---

## ディレクトリ構成（主要ファイル）

（この README はソースツリーの一部を反映しています）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定管理（.env 自動ロード）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得・保存）
    - news_collector.py       — RSS ニュース収集・保存・銘柄抽出
    - pipeline.py             — ETL パイプライン（差分更新など）
    - schema.py               — DuckDB スキーマ定義・初期化
    - stats.py                — Zスコア正規化等の統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py      — Momentum / Volatility / Value 等の計算
    - feature_exploration.py  — forward returns / IC / summary utilities
  - strategy/
    - __init__.py
    - feature_engineering.py  — features 作成（正規化・フィルタ）
    - signal_generator.py     — final_score 計算と signals 作成
  - backtest/
    - __init__.py
    - engine.py               — バックテスト主要ループ
    - simulator.py            — 約定シミュレータ & ポートフォリオ管理
    - metrics.py              — バックテスト評価指標計算
    - run.py                  — CLI エントリポイント
    - clock.py                — 将来用の模擬時計
  - execution/                — 実行層（発注/約定）用プレースホルダ
  - monitoring/               — 監視・メトリクス収集（将来拡張）

---

## 開発・運用上の注意

- 環境変数の保護:
  config モジュールは OS 環境変数を優先し、.env.local を .env の上に読み込みます。テスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを無効にできます。

- 冪等性:
  DB 保存処理（raw / processed / features / news 等）は基本的に冪等設計（ON CONFLICT / DO UPDATE / DO NOTHING）となっています。

- ルックアヘッドバイアス防止:
  研究・シグナル生成処理は原則 target_date 時点までのデータのみを使用します。取得したデータには fetched_at を記録して「データがいつ利用可能になったか」を追跡できるよう設計されています。

- エラーハンドリング:
  ネットワークや API エラー時にはリトライやログ出力を行いますが、運用用途では監視や適切なアラート（Slack 等）連携を推奨します。

---

## 参考（よく使う関数）

- init_schema(db_path) — DuckDB スキーマを初期化して接続を返す
- jquants_client.fetch_daily_quotes / .save_daily_quotes
- data.pipeline.run_prices_etl  — 差分 ETL 実行（対象日を指定）
- strategy.build_features(conn, target_date)
- strategy.generate_signals(conn, target_date)
- backtest.run_backtest(conn, start_date, end_date, ...)

---

## ライセンス / コントリビューション

この README はコードベースの要点をまとめたものです。実運用・公開リポジトリにする場合は LICENSE、CONTRIBUTING、詳細な設計ドキュメント（StrategyModel.md、DataPlatform.md、BacktestFramework.md 等）の追加を推奨します。

ご質問や README の追記・改善要望があれば教えてください。