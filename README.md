# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（プロトタイプ）
バッチでのデータ取得（J-Quants）、DuckDB によるデータレイク管理、特徴量作成、シグナル生成、
ニュース収集、監査ログなどの基盤機能を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのデータ・戦略基盤を提供する Python パッケージです。
主な目的は以下です。

- J-Quants API から株価・財務・マーケットカレンダーを差分取得して DuckDB に保存
- 生データ → 整形データ → 戦略用特徴量（features）までの ETL パイプライン
- 特徴量正規化・シグナル生成ロジック（ルックアヘッドバイアスに配慮）
- RSS からニュースを収集して記事保存および銘柄抽出
- 発注監査ログ・トレーサビリティ用テーブル定義
- DuckDB スキーマの初期化ユーティリティ

設計方針の要点:
- ルックアヘッドバイアスを避ける（target_date 時点のデータのみ参照）
- DuckDB を中心とした冪等的なデータ保存（ON CONFLICT 等）
- 外部 API 呼び出しに対するレート制御・再試行・トークン自動刷新などの保護機構
- 本番システムへ直接発注する層（execution）は独立しており、戦略モジュールは発注層に依存しない

---

## 主な機能一覧

- データ取得／保存
  - J-Quants クライアント（株価、財務、カレンダー取得、保存用ユーティリティ）
  - 差分 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - DuckDB スキーマ初期化（init_schema）

- データ品質／ユーティリティ
  - 統計ユーティリティ（zscore_normalize 等）
  - カレンダー管理（営業日判定、next/prev_trading_day、calendar_update_job）

- 研究・特徴量
  - factor_research: momentum / volatility / value 等のファクター計算
  - feature_engineering: 正規化・ユニバースフィルタを適用して features テーブルに保存

- 戦略
  - signal_generator: features と ai_scores を統合して BUY/SELL シグナルを作成・保存

- ニュース収集
  - RSS フェッチ、記事前処理、raw_news への冪等保存、銘柄抽出と紐付け

- 監査・実行ログ
  - audit テーブル群（signal_events / order_requests / executions 等）定義

---

## 要件（想定）

少なくとも以下のライブラリが必要です（実際の requirements はプロジェクトの配布パッケージに依存します）:

- Python 3.10+
- duckdb
- defusedxml

その他、J-Quants API、kabuステーション API（発注）、Slack など外部サービスの認証情報が必要になります。

---

## 環境変数 / .env

KabuSys は .env（および .env.local）から環境変数を自動読み込みします（プロジェクトルートに `.git` または `pyproject.toml` がある場合）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主に必要な環境変数（例）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API の base URL（デフォルト "http://localhost:18080/kabusapi"）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト `data/monitoring.db`）
- KABUSYS_ENV: 環境 ("development" / "paper_trading" / "live")（デフォルト development）
- LOG_LEVEL: ログレベル ("DEBUG"/"INFO"/...、デフォルト INFO)

例（.env）:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

必須変数が設定されていない場合、kabusys.config.Settings のプロパティ参照時に ValueError が発生します。

---

## セットアップ手順（開発ローカル）

1. 仮想環境作成 / 有効化

   ```
   python -m venv .venv
   source .venv/bin/activate    # macOS / Linux
   .venv\Scripts\activate       # Windows (PowerShell)
   ```

2. 依存ライブラリをインストール

   （requirements.txt がある場合はそれを使う。ここでは代表例）

   ```
   pip install duckdb defusedxml
   ```

3. パッケージをインストール（編集可能モード）

   ```
   pip install -e .
   ```

4. プロジェクトルートに `.env` を作成し、必要な環境変数を設定

5. DuckDB スキーマ初期化

   Python REPL またはスクリプトで初期化します:

   ```python
   from kabusys.data.schema import init_schema, get_connection
   conn = init_schema("data/kabusys.duckdb")  # ファイル作成・テーブル作成
   # またはメモリ DB（テスト用）
   # conn = init_schema(":memory:")
   ```

---

## 使い方（主要な操作例）

以下は主要なユースケースの簡単なコード例です。

- 日次 ETL を実行（株価 / 財務 / カレンダー取得 + 品質チェック）

  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量の構築（features テーブルへ書き込む）

  ```python
  from datetime import date
  from kabusys.data.schema import get_connection, init_schema
  from kabusys.strategy import build_features

  conn = init_schema("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2025, 1, 15))
  print(f"features upserted: {n}")
  ```

- シグナル生成（signals テーブルへ書き込む）

  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.strategy import generate_signals

  conn = init_schema("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2025, 1, 15))
  print(f"signals created: {total}")
  ```

- RSS ニュース取得と保存

  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = init_schema("data/kabusys.duckdb")
  # known_codes は既知の銘柄コード集合（抽出用）
  known_codes = {"7203", "6758", "9432"}
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- カレンダーの夜間更新ジョブ

  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.calendar_management import calendar_update_job

  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"market calendar saved: {saved}")
  ```

---

## 運用ノート / 推奨

- 自動化: 日次 ETL・特徴量構築・シグナル生成を CI / cron / ワークフローツールでスケジュールする。
- 環境切替: KABUSYS_ENV を `development` / `paper_trading` / `live` に設定して環境ごとの挙動を区別。
- 機密情報: .env.local を用いてローカル上の機密情報を管理し、`.env.local` は gitignore に追加することを推奨。
- エラー処理: ETL はステップ毎にエラーを捕捉して処理を継続する設計（呼び出し元で結果を確認して対処）。
- レート制御: J-Quants クライアントは API レート制限に対応（120 req/min）しているが、運用上もリトライやレートの観察を行ってください。

---

## ディレクトリ構成（主要ファイル）

以下は `src/kabusys/` 以下の主なモジュールと簡単な説明です。

- kabusys/
  - __init__.py (パッケージ定義, __version__ = "0.1.0")
  - config.py
    - 環境変数読み込みと Settings クラス
  - data/
    - __init__.py
    - jquants_client.py : J-Quants API クライアント・保存ユーティリティ
    - news_collector.py : RSS 収集・前処理・保存・銘柄抽出
    - schema.py : DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py : ETL の差分処理・run_daily_etl 等
    - calendar_management.py : market_calendar 管理・営業日ロジック
    - features.py : zscore_normalize の再エクスポート
    - stats.py : zscore_normalize 等の統計ユーティリティ
    - audit.py : 監査ログ用テーブル定義
    - (その他: quality モジュール想定 — 品質チェック関連)
  - research/
    - __init__.py
    - factor_research.py : momentum / volatility / value の計算
    - feature_exploration.py : 将来リターン計算、IC、統計サマリー
  - strategy/
    - __init__.py (build_features, generate_signals を公開)
    - feature_engineering.py : feature 作成パイプライン
    - signal_generator.py : final_score 計算と signals への保存
  - execution/
    - __init__.py (発注周りの層はここに配置想定)
  - monitoring/ (モニタリング用コード想定)

実際のリポジトリは上述ファイル群が src/kabusys 配下に存在します。

---

## 開発・貢献

- コードはモジュール単位で分離されており、ユニットテストを容易に作成できます（DuckDB の :memory: 接続を活用）。
- 環境変数の自動ロードをテストで無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 新機能追加時はスキーマ変更の互換性（既存データの扱い）と ETL の冪等性を維持することに注意してください。

---

以上が README の概要です。README に追記したい実行スクリプト例や、requirements.txt / Dockerfile / systemd ユニットのテンプレートが必要であれば、用途に合わせて追加例を作成します。必要であれば、各モジュールの詳細（関数シグネチャ、返り値の仕様）も目次式に展開できます。どの追加情報をご希望ですか？