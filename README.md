# KabuSys

日本株向けの自動売買プラットフォーム（ライブラリ）です。  
J-Quants / kabuステーション 等の外部APIと連携して、データ取得（ETL）→品質チェック→特徴量生成→シグナル発行→発注・監査までを想定したモジュール群を含みます。本リポジトリはデータ基盤・ETL・監査周りの実装を中心に提供します。

## 主な特徴
- J-Quants API クライアント
  - 日足（OHLCV）、財務データ、JPXカレンダー取得に対応
  - レート制限（120 req/min）に準拠する内部 RateLimiter
  - リトライ（指数バックオフ）、401 時の自動トークン更新
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead バイアスを可視化
  - DuckDB への冪等的な保存（ON CONFLICT DO UPDATE）
- DuckDB スキーマ定義
  - Raw / Processed / Feature / Execution 層を想定したテーブル群を作成
  - インデックス定義、外部キー考慮の作成順
- ETL パイプライン
  - 差分更新（最終取得日からの差分/バックフィルを自動算出）
  - 市場カレンダーの先読み（lookahead）
  - 品質チェック（欠損・重複・スパイク・日付不整合）
  - ETL 実行結果を表す `ETLResult`
- 監査ログ（audit）
  - シグナル→発注→約定の完全トレーサビリティ用テーブル
  - 発注の冪等性を担保（order_request_id）
  - すべての TIMESTAMP を UTC で保存
- 設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート判定）
  - 必須環境変数のラッパー `settings`（存在チェック・既定値処理）
  - 自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能

---

## 要件
- Python 3.10 以上（型注釈に `|` を使用）
- 依存パッケージ（最低限）
  - duckdb
- ネットワークアクセス（J-Quants API）

（実際のセットアップでは pyproject / requirements.txt を参照してください）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成・有効化（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   - 最低限:
     ```bash
     pip install duckdb
     ```
   - 開発用の依存はプロジェクトの管理ファイルに従ってください（pyproject.toml 等）。

