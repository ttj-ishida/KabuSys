# KabuSys

KabuSys は日本株向けの自動売買システム用ライブラリです。データ取得（J-Quants）、ETL、特徴量エンジニアリング、シグナル生成、バックテストおよびポートフォリオシミュレーションをワンパッケージで提供します。

バージョン: 0.1.0

---

## 概要

主な目的は「ルックアヘッドバイアスを避けつつ、再現性のある量的売買パイプライン」を提供することです。  
設計方針の例:

- データ取得時に取得時刻（fetched_at）を記録していつデータが利用可能になったかトレース可能にする
- DuckDB をデータストアとし、スキーマを一括初期化できる
- ETL は冪等（duplicate-safe）に実装
- 研究用（research）と運用用（strategy/execution/backtest）が分離されている

---

## 機能一覧

- データ取得 / 保存
  - J-Quants API クライアント（株価、財務、マーケットカレンダー）
  - raw_prices / raw_financials / market_calendar への保存（冪等）
- ETL パイプライン
  - 差分取得、バックフィル、品質チェック（品質チェックモジュールは別に存在）
- ニュース収集
  - RSS フィードの収集、前処理、raw_news 保存、銘柄コード抽出
  - SSRF 対策、gzip/サイズ検査、XML デコーダ保護等を実装
- 研究（research）
  - ファクター計算（momentum, volatility, value 等）
  - 将来リターン、IC（Spearman）、統計サマリ等のユーティリティ
- 特徴量エンジニアリング
  - 研究で得た生ファクターを正規化（Z スコア）し features テーブルへ UPSERT
- シグナル生成
  - features + ai_scores を統合して final_score を計算し BUY / SELL シグナルを生成
  - Bear 相場の抑制、SELL の優先処理（ポジション保護ロジック）
- バックテスト
  - ポートフォリオシミュレータ（スリッページ、手数料モデル）
  - 日次ループで generate_signals を呼び出すフレームワーク
  - 評価指標（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio）
- スキーマ管理
  - DuckDB 用のスキーマ初期化（init_schema）と接続取得ユーティリティ

---

## 前提 / 必要環境

- Python 3.10 以上（| 型注釈、match 等を使わないが union 演算子 `|` を使用）
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml
- ネットワーク通信を行うため適切な環境変数（API トークン等）が必要

※実プロジェクトでは追加パッケージ（ログ収集、Slack 通知、テストフレームワーク等）が必要になる可能性があります。

---

## セットアップ手順（ローカル）

1. リポジトリをクローンし仮想環境を作成
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール（例）
   ```bash
   pip install -U pip
   pip install duckdb defusedxml
   # 開発時: pip install -e .
   ```

3. DuckDB スキーマの初期化
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ディレクトリは自動作成されます
   conn.close()
   ```

4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可）。
   - 必須の環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API パスワード（execution 層）
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack チャネル ID
   - 任意/デフォルト
     - DUCKDB_PATH （デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH （デフォルト: data/monitoring.db）
     - KABUSYS_ENV （development | paper_trading | live。デフォルト: development）
     - LOG_LEVEL （DEBUG | INFO | ...。デフォルト: INFO）

   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（主なユースケース）

以下では主要なモジュールの簡単な使い方を示します。

1. データベースの初期化
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

2. J-Quants から株価を取得して保存（取得 → 保存）
   ```python
   from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

   records = fetch_daily_quotes(date_from=..., date_to=...)
   saved = save_daily_quotes(conn, records)
   ```

3. ニュース収集ジョブ（RSS）
   ```python
   from kabusys.data.news_collector import run_news_collection

   # known_codes: 銘柄コードのセットを渡すと記事に含まれる4桁コードを紐付けます
   results = run_news_collection(conn, sources=None, known_codes=set(["7203","6758"]))
   ```

4. 特徴量作成（features テーブルへ書き込み）
   ```python
   from kabusys.strategy import build_features
   from datetime import date

   n = build_features(conn, target_date=date(2024, 3, 15))
   print(f"built features for {n} symbols")
   ```

5. シグナル生成
   ```python
   from kabusys.strategy import generate_signals
   from datetime import date

   total_signals = generate_signals(conn, target_date=date(2024, 3, 15), threshold=0.6)
   print(f"generated {total_signals} signals")
   ```

6. バックテスト（CLI）
   - モジュール化された CLI エントリポイントが提供されています。
   ```bash
   python -m kabusys.backtest.run \
       --start 2023-01-01 --end 2024-12-31 \
       --cash 10000000 \
       --db data/kabusys.duckdb
   ```
   - 主要オプション:
     - --start / --end : バックテスト期間
     - --cash : 初期資金（円）
     - --slippage / --commission : スリッページ・手数料率
     - --max-position-pct : 1 銘柄あたりの最大比率
     - --db : DuckDB ファイルパス（必須）

7. バックテストを Python API から実行
   ```python
   from datetime import date
   from kabusys.backtest.engine import run_backtest
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
   print(result.metrics)
   conn.close()
   ```

---

## 重要な設計上の注意点

- ルックアヘッドバイアス対策: features / signals / ai_scores 等は target_date 時点で利用可能な情報のみを使うように実装されています。
- 冪等性: データ保存は ON CONFLICT / DO UPDATE 等で重複を上書きし、再実行可能な ETL を目指しています。
- ロギングと環境判定: KABUSYS_ENV（development, paper_trading, live）で挙動を切り替えられます。log level は LOG_LEVEL 環境変数で制御します。
- 自動 .env ロード: パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して `.env` / `.env.local` を自動読み込みします。無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（抜粋）

以下はこのリポジトリの主要なファイル・モジュール構成（src/kabusys 内）です。

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - data/
    - __init__.py
    - schema.py                    — DuckDB スキーマ定義 & init_schema()
    - jquants_client.py            — J-Quants API クライアント + 保存関数
    - news_collector.py            — RSS 収集・raw_news 保存・銘柄抽出
    - pipeline.py                  — ETL パイプライン（差分取得 等）
    - stats.py                     — zscore_normalize 等ユーティリティ
  - research/
    - __init__.py
    - factor_research.py           — momentum / volatility / value 計算
    - feature_exploration.py       — forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py       — features 作成（正規化・フィルタ）
    - signal_generator.py          — final_score 計算 & signals 書き込み
  - backtest/
    - __init__.py
    - engine.py                    — run_backtest の実装
    - simulator.py                 — PortfolioSimulator（約定ロジック）
    - metrics.py                   — バックテスト指標計算
    - run.py                       — CLI エントリポイント
    - clock.py                     — SimulatedClock（将来用途）
  - execution/                      — 発注周り（現状はパッケージ用のプレースホルダ）
  - monitoring/                     — 監視系（DB sqlite 等を想定）

---

## 追加メモ / 推奨事項

- DuckDB のファイルはバックアップ・バージョン管理の対象から除外してください（大きくなるため）。
- 実運用（live）では KABUSYS_ENV を `live` にし、Slack 等での監視通知を有効にしてください。
- API トークンは安全な秘匿保管（Vault 等）を検討してください。`.env` を使う場合もリポジトリに含めないこと。
- tests、CI、依存固定（requirements.txt / poetry）があればそれに従ってください。

---

この README はコードベースの主要機能と典型的な使い方を簡潔にまとめたものです。必要に応じて各モジュール（例: jquants_client, news_collector, backtest.engine）内の docstring を参照してください。質問や追記したい項目があれば教えてください。