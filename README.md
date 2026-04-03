# KabuSys

日本株向け自動売買 / データプラットフォームライブラリ

簡潔な説明:
KabuSys は J-Quants や RSS、OpenAI などの外部ソースを連携して日本株のデータ収集（ETL）、データ品質チェック、ニュースセンチメント（LLM）、市場レジーム判定、監査ログ（発注→約定のトレーサビリティ）を提供する Python モジュール群です。研究（リサーチ）用のファクター計算や統計ユーティリティも含まれます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 環境変数（.env）／設定
- 使い方（代表的な API・スニペット）
- ディレクトリ構成

---

プロジェクト概要
- J-Quants API から株価・財務・上場銘柄情報・市場カレンダーを差分取得して DuckDB に保存する ETL パイプライン（kabusys.data.pipeline）。
- RSS を使ったニュース収集と前処理（kabusys.data.news_collector）。
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント評価（kabusys.ai.news_nlp）と、ETF（1321）のMA乖離＋マクロニュースから市場レジームを判定する機能（kabusys.ai.regime_detector）。
- 研究用ファクター計算（momentum / volatility / value）と特徴量探索（kabusys.research）。
- データ品質チェック（欠損・スパイク・重複・日付整合性）（kabusys.data.quality）。
- 発注〜約定までの監査ログテーブル定義と初期化ユーティリティ（kabusys.data.audit）。
- 設定の自動ロード（.env / .env.local / 環境変数）と設定オブジェクト（kabusys.config）。

---

主な機能一覧
- ETL（差分取得・保存・品質チェック）: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- ニュース収集: fetch_rss / preprocess_text / raw_news 保存フロー
- ニュース NLP（LLM）スコアリング: score_news（銘柄ごとの ai_score を ai_scores テーブルへ）
- 市場レジーム判定: score_regime（1321 の MA200 乖離 + マクロ記事センチメントを合成）
- J-Quants クライアント: get_id_token / fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar / save_*（DuckDB への冪等保存）
- 研究用: calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / zscore_normalize
- データ品質チェック: check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
- 監査ログ初期化: init_audit_schema / init_audit_db

---

前提・依存（主要）
- Python 3.10+
- DuckDB（Python パッケージ）
- openai（OpenAI の Python SDK）
- defusedxml（RSS の安全パース）
- （ネットワークアクセスに依存：J-Quants API、RSS、OpenAI）

インストールはプロジェクトに合わせた requirements.txt を用意して行ってください。開発用には以下のような手順の例を推奨します。

セットアップ手順（例）
1. ソースをクローン
   - git clone <repo-url>
2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate
3. パッケージ依存をインストール（例）
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （プロジェクトに setup.cfg / pyproject.toml があれば）pip install -e .
4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。
   - 必要な環境変数を後述のセクションに従って設定してください。

注意:
- settings（kabusys.config.settings）は自動で環境変数を読み込みます。テスト時に自動ロードを抑制したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

環境変数（主なもの）
kabusys.config.Settings で参照される主要な環境変数（.env に設定可能）:

必須（使用する機能による）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（get_id_token に使用）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime などで使用）
- KABU_API_PASSWORD — kabuステーション API を使う場合のパスワード

任意（デフォルト値あり）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（必要時）
- DUCKDB_PATH — DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 sqlite パス（default: data/monitoring.db）
- PID_FILE_PATH — 実行プロセス PID ファイルパス（default: data/execution.pid）
- KILL_FLAG_PATH — 停止フラグパス（default: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill flag をクリアするか（"1" で True）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値（パーセント）
- KABUSYS_ENV — 実行環境 ("development" / "paper_trading" / "live")（デフォルト "development"）
- LOG_LEVEL — ログレベル ("DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL")（デフォルト "INFO"）

.env の例
（プロジェクトルートに `.env` を作成）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

使い方（代表的な例）

基本: DuckDB 接続を作成して ETL / スコアリング / 監査初期化 等を呼ぶ流れ。

1) 日次 ETL 実行例（データ取得・保存・品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメント（銘柄別）を生成（score_news）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"Scored {count} symbols")
```
- OpenAI API キーは score_news の引数 api_key に渡すか、環境変数 OPENAI_API_KEY を設定してください。

3) 市場レジーム判定（score_regime）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログテーブル初期化
- 既存の DuckDB 接続に監査スキーマ（signal_events, order_requests, executions）を追加する:
```python
from kabusys.data.audit import init_audit_schema, init_audit_db
import duckdb
from pathlib import Path
from kabusys.config import settings

# 既存 DB へ追加
conn = duckdb.connect(str(settings.duckdb_path))
init_audit_schema(conn, transactional=True)

# 監査専用 DB を新規に作る場合
audit_conn = init_audit_db(Path("data/audit.duckdb"))
```

5) J-Quants API 呼び出し（直接 fetch）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
from kabusys.config import settings

token = get_id_token()  # settings.jquants_refresh_token を使用して取得
records = fetch_daily_quotes(id_token=token, date_from=date(2026,3,1), date_to=date(2026,3,20))
```

6) RSS フェッチ（ニュース収集）
```python
from kabusys.data.news_collector import fetch_rss, preprocess_text

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    text = preprocess_text(a["title"] + " " + a["content"])
    # raw_news テーブルへの保存は ETL / 専用関数で行ってください
```

注意点 / 設計上の懸念
- LLM 呼び出しや外部 API 呼び出しはネットワークエラーやレート制限に配慮してリトライ／フォールバックが組まれています。API キーが未設定の場合は score_news / score_regime は ValueError を投げます。
- データベース操作（DuckDB）でトランザクション管理を行っている箇所があります。呼び出し側でトランザクションを管理する場合、init_audit_schema の transactional フラグなどに注意してください。
- Look-ahead bias を回避する設計（関数は内部で date.today() を直接参照しない / データ選択で排他条件を用いる等）を採用しています。バックテスト用途では API 呼び出しや ETL の使用に注意してください（履歴データの事前準備が必要）。

---

ディレクトリ構成（主なファイル）
（ソースツリーは src/kabusys 配下に実装されています）

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
      - calendar_management.py
      - etl.py
      - pipeline.py
      - stats.py
      - quality.py
      - audit.py
      - jquants_client.py
      - news_collector.py
      - (その他 data 関連モジュール)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - monitoring/ (モニタリング関連は __all__ に含まれますが実装ファイルは該当パッケージ内)
    - strategy/ (戦略・実行層は __all__ に含まれます)
    - execution/ (発注実行関連)
- pyproject.toml / setup.cfg / requirements.txt （プロジェクトルートに配置する想定）

---

サポート & 貢献
- バグ修正・機能追加の貢献は Pull Request でお願いします。大きな設計変更は Issue で議論してください。
- テストカバレッジや CI の整備を推奨します（外部 API 呼び出しはモックを使うこと）。

---

補足
- README 中の使用例はライブラリの公開 API を簡易に示したものです。実運用ではログ設定、エラー監視、シークレット管理、レート制御の調整など環境に応じた追加実装が必要です。
- セキュリティ: RSS のフェッチでは SSRF 防止や XML の安全パース（defusedxml）を導入していますが、外部入力を扱う場合は常に防御を重ねてください。

以上。必要であれば導入手順を自動化するスクリプトや具体的な .env.example を作成した README 版を追加で生成できます。