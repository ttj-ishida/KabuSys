# KabuSys

日本株向けの自動売買システム用ライブラリ（ライブラリ部分）。  
データ収集（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、監査・スキーマ管理などを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム構築を支援するための内部ライブラリ群です。主な目的は以下です。

- J-Quants API からの時系列・財務・カレンダー等のデータ取得と DuckDB への保存（冪等）
- データ品質チェック、マーケットカレンダー管理
- 研究環境で作成したファクターを正規化・統合して features テーブルに保存
- 正規化済み特徴量と AI スコアを統合して売買シグナルを生成
- RSS フィードからニュース記事を収集して raw_news へ保存し、記事 → 銘柄の紐付けを行う
- 発注／約定／ポジション等の監査ログ用スキーマを提供

設計上の重点は「ルックアヘッドバイアス回避」「冪等性」「堅牢なエラーハンドリング」「DB トランザクションによる原子性」です。

---

## 主な機能一覧

- 環境設定管理
  - .env/.env.local の自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
  - 必須環境変数チェック（Settings クラス）
- データ取得 / 保存
  - J-Quants クライアント（差分取得・ページネーション・リトライ・トークン自動リフレッシュ）
  - raw_prices / raw_financials / market_calendar の取得・保存（冪等）
- DuckDB スキーマ管理
  - init_schema() によるテーブル作成（Raw / Processed / Feature / Execution 層）
- ETL パイプライン
  - run_daily_etl(): カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック（オプション）
- 研究用 / 戦略用ユーティリティ
  - ファクター計算（momentum / volatility / value）
  - Z スコア正規化ユーティリティ
  - features の構築（build_features）
  - シグナル生成（generate_signals）: final_score 計算、BUY/SELL 判定、signals テーブルへの保存
- ニュース収集
  - RSS フィード取得（SSRF 防御、gzip 対応、XML セキュリティ）
  - raw_news 保存と news_symbols への紐付け
- カレンダー管理
  - 営業日判定 / 前後営業日取得 / 期間内営業日リスト取得
  - calendar_update_job(): 夜間バッチで JPX カレンダー更新
- 監査ログ（audit）
  - signal_events / order_requests / executions 等の監査スキーマ

---

## 必要要件（推奨）

- Python >= 3.10（PEP 604 の | 型記法を利用）
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml

（プロジェクトの requirements.txt / pyproject.toml がある場合はそちらを参照してください）

---

## セットアップ手順

1. リポジトリをクローン / コピー
   - 例: git clone <repo-url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 例（最小）:
     pip install duckdb defusedxml

   - パッケージとしてインストール可能な場合:
     pip install -e .

4. 環境変数を設定
   - プロジェクトルートに `.env`（および必要に応じて `.env.local`）を作成してください。
   - 自動ロードされる順序: OS 環境 > .env.local > .env
   - 自動ロードを無効化するには実行環境で `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   - 主要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション等の API パスワード
     - SLACK_BOT_TOKEN: Slack 通知用ボットトークン
     - SLACK_CHANNEL_ID: Slack チャンネル ID

   - 任意 / デフォルト
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（デフォルト）

5. データベース初期化（DuckDB）
   - Python REPL / スクリプトで schema.init_schema を実行:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
   - ":memory:" を指定するとインメモリ DB を使用できます（テスト等に便利）。

---

## 使い方（簡易チュートリアル）

以下は主要なユースケースのサンプルです。

- DuckDB の初期化と日次 ETL 実行

  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- 特徴量（features）構築

  from kabusys.strategy import build_features
  from datetime import date

  num = build_features(conn, target_date=date.today())
  print(f"features upserted: {num}")

- シグナル生成

  from kabusys.strategy import generate_signals
  from datetime import date

  total = generate_signals(conn, target_date=date.today(), threshold=0.6)
  print(f"signals created: {total}")

- ニュース収集ジョブ（RSS）

  from kabusys.data.news_collector import run_news_collection
  # known_codes は既知の銘柄コード集合（抽出時のフィルタ）
  stats = run_news_collection(conn, sources=None, known_codes=set(["7203","6758"]))
  print(stats)

- カレンダー更新バッチ

  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")

注意:
- これらの関数は多くが DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。
- ETL / 保存処理は冪等（ON CONFLICT）で設計されているため、複数回実行してもデータの二重登録を抑制します。
- run_daily_etl は品質チェック等で例外を捕捉して処理を継続する設計です。戻り値の ETLResult を確認してください。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (オプション、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (オプション、デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (オプション、デフォルト: data/monitoring.db)
- KABUSYS_ENV (development / paper_trading / live、デフォルト: development)
- LOG_LEVEL (INFO など)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 を設定すると .env 自動読み込みを無効化)

settings オブジェクト経由でこれらを参照できます:
from kabusys.config import settings
token = settings.jquants_refresh_token

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                        — 環境変数 / Settings 管理（.env 自動ロード含む）
- data/
  - __init__.py
  - jquants_client.py              — J-Quants API クライアント（取得 + 保存ユーティリティ）
  - pipeline.py                    — ETL パイプライン (run_daily_etl, run_prices_etl 等)
  - schema.py                      — DuckDB スキーマ定義 & init_schema
  - stats.py                       — zscore_normalize 等の統計ユーティリティ
  - features.py                    — data.stats の再エクスポート
  - news_collector.py              — RSS 取得・前処理・保存・銘柄抽出
  - calendar_management.py         — market_calendar 管理・営業日判定
  - audit.py                       — 監査ログスキーマ定義
  - pipeline.py                    — ETL の差分更新ロジック（上記）
- research/
  - __init__.py
  - factor_research.py             — momentum / volatility / value の計算
  - feature_exploration.py         — 将来リターン / IC / 統計サマリー
- strategy/
  - __init__.py
  - feature_engineering.py         — features の作成（正規化・フィルタ）
  - signal_generator.py            — final_score 計算、BUY/SELL シグナル生成
- execution/                        — 発注・execution 層（パッケージプレースホルダ）
- monitoring/                       — 監視系（プレースホルダ）

（README に掲載の構成はコードベースの抜粋に基づいています）

---

## 追加の注意点 / 実運用向け考慮事項

- セキュリティ
  - RSS 取得で SSRF 対策や XML の安全なパース（defusedxml）を導入済み
  - J-Quants 認証トークンは環境変数で管理してください
- データ整合性
  - DuckDB のトランザクション（BEGIN/COMMIT/ROLLBACK）を多用して原子性を担保
- ロギング / モニタリング
  - LOG_LEVEL と KABUSYS_ENV により挙動が変わります（is_live / is_paper / is_dev）
- テスト
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を使って環境の自動ロードを無効化し、テスト用の環境を注入すると便利です
- Python バージョン
  - 型注釈や union 型（X | None）に依存しているため Python >= 3.10 を推奨します

---

## 開発に参加するには

- コードのスタイルとテストを整備してください（プロジェクトに合わせた linters / formatters を導入推奨）
- 追加の外部依存は pyproject.toml / requirements.txt に明記してください
- 大きな設計変更は README と DataPlatform.md / StrategyModel.md 等の設計ドキュメントも更新してください

---

README に含めるべき補足や、サンプルスクリプト（cron ジョブ用、デプロイ手順、CI 設定など）を希望される場合は用途に合わせたテンプレートを作成します。どの例が必要か教えてください。