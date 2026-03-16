# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
J-Quants API から市場データ（株価・財務・マーケットカレンダー等）を取得して DuckDB に保存し、ETL・品質チェック・監査ログ基盤を提供します。発注・実行・モニタリング周りのモジュールも含む設計になっています（コアは data パッケージ）。

---

## 主な特徴（機能一覧）

- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得
  - レート制限（120 req/min）対応の固定間隔レートリミッタ
  - リトライ（指数バックオフ、最大 3 回）、401 時の自動トークンリフレッシュ
  - ページネーション対応
  - 取得時刻（fetched_at）を UTC で記録（Look-ahead bias 対策）

- DuckDB スキーマ定義・初期化
  - Raw / Processed / Feature / Execution 層にまたがるテーブル定義
  - インデックス定義、外部キー・制約を含む冪等な初期化

- ETL パイプライン
  - 差分取得（最終取得日からの差分 or 指定範囲）
  - backfill による後出し修正吸収（デフォルト 3 日）
  - 市場カレンダーを先読みして営業日調整
  - 保存は冪等（ON CONFLICT DO UPDATE を使用）

- データ品質チェック
  - 欠損データ、主キー重複、スパイク（前日比閾値）、日付不整合（未来日、非営業日）検出
  - 各問題は QualityIssue オブジェクトとして収集（Fail-Fast ではない）

- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定 のトレーサビリティ用テーブル群
  - order_request_id を冪等キーとして二重発注防止
  - UTC タイムスタンプ、変更履歴用 updated_at 等を想定

- 環境/設定管理
  - .env / .env.local 自動読み込み（プロジェクトルートを .git / pyproject.toml で探索）
  - OS 環境変数の保護、上書き挙動の制御
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロード無効化可能（テスト用）

---

## 必要な依存（概要）

- Python 3.9+（型注釈で | 型を使用しているため）
- duckdb（DuckDB Python バインディング）
- 標準ライブラリ: urllib, json, logging, datetime 等

（実際のパッケージ化では pyproject.toml / requirements.txt に依存関係を明記してください）

---

## セットアップ手順

1. リポジトリをクローン／チェックアウトします（プロジェクトルートを .git または pyproject.toml が見つかる場所にしてください）。

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb
   - （その他必要があれば追加でインストール）

4. 環境変数を準備（.env をプロジェクトルートに置く。自動ロードが有効なら起動時に読み込まれます）
   例: `.env`
   ```
   JQUANTS_REFRESH_TOKEN=あなたの_jquants_refresh_token
   KABU_API_PASSWORD=kabu_station_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. 自動 .env ロードをテストで無効化したい場合:
   - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

---

## 使い方（簡易ガイド）

以下は Python REPL やスクリプトから利用する基本例です。

- DuckDB スキーマを初期化（データベースを作成し全テーブルを作成）
```
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可
```

- J-Quants からデータを取得して保存（ETL を手動で実行）
```
from datetime import date
from kabusys.data.pipeline import run_daily_etl, ETLResult
# conn: DuckDB 接続（init_schema の戻り値）
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- jquants_client の個別 API 利用例
```
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
token = get_id_token()  # settings から refresh token を取得して POST で id_token を得る
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = save_daily_quotes(conn, records)
print(f"fetched={len(records)} saved={saved}")
```

- 品質チェック単体実行
```
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2024,1,31))
for i in issues:
    print(i)
```

- 監査ログテーブルの初期化（既存の conn に追加）
```
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```

---

## 環境変数（主要設定）

必須・推奨される環境変数（.env に設定する例）:

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須)
  - kabu ステーション API 用パスワード
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
  - Slack 通知に使用するボットトークン
- SLACK_CHANNEL_ID (必須)
  - 通知先の Slack チャンネル ID
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
  - DuckDB ファイルパス（:memory: も可）
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- KABUSYS_ENV (任意, default: development)
  - 有効値: development / paper_trading / live
  - settings.is_live / is_paper / is_dev で判定可能
- LOG_LEVEL (任意, default: INFO)
  - 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL

.env のロード順序:
- OS 環境変数 > .env.local > .env
- プロジェクトルートはパッケージ内で .git または pyproject.toml を基準に探索
- テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

.env のパースは export KEY=val 形式、クォートやコメントも考慮しています。

---

## 主要 API（短い説明）

- kabusys.config.settings
  - 設定アクセス用オブジェクト（settings.jquants_refresh_token など）

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)

- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)

- kabusys.data.pipeline
  - run_prices_etl(...)
  - run_financials_etl(...)
  - run_calendar_etl(...)
  - run_daily_etl(...)

- kabusys.data.quality
  - run_all_checks(conn, target_date, reference_date, spike_threshold)

- kabusys.data.audit
  - init_audit_schema(conn)
  - init_audit_db(db_path)

---

## 開発・テスト時の注意点

- 自動 .env ロードは便利ですが、テストで明示的に環境変数を制御したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使って無効化してください。
- J-Quants API はレート制限・認証があるため、テストではモックや録音（VCR 等）を活用すると良いです。
- DuckDB 接続はプロセス内で軽量に開けますが、スキーマ初期化は一度にまとめて行うと高速です。

---

## ディレクトリ構成

（リポジトリの src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定管理（.env 自動読み込み・settings）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存ロジック）
    - schema.py
      - DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py
      - ETL パイプライン（差分取得・保存・品質チェック）
    - audit.py
      - 監査ログテーブル定義と初期化
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py
    - （戦略実装用プレースホルダ）
  - execution/
    - __init__.py
    - （発注実行用プレースホルダ）
  - monitoring/
    - __init__.py
    - （監視用プレースホルダ）

その他:
- README.md（このファイル）
- .env.example（プロジェクトルートに置く想定の例ファイル）

---

## 補足・設計上のポイント

- ETL は冪等性を重視（DuckDB 側は INSERT ... ON CONFLICT DO UPDATE を使用）
- 取得時刻（fetched_at）は UTC で保存し、いつデータが取得されたかをトレース可能にする（Look-ahead bias 対策）
- 品質チェックは重大度ごとに収集し、呼び出し元が停止/警告を判断する（Fail-Fast ではない）
- 監査ログはトレーサビリティを重視し、削除しない前提で設計（FK は ON DELETE RESTRICT）

---

必要があれば README にサンプル .env.example ファイルや、より詳細な API リファレンス（関数引数・戻り値の例）を追加できます。どの部分を詳しく載せたいか教えてください。