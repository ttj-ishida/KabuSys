# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ集です。  
ETL、ニュース収集・NLP（LLM）、ファクター計算、監査ログ（発注〜約定トレーサビリティ）などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けに設計された、データ取得（J-Quants）、データ品質管理、ETL パイプライン、ニュース収集・NLP（OpenAI 使用）、リサーチ用ファクター計算、監査ログ（発注/約定のトレーサビリティ）などを備えたライブラリです。  
DuckDB を中心にローカルにデータを保持し、J-Quants と OpenAI（gpt-4o-mini 等）を外部 API として利用します。バックテストや本番運用（paper/live）に配慮した設計がなされています。

主な設計方針:
- ルックアヘッドバイアス回避（内部で date.today() 等の暗黙参照を避ける）
- 冪等性（DB 保存は ON CONFLICT 等で安全に上書き）
- フェイルセーフ（外部 API 失敗時のフォールバック）
- テスト容易性（API 呼び出し部分は差し替え可能）

---

## 機能一覧

- 環境設定管理
  - `.env` / `.env.local` の自動読み込み（プロジェクトルート検出）
  - 必須環境変数取得ユーティリティ（`kabusys.config.settings`）

- データ ETL（kabusys.data.pipeline）
  - J-Quants からの差分取得（株価、財務、カレンダー）
  - 保存（DuckDB へ冪等保存）
  - 品質チェック（欠損・スパイク・重複・日付不整合）

- データクライアント（kabusys.data.jquants_client）
  - 認証（リフレッシュトークン → id_token）
  - API 呼び出し（リトライ・レート制御）
  - データ取得・保存ヘルパー（daily_quotes / financials / calendar / listed info）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得（SSRF 対策、トラッキングパラメータ削除、前処理）
  - raw_news / news_symbols 連携を想定した冪等保存ロジック

- NLP / LLM（kabusys.ai）
  - score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価、`ai_scores` へ保存
  - regime_detector: ETF（例: 1321）MA とマクロニュースを合成して市場レジーム判定

- 研究用（kabusys.research）
  - ファクター計算（momentum / value / volatility 等）
  - 特徴量探索（将来リターン、IC、統計サマリー、正規化ユーティリティ）

- カレンダー管理（kabusys.data.calendar_management）
  - JPX マーケットカレンダー管理、営業日判定、next/prev/trading_days 取得

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions のスキーマと初期化ユーティリティ
  - 監査 DB 初期化（DuckDB）

- ユーティリティ
  - 統計ユーティリティ（zscore 正規化等）
  - データ品質チェック（kabusys.data.quality）

---

## セットアップ手順

以下はローカル開発環境での最低セットアップ例です。

1. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール  
   （プロジェクトの requirements.txt が無い場合、主要なランタイム依存のみ列挙）
   - pip install duckdb openai defusedxml

   追加で使う可能性のあるパッケージ:
   - requests 等（必要に応じて）

3. パッケージをインストール（開発モード）
   - プロジェクトルートで:
     - pip install -e .

4. 環境変数 / .env の準備  
   プロジェクトルートの `.env`（および `.env.local`）を用意します。例:

   ```
   # .env (例)
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   KABU_API_PASSWORD=your_kabu_api_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   自動読み込みについて:
   - パッケージはインポート時にプロジェクトルート（.git または pyproject.toml のある親ディレクトリ）を探索して自動で `.env` / `.env.local` をロードします。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利です）。

5. DuckDB データベースおよび監査 DB の初期化
   - 監査ログ用の DB を初期化:
     ```
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - ETL 用のメイン DB は settings.duckdb_path 等に従って作成・接続します（下記使用例参照）。

---

## 使い方（主要な API とサンプル）

以下は代表的な利用例です。実行は Python スクリプト / REPL で行えます。

- 設定取得

```
from kabusys.config import settings

# 環境変数から値を取得（必須項目は設定漏れで例外）
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
print(settings.env)  # development / paper_trading / live
```

- DuckDB 接続の作成

