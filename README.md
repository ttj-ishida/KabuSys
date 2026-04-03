# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
ETL、ニュースNLP（LLM）、市場レジーム判定、ファクター計算、監査ログなどを含み、DuckDB をデータレイクとして利用する設計になっています。

---

## プロジェクト概要

KabuSys は以下の用途を想定したモジュール群を提供します。

- J-Quants API からの株価・財務・マーケットカレンダーの差分 ETL（jquants_client / pipeline）
- RSS によるニュース収集と前処理（news_collector）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価と銘柄ごとの AI スコア生成（ai.news_nlp）
- ETF とマクロニュースを統合した市場レジーム判定（ai.regime_detector）
- 研究（研究用のファクター計算・特徴量解析）（research）
- データ品質チェック（data.quality）
- 監査ログ（signal → order → execution のトレーサビリティ）（data.audit）
- 各種ユーティリティ（設定管理、統計関数等）

設計上の注意点として、バックテスト等でのルックアヘッドバイアス防止のため内部処理は明示的な target_date を受け取り、datetime.today()/date.today() を直接参照しない関数設計になっています。

---

## 主な機能一覧

- ETL:
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（差分取得・保存・品質チェック）
- ニュース処理:
  - fetch_rss（RSS 取得と前処理）
  - score_news（OpenAI を使った銘柄ごとのニュースセンチメント算出）
- レジーム判定:
  - score_regime（1321 の MA200 とマクロニュースを合成し bull/neutral/bear 判定）
- 研究用:
  - calc_momentum, calc_value, calc_volatility（ファクター算出）
  - calc_forward_returns, calc_ic, factor_summary, rank（特徴量探索）
- データ品質:
  - run_all_checks（欠損、スパイク、重複、日付不整合チェック）
- データクライアント:
  - jquants_client（J-Quants API の取得・保存、トークン自動リフレッシュ、レート制御、リトライ）
- 監査ログ:
  - init_audit_db / init_audit_schema（監査用 DuckDB 初期化）
- 設定管理:
  - kabusys.config.Settings（.env / .env.local / 環境変数の読み込み・検証）

---

## セットアップ手順

推奨: Python 仮想環境を作成して使用してください。

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. 仮想環境の作成と有効化
   - macOS / Linux:
     python -m venv .venv
     source .venv/bin/activate
   - Windows (PowerShell):
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1

3. 依存ライブラリをインストール
   requirements.txt がある場合はそちらを使用してください。なければ少なくとも以下が必要です:
   - duckdb
   - openai
   - defusedxml
   - （標準ライブラリ以外に urllib 等は不要）

   例:
   pip install duckdb openai defusedxml

4. 環境変数（.env）を設定
   プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。

   必須（動作させる機能によって必要なもの）:
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - OPENAI_API_KEY=sk-...
   - KABU_API_PASSWORD=...  （kabuステーション連携を使う場合）

   任意（デフォルトがある設定も含む）:
   - KABUSYS_ENV=development|paper_trading|live  （デフォルト: development）
   - LOG_LEVEL=DEBUG|INFO|...  （デフォルト: INFO）
   - DUCKDB_PATH=data/kabusys.duckdb  （デフォルト）
   - SQLITE_PATH=data/monitoring.db
   - PID_FILE_PATH=data/execution.pid
   - KILL_FLAG_PATH=data/kill.flag
   - KILL_FLAG_CLEAR_ON_START=0|1
   - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

   .env のパースはシェルの export 形式やクォートも許容します。詳しくは kabusys.config のロジックに従います。

---

## 使い方（主な利用例）

以下は Python REPL / スクリプト内での利用例です。target_date には必ず日付を指定してルックアヘッドを防ぎます。

- DuckDB 接続の作成（既定パスを使用）
  from pathlib import Path
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニューススコア（OpenAI が必要）
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  # api_key を明示的に渡すか、OPENAI_API_KEY を設定してください
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込んだ銘柄数:", n_written)

- 市場レジーム判定（OpenAI が必要）
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ DB 初期化（専用 DB を作る）
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  # audit_conn は初期化済み DuckDB 接続を返します

- 研究用ファクター計算
  from datetime import date
  from kabusys.research import calc_momentum
  factors = calc_momentum(conn, date(2026, 3, 20))

注意点:
- OpenAI API 呼び出しはリトライやフォールバックを実装していますが、API キーのレート制限や費用に注意してください。
- ETL / ニュース収集など外部 API を叩く部分はネットワークエラーや API 変更に依存するため、運用時はログと監視を設定してください。
- テスト時は各モジュール内の _call_openai_api / _urlopen などをモックして外部依存を切り離す設計になっています。

---

## .env の例

例（プロジェクトルート/.env）:

JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

src/
  kabusys/
    __init__.py
    config.py                      # 環境変数・設定管理
    ai/
      __init__.py
      news_nlp.py                   # ニュース NLP スコアリング（OpenAI）
      regime_detector.py            # 市場レジーム判定（MA + マクロニュース）
    data/
      __init__.py
      jquants_client.py             # J-Quants API クライアント（取得・保存）
      pipeline.py                   # ETL パイプライン（run_daily_etl など）
      etl.py                        # ETL 公開インターフェース
      calendar_management.py        # 市場カレンダー管理
      news_collector.py             # RSS ニュース収集
      stats.py                      # 統計ユーティリティ（zscore_normalize など）
      quality.py                    # データ品質チェック
      audit.py                      # 監査ログ（監査テーブル定義・初期化）
    research/
      __init__.py
      factor_research.py            # ファクター計算（momentum/value/volatility）
      feature_exploration.py        # 将来リターン/IC/summary 等
    research/（上に続く）
    (その他モジュール：strategy, execution, monitoring などが __all__ に準備）

ドキュメントや設計資料がプロジェクトに同梱されている場合はそちら（DataPlatform.md, StrategyModel.md 等）に詳細が記載されています。

---

## 運用上の注意

- DuckDB ファイルのバックアップとスキーマ管理を運用ルールに従って行ってください。
- OpenAI/API キーは漏洩しないように環境変数で管理し、ローテーションを検討してください。
- jquants_client のレート制限（120 req/min）や retry ロジックがありますが、過度な並列リクエストは避けてください。
- news_collector は外部の RSS を取得するため、SSRF 対策やレスポンスサイズ上限、XML パースの安全化（defusedxml）などのセキュリティ対策が組み込まれています。カスタム RSS を追加する際もホワイトリスト運用を推奨します。

---

以上が README の概要です。追加で「セットアップ用のスクリプト」「具体的な Docker / systemd 単位での運用例」「CI テストの書き方」などが必要であれば、その用途に合わせて追記します。