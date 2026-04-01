# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）の README です。  
本リポジトリはデータ ETL、ニュース NLP、研究用ファクター、監査ログ等を含むモジュール群を提供します。

目次
- プロジェクト概要
- 主な機能一覧
- 前提条件 / インストール
- 環境変数（.env）と設定
- セットアップ手順
- 使い方（主要 API の例）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを支える共通ライブラリ群です。  
データ取得（J-Quants 連携）、日次 ETL、ニュース収集と LLM を使ったセンチメント評価、ファクター計算、監査ログ（発注→約定のトレーサビリティ）などを提供します。  
設計上、バックテストでのルックアヘッドバイアスを避ける実装方針（日時の参照やクエリ条件）を重視しています。

---

## 主な機能一覧

- 設定管理
  - .env / 環境変数自動読み込み（プロジェクトルート検出）
  - 必須値の取得ラッパー（settings）

- データ（data）
  - J-Quants API クライアント（レートリミット・リトライ・トークン自動更新対応）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 市場カレンダー管理（営業日判定・next/prev）
  - ニュース収集（RSS, 前処理, SSRF/サイズ対策）
  - 監査ログ初期化 / 専用 DB 作成（audit テーブル群）

- 研究（research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（情報係数）、ファクター統計サマリー
  - zscore 正規化ユーティリティ

- AI（ai）
  - ニュース NLP（gpt-4o-mini を用いた銘柄ごとのセンチメント評価: score_news）
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成: score_regime）

- その他ユーティリティ
  - 統計ユーティリティ（z-score）
  - DuckDB を前提とした処理（接続受け渡し設計）

---

## 前提条件 / インストール

必要な Python バージョン:
- Python 3.10+

主な外部依存パッケージ:
- duckdb
- openai (OpenAI の新版 SDK を想定)
- defusedxml

インストール例（仮: 本パッケージをローカルで開発しながら使う場合）:

```bash
# 基本ライブラリをインストール
pip install duckdb openai defusedxml

# （パッケージをプロジェクトルートで editable install できる場合）
pip install -e .
```

※ pyproject.toml / setup.py がある想定で pip install -e . が使えます。ない場合は必要な依存だけ個別に pip インストールしてください。

---

## 環境変数（.env）と設定

config.py により、プロジェクトルート（.git または pyproject.toml があるディレクトリ）から自動で `.env` / `.env.local` を読み込みます。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数（名前と説明 / デフォルト）:

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants リフレッシュトークン（ETL で使用）

- KABU_API_PASSWORD (必須)
  - kabu ステーション API のパスワード

- KABU_API_BASE_URL
  - kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）

- SLACK_BOT_TOKEN (必須)
  - Slack 通知用 Bot トークン

- SLACK_CHANNEL_ID (必須)
  - Slack 通知先チャンネル ID

- DUCKDB_PATH
  - DuckDB ファイルパス（例: data/kabusys.duckdb; デフォルト: data/kabusys.duckdb）

- SQLITE_PATH
  - 監視用 sqlite（デフォルト: data/monitoring.db）

- PID_FILE_PATH
  - 実行プロセスの PID ファイル（デフォルト: data/execution.pid）

- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
  - 監視のしきい値（%）

- KABUSYS_ENV
  - 環境名 (development | paper_trading | live)。デフォルト development

- LOG_LEVEL
  - ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）。デフォルト INFO

- OPENAI_API_KEY
  - OpenAI API キー（ai モジュールで使用）。関数引数で上書き可能。

例: .env（最低限の必須キーを埋める）

```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動。

2. 依存ライブラリをインストール:

   ```bash
   pip install duckdb openai defusedxml
   ```

   （必要なら他の依存も pip で追加）

3. プロジェクトルートに `.env` を作成し、上記の必須値を設定。

4. DuckDB のデータベースディレクトリを作成（パスに親ディレクトリが必要な場合）:

   ```bash
   mkdir -p data
   ```

5. （任意）監査ログ用 DB 初期化:

   Python コンソールで:

   ```python
   from kabusys.config import settings
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db(settings.duckdb_path)  # または別パスを指定
   conn.close()
   ```

---

## 使い方（主要 API の例）

以下は代表的な使い方です。すべて DuckDB 接続を渡す設計です。

- DuckDB 接続を作る（設定からパスを取得）

```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する（run_daily_etl）

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定（省略時は今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- 単独の株価 ETL / 財務 ETL / カレンダー ETL を呼ぶ

```python
from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl

prices_fetched, prices_saved = run_prices_etl(conn, target_date=date(2026,3,20))
financials_fetched, financials_saved = run_financials_etl(conn, target_date=date(2026,3,20))
cal_fetched, cal_saved = run_calendar_etl(conn, target_date=date(2026,3,20))
```

- ニュース NLP による銘柄スコアリング（score_news）

```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY は環境変数か api_key 引数で指定
written = score_news(conn, target_date=date(2026,3,20), api_key=None)
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定（score_regime）

```python
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- ニュース RSS の収集（fetch_rss）

```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

- 監査ログ DB の初期化（専用 DB を作る）

```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# settings.duckdb_path を使うか別ファイルを渡す
audit_conn = init_audit_db("data/audit.duckdb")
# 以降 audit_conn を使って監査テーブルに発注ログ等を書き込む
```

注意点:
- AI 呼び出し（score_news / score_regime）は OpenAI API キーが必須です。api_key 引数で注入するか、環境変数 OPENAI_API_KEY を設定してください。
- 各関数は DuckDB 接続（kabusys 側で期待するスキーマが作られていること）を前提とします。ETL の初回実行前にスキーマ（テーブル定義）を用意してください（本 README では DDL は割愛）。

---

## ディレクトリ構成

主要ファイル・モジュール構成（src/kabusys 以下、抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP（AI によるセンチメント）
    - regime_detector.py            — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（ETL 用）
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETLResult 再エクスポート
    - news_collector.py             — RSS ニュース収集
    - calendar_management.py        — 市場カレンダー管理
    - quality.py                    — データ品質チェック
    - stats.py                      — 汎用統計ユーティリティ
    - audit.py                      — 監査ログテーブル初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py            — モメンタム/ボラティリティ/バリュー等
    - feature_exploration.py        — 将来リターン・IC・統計サマリー
  - monitoring/ (存在する場合監視コード)
  - strategy/ execution/ (戦略・実行層は別モジュールとして想定)

上記は本リポジトリに含まれる主要モジュールの一覧です。各モジュールは DuckDB 接続や外部 API キーの注入を受ける形で設計されています。

---

## 補足 / 運用上の注意

- Look-ahead bias（バックテストで未来情報を参照してしまう問題）を避ける設計になっていますが、運用やテストで誤って現在時刻を参照するコードを書かないように注意してください。
- OpenAI 呼び出しは失敗時にフェイルセーフ（スコア 0 など）で続行する実装が多くありますが、API コストやレート制限を考慮して実行頻度を制御してください。
- J-Quants API のレート制限（120 req/min）に従うよう内部で RateLimiter を実装していますが、大量並列処理時の外部制約に注意してください。
- DuckDB の executemany にまつわる互換性（空リスト不可など）を考慮した実装がなされています。DuckDB バージョンに依存する挙動に注意してください。

---

もし README に追加したい具体的な手順（例: docker-compose, CI 設定、サンプル .env.example の生成、スキーマ DDL 一式）や、個別モジュールの詳しい使い方を出力するようご希望があれば教えてください。