# KabuSys

日本株自動売買プラットフォームのコアライブラリ（モジュール群）です。データ取得・保存・スキーマ管理・データ品質チェック・監査ログ機能など、アルゴリズム取引の基盤となるコンポーネントを提供します。

バージョン: 0.1.0

---

## 特徴（要約）

- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーを取得
  - レート制限（120 req/min）を遵守する RateLimiter
  - 冪等性／ページネーション対応
  - リトライ（指数バックオフ、最大 3 回）、401 受信時はトークン自動リフレッシュ
  - データ取得時に fetched_at を UTC で記録（Look-ahead bias の抑止）

- DuckDB ベースのスキーマ管理
  - Raw / Processed / Feature / Execution（と監査テーブル）を定義する DDL を持ち、初期化関数を提供
  - 各テーブルは冪等的に作成（IF NOT EXISTS）・インデックス定義あり

- 監査（audit）機能
  - シグナル → 発注要求 → 約定のトレーサビリティを UUID 連鎖で記録
  - 冪等キー（order_request_id）やステータス遷移、UTC タイムスタンプ等の設計方針を実装

- データ品質チェック
  - 欠損データ、主キー重複、株価スパイク（前日比閾値）、日付整合性（未来日付・非営業日）を検出
  - QualityIssue のリストを返し、呼び出し側が重大度によって処理を決定可能

- 環境設定管理
  - .env / .env.local を自動でロード（OS 環境変数が優先）
  - 自動ロード無効化フラグあり（KABUSYS_DISABLE_AUTO_ENV_LOAD）
  - settings オブジェクト経由の型付きプロパティアクセス

---

## 要件

- Python 3.10 以上（型ヒントに `X | None` を使用）
- duckdb（Python パッケージ）
- ネットワークアクセス（J-Quants API 等）

必須 Python パッケージ例（最低限）:
- duckdb

（プロジェクトに requirements.txt / pyproject.toml があればそちらを参照してください）

---

## セットアップ

1. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb

   （プロジェクトがパッケージ化されている場合）
   - pip install -e .

3. 環境変数設定
   - プロジェクトルートに `.env`（および必要に応じて `.env.local`）を作成します。
   - 自動ロードは OS 環境変数 > .env.local > .env の順で行われます。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 必須環境変数（例）

以下はコードで参照される主な環境変数です。実際の値は `.env` に設定してください。

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン（get_id_token に使用）

- KABU_API_PASSWORD (必須)  
  kabuステーション API のパスワード

- KABU_API_BASE_URL (省略可)  
  kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）

- SLACK_BOT_TOKEN (必須)  
  Slack 通知用 Bot トークン

- SLACK_CHANNEL_ID (必須)  
  Slack チャンネル ID

- DUCKDB_PATH (省略可)  
  DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）

- SQLITE_PATH (省略可)  
  監視用 SQLite パス（用途に応じ）

- KABUSYS_ENV (省略可)  
  実行環境: development / paper_trading / live（デフォルト: development）

- LOG_LEVEL (省略可)  
  ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

---

## 使い方（簡易例）

以下は基本的な利用フローの例（Python スクリプト内で利用する想定）。

1) DuckDB スキーマ初期化

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は環境変数 DUCKDB_PATH に基づく Path
conn = init_schema(settings.duckdb_path)
```

2) J-Quants から日足を取得して保存

```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

# 取得（settings.jquants_refresh_token を自動利用）
records = fetch_daily_quotes(code="7203", date_from=None, date_to=None)

# DuckDB に保存
n = save_daily_quotes(conn, records)
print(f"saved {n} rows")
```

3) 財務データ / マーケットカレンダーも同様に fetch_* → save_* を実行できます

4) 監査スキーマの初期化（監査テーブルを別 DB にする場合）

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
# または既存 conn に対して init_audit_schema(conn)
```

5) データ品質チェックの実行

```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn, target_date=None)
for issue in issues:
    print(issue.check_name, issue.severity, issue.detail)
```

ログやエラーの扱いは呼び出し側で行ってください（重大度に応じて ETL を中断するなど）。

---

## 実装上の注意点 / 設計方針

- API レート制限は固定間隔スロットリングで制御（120 req/min → 最小インターバル 0.5s）
- リトライ処理は指数バックオフ（最大 3 回）、HTTP 429 は Retry-After ヘッダを優先
- 401 は自動でトークンリフレッシュして 1 回だけ再試行
- DuckDB へのデータ保存は ON CONFLICT DO UPDATE を使い冪等化
- 監査ログは基本的に削除しない前提（ON DELETE RESTRICT）で設計
- すべての TIMESTAMP は UTC で保存（監査用初期化で SET TimeZone='UTC' を実行）

---

## ディレクトリ構成

プロジェクトの主要ファイル・モジュール構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      <-- 環境変数 / 設定管理、自動 .env ロード
  - data/
    - __init__.py
    - jquants_client.py             <-- J-Quants API クライアント（取得・保存）
    - schema.py                     <-- DuckDB スキーマ定義・初期化
    - audit.py                      <-- 監査（signal/order/execution）スキーマ
    - quality.py                    <-- データ品質チェック
  - strategy/
    - __init__.py                   <-- 戦略モジュール（拡張用）
  - execution/
    - __init__.py                   <-- 発注実行モジュール（拡張用）
  - monitoring/
    - __init__.py                   <-- 監視 / メトリクス（拡張用）

---

## 開発メモ

- .env ファイルのパースはシェル風の単純パーサを実装しており、シングル/ダブルクォートやエスケープに対応しています。`export KEY=val` 形式もサポートしています。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml の存在）を基準に行われ、CWD に依存しません。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- settings.* のプロパティは値検証を行います（例: KABUSYS_ENV の許容値チェック、LOG_LEVEL の検証）。エラー時には ValueError が発生します。

---

この README はライブラリの概要・導入手順・基本的な使い方を示しています。戦略ロジックや発注実装、監視・通知機能等は拡張箇所が多いため、用途に応じて各モジュールを実装・調整してください。質問や追加のドキュメント化が必要であればお知らせください。