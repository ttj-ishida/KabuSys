# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買補助ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI 利用）による銘柄スコアリング、ファクター計算、監査ログ（発注→約定のトレーサビリティ）など、システム全体の基盤機能を提供します。

バージョン: 0.1.0

---

## 主な機能

- データ取得・ETL
  - J-Quants API 経由で株価（日次OHLCV）、財務データ、JPX マーケットカレンダーを差分取得・保存
  - 差分更新／バックフィルのサポート、品質チェック機能
- データ品質管理
  - 欠損、スパイク、重複、将来日付などの検出（quality モジュール）
- ニュース収集と NLP
  - RSS から記事取得（SSRF 対策・トラッキングパラメータ除去・前処理）
  - OpenAI（gpt-4o-mini）の JSON mode を使った銘柄別ニュースセンチメント評価（score_news）
  - マクロニュースとETF MA乖離を組合せた市場レジーム判定（score_regime）
- 研究用ユーティリティ
  - モメンタム / バリュー / ボラティリティ等のファクター計算（research パッケージ）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリ
- 監査ログ（audit）
  - シグナル → 発注要求 → 約定 のトレーサビリティ用テーブル定義と初期化補助
- 設定管理
  - .env / 環境変数から設定を自動読み込み（config.Settings）
  - 開発 / paper_trading / live の環境フラグ、ログレベル等

---

## 必要条件（推奨）

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml

（実行環境に応じて他に必要なパッケージがある場合があります。プロジェクトの requirements ファイルがある場合はそちらを使用してください。）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   - 最低限:
     ```
     pip install duckdb openai defusedxml
     ```
   - 開発インストール（setup.py / pyproject.toml がある場合）:
     ```
     pip install -e .
     ```

4. 環境変数の準備
   - プロジェクトルートに `.env` / `.env.local` を作成してください（`.env.example` を参照）。
   - 必須環境変数（アプリ起動時に必要なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN — Slack 通知を使う場合
     - SLACK_CHANNEL_ID — Slack 通知チャンネル ID
     - KABU_API_PASSWORD — kabuステーション API を使う場合
     - OPENAI_API_KEY — OpenAI を用いる機能（score_news, score_regime）で必要（関数呼び出しで渡すことも可）
   - 任意（デフォルト値あり）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト `development`
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト `INFO`
     - DUCKDB_PATH — データベースファイルのパス（デフォルト `data/kabusys.duckdb`）
     - SQLITE_PATH — 監視用 SQLite（デフォルト `data/monitoring.db`）
     - PID_FILE_PATH / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
   - 自動ロード:
     - パッケージ import 時にプロジェクトルート（.git または pyproject.toml を探す）から `.env` と `.env.local` を自動読み込みします。
     - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. データディレクトリの作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（例）

以下は主要な利用例です。各関数はモジュールから直接インポートして使用します。

- 設定の参照
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  ```

- DuckDB に接続して日次 ETL を実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- 個別 ETL（株価のみ）
  ```python
  from kabusys.data.pipeline import run_prices_etl
  fetched, saved = run_prices_etl(conn, target_date=date(2026,3,20))
  ```

- ニュース収集（RSS 取得）
  ```python
  from kabusys.data.news_collector import fetch_rss

  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  # raw_news への保存ロジックはプロジェクト側で DB 挿入を行うこと
  ```

- AI を使ったニューススコアリング（OpenAI API key を渡すか環境変数 OPENAI_API_KEY を設定）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  count = score_news(conn, target_date=date(2026,3,20), api_key=None)  # None なら環境変数を使う
  print("scored:", count)
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査ログ DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # conn_audit は監査用テーブルが初期化済み
  ```

- 研究用ファクター計算
  ```python
  from kabusys.research import calc_momentum, calc_value, calc_volatility

  mom = calc_momentum(conn, target_date=date(2026,3,20))
  ```

注意:
- OpenAI 呼び出しは API エラー時にフォールバックやリトライを行いますが、API キーと料金に注意してください。
- ETL / DB 書き込みは DuckDB を前提としています。DB スキーマはプロジェクト側で準備しておく必要があります（スキーマ初期化は別途実装されている想定）。

---

## 主要モジュール（API サマリ）

- kabusys.config
  - settings: 環境変数からの設定取得（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY など）
- kabusys.data
  - pipeline: run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl, ETLResult
  - jquants_client: J-Quants API クライアント（fetch_xxx / save_xxx）
  - news_collector: fetch_rss, プロセス用ユーティリティ
  - quality: データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
  - calendar_management: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
  - audit: init_audit_schema / init_audit_db（監査ログテーブル初期化）
  - stats: zscore_normalize
- kabusys.ai
  - news_nlp.score_news: ニュース記事を LL M に渡して銘柄スコアを ai_scores に書き込む
  - regime_detector.score_regime: ETF MA とマクロニュースを合成して market_regime を更新
- kabusys.research
  - calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank
- その他: kabusys.__init__.py で各サブパッケージを公開

---

## ディレクトリ構成

（抜粋・概略。実際のリポジトリに合わせて調整してください）

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
      - quality.py
      - stats.py
      - calendar_management.py
      - audit.py
      - pipeline.py
      - etl.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/
    - monitoring/ (存在する場合: 監視モジュール)
    - execution/ (存在する場合: 発注実行モジュール)
    - etc.

---

## 運用上の注意・設計方針（要点）

- Look-ahead bias 防止:
  - バックテストや指標計算で現在日時を直接参照しない設計（target_date を明示的に渡す）。
  - データ取得では fetched_at を記録し「いつデータを知り得たか」を追跡可能にする。
- 冪等性:
  - ETL 保存処理は ON CONFLICT / DO UPDATE を用いて冪等に設計
  - 監査ログの order_request_id は冪等キーとして扱う
- フェイルセーフ:
  - LLM 呼び出しや外部 API エラーは基本的に例外で停止させず、フォールバック値で継続する設計（運用上の安全性重視）
- セキュリティ:
  - news_collector では SSRF 対策、XML 外部実行攻撃対策（defusedxml）などを導入

---

## トラブルシューティング

- 環境変数が足りないと Settings が ValueError を投げます。`.env` を確認してください。
- OpenAI 関連で API エラーや JSON パースエラーが起きた場合、警告ログが出力され、該当銘柄はスキップされます（部分的失敗の保護）。
- DuckDB の executemany に空リストを渡すと例外となるバージョン依存の挙動に注意し、ライブラリ側で空チェックを行っています。

---

## 参考

- 設定値は kabusys.config.settings を通じて取得できます。
- AI 機能を本番で使う場合は OpenAI の利用制限・コスト・プライバシー条件を必ず確認してください。
- J-Quants API の利用には別途トークン取得が必要です。JQUANTS_REFRESH_TOKEN を `.env` に設定してください。

---

この README はコードベースの主要機能と使い方の概要を示しています。詳細な API ドキュメントや運用手順、スキーマ定義（CREATE TABLE 等）は別途参照してください。