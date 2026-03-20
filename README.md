# KabuSys

日本株向けの自動売買システム用ライブラリ群。データ取得・ETL、特徴量計算、戦略シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API からの市場データ／財務データ取得と DuckDB への冪等保存
- ニュース（RSS）収集と銘柄紐付け
- 価格データを元にしたファクター（Momentum / Volatility / Value 等）の計算
- 特徴量の正規化・保存（features テーブル）
- 戦略スコア計算と BUY/SELL シグナル生成（signals テーブル）
- マーケットカレンダー管理（JPX の祝日・半日・SQ 日判定）
- ETL パイプラインと品質チェック、監査ログ（発注→約定のトレーサビリティ）
- 発注層（execution）や監視（monitoring）のための土台

設計方針として、ルックアヘッドバイアス回避、API レート制御、冪等性、監査可能性を重視しています。

---

## 主な機能一覧

- 環境設定管理（.env の自動読み込み、必須環境変数チェック）
- J-Quants クライアント（認証、ページネーション、レートリミット、リトライ）
- DuckDB スキーマ定義・初期化（raw / processed / feature / execution 層）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- 特徴量計算（momentum / volatility / value 等）
- Z スコア正規化ユーティリティ
- 特徴量の構築（build_features）とシグナル生成（generate_signals）
- ニュース収集（RSS → raw_news、記事ID正規化・SSRF対策・トラッキング除去）
- マーケットカレンダー管理（営業日／SQ判定・前後営業日探索・夜間更新ジョブ）
- 監査ログスキーマ（signal_events / order_requests / executions 等）
- 実行（execution）・監視（monitoring）用の基盤（モジュール群の公開）

---

## セットアップ手順

前提:
- Python 3.10+（typing の Union 略記法や型ヒントで Path | None 等を使用）
- DuckDB を利用するため OS に合わせた Python パッケージをインストール

1. リポジトリをクローン／配置
   - この README と同階層に `src/` がある前提です。

2. 仮想環境作成・依存パッケージインストール
   例（pip を使用）:
   python -m venv .venv
   source .venv/bin/activate  # Windows は .venv\Scripts\activate
   pip install -U pip
   pip install duckdb defusedxml

   ※ ネットワーク通信や OS 固有の処理を行うため、追加の依存（requests 等）が必要になる場合は適宜追加してください。

3. 環境変数設定
   - パッケージはプロジェクトルート（.git または pyproject.toml の位置）を自動検出し、`.env` / `.env.local` を読み込みます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意（デフォルトあり）:
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - LOG_LEVEL (DEBUG/INFO/...) — default: INFO
     - DUCKDB_PATH — default: data/kabusys.duckdb
     - SQLITE_PATH — default: data/monitoring.db

   例 `.env`（プロジェクトルート）:
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=...
   SLACK_CHANNEL_ID=...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development

4. DB スキーマ初期化
   Python REPL またはスクリプトから:
   from kabusys.data.schema import init_schema, get_connection
   conn = init_schema("data/kabusys.duckdb")  # デフォルトパスを使用する場合
   conn.close()

---

## 使い方（主要 API 例）

以下は代表的なワークフローと簡単なコード例です。各関数は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。

1. DuckDB 初期化
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")

2. 日次 ETL 実行（J-Quants からの差分取得）
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())

3. 特徴量構築（feature テーブルへ保存）
   from datetime import date
   from kabusys.strategy import build_features
   count = build_features(conn, target_date=date.today())
   print(f"features upserted: {count}")

4. シグナル生成（signals テーブルへ保存）
   from datetime import date
   from kabusys.strategy import generate_signals
   n_signals = generate_signals(conn, target_date=date.today(), threshold=0.6)
   print(f"signals generated: {n_signals}")

5. ニュース収集（RSS）と保存
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   known_codes = {"7203", "6758", ...}  # あらかじめ有効銘柄コードを用意
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(results)

6. カレンダー更新ジョブ（夜間バッチ）
   from kabusys.data.calendar_management import calendar_update_job
   saved = calendar_update_job(conn)
   print(f"market_calendar saved: {saved}")

7. J-Quants から直接データを取得して DB に保存
   from kabusys.data import jquants_client as jq
   # 例: 株価を取得して保存
   records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
   saved = jq.save_daily_quotes(conn, records)

注意:
- 各保存関数は冪等（ON CONFLICT といった更新制御）になっています。
- ETL や API 呼び出しはネットワーク・外部 API に依存します。認証トークンや rate-limit に注意してください。

---

## 設定・環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション等との連携に使用するパスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live。デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...。デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動読み込みを無効化

設定はプロジェクトルートの `.env` / `.env.local` に記述することで自動読み込みされます。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                            — 環境変数／設定管理
  - data/
    - __init__.py
    - jquants_client.py                   — J-Quants API クライアント（認証・取得・保存）
    - news_collector.py                   — RSS 収集・前処理・保存
    - schema.py                           — DuckDB スキーマ定義・初期化
    - pipeline.py                         — ETL パイプライン（run_daily_etl など）
    - stats.py                            — zscore_normalize 等の統計ユーティリティ
    - features.py                         — data.stats の再エクスポート
    - calendar_management.py              — カレンダー管理／更新ジョブ
    - audit.py                            — 監査ログ（signal_events / order_requests / executions）
    - audit (続きファイルに注記)           — DDL・インデックス定義等
  - research/
    - __init__.py
    - factor_research.py                  — momentum/volatility/value 等のファクター計算
    - feature_exploration.py              — 将来リターン計算・IC・統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py              — features テーブルの構築（正規化・フィルタ）
    - signal_generator.py                 — final_score 計算と signals 生成（BUY/SELL）
  - execution/
    - __init__.py                         — 発注・ブローカー連携はここに実装予定
  - monitoring/ (パッケージ想定)          — 監視／アラート関連（今回のコード提供中には実装ファイルがない場合あり）

---

## 実装上の注意点・設計メモ

- ルックアヘッドバイアス防止: 全ての日付ベースの計算は target_date 時点で利用可能なデータのみを参照するよう設計されています。
- 冪等性: raw の保存・features・signals などは日付単位の置換や ON CONFLICT により再実行可能（idempotent）です。
- API 安全性: J-Quants クライアントはレートリミット（120 req/min）を守る、リトライ、401 の自動リフレッシュ等を備えます。
- ニュース収集: SSRF 対策、gzip 解凍上限、トラッキングパラメータ除去、記事 ID の正規化（SHA-256 先頭）等を行います。
- DuckDB: schema.init_schema() でテーブル・インデックスを一括作成します（親ディレクトリ自動作成あり）。":memory:" でインメモリ DB を利用可能。
- ロギング: settings.log_level で制御できます。production（live）環境では特に注意してログ・通知（Slack）を設定してください。

---

## 追加情報 / 今後の作業

- execution（発注層）と monitoring（監視）モジュールの具体的な実装はプロジェクトの別タスクとして追加可能です。
- 品質チェック（quality モジュール）は pipeline.run_daily_etl で利用されていますが、詳細実装に応じたカスタマイズが可能です。
- テスト用フレームワーク（ユニットテスト・統合テスト）と CI 設定の追加を推奨します。

---

もし README に含めたいサンプルスクリプト、CI 設定例、または .env.example のテンプレートを作成してほしい場合はお知らせください。必要に応じて日本語での詳細な API リファレンス（各関数の引数・戻り値解説）も作成できます。