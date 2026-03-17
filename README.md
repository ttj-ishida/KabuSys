# KabuSys

KabuSys は日本株の自動売買プラットフォーム向けに設計されたライブラリ群です。J-Quants や RSS などからデータを取得して DuckDB に蓄積し、ETL・品質チェック・監査ログ・マーケットカレンダー管理など自動売買に必要となる基盤機能を提供します。

主な設計方針は以下です。
- データ取得は冪等（ON CONFLICT / DO UPDATE または DO NOTHING）で安全に保存
- API レート制限・リトライ・トークン自動更新など耐障害性を考慮
- Look-ahead bias を防ぐため取得時刻（UTC）を記録
- RSS ニュース収集は SSRF・XML Bomb 対策を実施
- DuckDB をデータストアとして軽量に運用可能

---

## 機能一覧

- 環境変数／設定管理
  - .env / .env.local を自動読み込み（プロジェクトルート検出）
  - 必須キーが未設定の場合は明示的にエラー

- J-Quants クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX カレンダー取得
  - レートリミット（120 req/min）、指数バックオフでリトライ
  - 401 時のトークン自動リフレッシュ
  - DuckDB へ冪等保存（raw_prices / raw_financials / market_calendar）

- ニュース収集（kabusys.data.news_collector）
  - RSS から記事収集、前処理（URL 削除・空白正規化）
  - トラッキングパラメータ除去・URL 正規化・SHA-256 を用いた記事 ID
  - SSRF・XML 攻撃対策（defusedxml、リダイレクト検査、受信サイズ制限）
  - raw_news / news_symbols への冪等保存

- スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層の DuckDB スキーマ定義と初期化
  - インデックス作成とファイルパス自動ディレクトリ作成

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（最終取得日から未取得範囲を自動算出）
  - backfill による直近再取得（API の後出し修正吸収）
  - 市場カレンダー先読み、株価・財務の保存、品質チェックの実行

- カレンダー管理（kabusys.data.calendar_management）
  - JPX カレンダーの夜間バッチ更新
  - 営業日判定、前後営業日の取得、期間内の営業日列挙
  - DB が未取得時は曜日ベースのフォールバック

- 品質チェック（kabusys.data.quality）
  - 欠損データ、スパイク（前日比）、重複、日付不整合の検出
  - 各チェックは QualityIssue オブジェクト（severity 等）を返す

- 監査ログ（kabusys.data.audit）
  - シグナル → 発注要求 → 約定までトレーサビリティを確保する監査テーブル
  - UUID ベースの冪等キー、すべて UTC で timestamp 保存

---

## 前提 / 必要要件

- Python 3.10 以上（型ヒントで | 演算子を使用）
- pip
- 必要な Python パッケージ（少なくとも）:
  - duckdb
  - defusedxml

（プロジェクトルートに requirements.txt がある場合はそれを利用してください。ない場合は上記をインストールしてください）

例:
```
python -m pip install "duckdb" "defusedxml"
```

---

## 環境変数（主なもの）

設定は環境変数またはプロジェクトルートの `.env`, `.env.local` から読み込まれます（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

重要なキー:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD     : kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL     : kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN       : Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID      : Slack チャンネル ID（必須）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 SQLite のパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV           : 実行環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL             : ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")（デフォルト: INFO）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン / プロジェクトを配置
2. Python 仮想環境の作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```
3. 必要パッケージをインストール
   ```
   python -m pip install --upgrade pip
   python -m pip install duckdb defusedxml
   ```
   （プロジェクトに requirements.txt があれば `pip install -r requirements.txt` を使ってください）

4. 環境変数を設定（`.env` / `.env.local` をプロジェクトルートに作成）
5. DuckDB スキーマを初期化（下の「使い方」参照）

---

## 使い方（簡単な例）

以下は Python スクリプトや REPL からの利用例です。

- DuckDB スキーマ初期化
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
# またはインメモリ:
# conn = schema.init_schema(":memory:")
```

- 監査ログ用テーブルの初期化（既に init_schema した conn を渡す）
```python
from kabusys.data import audit
audit.init_audit_schema(conn)
# 監査専用 DB を別途作る場合:
# conn_audit = audit.init_audit_db("data/audit.duckdb")
```

- 日次 ETL を実行（J-Quants トークンは settings から自動取得）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定しなければ今日
print(result.to_dict())
```

- ニュース収集ジョブを実行（既知銘柄コードセットを渡して紐付け）
```python
from kabusys.data.news_collector import run_news_collection
known_codes = {"7203", "6758"}  # 例: トヨタ、ソニー等
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # { source_name: 新規保存件数, ... }
```

- J-Quants API を直接使う（データ取得例）
```python
from kabusys.data import jquants_client as jq
# トークンを自動取得（settings.jquants_refresh_token を使用）
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
# 保存
jq.save_daily_quotes(conn, records)
```

- カレンダーの夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"saved={saved}")
```

- 品質チェックを個別に実行
```python
from kabusys.data import quality
issues = quality.run_all_checks(conn)
for i in issues:
    print(i)
```

---

## 自動ロードの挙動（.env / .env.local）

- 起点はこのパッケージファイル位置から親方向に .git または pyproject.toml を探してプロジェクトルートを自動判定します。これにより実行時のカレントディレクトリに依存しません。
- 読み込み順: OS 環境変数 > .env.local > .env
- テストや明示的制御のために KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると自動ロードを抑制できます。

---

## ディレクトリ構成（概観）

（プロジェクトの `src/kabusys` 以下の主要モジュール）
- kabusys/
  - __init__.py
  - config.py                      — 環境設定・自動 .env ロード
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得・保存）
    - news_collector.py             — RSS ニュース収集（前処理・保存・紐付け）
    - schema.py                     — DuckDB スキーマ定義・初期化
    - pipeline.py                   — ETL パイプライン（差分取得・保存・品質チェック）
    - calendar_management.py        — マーケットカレンダー管理・営業日判定
    - audit.py                      — 監査ログ（signal/events/order_requests/executions）
    - quality.py                    — データ品質チェック群
  - strategy/
    - __init__.py                   — 戦略関連プレースホルダ
  - execution/
    - __init__.py                   — 発注関連プレースホルダ
  - monitoring/
    - __init__.py                   — 監視関連プレースホルダ

上記のうち data パッケージが主要な実装を多く持っています。strategy / execution / monitoring は拡張ポイントとして用意されています。

---

## 注意点 / 運用上のヒント

- API トークンやシークレットは `.env` を使って管理する場合、リポジトリにコミットしないよう注意してください（.gitignore を確認）。
- DuckDB ファイルは軽量ですがバックアップや排他アクセスの運用方針を検討してください。
- J-Quants のレート制限（120 req/min）に従っていますが、大量データの一括取得時はさらに調整が必要になる場合があります。
- ニュース収集は外部 URL を開くため SSRF 対策が実装されていますが、信頼できない環境での追加セキュリティ層（プロキシ・ネットワークポリシーなど）を推奨します。
- 本 README はコードヘッダ・ドキュメントに基づいた概要です。より詳細な設計資料（DataPlatform.md 等）がある場合はそちらを参照してください（プロジェクトに同梱されている想定）。

---

必要であれば、README に次の内容を追加できます:
- CI / テスト実行方法
- 具体的な .env.example のテンプレート
- 実運用でのデプロイ手順（systemd / cron / Airflow 等）
- strategy / execution の拡張方法サンプル

追加したい項目があれば教えてください。