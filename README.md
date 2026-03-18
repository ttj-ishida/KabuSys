# KabuSys

日本株向けの自動売買プラットフォーム基盤ライブラリです。  
データ取得（J-Quants）、ETLパイプライン、DuckDBベースのスキーマ、ニュース収集、データ品質チェック、マーケットカレンダー管理、監査ログ（トレーサビリティ）など、運用に必要な基盤機能を提供します。

---

## 主要機能（概要）

- 環境変数 / .env 管理
  - プロジェクトルートを自動検出して `.env` / `.env.local` を読み込み（OS環境変数優先、`.env.local` は上書き）
  - 自動読み込みを無効化するフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダー取得
  - レート制限（120 req/min）遵守、リトライ（指数バックオフ、401 時の自動トークンリフレッシュ対応）
  - 取得時刻（fetched_at）を UTC で記録、DuckDB への冪等保存（ON CONFLICT）
- ニュース収集
  - RSS フィードから記事を取得し前処理して DuckDB に保存
  - URL 正規化（トラッキングパラメータ除去）、SSRF 対策、受信サイズ制限、XML の安全パース
  - 記事IDは正規化URLの SHA-256（先頭32文字）で生成して冪等性を担保
  - 銘柄コード抽出・紐付け機能
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層を定義するDDLを一括初期化
  - インデックス、監査用スキーマ（audit）を含む
- ETL パイプライン
  - 差分更新（最終取得日ベース） + バックフィル（後出し修正を吸収）
  - 市場カレンダー先読み、品質チェック（欠損・重複・スパイク・日付整合性）
  - 日次 ETL のエントリポイント（run_daily_etl）
- マーケットカレンダー管理
  - 営業日判定、前後営業日取得、期間内営業日列挙、カレンダー差分更新ジョブ
  - DB 未取得時は曜日ベースのフォールバック（平日を営業日扱い）
- 監査（Audit）
  - シグナル → 発注要求 → 約定へと UUID で連鎖する監査テーブル群
  - order_request_id による冪等性保証、すべて UTC タイムスタンプ保存
- データ品質チェック
  - 欠損データ、スパイク（前日比閾値）、重複、日付不整合を検出
  - 各チェックは QualityIssue を返し呼び出し側で対処を決定可能

---

## 要件

- Python 3.10+
  - 型注釈に `X | None` を使用しているため Python 3.10 以上を想定
- 必要なパッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API, RSS）

インストール例（仮）:
```bash
python -m pip install "duckdb" "defusedxml"
# またはプロジェクトに requirements.txt があれば:
# pip install -r requirements.txt
```

---

## インストール（開発環境向け）

パッケージが setuptools/pyproject で配布されている前提の場合:
```bash
# ソースディレクトリで
pip install -e .
```
あるいは必要パッケージを個別にインストールしてください（上記参照）。

---

## 環境変数（必須 / 推奨）

少なくとも下記の環境変数を設定してください（`.env` に記載するのが便利です）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID — 通知先のチャンネル ID

オプション / デフォルト:
- KABUSYS_ENV — one of "development", "paper_trading", "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用など、デフォルト: data/monitoring.db）

.env 自動読み込み:
- プロジェクトルートは `.git` または `pyproject.toml` を基準に自動検出され、`.env` → `.env.local` の順で読み込まれます。
- OS 環境変数は保護され、`.env.local` の上書きは OS 変数以外に対して行われます。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時などに使用）。

---

## クイックスタート（コード例）

1) DuckDB スキーマ初期化:
```python
from kabusys.data import schema

# ファイル DB を初期化（親ディレクトリは自動作成）
conn = schema.init_schema("data/kabusys.duckdb")
```

2) 日次 ETL を実行:
```python
from kabusys.data import pipeline
from datetime import date

# conn は init_schema の返り値
result = pipeline.run_daily_etl(conn, target_date=date.today())

# 結果の要約
print(result.to_dict())
```

