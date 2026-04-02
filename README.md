# KabuSys

日本株向けのデータプラットフォームと自動売買支援ライブラリ。  
ETL（J-Quants からの株価・財務・カレンダー取得）、データ品質チェック、監査ログ用スキーマ、研究用ファクター計算、ニュース NLU（OpenAI を用いたセンチメント）、市場レジーム判定などを提供します。

主に DuckDB をデータ層に用い、J-Quants / kabuステーション / OpenAI 等の外部 API と連携することを想定したモジュール群です。

---

目次
- プロジェクト概要
- 機能一覧
- 必要条件・依存関係
- セットアップ手順
- 環境変数（設定項目）
- 使い方（簡単なコード例）
- ディレクトリ構成（主要ファイルの概説）
- 注意事項

---

プロジェクト概要
- ETL: J-Quants API から株価日足、財務データ、マーケットカレンダーを差分取得し DuckDB に保存（冪等保存）。
- 品質チェック: 欠損・重複・スパイク・日付整合性などの品質ルールを実施。
- 監査ログ: シグナル → 発注 → 約定のトレーサビリティ用テーブル群を初期化・管理。
- 研究ツール: ファクター計算（モメンタム/バリュー/ボラティリティ）、将来リターン・IC・統計サマリーなど。
- ニュース分析: RSS 収集、安全対策（SSRF等）・前処理・OpenAI による銘柄ごとのセンチメントスコア化。
- 市場レジーム判定: ETF（1321）200日移動平均乖離とマクロニュース（LLM）を合成してレジームを算出・保存。
- 設定管理: .env / .env.local / 環境変数からの設定読み込み（自動ロードあり、無効化可能）。

---

機能一覧（要点）
- データ収集・保存
  - J-Quants: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - 保存: save_daily_quotes, save_financial_statements, save_market_calendar（DuckDB に冪等保存）
- ETL パイプライン
  - run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl（ETLResult を返す）
- 品質チェック
  - check_missing_data, check_duplicates, check_spike, check_date_consistency, run_all_checks
- カレンダー管理
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- 研究用
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, zscore_normalize
- ニュース
  - fetch_rss（SSRF 対策・サイズ制限・トラッキングパラメータ除去）
  - score_news（OpenAI を用いて銘柄ごとの ai_score を ai_scores に書き込み）
- レジーム判定
  - score_regime（ETF 1321 の MA200 乖離 + マクロセンチメント → market_regime テーブルへ）
- 監査ログ
  - init_audit_schema, init_audit_db（監査テーブル群を初期化）
- 設定
  - kabusys.config.settings（環境変数ベースの設定ラッパー）

---

必要条件・依存関係
- Python 3.10 以上（typing の union 型 (|) を利用）
- 主な Python ライブラリ:
  - duckdb
  - openai (OpenAI SDK)
  - defusedxml
  - （標準ライブラリで多くを実装）
- ネットワークアクセス: J-Quants API、OpenAI、RSS ソース など

推奨インストール（開発用）例:
- pip install -e .
- pip install duckdb openai defusedxml

（実際のパッケージ化・requirements はプロジェクト側で用意してください）

---

セットアップ手順

1. リポジトリをクローン
   - git clone ...

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -e .
   - pip install duckdb openai defusedxml

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のある場所）に .env を置くと自動で読み込まれます（.env.local があれば優先的に上書き）。
   - 自動読み込みを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. DuckDB データベース準備
   - デフォルトは data/kabusys.duckdb（settings.duckdb_path）
   - 監査ログ専用 DB を初期化する例（Python 実行）:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

6. 初期スキーマ（必要に応じて）や ETL を実行

---

環境変数（主要）
- 認証系
  - JQUANTS_REFRESH_TOKEN  (必須) — J-Quants のリフレッシュトークン
  - OPENAI_API_KEY         — OpenAI API キー（score_news / score_regime で使用）
  - KABU_API_PASSWORD      (必須) — kabuステーション API パスワード
  - KABU_API_BASE_URL      — デフォルト: http://localhost:18080/kabusapi

- Slack（通知等で利用）
  - SLACK_BOT_TOKEN        (必須)
  - SLACK_CHANNEL_ID       (必須)

- ストレージ / ファイルパス
  - DUCKDB_PATH            — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH            — デフォルト: data/monitoring.db
  - PID_FILE_PATH          — デフォルト: data/execution.pid

