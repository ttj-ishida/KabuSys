# KabuSys

日本株向け自動売買プラットフォームのコアライブラリです。  
データ取得（J-Quants）・ETL・データ品質チェック・DuckDBスキーマ定義・監査ログなど、アルゴリズムトレードに必要な基盤機能を提供します。

主な設計方針：
- J-Quants API のレート制限（120 req/min）を厳守
- トークン自動リフレッシュ・リトライ（指数バックオフ）
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）
- データの取得時刻（fetched_at）や監査ログは UTC で保存
- 品質チェックは Fail-Fast ではなく全件収集して報告

バージョン: 0.1.0

---

## 機能一覧

- 環境変数・設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 必須設定の明示的取得とバリデーション（Settings）
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）取得（ページネーション対応）
  - 財務データ（四半期 BS/PL）取得（ページネーション対応）
  - JPX 市場カレンダー取得
  - レートリミット制御、リトライ、トークン自動リフレッシュ
  - DuckDB への保存（save_* 関数、冪等）
- DuckDB スキーマ定義（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックス作成、スキーマ初期化ユーティリティ（init_schema）
- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL（run_daily_etl）：カレンダー → 株価 → 財務 → 品質チェック
  - 差分取得（DBの最終取得日を参照）、バックフィル対応
  - ETL 実行結果（ETLResult）を返却
- データ品質チェック（kabusys.data.quality）
  - 欠損データ検出、スパイク検出、重複チェック、日付不整合チェック
  - QualityIssue 型で詳細（サンプル行含む）を返却
- 監査ログ（kabusys.data.audit）
  - シグナル → 発注要求 → 約定 のトレーサビリティテーブル
  - 冪等キー（order_request_id 等）や UTC タイムスタンプの運用を想定

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の | 型注釈を使用）
- Git が使える環境（自動 .env ロードのプロジェクトルート検出に .git / pyproject.toml を使用）

1. リポジトリをクローン（省略可）
   - git clone ...  

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 必須: duckdb
   - 例:
     - pip install duckdb
   - （将来的に HTTP クライアントや Slack 連携を追加する場合は追加依存が必要になります）

4. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に `.env` として以下を用意してください。
   - 例 (.env.example):
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     KABU_API_BASE_URL=http://localhost:18080/kabusapi    # 任意（デフォルト）
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. データベース初期化
   - DuckDB スキーマ初期化（例）:
     from kabusys.data.schema import init_schema
     from kabusys.config import settings
     conn = init_schema(settings.duckdb_path)

---

## 使い方

以下は代表的な利用例です。Python スクリプトやバッチから呼び出して使います。

1) DuckDB スキーマ初期化
- 1 回だけ実行して DB とテーブルを作成します。

from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)

2) 日次 ETL 実行
- 市場カレンダー、日足、財務データを差分取得して保存、品質チェックまで実行します。

from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # 引数で target_date や id_token を指定可能
print(result.to_dict())

3) J-Quants の個別データ取得（テストやユーティリティ用途）
- fetch / save 関数はテスト用に id_token を注入可能。

from kabusys.data import jquants_client as jq
from kabusys.data.schema import init_schema

conn = init_schema(":memory:")
records = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
jq.save_daily_quotes(conn, records)

4) 品質チェックのみ実行
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i)

5) 監査ログスキーマの初期化
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)  # 既存の DuckDB 接続に監査テーブルを追加

注意点
- run_daily_etl は内部で market_calendar を先に取得して「営業日調整」を行います（非営業日に対する補正）。
- J-Quants API へのリクエストはモジュール内でレート制御・リトライ・トークン更新を行います。
- DuckDB への INSERT は ON CONFLICT DO UPDATE としており冪等です。

---

## 環境変数一覧（主なもの）

必須
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD: kabu ステーション API パスワード（使用モジュールで必要）
- SLACK_BOT_TOKEN: Slack 通知用（実装により必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

任意 / デフォルトあり
- KABU_API_BASE_URL: デフォルト "http://localhost:18080/kabusapi"
- DUCKDB_PATH: デフォルト "data/kabusys.duckdb"
- SQLITE_PATH: デフォルト "data/monitoring.db"
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化

.env の自動読み込み
- プロジェクトルート（.git または pyproject.toml）を基準に `.env` → `.env.local` の順で読み込みます。
- OS 環境変数は上書きされません（.env.local の override=True でも OS 環境変数は保護されます）。

---

## ディレクトリ構成

リポジトリ内の主要ファイル／ディレクトリ構成（抜粋）:

src/
  kabusys/
    __init__.py                -- パッケージ定義（バージョン等）
    config.py                  -- 環境変数/設定管理
    data/
      __init__.py
      jquants_client.py        -- J-Quants API クライアント + 保存ロジック
      schema.py                -- DuckDB スキーマ定義・初期化
      pipeline.py              -- ETL パイプライン（run_daily_etl 等）
      quality.py               -- データ品質チェック
      audit.py                 -- 監査ログ（トレーサビリティ）定義
      pipeline.py              -- ETL 実装（差分取得・バックフィル）
    strategy/
      __init__.py              -- 戦略関連（拡張場所）
    execution/
      __init__.py              -- 発注/約定関連（拡張場所）
    monitoring/
      __init__.py              -- 監視・メトリクス関連（拡張場所）

各モジュールの役割
- config.py: .env 読込ロジック、Settings クラスによる設定取得
- data/jquants_client.py: HTTP リクエスト、トークン管理、fetch/save の実装
- data/schema.py: DuckDB の DDL（Raw / Processed / Feature / Execution 層）
- data/pipeline.py: 差分更新ロジック、ETL 実行フロー、品質チェック統合
- data/quality.py: データ品質チェック実装（欠損・スパイク・重複・日付不整合）
- data/audit.py: 監査用テーブルとインデックスの定義

---

## 運用上の注意 / ベストプラクティス

- トークン・シークレットは必ず安全に管理し、リポジトリにハードコードしないでください。
- 本ライブラリはデータプラットフォーム基盤を提供します。実際の発注や証券会社インテグレーションは execution 層を実装して接続してください。
- DuckDB ファイルは定期的にバックアップしてください。監査ログは削除せず長期間保存することを想定しています。
- ETL 実行結果（ETLResult）や QualityIssue を監視／アラートに組み込んで運用してください（Slack 連携等）。
- 本コードはレート制御やリトライ、トークン更新の仕組みを備えていますが、運用環境の API レートや使用量に応じて調整してください。

---

問題報告 / 貢献
- Issue や PR は歓迎します。設計意図や API の互換性を保ちながら拡張してください。

以上。README の追加・調整やサンプルスクリプト（CLI / cron 用ラッパー）を希望する場合は教えてください。