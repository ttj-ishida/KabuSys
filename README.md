# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（モジュール群）です。  
J-Quants / RSS / kabuステーション 等からデータを収集・保存し、ETL・品質チェック・監査ログ・カレンダー管理などの基盤機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを支える共通基盤ライブラリです。主な役割は次のとおりです。

- J-Quants API から株価・財務・マーケットカレンダーを取得
- RSS フィードからニュース記事を収集し、銘柄との紐付けを行う
- DuckDB を用いたスキーマ定義・初期化・保存（Raw / Processed / Feature / Execution / Audit 層）
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- マーケットカレンダー管理（営業日判定・次営業日/前営業日の計算）
- 監査ログ（signal → order_request → execution のトレースを保証）
- データ品質チェック（欠損、スパイク、重複、日付不整合）

設計上のポイント：
- API レート制限とリトライ、認証トークン自動更新を考慮
- データ保存は冪等（ON CONFLICT など）で安全に
- SSRF／XML Bomb などの安全性対策を多数組み込み

---

## 主な機能一覧

- data.jquants_client
  - J-Quants から daily_quotes（OHLCV）、financial statements、trading calendar を取得・保存
  - RateLimiter、リトライ、401時のトークンリフレッシュ、fetched_at 記録など対応

- data.news_collector
  - RSS フィードの取得（gzip 対応）、XML パース（defusedxml）、
    URL 正規化・トラッキング除去、記事 ID の生成（SHA-256 の先頭32文字）、
    raw_news / news_symbols への冪等保存
  - SSRF対策、最大レスポンスサイズ制限、記事内銘柄コード抽出

- data.schema
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution 層）
  - init_schema() で DB 初期化

- data.pipeline
  - 日次 ETL（run_daily_etl）：calendar → prices → financials → 品質チェック（run_all_checks）
  - 差分更新ロジック、backfill の取り込み

- data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days 等の営業日ロジック
  - calendar_update_job による夜間カレンダー更新

- data.audit
  - 監査用テーブル（signal_events / order_requests / executions）定義と初期化
  - init_audit_db() で監査DB初期化（UTC タイムゾーン固定）

- data.quality
  - 欠損チェック、スパイク検出、重複チェック、日付整合性チェック
  - QualityIssue オブジェクトリストを返す

- その他のパッケージ階層
  - strategy, execution, monitoring（将来的な戦略・発注・監視機能のための名前空間）

---

## セットアップ手順（開発用 / 最低限）

前提
- Python 3.10 以上（型注釈に | を使用しているため）
- pip が利用できること

1. リポジトリのクローン（省略）

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール（最低限）
   - pip install duckdb defusedxml
   - 他に必要なパッケージがあれば適宜追加してください（例: requests 等）

   注: リポジトリに requirements.txt / pyproject.toml があればそちらを利用してください。

4. パッケージのインストール（開発モードが便利）
   - pip install -e .

5. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` または `.env.local` を置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（一部）
     - JQUANTS_REFRESH_TOKEN  （J-Quants のリフレッシュトークン）
     - KABU_API_PASSWORD      （kabuステーション API のパスワード）
     - SLACK_BOT_TOKEN        （Slack 通知用 Bot トークン）
     - SLACK_CHANNEL_ID       （通知先 Slack チャンネル ID）
   - 任意 / デフォルト値あり
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
     - KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi
     - DUCKDB_PATH: デフォルト data/kabusys.duckdb
     - SQLITE_PATH: デフォルト data/monitoring.db

   参考: .env.example を用意しておく運用を推奨（リポジトリにない場合は README を参照して作成してください）。

---

## 使い方（代表的な例）

以下は Python スクリプトや REPL から呼び出す最小例です。

1) DuckDB スキーマの初期化
```python
from kabusys.data.schema import init_schema

# ファイル path または ":memory:"
conn = init_schema("data/kabusys.duckdb")
```

2) 監査DB（audit）初期化（専用DBを使う場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

3) 日次 ETL 実行
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

4) RSS ニュース収集（raw_news に保存）
```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = init_schema("data/kabusys.duckdb")

# known_codes を与えると記事と銘柄の紐付けを試みる
known_codes = {"7203", "6758", "8306"}  # など（銘柄リスト）
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)  # {source_name: new_inserted_count}
```

5) マーケットカレンダー関連の利用例
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = init_schema("data/kabusys.duckdb")
d = date(2026, 3, 18)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

6) データ品質チェックの実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

注意:
- run_daily_etl 等はエラーを吸収しつつ個別ステップを継続する設計です。戻り値の ETLResult に errors / quality_issues が含まれるためログや運用側で判定してください。
- J-Quants API のトークン取得は自動化されます（settings.jquants_refresh_token を必要とします）。rate limit（120 req/min）・リトライ・401 リフレッシュ等が実装済みです。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意、デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live、デフォルト development)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL、デフォルト INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env ロードを無効化

設定は .env または OS 環境変数から読み込まれます。自動読み込みはプロジェクトルート (.git または pyproject.toml) を探索して `.env` / `.env.local` を読みます。

---

## ディレクトリ構成（主要ファイル）

リポジトリの src/kabusys 以下（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数と Settings 管理（自動 .env ロード、必須チェック）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得・保存）
    - news_collector.py            — RSS → raw_news / news_symbols の収集処理
    - schema.py                    — DuckDB スキーマ定義・初期化
    - pipeline.py                  — ETL パイプライン（run_daily_etl など）
    - calendar_management.py       — マーケットカレンダー管理
    - audit.py                     — 監査ログテーブル初期化・管理
    - quality.py                   — データ品質チェック
  - strategy/
    - __init__.py                  — 戦略関連の名前空間（将来拡張）
  - execution/
    - __init__.py                  — 発注・ブローカー連携の名前空間（将来拡張）
  - monitoring/
    - __init__.py                  — 監視・メトリクスの名前空間（将来拡張）

各モジュールには詳細な docstring と設計注釈が含まれており、関数の利用方法や前提条件・副作用が明記されています。

---

## 運用上の注意

- J-Quants のレート制限（120 req/min）に従ってください（ライブラリは固定間隔のスロットリングを実装）。
- リトライロジックは 3 回まで（指数バックオフ）ですが、長時間の失敗監視は運用側で行ってください。
- DuckDB ファイルはバックアップ・ローテーションを検討してください。
- RSS フィード取得では SSRF / Gzip bomb / XML Bomb 対策を実装していますが、追加の内部ポリシーがあれば併用してください。
- audit テーブルは削除を想定していません。監査ログは原則保持して運用でローテートする場合は別 DB を用意することを推奨します。

---

## 追加情報 / 貢献

- バグ報告や改善提案は Issue を通してお願いします。
- 戦略（strategy）や発注（execution）モジュールは今後拡張する予定です。プルリクエスト歓迎します。

---

README の抜粋・利用例について質問があれば、実行シナリオや具体的なコード例（cron・Docker・CI での運用など）に合わせた補足を作成します。