# KabuSys

日本株向けの自動売買／データプラットフォームのライブラリ群です。  
このリポジトリはデータ収集（J‑Quants 等）→ ETL → 特徴量生成 → シグナル生成 → 発注（Execution 層）までを想定したモジュール群を備えています。研究（research）用のファクター計算やニュース収集、監査ログ／スキーマ管理などの機能を含みます。

バージョン: 0.1.0

---

## 主な機能（機能一覧）

- 環境設定管理
  - .env / .env.local 自動読み込み（優先順: OS 環境変数 > .env.local > .env）
  - 必須パラメータの検証（settings オブジェクト）
- データ取得（J‑Quants クライアント）
  - 株価日足（OHLCV）、財務諸表、マーケットカレンダーのフェッチ（ページネーション、リトライ、レート制限、トークン自動リフレッシュ）
  - DuckDB への冪等保存（ON CONFLICT 対応）
- ETL（差分更新／バックフィル）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - 品質チェックフック（quality モジュールと連携）
- マーケットカレンダー管理
  - 営業日判定、次/前営業日取得、期間内営業日取得、カレンダーの夜間更新ジョブ
- ニュース収集
  - RSS 取得（SSRF 対策、gzip 制限、XML サニタイズ defusedxml）、記事正規化、記事ID生成（URL 正規化 + SHA256）
  - raw_news / news_symbols への冪等保存
- 研究用ファクター計算
  - momentum / volatility / value 等のファクター計算（prices_daily / raw_financials を参照）
  - forward return / IC / 統計サマリなどのユーティリティ
- 特徴量作成 & シグナル生成（戦略）
  - features テーブルへの正規化・UPSERT（Zスコア正規化、ユニバースフィルタ）
  - features と ai_scores を統合した final_score 計算、BUY/SELL シグナル生成（エグジット判定含む）
- スキーマ管理
  - DuckDB 用のスキーマ初期化関数（init_schema）
  - テーブル群（Raw / Processed / Feature / Execution / Audit）を定義

---

## 前提条件

- Python 3.10 以上（| 型ヒントなどを使用）
- 推奨パッケージ（最低限）:
  - duckdb
  - defusedxml