4. 環境変数の準備
   - プロジェクトルート（.git か pyproject.toml のあるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます。
   - 自動ロードを無効化したい場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 例（.env）:
     ```
     # J-Quants
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx

     # kabuステーション
     KABU_API_PASSWORD=secret
     KABU_API_BASE_URL=http://localhost:18080/kabusapi

     # Slack
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567

     # DB
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db

     # 環境・ログ
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - 必須環境変数（アクセス時に未設定だと例外となる）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - オプション（既定値あり）
     - KABU_API_BASE_URL（既定: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（既定: data/kabusys.duckdb）
     - SQLITE_PATH（既定: data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live、既定: development）
     - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、既定: INFO）

---

## 使い方（主要ワークフロー例）

以下は DuckDB スキーマ初期化と日次 ETL 実行の簡単な例です。

1. DuckDB スキーマ初期化
   ```python
   from kabusys.data import schema

   conn = schema.init_schema("data/kabusys.duckdb")
   # 既存ファイルがあればスキップしつつ接続を返す
   ```

2. 監査ログスキーマ（必要な場合）
   ```python
   from kabusys.data import audit
   # init_schema で作成した conn を使う場合
   audit.init_audit_schema(conn)
   # もしくは専用DBファイルを初期化
   # audit_conn = audit.init_audit_db("data/audit.duckdb")
   ```

3. 日次 ETL 実行
   ```python
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl
   from kabusys.data import schema

   conn = schema.get_connection("data/kabusys.duckdb")  # 既に init_schema 済みであること
   result = run_daily_etl(conn)  # target_date を指定しなければ今日
   print(result.to_dict())
   ```

4. J-Quants API を直接利用（ID トークン取得・データ取得）
   ```python
   from kabusys.data import jquants_client as jq
   # id_token は自動キャッシュされ、401 時は refresh して再試行します
   id_token = jq.get_id_token()            # refresh token から idToken を取得
   records = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2023,1,1), date_to=date(2023,1,31))
   ```

5. ETL 実行時の品質チェック結果は `ETLResult.quality_issues` にまとまって返ります。重大度 "error" を見つけた場合は運用で止める/通知する等の判断を行ってください。

---

## 重要な実装上の注意点（挙動まとめ）
- jquants_client:
  - レート制限 120 req/min を守るため固定間隔スロットリングを使用。
  - 408/429/5xx 系に対して指数バックオフで最大 3 回リトライ。
  - 401 を受信した場合はリフレッシュトークンから id_token を更新して1回リトライ（再帰防止あり）。
  - ページネーションに対応し、module-level の ID トークンキャッシュを共有。
  - 保存関数は fetched_at を UTC で記録し、DuckDB 側で ON CONFLICT DO UPDATE により冪等性を保証。
- ETL（pipeline.run_daily_etl）:
  - 市場カレンダーを先に取得（lookahead）し、対象日を営業日に調整して以後の取得を行う。
  - 差分更新（最終取得日 + バックフィル）により必要分のみ取得。デフォルトバックフィルは 3 日。
  - 各ステップは独立してエラーを捕捉するため、1つの失敗が他の処理を止めない（結果に errors を蓄積）。
- 設定読み込み:
  - .env（→ .env.local）を自動でロード。OS環境変数が優先され、.env.local は上書き（override）される。
  - テストなどで自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

---

## 主要モジュール / ディレクトリ構成

リポジトリ内の主要ファイルと役割を示します（抜粋）。

- src/kabusys/
  - __init__.py
    - パッケージの公開メンバを定義（data, strategy, execution, monitoring）
  - config.py
    - 環境変数読み込みと `settings` オブジェクト（必須値チェック、デフォルト管理）
    - 自動 .env ロードロジック
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存ロジック、レート制御、リトライ、トークン管理）
    - schema.py
      - DuckDB スキーマ定義と初期化関数（init_schema, get_connection）
      - Raw/Processed/Feature/Execution 層の CREATE 文
    - pipeline.py
      - ETL パイプライン（差分更新・保存・品質チェック）と `run_daily_etl`
    - quality.py
      - 品質チェック（欠損、スパイク、重複、日付不整合）；QualityIssue データクラス
    - audit.py
      - 監査ログ（signal_events, order_requests, executions）及び初期化関数
    - audit 関連のインデックス定義や制約もここに含む
  - strategy/
    - __init__.py（戦略実装のプレースホルダ）
  - execution/
    - __init__.py（発注ロジックのプレースホルダ）
  - monitoring/
    - __init__.py（監視用モジュール領域のプレースホルダ）

---

## 運用ノート
- 本ライブラリは「データ基盤」「ETL」「監査ログ」周りの実装を主眼としています。戦略（signal の生成）や実際の証券会社インターフェース（kabuステーションへの通信・約定管理）は別モジュール／上位アプリケーションが担う想定です。
- DuckDB ファイルは既定で `data/kabusys.duckdb`。バックアップ・スキーママイグレーションは運用ポリシーに従ってください。
- 重要な環境（本番/ペーパー取引）を切り替えるには `KABUSYS_ENV` を `development | paper_trading | live` のいずれかに設定してください。`settings.is_live` 等で判定可能です。
- ログレベルは `LOG_LEVEL` で制御。運用では INFO→WARNING→ERROR を基準に調整してください。

---

## よく使うサンプルコマンド
- ETL をコマンドラインスクリプト化する際は、上記の Python スニペットを CLI ラッパーにして cron / Airflow 等から実行してください。
- テスト実行などで .env の自動読み込みを避けたい場合:
  ```bash
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1 pytest
  ```

---

README は以上です。必要であれば次の内容も追加できます:
- CLI スクリプト例（entrypoint）
- 詳細な .env.example ファイル
- サンプルワークフロー（Airflow DAG・systemd timer 例）
- strategy / execution 層の実装テンプレート

どれを追加しますか？