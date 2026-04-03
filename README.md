# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（データ取得・保存・品質チェック）、ニュースNLP（LLM を用いたセンチメント評価）、市場レジーム判定、ファクター計算、監査ログなど、トレード戦略・リサーチ・実運用に必要な機能群を提供します。

主な設計思想：
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を直接参照しない設計が多い）
- DuckDB を中心としたローカルデータストア（冪等保存、ON CONFLICT）による ETL
- 外部 API 呼び出し（J-Quants / OpenAI 等）はリトライ・レート制御を備えた安全な実装
- テスト容易性を考慮した依存注入（API キー引数等）

---

## 機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（fetch / save 関数、認証・レート制御・リトライ実装）
  - 市場カレンダー管理（営業日判定・next/prev_trading_day・calendar_update_job）
  - ニュース収集（RSS 取得、SSRF 対策、URL 正規化、raw_news 保存）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログ用スキーマ定義・初期化（signal_events / order_requests / executions）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - ニュースセンチメントスコアリング（score_news: gpt-4o-mini を用いた銘柄別スコア）
  - 市場レジーム判定（score_regime: ETF 1321 の MA200 とマクロ記事センチメントを合成）
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴探索系（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - 環境変数管理（.env 自動読み込み、Settings クラスでプロパティ参照）
- audit
  - 監査ログ DB 初期化ユーティリティ（init_audit_db/init_audit_schema）

---

## セットアップ手順

前提
- Python 3.9+（型ヒントに union 型などを使用）
- DuckDB（Python パッケージで利用）
- OpenAI API（news_nlp / regime_detector で使用する場合）
- ネットワークからの RSS / J-Quants API アクセスが必要

推奨手順（プロジェクトルートで実行）:

1. 仮想環境作成・有効化
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

2. 必要パッケージをインストール
   主要な依存例（プロジェクトに requirements.txt がない場合）:
   ```
   pip install duckdb openai defusedxml
   ```
   その他、プロジェクトに合わせて追加で必要なパッケージがあればインストールしてください。

3. パッケージをインストール（編集可能モード）
   ```
   pip install -e .
   ```
   または開発中は PYTHONPATH を通すなどして src を参照してください。

4. 環境変数（.env）を用意
   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くと、自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   必須項目（使用する機能に応じて）:
   - JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（データ ETL）
   - OPENAI_API_KEY: OpenAI 呼び出し（news_nlp / regime_detector）
   - KABU_API_PASSWORD: kabuステーション API（発注周りを使う場合）
   - その他: DUCKDB_PATH / SQLITE_PATH / 各種監視設定等はデフォルト値あり

---

## 使い方（代表的な例）

基本的に各 API は DuckDB 接続を受け取る形です。例を示します。

1) DuckDB 接続を作成して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニューススコアリング（OpenAI が必要）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY は環境変数か引数で指定
print(f"書き込み銘柄数: {written}")
```

3) 市場レジーム判定
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 研究用ファクター計算
```python
import duckdb
from datetime import date
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
print(len(records), "銘柄のモメンタムを計算しました")
```

5) 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# 以後 conn に対して order_requests / executions 等を挿入して監査ログを記録可能
```

6) market calendar 周辺ユーティリティ
```python
from kabusys.data.calendar_management import (
    is_trading_day, next_trading_day, prev_trading_day, get_trading_days
)
# conn = duckdb.connect(...)
# is_trading_day(conn, date(2026,3,20))
```

注意点:
- AI 系（news_nlp / regime_detector）は OpenAI のレスポンスに依存するため、API キーと料金設定に注意してください。
- J-Quants API を使う機能は JQUANTS_REFRESH_TOKEN を必須とします。取得した id_token はクライアント内でキャッシュ・自動リフレッシュされます。
- ETL・API 呼び出しはネットワークや API 制限で失敗する可能性があるためログやリトライ挙動を確認してください。

---

## 環境変数（主な一覧）

- JQUANTS_REFRESH_TOKEN (必須: J-Quants)
- OPENAI_API_KEY (必須: AI 機能使用時)
- KABU_API_PASSWORD (kabuステーション API を使う場合)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (通知用、任意)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START (監視・プロセス管理)
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT (監視閾値)
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

config.Settings 経由でプロパティとして参照できます：
```python
from kabusys.config import settings
print(settings.duckdb_path, settings.is_live, settings.log_level)
```

.env の自動読み込み:
- プロジェクトルート（.git または pyproject.toml がある場所）から `.env` → `.env.local` の順で読み込みます。
- OS 環境変数が優先されます。`.env.local` は上書き（override）されます。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化します。

---

## ディレクトリ構成

主要なファイル / モジュール概要（src/kabusys 以下）:

- __init__.py
  - パッケージのバージョン等を公開
- config.py
  - 環境変数読み込み・Settings クラス定義
- ai/
  - __init__.py
  - news_nlp.py : ニュースセンチメント取得（score_news）
  - regime_detector.py : 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py : J-Quants API クライアント（fetch/save）
  - pipeline.py : ETL パイプライン（run_daily_etl 等）、ETLResult
  - etl.py : ETLResult の再エクスポートインターフェース
  - calendar_management.py : 市場カレンダー管理（is_trading_day 等）
  - news_collector.py : RSS ニュース収集・前処理
  - quality.py : データ品質チェック
  - stats.py : 統計ユーティリティ（zscore_normalize）
  - audit.py : 監査ログテーブル定義と初期化ユーティリティ
- research/
  - __init__.py
  - factor_research.py : ファクター計算（momentum / value / volatility）
  - feature_exploration.py : 将来リターン計算 / IC / 統計サマリー / rank

（この README はコードベースの主要モジュールを要約したものです。各モジュール内に詳細な docstring や設計方針が記載されていますので、実装を読むことでより詳しい挙動が確認できます。）

---

## 運用上の注意

- 本リポジトリは実運用（特にライブ発注）に使用する前に十分なテストとレビューを行ってください。特に発注ロジックや冪等性・エラーハンドリングは重要です。
- OpenAI / J-Quants 等の外部 API 利用はコストやレート制限があります。テスト環境では API キーや自動ロード設定を切り替える等の対策を推奨します。
- DuckDB ファイルはバックアップを取り、監査ログは削除しない設計（トレーサビリティの観点）です。

---

この README でカバーされていない利用例や、特定機能の詳細な使い方が必要であれば、知りたい機能名や利用ケースを指定してください。具体的なコード例や運用手順を追加で作成します。