- 監視しきい値（デフォルト値あり）
  - CPU_THRESHOLD_PCT      — デフォルト: 90.0
  - MEMORY_THRESHOLD_PCT   — デフォルト: 85.0
  - DISK_THRESHOLD_PCT     — デフォルト: 90.0

- 実行環境
  - KABUSYS_ENV            — one of: development, paper_trading, live (default: development)
  - LOG_LEVEL              — one of: DEBUG, INFO, WARNING, ERROR, CRITICAL (default: INFO)

注意:
- settings は必須の環境変数が欠けていると ValueError を投げます（JQUANTS_REFRESH_TOKEN, SLACK_* 等）。

---

使い方（簡単なコード例）

準備: DuckDB 接続を作成して日次 ETL を実行する例
```
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

監査ログ DB 初期化
```
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は初期化済みの DuckDB 接続
```

ニューススコアリング（OpenAI 必須）
```
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数に設定するか、第3引数で api_key を渡す
written = score_news(conn, target_date=date(2026,3,20), api_key=None)
print(f"書き込み銘柄数: {written}")
```

市場レジーム判定
```
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

J-Quants から株価差分を取得して保存（個別実行）
```
from datetime import date
import duckdb
from kabusys.data.pipeline import run_prices_etl

conn = duckdb.connect("data/kabusys.duckdb")
fetched, saved = run_prices_etl(conn, target_date=date(2026,3,20))
```

RSS フィード取得（ニュース収集の一部）
```
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
# 取得した articles は NewsArticle 型のリスト。DB に格納するロジックはプロジェクト側で使用してください。
```

設定取得の例
```
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

---

ディレクトリ構成（主要モジュールの説明）

- src/kabusys/
  - __init__.py
  - config.py
    - .env/.env.local の自動読み込み機能
    - Settings クラス（環境変数アクセス）
  - ai/
    - __init__.py
    - news_nlp.py
      - score_news(conn, target_date, api_key=None)
      - ニュースを銘柄ごとに集約し OpenAI（gpt-4o-mini）でセンチメントを算出・ai_scores に書き込み
    - regime_detector.py
      - score_regime(conn, target_date, api_key=None)
      - ETF 1321 の MA200 乖離 + マクロセンチメントを合成して market_regime に保存
  - data/
    - __init__.py
    - calendar_management.py
      - market_calendar 管理、取引日判定ユーティリティ
    - etl.py
      - ETLResult の公開
    - pipeline.py
      - run_daily_etl 等の ETL ワークフロー実装
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - quality.py
      - データ品質チェック実装（QualityIssue を返す）
    - audit.py
      - 監査ログテーブル作成・初期化（init_audit_schema, init_audit_db）
    - jquants_client.py
      - J-Quants API クライアント（認証・レート制御・リトライ・保存ロジック）
    - news_collector.py
      - RSS 取得、前処理、SSRF 対策、ID 生成ユーティリティ
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum / calc_volatility / calc_value
    - feature_exploration.py
      - calc_forward_returns / calc_ic / factor_summary / rank

---

注意事項・設計上のポイント
- Look-ahead バイアス対策:
  - 多くの関数は内部で date.today() を直接参照せず、target_date を明示的に受け取ります。バックテスト用途ではこの設計を尊重して使用してください。
- 冪等性:
  - J-Quants からの保存関数は ON CONFLICT DO UPDATE を用いて冪等に保存します。
- レート制御:
  - jquants_client は固定間隔のレートリミッタを実装（120 req/min）。
- セキュリティ:
  - news_collector は URL 正規化・トラッキング除去・SSRF 防止（プライベートアドレスチェック・リダイレクト検査）・受信サイズ制限を実装。
- エラーハンドリング:
  - 多くの外部 API 呼び出しはリトライやフォールバックを備え、失敗時も例外を無闇に投げずフェイルセーフ（例: マクロセンチメント取得失敗時は 0.0）とする設計です。ただし重大な設定ミス（必須環境変数未設定等）は例外になります。

---

フィードバック・貢献
- README の補足や機能追加、テスト追加、CI 設定などの貢献は歓迎します。Issue / PR を通じて提案してください。

---

以上。必要であれば README に含める具体的な .env.example のテンプレートや、初回スキーマ作成用の SQL / スクリプト例も作成できます。どの情報を追加したいか教えてください。