実運用では追加で HTTP 等の環境依存パッケージが必要になることがあります。requirements.txt は本リポジトリに含まれていないため、プロジェクト用途に応じて必要パッケージをインストールしてください。

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成／有効化

   - Unix/macOS:
     ```
     git clone <repo-url>
     cd <repo-root>
     python -m venv .venv
     source .venv/bin/activate
     ```

   - Windows (PowerShell):
     ```
     git clone <repo-url>
     cd <repo-root>
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

2. 必要パッケージをインストール（例）
   ```
   pip install duckdb defusedxml
   ```

   実運用で J‑Quants や Slack、ネットワーク等を使う場合はそれらに必要な追加パッケージをインストールしてください。

3. パッケージを編集モードでインストール（任意）
   ```
   pip install -e src
   ```

4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（CWD に依存せずパッケージ位置からプロジェクトルートを検出）。
   - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必要な主要環境変数（例）
- JQUANTS_REFRESH_TOKEN — J‑Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション等の API パスワード（必須）
- KABU_API_BASE_URL — kabu API のベースURL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack ボットトークン（必須）
- SLACK_CHANNEL_ID — Slack チャネルID（必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG"/"INFO"/...（デフォルト: INFO）

---

## 使い方（主要フロー例）

以下はライブラリ関数を直接呼ぶ手順例です。実運用ではこれらをラッパー CLI やジョブスケジューラ（cron / Airflow / etc.）から呼び出します。

1. DuckDB スキーマの初期化
   ```python
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")  # data ディレクトリは自動で作成されます
   ```

   既存スキーマがある場合はスキップされるため安全に何度でも実行できます。

2. 日次 ETL（市場カレンダー・株価・財務の差分取得と品質チェック）
   ```python
   from kabusys.data.pipeline import run_daily_etl
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   result = run_daily_etl(conn)  # target_date を渡すことで任意日を処理できます
   print(result.to_dict())
   ```

3. 特徴量の構築（features テーブル作成）
   ```python
   from kabusys.strategy import build_features
   from kabusys.data.schema import get_connection
   from datetime import date

   conn = get_connection("data/kabusys.duckdb")
   n = build_features(conn, target_date=date.today())
   print(f"features 作成数: {n}")
   ```

4. シグナル生成
   ```python
   from kabusys.strategy import generate_signals
   from kabusys.data.schema import get_connection
   from datetime import date

   conn = get_connection("data/kabusys.duckdb")
   total = generate_signals(conn, target_date=date.today())
   print(f"signals 書き込み数: {total}")
   ```

5. ニュース収集（RSS）ジョブ
   ```python
   from kabusys.data.news_collector import run_news_collection
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   # sources を渡さなければデフォルトの RSS ソースを使用
   # known_codes は銘柄コード抽出に使う有効コード集合（None で抽出スキップ）
   results = run_news_collection(conn, sources=None, known_codes=None)
   print(results)  # {source_name: 新規保存数}
   ```

6. マーケットカレンダー夜間更新ジョブ
   ```python
   from kabusys.data.calendar_management import calendar_update_job
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   saved = calendar_update_job(conn)
   print(f"calendar 更新保存数: {saved}")
   ```

注意: run_daily_etl や fetch API は J‑Quants の認証トークンやネットワークを必要とします。settings から自動でトークンを参照するため、必ず環境変数を適切に設定してください。

---

## 設定（settings）について

- settings オブジェクトは `kabusys.config.settings` から参照します。
- .env のパースはシェル形式に近い仕様（export対応、クォート対応、インラインコメント処理など）をサポートしています。
- 自動ロード順序:
  - OS 環境変数（既にセットされているものは .env/.env.local で上書きされない）
  - .env（プロジェクトルート）
  - .env.local（.env を上書き）
- 自動ロードを無効化する:
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を環境変数に設定

必須環境変数を取得するプロパティは自動的に ValueError を投げるため、起動前に .env を整備してください。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要構成（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py — J‑Quants API クライアント（取得・保存）
    - news_collector.py — RSS 収集・正規化・保存
    - schema.py — DuckDB スキーマ定義と init_schema / get_connection
    - stats.py — zscore_normalize 等統計ユーティリティ
    - pipeline.py — ETL パイプライン（差分取得、run_daily_etl など）
    - calendar_management.py — マーケットカレンダー管理／ジョブ
    - audit.py — 監査ログ用スキーマ（signal_events / order_requests / executions 等）
    - features.py — データ側公開インターフェース（zscore_normalize の再エクスポート）
  - research/
    - __init__.py
    - factor_research.py — momentum / volatility / value の計算
    - feature_exploration.py — forward returns / IC / factor_summary 等
  - strategy/
    - __init__.py
    - feature_engineering.py — features 作成（正規化・ユニバースフィルタ）
    - signal_generator.py — features + ai_scores 統合 → signals 生成
  - execution/ — 発注関連（未実装ファイル群のエントリ領域）
  - monitoring/ — 監視・モニタリング関連（エントリ領域）

各モジュールは「DB 接続を受け取る」「発注 API など外部副作用に依存しない」といった設計方針に沿って実装されています。DB 操作は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取る形です。

---

## ログと運用上の注意

- ログレベルは環境変数 `LOG_LEVEL` で制御します（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
- ETL・API 呼び出しにはリトライ／バックオフ／レート制限が組み込まれていますが、API キーの管理や実行頻度は運用ルールに従ってください。
- DuckDB スキーマは冪等に作成されますが、運用中のマイグレーションは慎重に行ってください（バックアップ推奨）。
- ニュース収集では SSRF・XML Bomb・大容量レスポンス対策を実装していますが、追加のセキュリティ対策（ネットワーク ACL、プロキシ設定等）も検討してください。

---

この README は実装済みのソースコードに基づいた概要・使い方のサマリです。詳細な設計（StrategyModel.md / DataPlatform.md / Research ドキュメントなど）が別途ある想定のため、戦略パラメータの調整や運用フローはそれらを参照してください。質問やドキュメント追加の要望があれば教えてください。