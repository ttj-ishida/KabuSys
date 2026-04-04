# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。  
ETL（J-Quants 経由の株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI を利用したセンチメント）、研究用ファクター計算、監査ログ用スキーマなどを含むモジュール群を提供します。

---

## 特徴（概要）

- J-Quants API 経由で株価・財務・カレンダーを差分取得する ETL パイプライン
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント（銘柄別）スコアリング
- ETF（1321）200日移動平均とマクロニュースの合成による市場レジーム判定
- DuckDB を利用したデータ保存／冪等的な保存ロジック（ON CONFLICT に準拠）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal_events / order_requests / executions）テーブルの初期化ユーティリティ
- 研究用モジュール：ファクター計算、将来リターン、IC（Spearman）計算、Zスコア正規化等

---

## 主な機能一覧

- ETL（差分取得・保存・品質チェック）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- ニュース収集
  - fetch_rss（RSS 取得／前処理） / raw_news への保存ロジック（news_collector）
- ニュース NLP（OpenAI）
  - score_news(conn, target_date, api_key=None) — 銘柄別 ai_scores 書き込み
- 市場レジーム判定（AI + テクニカル）
  - score_regime(conn, target_date, api_key=None) — market_regime に書き込み
- J-Quants API クライアント
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, get_id_token 等
- データ品質チェック
  - run_all_checks（欠損・スパイク・重複・日付不整合）
- 監査ログ初期化
  - init_audit_schema / init_audit_db
- 研究用ツール
  - calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary / zscore_normalize

---

## セットアップ手順

前提
- Python 3.10 以上（typing の "|" などを使用）
- DuckDB を利用（ローカルファイルまたはインメモリ）
- OpenAI API キー（ニュース NLP / レジーム判定で使用）
- J-Quants リフレッシュトークン

推奨インストール（例）

1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   ※プロジェクトに requirements.txt / pyproject.toml があればそちらからインストールしてください。

3. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 利用する主な環境変数:
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
     - KABU_API_PASSWORD (必須) — kabu API パスワード
     - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime に未指定時に参照）
     - KABU_API_BASE_URL (任意) — kabu ステーション API ベース URL（デフォルト: http://localhost:18080/kabusapi）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（任意） — 通知用
     - DUCKDB_PATH（任意、デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（任意、デフォルト: data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
     - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
     - 監視関連（PID_FILE_PATH, KILL_FLAG_PATH, CPU_THRESHOLD_PCT 等）

   .env ファイルの例（参考）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

---

## 使い方（例）

以下はライブラリをインポートして機能を呼ぶ最小例です。実運用ではログ設定や例外処理を追加してください。

- DuckDB 接続作成と ETL 実行（日次 ETL）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのスコアリング（OpenAI API キーを環境変数にセットしている想定）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"wrote {written} ai_scores")
  ```

  または明示的に api_key を渡す:
  ```python
  score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026,3,20), api_key=None)  # 環境変数OPENAI_API_KEYを参照
  ```

- 監査ログ用 DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # または既存接続に対して init_audit_schema(conn)
  ```

- RSS フィード取得（ニュース収集の一部）
  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  ```

注意点
- score_news / score_regime は OpenAI を呼び出すため API キーが必要です。API 呼び出しの失敗はフェイルセーフとして一部機能ではゼロにフォールバックする実装がありますが、意図した動作のためには安定したキーと料金設定を用意してください。
- get_id_token / J-Quants API は rate limit・リトライ・401 リフレッシュに対応しています。JQUANTS_REFRESH_TOKEN は必須です。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env 自動ロード / Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント取得（score_news）
    - regime_detector.py — ETF MA200 とマクロニュースの合成による市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント、保存ロジック（save_*）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）、ETLResult
    - etl.py — ETLResult の再公開
    - news_collector.py — RSS 取得・前処理・ID生成（SSRF 対策あり）
    - calendar_management.py — 市場カレンダー管理・営業日判定・calendar_update_job
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py — 監査ログテーブル定義と初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank
  - research*.py etc. (研究用補助ファイル)

プロジェクトルートでは .env / .env.local が自動的に読み込まれます（priority: OS env > .env.local > .env）。自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 実運用上の注意

- 秘密情報（トークン等）は .env に保管するか CI のシークレット管理を利用し、リポジトリに含めないでください。
- OpenAI / J-Quants の API 利用に伴う課金やレート制限に注意してください（jquants_client ではレートリミッタ・リトライ実装あり）。
- DuckDB のバージョンによっては executemany の挙動やリストバインドに差異があるため、コード中で互換性考慮がなされていますが、利用する DuckDB のバージョンを固定しておくと安心です。
- バックテストや研究用途でデータのルックアヘッド（未来データ参照）が発生しないよう、各モジュールは date 引数を明示的に受け取る実装になっています。必ず target_date を明示して使用してください。

---

必要に応じて README を拡張して、具体的なコマンドライン実行例（スケジューリング/cron、systemd ユニット、Dockerfile など）や CI 設定、テストの流れを追加できます。必要であればそれらのテンプレートも作成します。