# KabuSys

日本株向けの自動売買／データプラットフォームライブラリです。本リポジトリはデータ収集・ETL・品質チェック・監査ログといった基盤機能を提供し、戦略（strategy）や発注（execution）モジュールと組み合わせて自動売買システムを構築するための土台を担います。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を提供します。

- J-Quants API を用いた株価（OHLCV）・財務データ・JPX マーケットカレンダーの取得
  - API レート制限（120 req/min）遵守、リトライとトークン自動更新
  - 取得時刻（fetched_at）を UTC で記録し、Look-ahead bias を防止
- RSS からのニュース収集（安全対策多数：SSRF/ZIP爆弾対策、トラッキング除去）
- DuckDB を用いた 3 層データスキーマ（Raw / Processed / Feature）および Execution / Audit レイヤ
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル→発注→約定までのトレーサビリティ）

設計方針として「冪等性」「セキュリティ（SSRF, XML 攻撃等）」」「オペレーショナリティ（ログ、監査）」を重視しています。

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（認証、ページネーション、リトライ、レート制御）
  - fetch / save 関数（daily quotes, financial statements, market calendar）
- data/news_collector.py
  - RSS フィード取得、記事正規化、ID 生成（SHA-256）、DuckDB への冪等保存、銘柄抽出
  - defusedxml／SSRF／gzip サイズ制限等の安全対策
- data/schema.py
  - DuckDB 上のスキーマ定義（Raw / Processed / Feature / Execution）
  - init_schema(), get_connection()
- data/pipeline.py
  - 差分 ETL（prices, financials, calendar）、日次 ETL エントリポイント run_daily_etl()
  - 品質チェック呼び出し（data/quality.py）
- data/calendar_management.py
  - market_calendar の夜間更新ジョブ、営業日判定・前後営業日取得等ユーティリティ
- data/audit.py
  - 監査ログテーブル定義／初期化（signal_events, order_requests, executions）
- data/quality.py
  - 欠損・スパイク・重複・日付整合性チェック（QualityIssue）

その他:
- config.py: 環境変数読み込み・設定管理（.env/.env.local の自動読み込み、必須キーの検査）
- monitoring/, strategy/, execution/: 将来的な拡張用のパッケージプレースホルダ

---

## 前提条件 / 依存関係

本コードが依存している主なライブラリ（インストールが必要）:

- Python 3.9+（typings に基づく型注釈があるため）
- duckdb
- defusedxml

（プロジェクトの pyproject.toml / requirements.txt がある場合はそちらを参照してください）

pip 例:
```
pip install duckdb defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン／配置

2. 仮想環境を作成（推奨）
```
python -m venv .venv
source .venv/bin/activate   # Unix/macOS
.venv\Scripts\activate      # Windows
```

3. 依存ライブラリをインストール
```
pip install duckdb defusedxml
```

4. 環境変数（.env）を準備

プロジェクトルートに `.env`（および必要なら `.env.local`）を置くと、自動で読み込まれます（ただしテスト時等に無効化可能）。

例（.env）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=your_slack_token
SLACK_CHANNEL_ID=your_slack_channel_id

# 任意
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

自動ロードを無効にしたい場合:
```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

5. DuckDB スキーマ初期化（例）
Python REPL またはスクリプトで:
```
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```
これで必要なテーブルとインデックスが作成されます。

監査データベースを別途初期化する場合:
```
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方（代表的な操作）

以下は簡単なコード例です。任意のスクリプトやタスクランナー（cron, systemd timer）から呼び出して運用してください。

- 日次 ETL を実行（市場カレンダー→株価→財務→品質チェック）
```
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 市場カレンダー夜間更新ジョブを実行
```
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn, lookahead_days=90)
print("saved:", saved)
```

- RSS ニュース収集ジョブを実行（銘柄紐付けに known_codes を与える）
```
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 上場銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

- J-Quants の生データを手動で取得して保存
```
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
records = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = save_daily_quotes(conn, records)
```

- 品質チェックのみ実行
```
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i)
```

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API 用パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視データ等用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 値が設定されていると .env 自動読み込みを無効化

config.Settings クラス経由でアクセス可能（例: from kabusys.config import settings; settings.jquants_refresh_token）

---

## 開発・テストのヒント

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を探索）から行われます。テスト時に環境を汚したくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- jquants_client は内部でモジュールレベルのトークンキャッシュを保持します。テストで強制リフレッシュしたい場合は get_id_token(force_refresh=True) 相当の呼び出しを行うか、_get_cached_token の挙動を理解してください（外部からは get_id_token を直接使う）。
- news_collector._urlopen をモックすることでネットワーク呼び出しの差し替えが容易です。
- DuckDB の初期化後は同じ接続オブジェクトを使うとトランザクション管理やパフォーマンス面で有利です。

---

## ディレクトリ構成

主要ファイル・モジュール構成を抜粋します。

- src/kabusys/
  - __init__.py
  - config.py
  - monitoring/
    - __init__.py
  - execution/
    - __init__.py
  - strategy/
    - __init__.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - pipeline.py
    - calendar_management.py
    - schema.py
    - audit.py
    - quality.py
    - pipeline.py
- その他:
  - pyproject.toml (プロジェクトルートに存在する想定)
  - .env / .env.local（環境変数）

（README はコードの現状に合わせて要点のみ記載しています。strategy / execution / monitoring の内部は将来的に拡張されます）

---

## 運用上の注意

- J-Quants の API レート制限（120 req/min）を尊重するため、jquants_client は固定間隔スロットリングとリトライを実装しています。独自に追加の並列リクエストを行う場合はレート制御に注意してください。
- ニュースフィード取得では SSRF・XML BOM（DefusedXml）・レスポンスサイズ制限などの安全対策を実施していますが、運用環境のポリシーに応じてホワイトリストやプロキシ経由のアクセスなどを追加してください。
- DuckDB ファイルはプロダクションではバックアップ戦略を考慮してください（定期的なスナップショット等）。

---

## 参考: よく使う API を短くまとめた例

- スキーマ初期化:
```
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL 実行:
```
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)
```

- RSS 収集:
```
from kabusys.data.news_collector import run_news_collection
res = run_news_collection(conn)
```

---

質問や補足があれば、どの部分を深掘りしたいか（例: ETL の調整方法、DuckDB スキーマ説明の詳細、テスト方法、運用パターン）を教えてください。README をプロジェクトの実状に合わせて追記・調整します。