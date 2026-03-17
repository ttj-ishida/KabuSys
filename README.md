# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。J-Quants API や RSS フィードから市場データ・財務データ・ニュースを取得し、DuckDB に保存・品質チェック・監査ログ管理までを行うことを目的としています。

主な設計方針は「冪等性」「トレーサビリティ」「セキュリティ（SSRF等対策）」「API レート制限遵守」「品質チェックの体系化」です。

---

## 主な機能一覧

- J-Quants API クライアント
  - 株価日足（OHLCV）取得（ページネーション対応）
  - 財務データ（四半期 BS/PL）取得
  - JPX マーケットカレンダー取得
  - トークン自動リフレッシュ、リトライ、固定間隔のレート制御

- ニュース収集（RSS）
  - RSS 取得・XML 安全パース（defusedxml）
  - URL 正規化（トラッキングパラメータ除去）、記事ID（SHA-256ベース）生成
  - SSRF対策（スキーム検証・プライベートホスト検出・リダイレクト検査）
  - DuckDB への冪等保存（INSERT ... ON CONFLICT / INSERT ... RETURNING）
  - 銘柄コード抽出および news_symbols テーブルへの紐付け

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
  - 初期化ヘルパー（init_schema / init_audit_schema）
  - 各種インデックス作成

- ETL パイプライン
  - 差分更新（最終取得日に基づく差分算出とバックフィル対応）
  - 市場カレンダー先読み（lookahead）
  - 品質チェック（欠損、スパイク、重複、日付不整合）
  - run_daily_etl で一括実行

- カレンダー管理
  - 営業日判定、前後の営業日取得、範囲の営業日リスト取得
  - 夜間バッチでのカレンダー更新ジョブ

- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定 のトレーサビリティを保持する監査テーブル群
  - 発注要求は冪等キー（order_request_id）で管理

---

## 必要環境・依存関係

- Python 3.10+
- 必要なライブラリ（主なもの）
  - duckdb
  - defusedxml

（実際のプロジェクトでは pyproject.toml / requirements.txt に依存関係を定義してください）

---

## セットアップ手順（開発向け）

1. リポジトリをクローンして仮想環境を用意
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （パッケージ化されていれば）pip install -e .

3. 環境変数を設定
   - ルートに `.env` または `.env.local` を配置すると、モジュール起動時に自動で読み込まれます（CWD ではなくパッケージ位置からプロジェクトルートを探索）。
   - 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 必要な環境変数（主要）

必須（実行する機能による）:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション等 API 用パスワード
- SLACK_BOT_TOKEN — Slack 通知用トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネルID

任意（デフォルトあり）:

- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルトは http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）

（.env.example を参考に .env を作成することを想定しています）

---

## 使い方（主要な API 例）

以下は Python REPL / スクリプトから使うサンプルです。

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# デフォルトの DUCKDB_PATH を使用する場合
conn = init_schema(settings.duckdb_path)
# もしくはインメモリ DB
# conn = init_schema(":memory:")
```

- 監査スキーマの追加（audit）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)  # conn は init_schema で得た接続
```

- 日次 ETL の実行（J-Quants から差分取得 → 保存 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

- ニュース収集（RSS）と保存
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes は銘柄抽出に使う有効な銘柄コードの集合
saved_map = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set(["7203","6758"]))
print(saved_map)  # {source_name: 新規保存件数}
```

- カレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("saved:", saved)
```

- 品質チェックを単独で実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn)
for i in issues:
    print(i)
```

- J-Quants の個別呼び出し（必要な場合）
```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
token = get_id_token()
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

---

## 注意点・設計上のポイント

- レート制御: J-Quants API は 120 req/min を想定しており、内部で固定間隔スロットリングを行っています。
- リトライ: ネットワーク障害や 429/408/5xx に対して指数バックオフでリトライ（最大3回）。401 は自動的にトークンをリフレッシュして再試行します（1回のみ）。
- 冪等性: DuckDB への保存は ON CONFLICT DO UPDATE / DO NOTHING を使用し、同一キーの重複挿入を安全に処理します。
- ニュース収集のセキュリティ: XML の安全パース（defusedxml）、SSRF対策（スキーム検証、プライベートアドレス拒否、リダイレクト検査）、レスポンスサイズ制限等を実施しています。
- トレーサビリティ: 監査ログ（signal_events, order_requests, executions）によりシグナルから約定までを UUID で辿れるように設計されています。
- 日付の扱い: DuckDB からの日付値は date オブジェクトに正規化されます。市場カレンダーが未取得の場合は曜日ベースのフォールバック（平日＝営業日）を使用します。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数 / 設定の自動読み込みと Settings クラス
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
  - news_collector.py — RSS ニュース収集・正規化・保存・銘柄抽出
  - schema.py — DuckDB スキーマ定義と init_schema / get_connection
  - pipeline.py — ETL パイプライン（差分更新・品質チェック）
  - calendar_management.py — 市場カレンダー管理・営業日ロジック
  - audit.py — 監査ログテーブル定義と初期化
  - quality.py — データ品質チェック（欠損・重複・スパイク・日付不整合）
- strategy/
  - __init__.py (戦略層用プレースホルダ)
- execution/
  - __init__.py (発注/ブローカー連携用プレースホルダ)
- monitoring/
  - __init__.py (監視・メトリクス用プレースホルダ)

---

## 開発メモ / テスト向け

- テストのために環境変数の自動読み込みを無効化するには
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- DuckDB のテストは init_schema(":memory:") を使用するとインメモリ DB で実行できます。
- news_collector._urlopen など一部のネットワーク呼び出しはテストでモックすることを想定して設計されています。

---

以上です。必要であれば次の追加を作成します:
- .env.example のテンプレート
- より詳しい API リファレンス（関数引数/戻り値の詳細）
- 開発用の Makefile / tox / pytest 設定例

必要なものを教えてください。