# KabuSys

日本株自動売買プラットフォーム用のライブラリ群（データ収集・ETL・スキーマ・品質チェック・監査ログ等）

このリポジトリは、J-Quants API を用いた市場データ取得、DuckDB によるデータ格納／スキーマ管理、ETL パイプライン、データ品質チェック、監査ログ用スキーマ等を提供するモジュール群です。戦略や実行・監視モジュールと組み合わせて自動売買基盤を構築できます。

主な目的：
- J-Quants から株価・財務・カレンダーを取得して DuckDB に永続化（冪等）
- 日次 ETL（差分更新 + バックフィル）と品質チェックの実行
- 発注・約定に関する監査ログスキーマの提供（トレーサビリティ保証）

---

## 機能一覧

- 設定管理
  - 環境変数およびプロジェクトルートの `.env` / `.env.local` の自動読み込み（無効化可）
  - 必須環境変数未設定時の明示的エラー

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX カレンダー取得
  - API レート制御（120 req/min）の組み込み
  - リトライ（指数バックオフ、最大 3 回）、401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録
  - DuckDB への保存は ON CONFLICT DO UPDATE により冪等性を担保

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の多層スキーマを定義
  - テーブル作成（冪等）とインデックス作成
  - init_schema / get_connection を提供

- 監査ログスキーマ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査テーブルを初期化
  - UTC タイムゾーン固定（SET TimeZone='UTC'）
  - 発注フローのトレーサビリティを UUID 連鎖で保証

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新ロジック（最終取得日からの差分 + backfill）
  - 市場カレンダー先読み（lookahead）
  - 株価・財務データの取得と保存（冪等）
  - 品質チェック（欠損・重複・スパイク・日付不整合）を実行して結果を返す
  - run_daily_etl により一括実行（各ステップは独立してエラーハンドリング）

- データ品質チェック（kabusys.data.quality）
  - 欠損（missing_data）、主キー重複（duplicates）、スパイク（spike）、日付不整合（future_date / non_trading_day）
  - 問題は QualityIssue オブジェクトで収集（error / warning）

---

## 前提要件

- Python >= 3.10（型ヒントの union 表記 (A | B) を使用）
- duckdb Python パッケージ
- （任意）J-Quants API のリフレッシュトークン等外部サービスの認証情報

インストールの例（仮）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb
# パッケージとして利用する場合はプロジェクトのセットアップ方法に従う（例: pip install -e .）
```

---

## 環境変数（必須 / 推奨）

主な環境変数（README に記載されているもの）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL (任意) — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — SQLite（監視用 DB）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

自動読み込み:
- パッケージはプロジェクトルート（.git または pyproject.toml を探索）から `.env` と `.env.local` を自動読み込みします。
- 環境変数の優先順位: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化するには: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

例: `.env` テンプレート（実際の値は各自で設定）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成・有効化
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb
   # 必要なら他の依存もインストール
   ```

2. 環境変数を準備
   - プロジェクトルートに `.env` または `.env.local` を作成するか、OS 環境変数として設定します。

3. DuckDB スキーマを初期化
   - スクリプトまたは Python REPL から初期化します。

   例:
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)  # data/kabusys.duckdb を作成して接続を返す
   ```

4. 監査ログスキーマを追加する（必要に応じて）
   ```python
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn)  # 既存の conn に監査テーブルを追加
   ```

---

## 使い方（基本例）

- 日次 ETL の実行（株価・財務・カレンダー取得 + 品質チェック）

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

# DB 初期化（初回のみ）
conn = init_schema(settings.duckdb_path)

# 日次 ETL 実行
result = run_daily_etl(conn)  # target_date を渡せば任意日で実行可能
print(result.to_dict())
```

- 個別ジョブの実行例

取得トークンを明示的に渡す、もしくは settings.jquants_refresh_token を使うことができます。

株価差分 ETL：
```python
from datetime import date
from kabusys.data.pipeline import run_prices_etl
# conn は init_schema で作成済み
fetched, saved = run_prices_etl(conn, target_date=date.today())
```

財務差分 ETL：
```python
from kabusys.data.pipeline import run_financials_etl
fetched, saved = run_financials_etl(conn, target_date=date.today())
```

カレンダー ETL（先読み含む）：
```python
from kabusys.data.pipeline import run_calendar_etl
fetched, saved = run_calendar_etl(conn, target_date=date.today())
```

監査 DB を別ファイルとして初期化する：
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

---

## 品質チェック（quality モジュール）

run_daily_etl の最後で実行される `quality.run_all_checks(conn, target_date, reference_date, spike_threshold)` は以下のチェックを行い、問題一覧（QualityIssue のリスト）を返します。

- 欠損データ（missing_data） — OHLC 欄の欠損を error として検出
- 重複（duplicates） — 主キー重複を error として検出
- スパイク（spike） — 前日比が指定閾値（デフォルト 50%）を超える変動を warning として検出
- 日付不整合（future_date / non_trading_day） — 将来日付や非営業日のデータを検出

ETL は各ステップを個別にエラーハンドリングして継続する設計です。品質問題の重大度（error/warning）に応じて外側の運用ロジックでアクションを決めてください。

---

## 実装上のポイント（開発者向け）

- 環境変数パーサは Bash 風クォート・エスケープ・コメント処理を実装しており、プロジェクトルートから .env を自動ロードします（テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
- J-Quants クライアントは:
  - 120 req/min に合わせた固定間隔スロットリング（RateLimiter）
  - 再試行（408/429/5xx 等）と指数バックオフ
  - 401 受信時は refresh token で ID トークンを再取得して 1 回だけリトライ
  - ページネーション対応（pagination_key の連結取得）
- DuckDB への保存は INSERT ... ON CONFLICT DO UPDATE を使い冪等性を確保
- 監査ログは削除しない前提（FK は ON DELETE RESTRICT）で設計

---

## ディレクトリ構成

（主要ファイルとモジュールのみ抜粋）

```
src/
  kabusys/
    __init__.py                # パッケージ定義（__version__ 等）
    config.py                  # 環境変数・設定管理
    data/
      __init__.py
      jquants_client.py        # J-Quants API クライアント & 保存関数
      schema.py                # DuckDB スキーマ定義・初期化
      pipeline.py              # ETL パイプライン（run_daily_etl 等）
      audit.py                 # 監査ログスキーマ初期化
      quality.py               # データ品質チェック
    strategy/
      __init__.py
    execution/
      __init__.py
    monitoring/
      __init__.py
```

---

## よくある運用注意点

- J-Quants の API レート制限（120 req/min）を超えないように、独自に高頻度で複数プロセスからリクエストする場合は注意してください。
- DUCKDB_PATH のバックアップ・ローテーションを運用で検討してください（大容量化するため）。
- KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかを設定してください。運用モードによりログや実行フローの振る舞いを制御できます。
- 自動 .env 読み込みは便利ですが、CI / テスト環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して明示的に環境を制御すると良いです。

---

必要があれば、README に以下を追記できます：
- CI 用の例（GitHub Actions 等）や cron / Airflow などでの ETL スケジューリング例
- Slack 通知や監視（monitoring）モジュールの使い方
- 詳細な .env.example ファイル

追加で盛り込みたい内容があれば教えてください。