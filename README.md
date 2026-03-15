# KabuSys

日本株向け自動売買プラットフォームのコアモジュール群です。  
データ取得、スキーマ定義、監査ログ、戦略・発注などの基盤を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム構築を支援する内部ライブラリ群です。  
主な役割は以下です。

- 外部データ（J-Quants 等）からの取得と DuckDB への保存
- DuckDB 上のスキーマ定義（Raw/Processed/Feature/Execution 層）
- 発注・約定の監査ログ（トレーサビリティ）
- 環境変数・設定管理
- （将来的に）戦略・発注実行・監視モジュールとの統合

設計上の特徴:
- J-Quants API に対するレート制御（120 req/min）とリトライ（指数バックオフ）
- 401 応答での自動トークンリフレッシュ
- 取得時刻（fetched_at）を UTC で記録し Look-ahead バイアスを抑制
- DuckDB への INSERT は冪等（ON CONFLICT DO UPDATE）で実装
- 監査ログは UUID ベースのチェーンでシグナル→発注→約定を完全にトレース可能

---

## 機能一覧

- 設定管理 (kabusys.config)
  - .env / .env.local 自動読み込み（プロジェクトルート基準）
  - 必須環境変数のチェックとラッパー（settings オブジェクト）
  - 環境フラグ（development / paper_trading / live）、ログレベル管理

- データ層 (kabusys.data)
  - jquants_client: J-Quants API クライアント
    - 日足（OHLCV）・財務データ・マーケットカレンダーの取得
    - ページネーション対応、レートリミット、リトライ、トークン自動更新
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）
  - schema: DuckDB のスキーマ定義と初期化（init_schema / get_connection）
    - Raw / Processed / Feature / Execution 層のテーブル定義
    - インデックス作成
  - audit: 監査ログスキーマと初期化（init_audit_schema / init_audit_db）
    - signal_events, order_requests, executions 等を定義

- プレースホルダ:
  - strategy, execution, monitoring パッケージ（今後の機能追加想定）

---

## セットアップ手順

前提
- Python 3.10 以上（型記法に | を使用）
- 必要パッケージ（最低限）:
  - duckdb
- J-Quants API 利用時にはネットワーク接続が必要

1. レポジトリをクローン / プロジェクトへ移動

2. 開発インストール（例）
   - pip を使う例:
     - python -m pip install -e . 
   - あるいは必要な依存を個別にインストール:
     - python -m pip install duckdb

3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）から自動で `.env` / `.env.local` を読み込みます。
   - 自動読み込みを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   必須の環境変数（例）:
   - JQUANTS_REFRESH_TOKEN=（J-Quants の refresh token）
   - KABU_API_PASSWORD=（kabuステーション API パスワード）
   - SLACK_BOT_TOKEN=（Slack ボットトークン）
   - SLACK_CHANNEL_ID=（通知先 Slack チャンネル ID）

   任意 / デフォルトあり:
   - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
   - LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）

   サンプル `.env`（.env.example）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマ初期化
   - 初回はスキーマを作成する必要があります（ファイル作成を含む）。
   - 例:
     ```python
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
     ```
   - 監査ログテーブルは別途初期化:
     ```python
     from kabusys.data import audit
     audit.init_audit_schema(conn)
     ```
   - 監査専用 DB を使う場合:
     ```python
     conn_audit = audit.init_audit_db("data/audit.duckdb")
     ```

---

## 使い方（基本例）

- J-Quants から日足を取得して DuckDB に保存する例:

```python
from datetime import date
import duckdb
from kabusys.data import jquants_client
from kabusys.data import schema

# DB 初期化（既に作成済みならスキップして接続を取得）
conn = schema.init_schema("data/kabusys.duckdb")

# ID トークンは内部で自動取得／キャッシュされる
records = jquants_client.fetch_daily_quotes(
    code="7203",  # 銘柄コード。省略で全銘柄
    date_from=date(2023, 1, 1),
    date_to=date(2023, 12, 31),
)

# DuckDB に保存（冪等）
inserted = jquants_client.save_daily_quotes(conn, records)
print(f"保存件数: {inserted}")
```

- トークン直接取得（必要な場合）:
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings から refresh token を使う
```

- 環境設定の参照:
```python
from kabusys.config import settings
print(settings.is_live, settings.log_level, settings.duckdb_path)
```

注意点:
- jquants_client は内部で RateLimiter を使い、120 req/min を超えないよう制御します。
- ネットワークエラーや 429/408/5xx は最大 3 回リトライ（指数バックオフ）。401 は自動で一度トークンリフレッシュしてリトライします。
- 保存時には fetched_at（UTC ISO 8601）を付与します。

---

## ディレクトリ構成

以下は主要ソースファイルの配置です（抜粋）。

- src/
  - kabusys/
    - __init__.py                (パッケージ定義、__version__)
    - config.py                  (環境変数・設定管理)
    - data/
      - __init__.py
      - jquants_client.py        (J-Quants API クライアント、保存ロジック)
      - schema.py                (DuckDB スキーマ定義 & 初期化)
      - audit.py                 (監査ログスキーマ & 初期化)
      - (その他: audit 用 util 等)
    - strategy/
      - __init__.py              (戦略関連モジュール用プレースホルダ)
    - execution/
      - __init__.py              (発注/実行関連プレースホルダ)
    - monitoring/
      - __init__.py              (監視用プレースホルダ)

主要なファイルの役割:
- config.py: .env 自動読み込み、settings オブジェクト、必須 env チェック、KABUSYS_ENV / LOG_LEVEL 検証
- data/jquants_client.py: API 呼び出し、ページネーション、保存関数（raw_prices 等）
- data/schema.py: DuckDB 上の全テーブル DDL と init_schema/get_connection
- data/audit.py: 発注フロー監査用テーブル群と初期化関数

---

## 運用上の注意

- 環境変数の漏洩に注意してください（API トークン等は機密情報です）。
- 本パッケージは発注処理の実装（kabuステーション連携等）を含みますが、実行時は本番環境（live）フラグやテスト機能に十分注意して運用してください。
- DuckDB ファイルは永続ストレージに保存してください（バックアップ推奨）。
- 監査ログは削除しない前提で設計されています（ON DELETE RESTRICT）。

---

## 今後の拡張候補

- strategy / execution / monitoring の具体実装（ポートフォリオ最適化、リスク管理、証券会社 API 連携）
- 単体テストおよび CI の追加
- データ取得の並列化（ただしレート制限に注意）
- メトリクス・アラート、Slack 通知の統合

---

README に掲載されていない詳細や、具体的な API キーの取り扱い・運用ルールについてはソースコード内の docstring（特に data/jquants_client.py, data/schema.py, data/audit.py）を参照してください。必要であればサンプルスクリプトや運用手順書を追加作成します。