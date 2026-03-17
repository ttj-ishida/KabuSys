# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群（KabuSys）。  
J-Quants API から市場データを取得して DuckDB に保存し、品質チェック・カレンダー管理・ニュース収集・ETL パイプライン・監査ログ構築などを提供します。

---

## 主な特徴（機能一覧）

- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーをページネーション対応で取得
  - レート制限（120 req/min）順守（固定間隔スロットリング）
  - リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
  - fetched_at を付与して Look-ahead Bias を防止
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）

- ETL パイプライン
  - 差分更新（最終取得日に基づく差分取得）
  - バックフィル機構（直近数日を再取得して API の後出し修正を吸収）
  - 品質チェック（欠損・重複・スパイク・日付不整合）

- マーケットカレンダー管理
  - JPX カレンダーの差分更新ジョブ
  - 営業日判定 / 前後営業日取得 / 期間内営業日リスト取得

- ニュース収集モジュール（RSS）
  - トラッキングパラメータ除去・URL 正規化による記事 ID（SHA-256 切取）生成で冪等性確保
  - defusedxml を利用した XML パース（XML Bomb 対策）
  - SSRF 対策（非 http/https スキーム拒否・プライベートアドレス拒否）
  - レスポンスサイズ制限（Gzip 解凍後も最大サイズ検査）
  - DuckDB への一括挿入（トランザクション・チャンク処理、INSERT ... RETURNING）

- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定までのトレースを担保する監査テーブル群の初期化機能
  - 全 TIMESTAMP を UTC に統一、冪等キーによる二重発注防止等の設計

- DuckDB スキーマ定義一式（Raw / Processed / Feature / Execution / Audit）

---

## 要件

- Python 3.10+
- 主要パッケージ（例）
  - duckdb
  - defusedxml

（プロジェクトで配布される requirements.txt / pyproject.toml がある場合はそちらを参照してください）

---

## セットアップ手順

1. リポジトリをクローン（例）
   ```
   git clone <repository-url>
   cd <repository>
   ```

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   - 最小例:
     ```
     pip install duckdb defusedxml
     ```
   - プロジェクトに `pyproject.toml` / `requirements.txt` があれば:
     ```
     pip install -r requirements.txt
     # または
     pip install .
     ```

4. 環境変数の設定
   - プロジェクトルートに `.env` を配置するか、OS 環境変数を設定します。
   - 自動ロード: `kabusys.config` はプロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を自動的に読み込みます。自動ロードを無効にするには:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. 主要な環境変数（例）
   - 必須:
     - JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD：kabu API パスワード
     - SLACK_BOT_TOKEN：Slack 通知用トークン
     - SLACK_CHANNEL_ID：Slack チャンネル ID
   - 任意/デフォルトあり:
     - KABUSYS_ENV：`development` | `paper_trading` | `live`（デフォルト `development`）
     - LOG_LEVEL：`DEBUG` | `INFO` | `WARNING` | `ERROR`（デフォルト `INFO`）
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）

   サンプル `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=yyyy
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（簡単な例）

以下は Python から主要機能を呼び出すサンプルです。

1. DuckDB スキーマの初期化
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)
   ```

2. 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
   ```python
   from kabusys.data.pipeline import run_daily_etl

   result = run_daily_etl(conn)  # target_date を指定しなければ今日
   print(result.to_dict())
   ```

3. 市場カレンダー更新ジョブ（夜間バッチ）
   ```python
   from kabusys.data.calendar_management import calendar_update_job

   saved = calendar_update_job(conn)
   print("calendar saved:", saved)
   ```

4. ニュース収集（RSS）ジョブ
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

   # known_codes: 銘柄抽出に使う有効な銘柄コードセット（例: セットで読み込む）
   known_codes = {"7203", "6758", ...}
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(results)
   ```

5. 監査スキーマの初期化（監査テーブルをプロジェクト DB に追加）
   ```python
   from kabusys.data.audit import init_audit_schema

   init_audit_schema(conn, transactional=True)
   ```

6. J-Quants から直接データ取得（トークン注入可能）
   ```python
   from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

   id_token = get_id_token()  # settings.jquants_refresh_token を利用して ID トークンを取得
   records = fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,1,31))
   ```

注意:
- jquants_client は内部でレート制御・リトライ・トークン自動リフレッシュを行います。
- news_collector は SSRF 防止やサイズ上限チェックを実施します。

---

## 主要モジュール概要

- kabusys.config
  - .env / 環境変数読み込み、Settings クラス（アプリ設定）を提供
- kabusys.data.jquants_client
  - J-Quants API クライアント、取得 & DuckDB 保存ユーティリティ
- kabusys.data.schema
  - DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution）
- kabusys.data.pipeline
  - ETL パイプライン（差分取得・保存・品質チェック）
- kabusys.data.news_collector
  - RSS 取得・前処理・DuckDB への保存、銘柄抽出ロジック
- kabusys.data.calendar_management
  - カレンダーの更新 / 営業日判定ユーティリティ
- kabusys.data.quality
  - 品質チェック（欠損・重複・スパイク・日付不整合）
- kabusys.data.audit
  - 監査ログ（signal/events/order_requests/executions）テーブル初期化

---

## ディレクトリ構成

リポジトリの主要ファイル（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - calendar_management.py
      - audit.py
      - quality.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

各ファイルは上で説明した機能を提供します。詳細なメソッド・引数はソースコードと docstring を参照してください。

---

## 運用上の注意（留意点）

- 環境変数はセキュアに管理してください（トークンやパスワードのローテーション・アクセス制御）。
- J-Quants のレート制限を越えないよう注意（ライブラリは制御していますが、外部からの並列呼び出しも考慮してください）。
- DuckDB ファイルはバックアップ・アクセス制御を検討してください（特に production）。
- news_collector は外部 URL を取得するため、ネットワーク環境や許可されたアウトバウンド先ポリシーを確認してください。
- init_audit_schema は TimeZone を UTC に固定します。監査ログは UTC ベースで扱ってください。

---

## 変更履歴 / バージョン

パッケージバージョンは kabusys.__version__（現状: 0.1.0）を参照してください。

---

README に記載されていない使い方や追加例、CI / デプロイ設定、外部サービス（Slack 通知・証券会社連携）に関する実装例が必要であれば、どの機能についてのドキュメントが欲しいか教えてください。