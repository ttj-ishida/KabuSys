# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
J-Quants API や RSS フィードを使ったデータ収集、DuckDB によるスキーマ管理、ETL パイプライン、品質チェック、ニュース収集、マーケットカレンダー管理、監査ログ用スキーマなどを提供します。

主な設計方針は「冪等性」「トレーサビリティ」「安全性（SSRF対策等）」「API レート制御」「品質チェックの自動化」です。

## 主な機能一覧

- J-Quants API クライアント
  - 株価日足（OHLCV）/ 財務データ / JPX マーケットカレンダーの取得
  - API レート制限（120 req/min）対応（内部 RateLimiter）
  - リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
  - fetched_at による取得時刻のトレーサビリティ
  - DuckDB への冪等保存（ON CONFLICT を利用）
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit 層のDDL 定義と初期化
  - インデックス定義・外部キー考慮の作成順序
- ETL パイプライン
  - 差分更新（最終取得日からの再取得）、バックフィル、品質チェック統合
  - run_daily_etl による一括処理（カレンダー取得 → 株価取得 → 財務取得 → 品質チェック）
- ニュース収集（RSS）
  - RSS 取得、XML パース（defusedxml）、URL 正規化（utm 等除去）、記事ID は正規化 URL の SHA-256（先頭32文字）
  - SSRF 対策（リダイレクト検査、プライベートIP拒否）、レスポンスサイズ上限
  - raw_news への冪等保存と記事⇄銘柄（news_symbols）紐付け
- データ品質チェック
  - 欠損、スパイク（前日比閾値）、重複、日付不整合（未来日／非営業日データ）検出
  - QualityIssue オブジェクトで詳細を返却
- マーケットカレンダー管理
  - JPX カレンダーの更新ジョブ、営業日判定ヘルパー（next/prev/get_trading_days 等）
- 監査ログ（Audit）
  - シグナル→発注→約定までトレース可能なスキーマ（UUID ベースの冪等キー等）
  - 発注要求・約定等の永続化用DDL とインデックス

---

## 動作環境・前提

- Python 3.10 以上を想定（型ヒントと union 演算子を利用）
- 必要な外部パッケージ（最低限）
  - duckdb
  - defusedxml

インストール例:
```bash
python -m pip install "duckdb" "defusedxml"
```

（実運用では requirements.txt / Poetry / PDM 等で依存管理してください）

---

## セットアップ手順

1. リポジトリを取得して仮想環境を作成・有効化します。

2. 依存パッケージをインストールします。
   - 例: pip install duckdb defusedxml

3. 環境変数を用意します（.env または環境変数で設定）。
   - このパッケージはプロジェクトルートにある `.env`/`.env.local` を自動で読み込みます（自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API パスワード
     - SLACK_BOT_TOKEN: Slack 通知に使う Bot トークン
     - SLACK_CHANNEL_ID: 通知先チャンネル ID
   - 任意／デフォルト:
     - KABUSYS_ENV: development / paper_trading / live （デフォルト: development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL （デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動読み込みを無効化
     - KABU_API_BASE_URL: kabusapi のベース URL（デフォルト "http://localhost:18080/kabusapi"）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト "data/kabusys.duckdb"）
     - SQLITE_PATH: 監視用 sqlite のパス（デフォルト "data/monitoring.db"）

4. DuckDB スキーマを初期化します（例は後述の「使い方」参照）。

---

## 使い方（主要な API と例）

注意: ここではライブラリ内部 API の使用例を示します。CLI や外部サービス連携ラッパーは含まれません。

共通:
```python
from kabusys.config import settings
```

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
# settings.duckdb_path は Path オブジェクト
conn = init_schema(settings.duckdb_path)
```

2) 監査ログ用 DB 初期化（専用DBと transactional=True の使用例）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

3) J-Quants から差分 ETL（日次パイプライン）を実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
# conn: DuckDB 接続（init_schema で作成したもの）
result = run_daily_etl(conn, target_date=date.today())
# result は ETLResult オブジェクト（取得/保存件数・品質問題などを含む）
print(result.to_dict())
```

