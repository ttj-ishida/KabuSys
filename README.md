# KabuSys

日本株向け自動売買基盤のコアライブラリです。データ取得（J‑Quants）、ニュース収集、ETLパイプライン、データ品質チェック、監査ログなどを備えたバックエンドモジュール群を提供します。

主な目的は「データ収集 → 永続化（DuckDB） → 品質チェック → 戦略／発注へ引き渡す」までの基盤機能を安定して再利用可能にすることです。

---

## 機能一覧

- 環境設定管理
  - .env / .env.local を自動で読み込む（プロジェクトルートを探索）
  - 必須環境変数の取得と検証（Settings オブジェクト）
- J‑Quants API クライアント（kabusys.data.jquants_client）
  - ID トークンの取得（refresh token → id token）
  - 株価日足（OHLCV）・財務データ・市場カレンダーの取得（ページネーション対応）
  - API レート制御（120 req/min）・リトライ・401 時の自動リフレッシュ
  - DuckDB へ冪等に保存する save_* 関数（ON CONFLICT DO UPDATE）
  - fetched_at によるトレーサビリティ（UTC）
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得・XML パース（defusedxml 使用）
  - URL 正規化 / トラッキングパラメータ除去 / 記事ID の生成（SHA-256）
  - SSRF 対策（スキーム検証・プライベートIP拒否・リダイレクト検査）
  - 受信サイズ制限・gzip 対応・DuckDB への冪等保存（INSERT ... RETURNING）
  - テキスト前処理・銘柄コード抽出（4桁コード）
- スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル DDL を提供
  - init_schema(db_path) で DuckDB を初期化（冪等）
  - インデックス定義あり
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（最終取得日からの差分）・バックフィル対応
  - 市場カレンダー先読み・品質チェック呼び出しを含む日次 ETL（run_daily_etl）
  - ETL 結果を ETLResult で返す（品質問題・エラーログを含む）
- 品質チェック（kabusys.data.quality）
  - 欠損（OHLC）検出、スパイク検出（前日比閾値）、重複、日付整合性検査
  - QualityIssue オブジェクトで問題の詳細・サンプル行を返す
- 監査ログ（kabusys.data.audit）
  - シグナル→発注要求→約定までをトレースする監査用テーブル群（init_audit_schema）
  - 発注の冪等キーやステータス遷移を考慮した設計

補足：
- strategy/execution/monitoring パッケージはエントリポイントを想定した構成（現状は空パッケージ）。
- データ永続化は主に DuckDB を想定。監視用の SQLite なども環境変数で指定可能。

---

## セットアップ手順

前提
- Python 3.9+（typing の | など使用）
- Git（プロジェクトルート検出に必要）
- ネットワーク接続（J‑Quants / RSS 等）

1. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （必要なら logging 等は標準ライブラリで賄われます）
   - 将来的にパッケージ化されていれば pip install -e . 等でインストール可能

3. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml がある場所）に .env を作成するか、OS 環境変数を設定します。
   - 環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN: J‑Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
     - KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID: 通知先チャンネル ID（必須）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: SQLite パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
   - 自動 .env 読み込みを無効にする場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

4. データベース初期化
   - Python REPL やスクリプトから DuckDB スキーマを初期化します（例は次節）。

---

## 使い方（主要な API とサンプル）

※ 以下は簡易的なサンプルコードです。実運用では例外処理やログ設定、認証情報の管理を適切に行ってください。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# 監査ログテーブルを追加したい場合
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```

2) J‑Quants から株価等を取得して保存
```python
from kabusys.data import jquants_client as jq
# get_id_token() は settings.jquants_refresh_token を用いて id token を返す
token = jq.get_id_token()
records = jq.fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
```

3) ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
# known_codes は valid な銘柄コードの集合（例えば証券コード一覧）
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(results)  # {source_name: saved_count}
```

4) 日次 ETL 実行（カレンダー・株価・財務・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を省略すると今日
if result.has_errors:
    print("ETL 中にエラーが発生しました:", result.errors)
if result.has_quality_errors:
    print("品質エラーあり:", [q.check_name for q in result.quality_issues])
```

5) 品質チェック単体実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

6) 設定値取得
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)  # Path オブジェクト
```

---

## よくある運用ポイント / 注意事項

- J‑Quants の API レート制限（120 req/min）をモジュールで守る設計です。大量ページネーション時は処理時間を考慮してください。
- get_id_token はリフレッシュトークンを用いるため、環境変数 JQUANTS_REFRESH_TOKEN を必ず設定してください。
- .env のパースはシェル風（export 対応、クォート・コメント処理あり）ですが、特殊ケースに注意してください。
- ニュース収集では SSRF 対策・レスポンスサイズ制限・gzip 解凍後のサイズチェックを行っていますが、外部フィードに依存するため常に堅牢なエラーハンドリングを行ってください。
- DuckDB のファイルはデフォルトで data/kabusys.duckdb に作成されます。バックアップや格納先は運用に合わせて設定してください。
- ETL は各ステップで例外をキャッチして処理を継続する設計です。呼び出し側で ETLResult を参照して問題を判断してください。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数・Settings 管理（.env 自動ロード機能含む）
  - data/
    - __init__.py
    - jquants_client.py             — J‑Quants API クライアント（fetch/save）
    - news_collector.py             — RSS ニュース収集・保存ロジック
    - schema.py                     — DuckDB スキーマ定義・初期化
    - pipeline.py                   — ETL パイプライン（差分取得・品質チェック）
    - audit.py                      — 監査ログ（信頼性／トレーサビリティ）
    - quality.py                    — データ品質チェック
  - strategy/
    - __init__.py                   — 戦略層のエントリ（拡張ポイント）
  - execution/
    - __init__.py                   — 発注実行層のエントリ（拡張ポイント）
  - monitoring/
    - __init__.py                   — 監視・メトリクス用プレースホルダ

---

## 開発 / テストに関するヒント

- 自動 .env ロードをテストで無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- network / HTTP を伴う関数群はモック可能な設計（例: news_collector._urlopen を差し替え）になっています。ユニットテストは外部依存を切り離して実施してください。
- DuckDB のインメモリ ":memory:" を使うとテストが容易です（init_schema(":memory:")）。

---

必要であれば、README に以下を追加できます：
- .env.example の雛形
- 実運用で推奨される systemd / cron / container 実行例
- Slack 通知や監視（Prometheus / Grafana）との連携方法
- strategy / execution のテンプレート実装例

追加したいセクションがあれば教えてください。