3) RSS ニュース収集:
```python
from kabusys.data.news_collector import run_news_collection

# known_codes は銘柄抽出に使用するコードの set (例: {"7203","6758",...})
stats = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
print(stats)  # {source_name: new_count, ...}
```

4) カレンダー夜間ジョブ:
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn, lookahead_days=90)
print(f"saved calendar rows: {saved}")
```

5) 監査スキーマのみ初期化（必要に応じて別DBで管理可能）:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

注意:
- J-Quants API 呼び出しは rate limit の都合で遅延が入る可能性があります。
- ETL の各ステップは独立にエラーハンドリングされ、途中失敗しても残りの処理は継続します（結果に errors が追加される）。

---

## よく使う公開 API（抜粋）

- kabusys.config.settings
  - settings.jquants_refresh_token, kabu_api_password, kabu_api_base_url, slack_bot_token, slack_channel_id, duckdb_path, env, log_level など

- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)

- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...)
  - run_prices_etl(...)
  - run_financials_etl(...)
  - run_calendar_etl(...)

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles)
  - run_news_collection(conn, sources=None, known_codes=None)

- kabusys.data.calendar_management
  - is_trading_day(conn, d)
  - next_trading_day(conn, d)
  - prev_trading_day(conn, d)
  - get_trading_days(conn, start, end)
  - calendar_update_job(conn, lookahead_days=90)

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)
  - check_missing_data, check_spike, check_duplicates, check_date_consistency

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

---

## ディレクトリ構成

以下は主要なファイルと役割の一覧（リポジトリの src/kabusys 以下を想定）:

- src/kabusys/
  - __init__.py — パッケージ初期化、バージョン等
  - config.py — 環境変数/.env のパース・設定アクセス（settings オブジェクト）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存・認証・リトライ・レート制御）
    - news_collector.py — RSS 取得、記事正規化、DuckDB 保存、銘柄抽出
    - schema.py — DuckDB のスキーマ定義と初期化（Raw / Processed / Feature / Execution）
    - pipeline.py — ETL パイプライン（差分取得・保存・品質チェック）
    - calendar_management.py — マーケットカレンダー更新と営業日判定ユーティリティ
    - audit.py — 監査用テーブル定義・初期化（signal / order_request / executions）
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - pipeline.py — 日次 ETL の統合処理
  - strategy/ — 戦略関連（空の __init__.py、戦略実装を配置）
  - execution/ — 発注実行（空の __init__.py、証券会社連携等を配置）
  - monitoring/ — 監視関連（空の __init__.py、Prometheus/Slack 等の実装を配置）

---

## 運用上の注意点 / 設計上の特徴

- API 呼び出しのレート制御（120 req/min）やリトライ・トークンリフレッシュなど、実運用向けの堅牢性を重視しています。
- データ取得時点（fetched_at）や UTC のタイムゾーン管理により Look-ahead Bias を防止できるよう設計されています。
- DuckDB による永続化でローカル環境でも高速に分析・ETL が可能です。":memory:" を指定して一時的にインメモリ DB を使うこともできます。
- ニュース収集は SSRF 対策、Content-Length/受信サイズ制限、Gzip 解凍後サイズ検査などセキュリティ・リソース対策を多数実装しています。
- 品質チェックは Fail-Fast ではなく、問題を網羅的に収集して呼び出し側に委ねる設計です。

---

## 参考・今後の拡張案

- kabuステーション（証券会社）との発注/約定連携実装（execution パッケージ）
- 戦略レイヤー / ポートフォリオ最適化の実装
- 監視・アラート（Slack 通知 / メトリクス出力）
- テスト用のモッククライアントや CI ワークフロー

---

必要であれば、README の英語版やインストール用の requirements.txt、サンプル .env.example、簡単なユニットテストの雛形、CLI ラッパー（ETL を実行するコマンドラインツール）の追加例も作成できます。どれを優先するか教えてください。