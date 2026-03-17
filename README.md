# KabuSys README

KabuSys は日本株のデータ収集・品質管理・ETL・監査ログを備えた自動売買基盤のコアライブラリです。J-Quants や RSS を用いて市場データ・財務データ・ニュースを取得し、DuckDB に階層化されたスキーマで格納します。戦略・注文実行・モニタリング層と組み合わせて自動売買ワークフローを構築できます。

## 主要機能
- J-Quants API クライアント
  - 日足（OHLCV）、四半期財務データ、JPX マーケットカレンダー取得
  - レート制限（120 req/min）、リトライ、トークン自動リフレッシュ、ページネーション対応
  - 取得時刻（fetched_at）を UTC で記録
- DuckDB ベースのデータスキーマ
  - Raw / Processed / Feature / Execution / Audit 層を想定したテーブル定義
  - 冪等性を考慮した保存（ON CONFLICT 句など）
- ETL パイプライン
  - 差分取得（最終取得日からの差分 + バックフィル）
  - カレンダーの先読み（lookahead）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）
  - RSS 取得、XML パース（defusedxml 使用）、URL 正規化、記事ID は SHA-256 ハッシュ
  - SSRF 防御、受信サイズ上限、Gzip 対応、DB への冪等保存
  - 銘柄コード抽出と news_symbols への紐付け
- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定 のトレーサビリティテーブル群
  - UUID ベースの冪等キー、UTC タイムスタンプ管理

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈で | を使用しているため）
- DuckDB を使用するためネイティブライブラリが必要（pip でインストールされます）

1. リポジトリをクローンしてインストール（開発モード）
   ```
   git clone <repo-url>
   cd <repo-root>
   pip install -e .
   ```
   必要なパッケージがある場合は requirements.txt があればその内容を pip でインストールしてください。主な依存例:
   ```
   pip install duckdb defusedxml
   ```

2. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（`src/kabusys/config.py` の自動ロード機能）。
   - 自動ロードはルートディレクトリを `.git` または `pyproject.toml` で検出します。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   重要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - DUCKDB_PATH: デフォルトデータベースパス（例: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（例: data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

   .env の例（プロジェクトルート）
   ```
   JQUANTS_REFRESH_TOKEN=xxx
   KABU_API_PASSWORD=yyy
   SLACK_BOT_TOKEN=zzz
   SLACK_CHANNEL_ID=C123456
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

3. データベース初期化（DuckDB）
   - スキーマ初期化関数を利用して DuckDB ファイルを作成・テーブルを作成します。

   例:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

4. 監査ログテーブル（Audit）を追加する場合
   - 既存の DuckDB 接続に監査テーブルを追加:
   ```python
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn)  # conn は init_schema の戻り値
   ```

---

## 使い方（簡単な例）

1. 日次 ETL を実行する
   ```python
   from datetime import date
   from kabusys.data.schema import init_schema
   from kabusys.data.pipeline import run_daily_etl

   conn = init_schema("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

   run_daily_etl はカレンダー取得 → 株価 ETL → 財務 ETL → 品質チェック の順に実行し、ETLResult を返します。

2. ニュース収集ジョブを実行する
   ```python
   from kabusys.data.schema import init_schema, get_connection
   from kabusys.data.news_collector import run_news_collection

   conn = init_schema("data/kabusys.duckdb")
   # known_codes があれば銘柄抽出と紐付けを実行（省略可）
   known_codes = {"7203", "6758", "9984"}
   results = run_news_collection(conn, known_codes=known_codes)
   print(results)  # {source_name: saved_count, ...}
   ```

3. 市場カレンダーの夜間更新ジョブ
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.data.calendar_management import calendar_update_job

   conn = init_schema("data/kabusys.duckdb")
   saved = calendar_update_job(conn)
   print("saved:", saved)
   ```

4. J-Quants から直接データを取得して保存する（テスト用）
   ```python
   from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes, save_daily_quotes
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   token = get_id_token()  # settings.jquants_refresh_token を使用
   records = fetch_daily_quotes(id_token=token, date_from=None, date_to=None)
   saved = save_daily_quotes(conn, records)
   ```

注意点:
- jquants_client は内部でレート制限・リトライ・トークン再取得を行います。大量のリクエストを行う際はこれらの設計方針を尊重してください。
- news_collector は SSRF 対策・受信サイズ制限・XML パースの安全化を実装しています。実運用で RSS ソースを追加する際は URL 検証に注意してください。

---

## ディレクトリ構成（主要ファイル）
プロジェクトの主要なモジュールと役割を簡潔に示します。

- src/kabusys/
  - __init__.py  -- パッケージ定義（version, export）
  - config.py    -- 環境変数 / 設定の読み込みと validation（自動 .env ロード、Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント・保存ロジック
    - news_collector.py      -- RSS ニュース収集、前処理、保存、銘柄抽出
    - schema.py              -- DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py            -- ETL パイプライン（差分取得 / 品質チェック統合）
    - calendar_management.py -- 市場カレンダー管理（営業日判定、更新ジョブ）
    - audit.py               -- 監査ログ（signal/order/execution テーブル群）
    - quality.py             -- データ品質チェック（欠損/重複/スパイク/日付不整合）
  - strategy/
    - __init__.py (戦略関連のプレースホルダ)
  - execution/
    - __init__.py (発注/ブローカー連携のプレースホルダ)
  - monitoring/
    - __init__.py (モニタリング関連のプレースホルダ)

---

## 実運用の考慮点
- 環境切替:
  - KABUSYS_ENV により development / paper_trading / live を切替。settings.is_live / is_paper / is_dev を使用可能。
- セキュリティ:
  - .env ファイルは機密情報を含むためアクセス制御を厳格に行ってください。
  - news_collector は SSRF・XML Bomb・Gzip Bomb 対策を実装していますが、追加のネットワーク制限（プロキシや egress 制御）を推奨します。
- テスト容易性:
  - news_collector._urlopen や jquants_client の id_token 注入など、モックが可能な設計になっています。
- トランザクション:
  - DuckDB への一括挿入はトランザクションでまとめられており、失敗時はロールバックされます。

---

## 開発・拡張
- 戦略（strategy）・実行（execution）・監視（monitoring）層はプレースホルダとして用意されています。そこに取引戦略やブローカー API 連携、モニタリング処理を実装していく想定です。
- Schema の拡張やインデックス追加は schema.py に定義を追加してください（既存定義は冪等で CREATE IF NOT EXISTS を使用）。

---

ご不明点や README に追加したい具体的な利用シナリオ（CI/CD、Docker、運用ジョブの cron 設定など）があれば教えてください。必要に応じてサンプルスクリプトや .env.example、systemd / cron のジョブ定義例も作成します。