# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（研究・データ基盤・特徴量・シグナル生成・ETL 等）。  
このリポジトリはデータ取得（J-Quants）、ETL、特徴量計算、シグナル生成、ニュース収集、DuckDB スキーマ定義などを含むモジュール群を提供します。

## 主な特徴
- J-Quants API クライアント（ページネーション / レート制限 / トークン自動リフレッシュ / 冪等保存）
- DuckDB ベースのスキーマ設計（Raw / Processed / Feature / Execution 層）
- 日次 ETL パイプライン（差分取得 / バックフィル / 品質チェック）
- 研究向けファクター計算（モメンタム / ボラティリティ / バリュー）と z-score 正規化
- 戦略用特徴量ビルド（ユニバースフィルタ・Z スコアクリップ・features テーブルへの UPSERT）
- シグナル生成（コンポーネントスコア統合、Bear レジーム抑制、BUY/SELL の冪等書き込み）
- ニュース収集（RSS 取得・前処理・SSRF/サイズ/XML安全対策・銘柄リンク付与）
- マーケットカレンダー管理（JPX カレンダーの差分取得・営業日判定ユーティリティ）
- 監査ログ設計（シグナル〜発注〜約定のトレーサビリティ）

---

## 必要条件
- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - defusedxml
  - （標準ライブラリのみで実装している部分も多いですが、実行に必要な外部依存はプロジェクトに合わせて追加してください）

pip での例:
```bash
pip install duckdb defusedxml
```

---

## 環境変数 / 設定
設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込まれます（自動ロード）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API 用パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — 通知用途（戦略やモニタリングで使用）
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

簡単な `.env.example`（プロジェクトルート）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（開発時の基本フロー）

1. レポジトリをクローンして Python 環境を準備
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt   # もし requirements.txt があれば
   pip install duckdb defusedxml
   ```

2. 環境変数を用意（`.env` をプロジェクトルートに配置）
   - 上の `.env.example` を参考に必要な値をセットしてください。

3. DuckDB スキーマを初期化
   Python REPL またはスクリプトで:
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)  # ファイルがなければ作成され、全テーブルを初期化
   ```

---

## 使い方（主な API / ワークフロー）

以下は代表的な操作フローの例です。プロダクションではジョブスケジューラ（cron / Airflow 等）で定期実行することを想定します。

1. 日次 ETL 実行（市場カレンダー、株価、財務データ、品質チェック）
   ```python
   from datetime import date
   from kabusys.config import settings
   from kabusys.data.schema import get_connection, init_schema
   from kabusys.data.pipeline import run_daily_etl

   conn = init_schema(settings.duckdb_path)
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

2. 特徴量のビルド（features テーブルを更新）
   ```python
   from datetime import date
   import duckdb
   from kabusys.config import settings
   from kabusys.strategy import build_features
   from kabusys.data.schema import get_connection

   conn = get_connection(settings.duckdb_path)
   count = build_features(conn, target_date=date.today())
   print(f"features upserted: {count}")
   ```

3. シグナル生成（signals テーブルへ書き込み）
   ```python
   from datetime import date
   from kabusys.strategy import generate_signals
   from kabusys.config import settings
   from kabusys.data.schema import get_connection

   conn = get_connection(settings.duckdb_path)
   total = generate_signals(conn, target_date=date.today(), threshold=0.6)
   print(f"signals generated: {total}")
   ```

4. ニュース収集ジョブ（RSS から raw_news へ保存し、銘柄紐付け）
   ```python
   from kabusys.data.news_collector import run_news_collection
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   known_codes = {"7203", "6758", ...}  # 実際の銘柄コードリスト
   results = run_news_collection(conn, known_codes=known_codes)
   print(results)
   ```

5. カレンダーの夜間更新ジョブ
   ```python
   from kabusys.data.calendar_management import calendar_update_job
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   saved = calendar_update_job(conn)
   print(f"market_calendar saved: {saved}")
   ```

注意:
- 上記の関数は DuckDB 接続を直接受け取ります。単体での呼び出しやテストに向いています。
- ログレベルは環境変数 `LOG_LEVEL` で制御できます。

---

## 開発者向けメモ
- 自動で .env をロードする挙動は `kabusys.config` 内で行われます。テストや一時的に無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 必須環境変数が未設定の場合、Settings のプロパティアクセスで ValueError が発生します（例: JQUANTS_REFRESH_TOKEN 等）。
- DuckDB の初期化は `init_schema(db_path)` を使って下さい。既存テーブルがあればスキップされます（冪等）。
- J-Quants クライアントはレート制限や再試行の実装があり、HTTP 401 に対してはトークンを自動でリフレッシュしてリトライします。

---

## ディレクトリ構成（抜粋）
以下は主要なモジュールの構成です（src/kabusys 以下）。

- kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定読み込み
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py        — RSS ベースのニュース収集
    - schema.py                — DuckDB スキーマ定義と初期化
    - stats.py                 — 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - features.py              — features 用公開ユーティリティ（再エクスポート）
    - calendar_management.py   — マーケットカレンダー管理
    - audit.py                 — 監査ログ用スキーマ DDL
  - research/
    - __init__.py
    - factor_research.py       — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py   — IC / 将来リターン / ファクター統計
  - strategy/
    - __init__.py
    - feature_engineering.py   — features テーブル構築（正規化・フィルタ含む）
    - signal_generator.py      — final_score 計算と signals 生成
  - execution/
    - __init__.py              — 発注層（将来的/別モジュールで実装想定）
  - monitoring/
    - (モニタリング関連モジュールを配置予定)

---

## 参考 / 備考
- ドキュメント本文中にある「StrategyModel.md」「DataPlatform.md」等は設計仕様の参照を想定しています（本リポジトリに同梱されている場合は参照してください）。
- 本ライブラリは発注機能と実際のブローカーとの連携を直接行わない（execution 層は分離）設計です。実運用時はリスク管理・監査・安全機構を十分に実装してください。
- ライブラリ内部では多くの処理において「冪等性」「ルックアヘッドバイアス防止」「エラーハンドリング（トランザクションでのROLLBACK処理等）」を考慮しています。

---

ご不明点や README に追記したい項目があれば教えてください。必要に応じてサンプル .env のテンプレートや運用例（cron / systemd unit / Airflow DAG）の雛形も作成します。