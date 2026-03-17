# KabuSys

KabuSys は日本株のデータ収集・品質管理・ETL・監査・自動売買の基盤となる Python パッケージです。J-Quants API や RSS を使ったニュース収集、DuckDB を用いた冪等なデータ保存・スキーマ管理、データ品質チェック、監査ログの仕組みを提供します。

バージョン: 0.1.0

---

## 主な特徴

- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務諸表、JPX マーケットカレンダーの取得
  - API レート制御（120 req/min 固定間隔スロットリング）
  - リトライ（指数バックオフ、最大 3 回）、401 時の自動トークンリフレッシュ
  - 取得日時（fetched_at）を UTC で記録し Look-ahead Bias を防止
  - DuckDB へ冪等的に保存（ON CONFLICT DO UPDATE）

- ニュース収集モジュール
  - RSS フィードから記事を収集して前処理（URL 除去、空白正規化）
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）で冪等性を保証
  - SSRF 対策、受信サイズ制限（デフォルト 10MB）、XML パースに defusedxml を使用
  - DuckDB に一括トランザクションで保存し、銘柄コード抽出 → 紐付け（news_symbols）

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層を定義する包括的な DDL
  - 初期化関数でテーブルとインデックスを冪等作成
  - 監査ログ用スキーマ（signal_events, order_requests, executions）を別途初期化可能

- ETL パイプライン
  - 差分更新（最終取得日からの差分 or 初回は全件）
  - backfill による後出し修正吸収
  - 品質チェック（欠損、スパイク、重複、日付不整合）を実行し結果を返却

- マーケットカレンダー管理
  - JPX カレンダーの差分更新ジョブ
  - 営業日判定・次/前営業日取得・期間内営業日一覧を提供
  - DB 未取得時は曜日ベースでフォールバック

- 監査ログ（トレーサビリティ）
  - 戦略 → シグナル → 発注要求 → 証券会社約定 のチェーンを UUID で追跡
  - 発注の冪等キー、全てのイベントに created_at を付与

---

## 必要条件

- Python 3.10 以上（型注釈の | 記法等を使用）
- 主要依存ライブラリ（最低限）
  - duckdb
  - defusedxml

インストール例:
```bash
python -m pip install "duckdb" "defusedxml"
```

（プロジェクト配布時は requirements.txt / pyproject.toml を用意してください）

---

## 環境変数（必須／任意）

settings クラスから取得される主要な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID — Slack 通知先チャネルID

任意（デフォルトあり）:
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) (default: development)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) (default: INFO)

自動読み込み:
- プロジェクトルートにある `.env` / `.env.local` を自動読み込みします（ただし OS 環境変数が優先されます）。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。

.env の例:
```env
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
```bash
git clone <repo-url>
cd <repo-dir>
```

2. Python 仮想環境作成（推奨）
```bash
python -m venv .venv
source .venv/bin/activate   # Unix / macOS
# .venv\Scripts\activate    # Windows
```

3. 依存パッケージをインストール
```bash
python -m pip install --upgrade pip
python -m pip install duckdb defusedxml
```

4. 環境変数を設定（.env をプロジェクトルートに配置）
5. DuckDB スキーマの初期化（例）
```python
from kabusys.data.schema import init_schema
init_schema("data/kabusys.duckdb")
```

---

## 使い方（主要な API と実行例）

以下は最小限の呼び出し例です。実際はロガー設定やエラーハンドリング、運用ジョブ化を検討してください。

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
```

- 監査スキーマの初期化（既存接続へ追加）
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)
```

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集ジョブ（RSS から収集して DB に保存）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes を渡すと記事と銘柄コードの紐付けを行う（省略可）
results = run_news_collection(conn, known_codes={"7203", "6758"})
print(results)  # {source_name: new_count, ...}
```

- カレンダー差分更新ジョブ（夜間バッチ想定）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved: {saved}")
```

- J-Quants から生データを直接取得する例
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

token = get_id_token()  # settings.jquants_refresh_token を使用
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

---

## ディレクトリ構成

パッケージの主要ファイル（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数・設定管理（.env 自動ロード含む）
  - data/
    - __init__.py
    - schema.py              # DuckDB スキーマ定義と初期化
    - jquants_client.py      # J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py            # ETL パイプライン（差分取得・品質チェック）
    - news_collector.py      # RSS ニュース収集・保存・銘柄抽出
    - calendar_management.py # 市場カレンダー管理（営業日判定・更新ジョブ）
    - audit.py               # 監査ログ（トレーサビリティ）スキーマ
    - quality.py             # データ品質チェック
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

（この README 作成時点では strategy, execution, monitoring の多くは初期モジュールのみ実装されています）

---

## 注意事項 / 運用上のポイント

- API レート制限:
  - J-Quants は 120 req/min を想定。jquants_client は固定間隔の RateLimiter を使って制御します。
- ID トークン:
  - 401 が返った場合は自動的にリフレッシュを試みます（1 回のみ）。リトライロジックは 408/429/5xx を対象に指数バックオフで再試行します。
- DuckDB への保存:
  - 生データ保存は ON CONFLICT を使い冪等化されています。外部からの改変には注意してください。
- ニュース収集:
  - RSS パースに失敗したり、SSRF が疑われる URL はスキップされます。受信サイズは上限（デフォルト 10MB）で保護されています。
- 品質チェック:
  - ETL では品質チェックを行い、重大な問題は QualityIssue として返されます。運用でどの段階でストップするかは別途方針を決めてください。
- タイムゾーン:
  - 監査用テーブルでは UTC を強制（SET TimeZone='UTC'）します。日時は意図せずローカルタイムが混入しないよう注意してください。

---

## 貢献 / 拡張ポイント

- strategy / execution / monitoring モジュールに戦略実装・ブローカー連携・運用監視を追加できます。
- Slack 通知やジョブスケジューラ（cron, Airflow 等）との連携を実装すると運用が楽になります。
- テレメトリ・メトリクス収集（Prometheus 等）や詳細なログ集約を追加することで運用性が向上します。

---

README に記載の API/スキーマ/挙動はコード内ドキュメントをもとにまとめています。実運用にあたっては J-Quants や使用するブローカーの仕様、セキュリティ要件（API トークンの保護、ネットワーク制御）を十分に考慮してください。