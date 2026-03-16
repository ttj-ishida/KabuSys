# KabuSys

日本株向け自動売買プラットフォームのライブラリ群（プロトタイプ）。  
データ取得（J-Quants）→ DuckDB 保存 → 品質チェック → （戦略・発注）へつなぐための基盤モジュールを含みます。

## 概要
KabuSys は日本株の市場データ・財務データ・マーケットカレンダーを J-Quants API から取得し、DuckDB に三層（Raw / Processed / Feature）構造で保存、品質チェックと監査ログの仕組みを提供するライブラリです。  
設計上のポイント：

- J-Quants API のレート制限（120 req/min）を尊重する固定間隔スロットリング
- 401 時の自動トークンリフレッシュ（1 回）とリトライ（指数バックオフ、最大 3 回）
- データ取得時に fetched_at を UTC で記録し、Look-ahead Bias を抑制
- DuckDB への挿入は冪等（ON CONFLICT DO UPDATE）で二重挿入を防止
- ETL の品質チェック機能（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal → order_request → executions のトレーサビリティ）

現在のバージョン: 0.1.0

---

## 機能一覧
- 環境変数・設定管理（自動 .env 読込、必須チェック、環境モード判定）
  - 環境切替: development / paper_trading / live
  - LOG_LEVEL 検証
- J-Quants API クライアント
  - 株価日足（OHLCV）取得（ページネーション対応）
  - 財務諸表（四半期 BS/PL）取得（ページネーション対応）
  - JPX マーケットカレンダー取得
  - RateLimiter、リトライ、トークン管理を持つ HTTP 層
- DuckDB スキーマ定義・初期化
  - Raw / Processed / Feature / Execution 層のテーブル群
  - インデックス定義
  - audit（監査）テーブルの初期化補助
- ETL パイプライン（差分取得・バックフィル・品質チェック）
  - run_daily_etl：カレンダー → 株価 → 財務 → 品質チェック の一括実行
  - 差分算出とバックフィル（デフォルト 3 日）
- データ品質チェック
  - 欠損データ、スパイク（前日比閾値）、重複（主キー）、日付不整合チェック
  - QualityIssue オブジェクトで集約し呼び出し元に返却
- 監査ログ（audit）初期化ユーティリティ
  - signal_events, order_requests, executions のテーブルとインデックス

---

## セットアップ手順

1. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール  
   （プロジェクトに requirements.txt / pyproject.toml がない想定の例）
   - pip install duckdb

   （開発用にパッケージとしてインストールする場合）
   - python -m pip install -e .

3. 環境変数設定  
   プロジェクトルートに `.env` または `.env.local` を配置すると自動で読み込まれます（パッケージ内の自動ローダーが .git または pyproject.toml を基準に探します）。自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須の環境変数（例）:
   - JQUANTS_REFRESH_TOKEN  （必須） — J-Quants リフレッシュトークン
   - KABU_API_PASSWORD      （必須） — kabu ステーション API のパスワード
   - SLACK_BOT_TOKEN        （必須） — 通知用 Slack Bot トークン
   - SLACK_CHANNEL_ID       （必須） — 通知先 Slack チャンネルID

   任意/デフォルトあり:
   - KABU_API_BASE_URL      （デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH            （デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH            （デフォルト: data/monitoring.db）
   - KABUSYS_ENV            （development|paper_trading|live、デフォルト: development）
   - LOG_LEVEL              （DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト: INFO）

   サンプル .env（.env.example）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（基本例）

以下は Python からの基本的な利用例です。

1) DuckDB スキーマ初期化（永続 DB ファイル）
```python
from kabusys.data.schema import init_schema

# ファイルパスを指定（":memory:" でインメモリ DB）
conn = init_schema("data/kabusys.duckdb")
```

2) 監査ログスキーマを追加
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)  # 既存 conn に監査テーブルを追加
```

3) J-Quants トークン取得（手動）
```python
from kabusys.data.jquants_client import get_id_token
id_token = get_id_token()  # 環境変数の JQUANTS_REFRESH_TOKEN を使用
```

4) 日次 ETL 実行（市場カレンダー・株価・財務・品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

5) 個別ジョブを実行する例（価格 ETL のみ）
```python
from kabusys.data.pipeline import run_prices_etl
fetched, saved = run_prices_etl(conn, target_date=date.today())
```

注意点:
- run_daily_etl は内部で calendar → prices → financials → quality の順に処理し、各ステップで例外が発生しても他ステップは継続する設計です。最終的なエラー情報は ETLResult.errors / quality_issues に集約されます。
- J-Quants へのリクエストはモジュール内で RateLimiter によりスロットリングされます。大量バッチを組む場合は注意してください。

---

## 実運用のヒント
- 定期実行（cron / Airflow / GitHub Actions）で run_daily_etl を日次で実行するのが基本パターンです。
- 本番（live）モードでは KABUSYS_ENV=live を設定しておき、アプリ側で is_live を参照して発注フローを分岐させてください。
- DuckDB ファイルはバックアップ・スナップショットを取ることを推奨します。
- 監査ログは削除しない前提で設計されています（ON DELETE RESTRICT 等）。履歴保存ポリシーを検討してください。
- 自動 .env 読み込みを無効にする必要があるテスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成

（プロジェクトルートの `src/kabusys` 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント（取得・保存）
    - schema.py                 — DuckDB スキーマ定義・初期化
    - pipeline.py               — ETL パイプライン（差分取得・品質チェック）
    - audit.py                  — 監査ログ（signal/order_request/executions）
    - quality.py                — データ品質チェック
  - strategy/
    - __init__.py               — 戦略用パッケージ（拡張ポイント）
  - execution/
    - __init__.py               — 発注実装（ブリッジ）
  - monitoring/
    - __init__.py               — 監視用モジュール（将来的な拡張）

主要ファイル説明:
- config.py: .env 自動読み込み、必須チェック、環境・ログレベル検証、設定オブジェクト settings を提供
- jquants_client.py: HTTP 層、トークン取得、fetch_* / save_* 関数
- schema.py: DuckDB の DDL を集中管理し init_schema() を提供
- pipeline.py: 差分取得ロジック、run_daily_etl による一括処理
- quality.py: 各種品質チェック関数と run_all_checks

---

## 追加情報（設計上の注意）
- J-Quants API のレスポンスは JSON を前提とし、JSON デコードエラー時は RuntimeError を送出します。
- jquants_client は 401 受信時に get_id_token による自動リフレッシュを行い 1 回再試行します（無限再帰を避ける設計）。
- DuckDB に対する挿入は "ON CONFLICT DO UPDATE" を使って冪等にしています。外部からの直接挿入が行われた場合に備えて quality.check_duplicates があります。
- タイムスタンプは原則 UTC で取り扱うように実装されています（audit.init_audit_schema は SET TimeZone='UTC' を実行）。

---

## ライセンス・貢献
この README はコードベースの概要説明です。実際の公開・配布・商用利用を行う場合はライセンスやセキュリティ要件（API トークンの保護など）を整備してください。機能追加・バグ修正の PR は歓迎します（テスト追加を推奨）。

---

不明点や README に追記してほしい使い方があれば、どの部分を詳しく書くか教えてください。