4) ニュース収集ジョブを実行
```python
from kabusys.data.news_collector import run_news_collection
# known_codes: 既知の銘柄コードセット（extract_stock_codes に使用）
results = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
# results はソースごとの新規保存件数辞書
```

5) マーケットカレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
```

6) 低レベルな J-Quants API 呼び出し
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
# id_token を自分で取得して渡すことも可能
quotes = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,3,1))
```

7) 品質チェックを個別に実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for issue in issues:
    print(issue.check_name, issue.severity, issue.detail)
```

ログレベルは環境変数 LOG_LEVEL で制御されます（Settings.log_level）。

---

## 注意事項 / 実装上のポイント

- 自動環境読み込み:
  - パッケージはプロジェクトルート（.git または pyproject.toml を探索）から `.env` と `.env.local` を自動読み込みします。OS 環境変数が優先され、`.env.local` は `.env` より優先して上書きします。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能です。
- J-Quants クライアント:
  - レート制御（120 req/min）とリトライ（最大 3 回）を組み込んでいます。
  - 401 受信時は自動でリフレッシュトークンから id_token を更新して 1 回だけ再試行します。
  - ページネーション対応（pagination_key）。
- ニュース収集:
  - XML パースに defusedxml を用いて XML インジェクション等を防止しています。
  - SSRF 対策としてリダイレクト先のスキーム確認、ホストがプライベートかどうかの判定、受信サイズ上限（10MB）などを実施します。
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証します。
- DuckDB スキーマ:
  - Raw → Processed → Feature → Execution → Audit の各層を定義しています。init_schema() は冪等にテーブル/インデックスを作成します。
  - 監査ログ（audit）用のスキーマは init_audit_schema / init_audit_db で追加または別DB化できます。
- 品質チェック:
  - Fail-Fast ではなく、検出された問題は QualityIssue リストとして返却し、呼び出し側が処理判断を行います。
- 型と互換性:
  - コードは Python 3.10 以上を想定しています。typing の union 演算子（|）等を使用しています。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージの主要なファイル構成（src/kabusys 以下）です。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理（.env 自動読み込み、Settings）
  - data/
    - __init__.py
    - jquants_client.py           — J-Quants API クライアント（fetch/save 関数）
    - news_collector.py           — RSS ベースのニュース収集・解析・DB保存
    - schema.py                   — DuckDB スキーマ定義・初期化
    - pipeline.py                 — ETL パイプライン（差分取得・バックフィル・品質チェック）
    - calendar_management.py      — マーケットカレンダー更新・営業日判定
    - audit.py                    — 監査ログ（signal/order/execution）スキーマ
    - quality.py                  — データ品質チェック
  - strategy/
    - __init__.py                 — 戦略層（空のエントリプレースホルダ）
  - execution/
    - __init__.py                 — 発注層（空のエントリプレースホルダ）
  - monitoring/
    - __init__.py                 — 監視関連（エントリプレースホルダ）

--- 

## 開発・運用に向けたヒント

- ETL を定期実行する場合は以下の点に留意してください。
  - J-Quants API のレート制限とリトライ挙動（429/Retry-After）を尊重すること。
  - run_daily_etl は market calendar を先に更新し、その後 trading day に合わせて差分取得を行います。
  - バックフィル日数（backfill_days）を調整すると API 側の後出し訂正への耐性が変わります。
- ローカル実行時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してテスト用の環境構成を行うと良いです。
- DuckDB ファイルのバックアップ・運用ポリシーを事前に決めておいてください。大規模データや複数プロセスからの同時書き込みには注意が必要です（DuckDB の同時書き込み特性を理解してください）。

---

もし README に追加したい項目（CLI 実行例、Docker コンテナ化、CI 設定、具体的な .env.example のテンプレート等）があれば教えてください。必要に応じてサンプル .env.example も作成します。