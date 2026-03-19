# KabuSys

日本株向けの自動売買プラットフォーム（ライブラリ）です。  
市場データ取得、ETL、データ品質チェック、特徴量生成、ファクター研究、ニュース収集、監査ログなど、量的運用に必要な基盤処理を提供します。

---

## 概要

KabuSys は以下を目的としたモジュール群を含む Python パッケージです。

- J-Quants API からの市場データ取得と DuckDB への冪等保存
- RSS を使ったニュース収集と銘柄紐付け
- DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- ファクター（モメンタム / バリュー / ボラティリティ等）の計算と研究ユーティリティ
- 監査ログ（signal → order → execution のトレース）用スキーマ
- マーケットカレンダー管理（営業日判定 / next/prev / calendar 更新）
- 設定（.env の自動読み込み / 環境変数管理）

設計方針の一部：
- DuckDB を中心としたオンディスク DB を採用（in-memory も可）
- API 呼び出しはレート制御とリトライ、トークン自動更新を備える
- ETL は冪等（ON CONFLICT）により安全に何度でも実行可能
- Research / Data モジュールは本番口座や発注 API にアクセスしない（安全）

---

## 主な機能一覧

- data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - レートリミット、再試行、トークン自動更新、fetched_at の記録
- data.news_collector
  - RSS 取得（gzip 対応、SSRF 対策、XML 安全パース）
  - 記事正規化・記事ID生成（URL正規化→SHA256）、raw_news 保存、news_symbols 紐付け
- data.schema
  - DuckDB スキーマ作成（Raw / Processed / Feature / Execution 層）
  - init_schema / get_connection
- data.pipeline
  - run_daily_etl：calendar → prices → financials → 品質チェック の一括処理
  - 差分更新 / バックフィル / 品質チェックの統合
- data.quality
  - 欠損・重複・スパイク・日付不整合のチェックと QualityIssue の報告
- data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- data.audit
  - 監査ログ（signal_events, order_requests, executions）のスキーマ初期化
- research
  - calc_momentum / calc_volatility / calc_value（prices_daily / raw_financials を参照）
  - calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（data.stats で提供）
- 設定管理（kabusys.config）
  - .env 自動読み込み（プロジェクトルート検出）、必須環境変数チェック、KABUSYS_ENV 判定

---

## 要件（必須パッケージ）

- Python 3.10+
- duckdb
- defusedxml

インストール例:
```bash
python -m pip install "duckdb" "defusedxml"
# またはプロジェクトの requirements.txt / pyproject に従ってください
```

---

## セットアップ手順

1. リポジトリをチェックアウト（任意）
2. Python 環境を用意（推奨: venv / pyenv）
3. 依存パッケージをインストール（上記参照）
4. 環境変数を設定（.env をプロジェクトルートに置くと自動読み込みされます）

必須の環境変数（一例）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API 用パスワード（発注系を使う場合）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — 通知を行う場合

オプション:
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB など用（デフォルト: data/monitoring.db）

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に `.env` と `.env.local` を読み込みます
- OS 環境変数が優先されます
- テスト等で自動ロードを無効にするには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

例 .env（簡易）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
```

---

## 初期化 / 使い方（簡単な例）

以下は Python REPL / スクリプト等から実行する例です。

1) DuckDB スキーマ初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)  # デフォルト: data/kabusys.duckdb
```

2) 日次 ETL 実行
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を与えることも可能
print(result.to_dict())
```

3) ニュース収集ジョブ（RSS）
```python
from kabusys.data.news_collector import run_news_collection

# known_codes は銘柄抽出で利用する既知のコード集合（任意）
known_codes = {"7203", "6758", "9984"}
stats = run_news_collection(conn, known_codes=known_codes)
print(stats)  # { source_name: saved_count, ... }
```

4) J-Quants から個別取得・保存（例）
```python
from kabusys.data import jquants_client as jq
from kabusys.config import settings
from datetime import date

