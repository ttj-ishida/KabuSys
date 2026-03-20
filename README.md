# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
市場データの取得（J-Quants）、DuckDB によるデータ永続化、特徴量計算、シグナル生成、ニュース収集、カレンダー管理、ETL パイプラインなどをモジュール化して提供します。

---

## 目次
- プロジェクト概要
- 機能一覧
- 要求環境 / 依存ライブラリ
- セットアップ手順
- 環境変数（主要）
- 使い方（基本例）
  - DB 初期化
  - 日次 ETL 実行
  - 特徴量構築 / シグナル生成
  - ニュース収集
  - 研究ユーティリティ
- ディレクトリ構成

---

## プロジェクト概要
KabuSys は日本株向けのデータプラットフォームと戦略層を含むライブラリ群です。主な目的は以下です。

- J-Quants API から市場データ・財務データ・マーケットカレンダーを取得して DuckDB に保存
- 生データ → 加工データ → 特徴量 → シグナル → 発注 というレイヤ設計
- 研究（research）向けのファクター計算・評価ユーティリティ（ルックアヘッドバイアス対策あり）
- ニュースの RSS 収集と銘柄紐付け
- ETL の差分更新・品質チェック・トレース可能な監査ログ構造

---

## 機能一覧
- データ取得 / 永続化
  - J-Quants から日足（OHLCV）、財務、マーケットカレンダーを取得（ページネーション / レートリミット対応）
  - DuckDB スキーマ定義と初期化（冪等）
- ETL パイプライン
  - 差分取得・バックフィル・品質チェックを備えた日次 ETL
- 特徴量（feature）計算
  - モメンタム・ボラティリティ・バリュー等のファクター計算
  - Z スコア正規化・ユニバースフィルタ適用・features テーブルへの保存
- シグナル生成
  - 特徴量 + AI スコアを統合し final_score を算出、BUY/SELL シグナルを生成して signals テーブルへ保存
  - Bear レジーム抑制、エグジット判定（ストップロス等）
- ニュース収集
  - RSS フィード取得（SSRF 対策、XML セキュリティ、サイズ制限）
  - raw_news / news_symbols テーブルへの冪等保存
- カレンダー管理
  - market_calendar を利用した営業日判定 / next/prev_trading_day / get_trading_days 等
- 研究用ユーティリティ
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリなど

---

## 要求環境 / 依存ライブラリ
- Python 3.10+
- 必要な（主な）パッケージ:
  - duckdb
  - defusedxml
- コードは標準ライブラリの urllib 等を利用しており、requests に依存しない実装です。

pip でインストールする際は上記パッケージをインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（任意だが推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   ```
   pip install duckdb defusedxml
   ```

   （プロジェクトをパッケージとして扱う場合）
   ```
   pip install -e .
   ```

4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置いて環境変数を設定できます。
   - 自動ロードはデフォルトで有効（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化）。

   主要な環境変数（必須）
   - JQUANTS_REFRESH_TOKEN — J-Quants の refresh token（必須）
   - KABU_API_PASSWORD — kabu API パスワード（必須）
   - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID — Slack チャネル ID（必須）

   任意 / デフォルトあり
   - KABUSYS_ENV — 実行環境: development / paper_trading / live （デフォルト: development）
   - LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（`1`）

   DB パス（デフォルト値）
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)

---

## 使い方（基本例）

以下は Python REPL やスクリプトからの利用例です。各例は簡略化してあります。

- DB 初期化（DuckDB スキーマ作成）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)  # ファイルが無ければ作成しスキーマを初期化
  ```

- 日次 ETL 実行
  ```python
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # target_date を指定しなければ本日扱い
  print(result.to_dict())
  ```

- 特徴量構築（features テーブルに保存）
  ```python
  from datetime import date
  import duckdb
  from kabusys.strategy import build_features
  from kabusys.config import settings

  conn = duckdb.connect(settings.duckdb_path.__str__())
  n = build_features(conn, date(2025, 3, 1))
  print(f"upserted features: {n}")
  ```

- シグナル生成
  ```python
  from datetime import date
  import duckdb
  from kabusys.strategy import generate_signals
  from kabusys.config import settings

  conn = duckdb.connect(settings.duckdb_path.__str__())
  total = generate_signals(conn, date(2025, 3, 1))
  print(f"signals written: {total}")
  ```

- ニュース収集（RSS）
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  known_codes = {"7203", "6758", "9984"}  # 有効銘柄コードセット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- 研究用ユーティリティ（将来リターン・IC）
  ```python
  from kabusys.research import calc_forward_returns, calc_ic, rank
  # DuckDB 接続とファクターレコード等を用意し、calc_forward_returns / calc_ic を呼ぶ
  ```

- J-Quants API 直接利用（トークン取得・fetch）
  ```python
  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
  token = get_id_token()  # settings.jquants_refresh_token を使用
  records = fetch_daily_quotes(id_token=token, date_from=date(2025,1,1), date_to=date(2025,1,31))
  ```

注意：
- すべての日付関連処理はルックアヘッドバイアスを避けるため「target_date 時点までのデータのみ」を参照する設計になっています。
- 各種保存関数（save_*）は冪等に設計されており、ON CONFLICT による上書きを行います。

---

## 設定・動作に関する補足

- 自動環境変数ロード
  - パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して `.env` / `.env.local` を読み込みます。テスト時などに無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 環境変数検証
  - Settings クラスは一部の必須変数が設定されていないと ValueError を送出します（例: JQUANTS_REFRESH_TOKEN）。
- ログレベル
  - `LOG_LEVEL` 環境変数で調整できます（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
- 実行モード
  - `KABUSYS_ENV` は `development` / `paper_trading` / `live` のいずれかを指定します。`is_live` / `is_paper` / `is_dev` で判定できます。

---

## ディレクトリ構成（主要ファイル）
以下はこの README 作成時点での主要モジュール一覧（src/kabusys 以下）です。

- kabusys/
  - __init__.py
  - config.py                         — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント（取得・保存）
    - news_collector.py               — RSS 収集・前処理・DB 保存
    - schema.py                       — DuckDB スキーマ定義・初期化
    - stats.py                        — 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py                     — ETL パイプライン（run_daily_etl 等）
    - features.py                     — features の薄い再エクスポート
    - calendar_management.py          — マーケットカレンダー管理
    - audit.py                        — 監査ログ（signal_events / order_requests / executions）
  - research/
    - __init__.py
    - factor_research.py              — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py          — 将来リターン / IC / 統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py          — features 作成 (build_features)
    - signal_generator.py             — シグナル生成 (generate_signals)
  - execution/                         — 発注・execution 層（空のパッケージプレースホルダ）
  - monitoring/                        — 監視・モニタリング用（プレースホルダ）

---

## 開発 / 貢献
- コードの設計方針や仕様は各モジュールの docstring / コメントに詳述しています（例: StrategyModel.md / DataPlatform.md 等参照箇所あり）。
- 新しい機能追加や修正は、既存のルックアヘッドバイアス対策・冪等性・トレーサビリティ方針を尊重してください。

---

補足や追加のドキュメント（操作スクリプト例、運用手順、.env.example 等）が必要であればご要望ください。