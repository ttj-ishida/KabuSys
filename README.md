# KabuSys

KabuSys は日本株向けのデータ基盤・研究・自動売買サブシステム群です。本リポジトリは以下の主要機能を持ち、DuckDB を中核にしてデータ収集（J-Quants）、NLP/LLM によるニューススコアリング、ファクター計算、監査ログの管理、ETL パイプラインなどを提供します。

- バックエンド言語: Python
- 主要外部依存: duckdb, openai（OpenAI SDK）, defusedxml（RSS パーサ保護）ほか

---

## プロジェクト概要

KabuSys は次の領域をカバーします。

- データ収集 / ETL: J-Quants API から株価・財務・市場カレンダー等を差分取得・保存（ページネーション、レート制御、リトライ、冪等保存）
- ニュース収集: RSS フィードを安全に取得・正規化して raw_news に格納（SSRF 対策、トラッキング除去、コンテンツ前処理）
- ニュースNLP / LLM: OpenAI（gpt-4o-mini 等）を用いた銘柄別ニュースセンチメント算出（JSON mode を利用した厳格な入出力設計）
- レジーム判定: ETF（1321）MA200 乖離とマクロニュースセンチメントを合成して市場レジーム判定
- リサーチ: モメンタム、バリュー、ボラティリティ等ファクター計算、将来リターン計算、IC 計算、Z スコア正規化
- 監査ログ（audit）: シグナル → 発注 → 約定のトレーサビリティを保持する監査テーブル群の初期化ユーティリティ
- 品質チェック: データ品質検査（欠損・重複・スパイク・日付整合など）

設計上の重要点:
- ルックアヘッドバイアス対策（target_date を引数で与え、date.today() をテスト以外で直接参照しない）
- 冪等性（DB 保存は ON CONFLICT / DO UPDATE を多用）
- フェイルセーフ（外部 API 失敗時はゼロフォールバックやスキップで継続）
- セキュリティ考慮（RSS の SSRF 対策、defusedxml 使用、OpenAI レスポンスの厳密検証）

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save 関数、認証・レート制御）
  - news_collector（fetch_rss、記事正規化、SSRF 対策）
  - quality（データ品質チェック群）
  - audit（監査テーブル初期化・DB 初期化ユーティリティ）
  - calendar_management（営業日判定、next/prev_trading_day 等）
  - stats（zscore_normalize 等）
- ai/
  - news_nlp.score_news（銘柄別ニュースセンチメントを ai_scores に書き込み）
  - regime_detector.score_regime（マクロ + MA200 を合成して market_regime に書き込み）
- research/
  - factor_research（calc_momentum, calc_value, calc_volatility）
  - feature_exploration（calc_forward_returns, calc_ic, factor_summary, rank）
- config.py
  - 環境変数読み込み（.env / .env.local 自動読み込み。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - Settings クラス（各種必須環境変数のアクセサ）

---

## セットアップ手順

前提:
- Python 3.10+（typing の一部記法を利用）
- Git クローン可能な環境

1. リポジトリをクローン
   ```
   git clone <このリポジトリの URL>
   cd <リポジトリ>
   ```

2. 仮想環境を作成して有効化（例）
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 依存パッケージをインストール
   - requirements.txt がある場合:
     ```
     pip install -r requirements.txt
     ```
   - 主要パッケージ（例）:
     ```
     pip install duckdb openai defusedxml
     ```
   - 開発インストール（パッケージ形式がある場合）:
     ```
     pip install -e .
     ```

4. 環境変数設定
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（.env.local により上書き可能）。
   - 自動読み込みを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必要な環境変数（主なもの）
     - JQUANTS_REFRESH_TOKEN (必須)
     - OPENAI_API_KEY (LLM を使用する場合必須)
     - KABU_API_PASSWORD
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (通知用)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視用 DB、デフォルト: data/monitoring.db)
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV: development / paper_trading / live
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxxx
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB 用ディレクトリを作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（主要ユースケース）

注意: ここでは Python スクリプトから直接モジュールを呼ぶ前提の例を示します。

1) ETL（日次パイプライン）の実行例
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# target_date を None にすると今日（ローカル）を使います
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニューススコアリング（OpenAI を使う）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
import os

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数に設定しておくか、api_key を直接渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("scored:", n_written)
```

3) 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで監査テーブル群とインデックスが作成されます
```

5) リサーチ用ファクター計算（例：モメンタム）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# さらに z-score 正規化:
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
```

6) news_collector の RSS 取得（単体）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["title"], a["datetime"])
```

---

## 環境変数（主な一覧）

- JQUANTS_REFRESH_TOKEN : J-Quants API 用リフレッシュトークン（必須）
- OPENAI_API_KEY : OpenAI API キー（AI モジュール使用時に必須）
- KABU_API_PASSWORD : kabuステーション API 用パスワード
- KABU_API_BASE_URL : kabu API のベース URL
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID : Slack 通知用
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite パス（デフォルト data/monitoring.db）
- PID_FILE_PATH : 実行プロセス PID ファイルパス
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT : 監視閾値
- KABUSYS_ENV : development / paper_trading / live（デフォルト development）
- LOG_LEVEL : ログレベル（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 任意。1 をセットすると .env の自動読み込みを無効化

.env の自動読み込み:
- プロジェクトルート（.git または pyproject.toml を検出したパス）にある `.env` を読み込みます。
- `.env.local` がある場合はそれが優先して上書きします。
- OS 環境変数は上書きされません（ただし .env.local は override=True で設定可）。

---

## ディレクトリ構成（主なファイル）

リポジトリの主要モジュール・ファイル構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - news_collector.py
    - quality.py
    - stats.py
    - calendar_management.py
    - audit.py
    - etl.py (再エクスポート等)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/__init__.py
  - ai/__init__.py
  - (その他: strategy/, execution/, monitoring/ のプレースホルダがパッケージ公開対象に含まれる)

---

## 注意事項 / 運用上のヒント

- OpenAI 呼び出しは外部 API なのでコストが発生します。テスト時は API 呼び出し関数をモックしてください（モジュール内で差し替え可能な設計）。
- J-Quants API のレート制限や ID トークン刷新ロジックを組み込んでいますが、実際のプロダクション稼働では API の利用制限に注意してください。
- ETL / データ操作は DuckDB を前提に SQL を組んでいます。DuckDB のバージョン差で動作差が出る可能性があるため、CI 等でバージョン固定を推奨します。
- audit テーブルは監査ログ用で削除しない前提です。スキーマ初期化は init_audit_db() 等を利用してください。
- news_collector は RSS の外部コンテンツを扱うため、SSR F・サイズ制限・圧縮等の検査を行っています。fetch_rss は例外や空リストを返す可能性がありますのでハンドリングしてください。

---

もし README に追記したい具体的な情報（CI 手順、テストの実行方法、デプロイ手順、requirements.txt の内容例など）があれば教えてください。必要に応じてサンプルスクリプトや .env.example を作成します。