```
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL の実行（run_daily_etl）

```
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# conn は duckdb 接続
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（AI）スコアリング

```
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API キーは OPENAI_API_KEY 環境変数、または api_key 引数で指定
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written: {n_written}")
```

- 市場レジーム判定

```
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは env 参照
```

- 監査 DB 初期化（個別）

```
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブル等が作成されます
```

- RSS フィード取得（ニュース収集単体利用）

```
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

注意点:
- OpenAI 呼び出し部はネットワーク/レート・エラーで失敗する可能性があります。実装側でリトライやフォールバックが行われますが、API キーは必ず正しく設定してください。
- J-Quants API はレート制限を守るため内部に RateLimiter を備えています。`JQUANTS_REFRESH_TOKEN` が必要です。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注関連で使用）
- KABUSYS_ENV: 実行モード（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- DUCKDB_PATH: デフォルト DuckDB ファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（例: data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH: 実行監視用ファイルパス
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: .env 自動読み込みを無効にする

必須項目が未設定の場合は `kabusys.config.Settings` のプロパティ呼び出し時に ValueError が発生します。

---

## ディレクトリ構成

主要ファイル・モジュールを抜粋しています（ソースは `src/kabusys`）:

- src/kabusys/__init__.py
- src/kabusys/config.py
  - 環境変数読み込み・設定管理
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py          : ニュースの LLM センチメントスコア化
  - regime_detector.py   : ETF MA とマクロセンチメントの合成による市場レジーム判定
- src/kabusys/data/
  - __init__.py
  - jquants_client.py    : J-Quants API クライアント（取得・保存ユーティリティ）
  - pipeline.py          : ETL パイプライン（run_daily_etl 等）
  - etl.py               : ETLResult の再エクスポート
  - calendar_management.py : マーケットカレンダー管理・営業日判定
  - stats.py             : 統計ユーティリティ（zscore_normalize 等）
  - quality.py           : データ品質チェック（欠損・スパイク・重複・日付不整合）
  - news_collector.py    : RSS 収集・前処理
  - audit.py             : 監査ログスキーマ初期化（signal_events / order_requests / executions）
- src/kabusys/research/
  - __init__.py
  - factor_research.py   : モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py : 将来リターン / IC / 統計サマリー 等

（実際のプロジェクトにはさらにモジュールや補助ファイルが存在する可能性があります）

---

## 運用上の注意 / ベストプラクティス

- 本システムは実際の売買や資金管理を伴うため、本番環境（KABUSYS_ENV=live）では特に環境変数・認証情報の管理に注意してください。
- OpenAI / J-Quants の API キーは安全に保管し、ログ等に漏洩しないようにしてください。
- ETL 実行はスケジューラ（cron 等）で定期的に実行し、品質チェックの結果に応じてアラートを出す運用が推奨されます。
- DuckDB のファイルはバックアップ・バージョン管理（スナップショット）を検討してください。監査ログは削除しない前提で設計されています。
- テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用し、外部 API 呼び出しはモック（unittest.mock）で差し替えてください。

---

## よくある質問（FAQ）

Q: .env の自動読み込みを無効化するには？  
A: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

Q: OpenAI の呼び出しをテストで差し替えたい  
A: ai モジュール内の `_call_openai_api` 関数を unittest.mock.patch で差し替える設計になっています（各モジュールにテスト用フックあり）。

Q: DuckDB のスキーマはどこで作る？  
A: 各機能（ETL / audit 等）に初期化ユーティリティを用意しています。監査ログは `init_audit_db` を使用して初期化します。ETL 側は呼び出し先で必要テーブルを作成する想定です（運用スクリプトで schema 初期化を行ってください）。

---

この README はライブラリの主要機能利用開始のための簡易ガイドです。詳細な API ドキュメント、運用手順、スキーマ定義（DDL）や稼働例は別途ドキュメント（Design docs や DataPlatform.md / StrategyModel.md 等）を参照してください。必要であれば README を拡張して CLI、設定例、詳しいテスト手順、サンプルデータの用意方法なども追加できます。