token = None  # None ならモジュールキャッシュを使用して自動リフレッシュ
recs = jq.fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, recs)
print("fetched:", len(recs), "saved:", saved)
```

5) 研究用ファクター計算例
```python
from kabusys.research import calc_momentum, calc_volatility, calc_value, zscore_normalize
from datetime import date

d = date(2024, 1, 31)
mom = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
val = calc_value(conn, d)

# Zスコア正規化（例: mom_1m と ma200_dev を正規化）
normed = zscore_normalize(mom, ["mom_1m", "ma200_dev"])
```

6) 監査スキーマ初期化（監査用 DB を別で用意する場合）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

---

## よく使う API（抜粋）

- kabusys.config.settings — 環境変数ラッパー（必須 env のチェック付き）
- kabusys.data.schema.init_schema(db_path) — DuckDB スキーマ初期化
- kabusys.data.pipeline.run_daily_etl(conn, target_date=None, ...) — 日次 ETL
- kabusys.data.news_collector.run_news_collection(conn, sources=None, known_codes=None)
- kabusys.data.jquants_client.fetch_* / save_* — データ取得と保存
- kabusys.data.quality.run_all_checks(conn, target_date=None, ...)
- kabusys.data.calendar_management.calendar_update_job(conn)
- kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary
- kabusys.data.stats.zscore_normalize — Z スコア正規化

---

## 開発者向けメモ / 注意点

- Python の型ヒントに | を使っているため Python 3.10 以上を想定しています。
- J-Quants API のレート制限 (120 req/min) に合わせて内部でスロットリングが実装されています。
- jquants_client は 401 受信時にリフレッシュトークンで自動的に ID トークンを更新してリトライします（1 回のみ）。
- DuckDB のトランザクションはファイルベースでも動作しますが、並列書き込みには注意してください。
- news_collector は SSRF 対策や XML インジェクション対策（defusedxml）を実施していますが、外部ソースの扱いは常に慎重に。
- ETL は Fail-Fast ではなく、品質チェックは結果を返して呼び出し元が対応を決める設計です。
- .env の自動ロードはプロジェクトルートを探索して行います。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成

主要ファイル・モジュール（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py — 環境変数管理・.env 自動読み込み
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント / 保存関数
    - news_collector.py — RSS 収集・正規化・DB 保存
    - schema.py — DuckDB スキーマ定義・初期化
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - pipeline.py — ETL パイプライン（run_daily_etl など）
    - features.py — 特徴量ユーティリティ（再エクスポート）
    - calendar_management.py — カレンダー管理・営業日判定
    - audit.py — 監査ログ用スキーマ初期化
    - etl.py — ETLResult 再エクスポート
    - quality.py — データ品質チェック
  - research/
    - __init__.py
    - feature_exploration.py — forward returns / IC / summary 等
    - factor_research.py — momentum / volatility / value 計算
  - strategy/
    - __init__.py  — 戦略モデルやルールの置き場（現在はパッケージ化のみ）
  - execution/
    - __init__.py  — 発注・約定管理のモジュール領域（拡張予定）
  - monitoring/
    - __init__.py  — 監視系（未実装・拡張予定）

---

## 例: 最小実行フロー（まとめ）

1. .env を準備
2. 必要パッケージをインストール
3. Python スクリプトで
   - init_schema(settings.duckdb_path)
   - run_daily_etl(conn)
   - run_news_collection(conn)

---

## ライセンス / 貢献

このリポジトリにライセンスヘッダや CONTRIBUTING.md がない場合はリポジトリポリシーに従ってください。外部 API の認証情報は決して公開リポジトリにコミットしないでください。

---

何か特定の使い方（例: ETL 周期の cron 設定、kabu API を使った発注サンプル、DuckDB のクエリ例など）についてドキュメントを充実させたい場合は、どの部分を優先して書けばよいか教えてください。