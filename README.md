# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL・品質チェック、ニュース収集とNLPスコアリング、リサーチ用ファクター計算、監査ログ・発注監視などの機能を含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- 必要条件・セットアップ
- 環境変数（設定）
- 使い方（簡易サンプル）
- 主要モジュール / API一覧
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は以下を目的とした Python パッケージ群です。

- J-Quants API を用いた株価・財務・マーケットカレンダーの差分取得と DuckDB への保存（ETL）
- RSS によるニュース収集と前処理、記事→銘柄紐付け
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント（銘柄別）とマクロセンチメント評価
- 市場レジーム判定（ETF MA と LLM の融合）
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量解析ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal → order_request → execution）用スキーマと初期化ユーティリティ

設計上の特徴:
- ルックアヘッドバイアス対策（target_date を明示し、内部で date.today() を参照しない箇所が多い）
- DuckDB を中核DBとして利用（軽量にローカル保持）
- 冪等性を重視（ETL 保存は ON CONFLICT/UPSERT 等で上書き）
- 外部API呼び出しに対するリトライ/バックオフ・フェイルセーフを備える

---

## 主な機能（機能一覧）

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（fetch / save 各種）
  - 市場カレンダー管理（is_trading_day, next_trading_day, get_trading_days, calendar_update_job）
  - ニュース収集（RSS fetch_rss、前処理、保存処理）
  - データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: 銘柄別ニュースセンチメントを生成し ai_scores に保存
  - regime_detector.score_regime: ETF(1321) MA とマクロ記事センチメントを合成して market_regime を生成
- research/
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- config.py: 環境変数・設定の読み込みと accessor（自動 .env 読み込み機能あり）

---

## 必要条件 / 推奨環境

- Python 3.9+（型注釈や一部機能を前提）
- 必要パッケージ（コードベースから推測）:
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants / OpenAI / RSS フィードへのアクセス）

（プロジェクトの実際の requirements.txt がある場合はそちらを優先してください）

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)
3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt があれば）pip install -r requirements.txt
4. 環境変数を設定する:
   - プロジェクトルートに `.env` または `.env.local` を作成することで自動読み込みされます（config.py による自動読み込み）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
5. DuckDB ファイルや監査DBの初期化（任意）:
   - 監査DB初期化例（ファイル作成とスキーマ生成）:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
6. J-Quants / OpenAI の API キーを `.env` に記載（下記参照）

---

## 環境変数（例）

config.py で参照される主な変数（大文字）:

- JQUANTS_REFRESH_TOKEN - J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD - kabuステーション API パスワード（必須）
- KABU_API_BASE_URL - kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN - Slack bot トークン（通知用）
- SLACK_CHANNEL_ID - Slack 通知先チャンネルID
- DUCKDB_PATH - DuckDB のデフォルトパス（例: data/kabusys.duckdb）
- SQLITE_PATH - 監視用 SQLite（例: data/monitoring.db）
- KABUSYS_ENV - 環境 (development | paper_trading | live). default: development
- LOG_LEVEL - ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL). default: INFO
- OPENAI_API_KEY - OpenAI API キー（ai モジュール呼び出しで参照）

注意:
- config.py はプロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を自動読み込みします。OS環境変数が優先され、`.env.local` は上書き可能です。
- `.env` のフォーマットは export を含む行、コメント、クォートなど一般的な形式に対応します。

---

## 使い方（簡易サンプル）

以下はライブラリをプログラムから呼ぶ最小例です。実運用ではログ設定や例外処理、APIキー管理を適切に行ってください。

- DuckDB 接続を作って日次 ETL を実行する（データ取得・保存・品質チェック）:
```python
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
# target_date を指定しないと today が使われます（内部で営業日調整あり）
result = run_daily_etl(conn)
print(result.to_dict())
```

- ニュースセンチメント（前日15:00 JST〜当日08:30 JST のウィンドウ）を生成:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジームを算出して書き込む（1321 の MA200 とマクロ記事 LLM を合成）:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査DBの初期化:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 以降 conn を監査ログ書き込みに利用
```

- 研究用ファクター計算（例: モメンタム）:
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は [{"date": ..., "code": "...", "mom_1m": ..., ...}, ...]
```

---

## 主要モジュール / API（抜粋）

- kabusys.config.settings: 環境変数アクセサ
- kabusys.data.jquants_client:
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token (refresh)
- kabusys.data.pipeline:
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - ETLResult
- kabusys.data.news_collector:
  - fetch_rss, preprocess_text, 他 RSS 取り回しユーティリティ
- kabusys.data.quality:
  - run_all_checks, check_missing_data, check_spike, check_duplicates, check_date_consistency
- kabusys.data.calendar_management:
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- kabusys.data.audit:
  - init_audit_schema, init_audit_db
- kabusys.ai.news_nlp:
  - score_news
- kabusys.ai.regime_detector:
  - score_regime
- kabusys.research.factor_research:
  - calc_momentum, calc_value, calc_volatility
- kabusys.research.feature_exploration:
  - calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.data.stats:
  - zscore_normalize

---

## ディレクトリ構成

（ソースベース抜粋）

- src/
  - kabusys/
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
      - calendar_management.py
      - quality.py
      - stats.py
      - audit.py
      - etl.py (ETLResult re-export)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/（他サブモジュール）
    - monitoring/（※ README 内で参照あり：パッケージ公開時に含む想定）
    - strategy/（戦略ロジックは別途実装想定）
    - execution/（発注・ブローカー連携は別途実装想定）

---

## 運用上の注意 / ベストプラクティス

- API キーは環境変数やシークレット管理により安全に管理してください（.env をリポジトリに含めない）。
- ETL は夜間バッチでの実行を想定しています。run_daily_etl はカレンダーの先読み・バックフィル処理を含みます。
- OpenAI 呼び出しはコストとレート制限を伴います。テスト時は各モジュールの _call_openai_api をモックしてください（コード内にモック想定コメントあり）。
- DuckDB はファイルロックや同時接続に注意してください。複数プロセスで同一ファイルを扱う場合の挙動を確認してください。
- ニュース収集時の SSRF / XML 攻撃対策は一部実装済み（defusedxml, SSRF チェック、サイズ制限など）。ただし運用環境ではソースリストの信頼性を担保してください。

---

以上がこのコードベースに基づく README の概略です。README に追記したい具体的な実行例、CI 設定、requirements.txt、.env.example のテンプレートなどがあれば、その内容に合わせて追記します。