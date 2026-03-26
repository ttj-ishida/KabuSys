# KabuSys

KabuSys は日本株向けのデータプラットフォーム兼自動売買補助ライブラリです。  
J-Quants からのデータ取得・ETL、ニュース収集・NLP による銘柄センチメント評価、マーケットレジーム判定、因子計算（研究用）、監査ログ（発注トレーサビリティ）などを提供します。

主な設計方針：
- ルックアヘッドバイアスを防ぐ（内部で date.today()/datetime.today() を不用意に参照しない）
- DuckDB をデータベースとして利用し、ETL は冪等に実行
- OpenAI（gpt-4o-mini）を用いた JSON Mode による NLP 評価（API 失敗時はフォールバック）
- セキュリティ配慮（RSS の SSRF 防止、XML の defusedxml 利用 等）

---

## 主要機能一覧

- data
  - ETL パイプライン（日次 ETL: 株価、財務、マーケットカレンダー）
  - J-Quants API クライアント（認証、ページネーション、レート制限、リトライ）
  - カレンダー管理（営業日判定、next/prev_trading_day、calendar_update_job）
  - ニュース収集（RSS → raw_news、URL 正規化、SSRF 対策）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログ（signal_events / order_requests / executions テーブル、init ユーティリティ）
  - 汎用統計ユーティリティ（Zスコア正規化）
- ai
  - news_nlp: ニュースを銘柄ごとに集約して LLM でセンチメントを算出し ai_scores に保存
  - regime_detector: ETF（1321）200日 MA とマクロニュース（LLM）を合成して市場レジームを判定
- research
  - factor 計算（momentum / volatility / value）
  - feature exploration（forward returns / IC / summary / rank）
- 設定管理
  - 環境変数・.env の自動ロード・検証（settings オブジェクトでアクセス）

---

## セットアップ手順

前提
- Python 3.10+（typing の一部が利用されているため）
- DuckDB を利用可能であること

1. リポジトリをチェックアウトしてパッケージをインストール（開発モード推奨）
   ```bash
   git clone <repo-url>
   cd <repo>
   pip install -e .
   ```

2. 依存ライブラリ（最小セットの例）
   ```bash
   pip install duckdb openai defusedxml
   ```
   ※ 実環境では additional requirements（HTTP クライアント等）が必要になる可能性があります。プロジェクトの requirements.txt があればそちらを使用してください。

3. 環境変数または .env ファイルを準備する  
   プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化）。
   必須例（.env）
   ```
   JQUANTS_REFRESH_TOKEN=あなたの_jquants_refresh_token
   KABU_API_PASSWORD=あなたの_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   OPENAI_API_KEY=sk-...
   KABUSYS_ENV=development   # development | paper_trading | live
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```
   - settings オブジェクトで必要環境変数の存在を検証します（必須変数がない場合は ValueError が発生します）。

4. DuckDB データベースの初期化（監査ログ用など）
   Python から監査スキーマを初期化する例：
   ```python
   import duckdb
   from kabusys.data.audit import init_audit_db

   conn = init_audit_db("data/audit.duckdb")
   # あるいは既存接続にスキーマ追加
   # conn = duckdb.connect("data/kabusys.duckdb")
   # from kabusys.data.audit import init_audit_schema
   # init_audit_schema(conn, transactional=True)
   ```

---

## 使い方（代表的な API）

以下は主要なユースケースの簡単な使用例です。

- 日次 ETL を実行する（DuckDB 接続を渡す）
  ```python
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  # target_date を指定しない場合は今日が対象（module 内で調整あり）
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- ニュースセンチメント算出（score_news）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY は環境変数に設定しておくか、api_key 引数で渡す
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {n_written}")
  ```

- 市場レジーム判定（score_regime）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 研究用ファクター計算（例：モメンタム）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  factors = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

- 設定値参照
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

注意点：
- OpenAI を呼ぶ関数（news_nlp, regime_detector）は API エラー時にフォールバックする実装になっていますが、API キーが無ければ ValueError を送出します。
- DB 操作は基本的に DuckDB 接続を受け取る形です。接続の管理（ファイルパス、永続化）は呼び出し側で行ってください。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- OPENAI_API_KEY (必須 for AI modules unless passed as arg) — OpenAI API キー
- KABUSYS_ENV — 開発環境: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- DUCKDB_PATH — デフォルトの DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — monitoring 用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動読み込みを無効化

.env のパースは高度に実装されており、シングル/ダブルクォート・エスケープ・コメント処理をサポートします。

---

## ディレクトリ構成（主要ファイル）

プロジェクト内の主要モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・.env 読み込み / settings
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（score_news）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch/save 系）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — 市場カレンダー関連（is_trading_day 等）
    - news_collector.py      — RSS ニュース収集
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログ初期化 / init_audit_db
    - etl.py                 — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py     — momentum / value / volatility
    - feature_exploration.py — forward returns, IC, summary, rank
  - research/*.py
  - ai/*.py
  - その他（strategy / execution / monitoring は将来的な拡張や別モジュールとして意図）

（詳細なファイル一覧はリポジトリの src/kabusys 配下を参照してください）

---

## 運用上の注意

- 本ライブラリは実際の発注（ブローカー API 呼び出し）を直接行うモジュールを含みませんが、監査ログや発注要求のモデルを提供しています。実際のライブ運用を行う場合はリスク管理・レート制限・二重発注防止・監査・セキュリティ周りを十分検討してください。
- OpenAI や J-Quants の API キーは機密情報です。公開リポジトリ等で漏洩しないように注意してください。
- DuckDB のスキーマやテーブル定義は ETL / audit モジュールに依存しています。既存 DB と互換性を保つため、スキーマ変更時はマイグレーション手順を用意してください。

---

## 貢献・開発

- 開発時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを無効化できます（テスト等で便利）。
- テスト用に OpenAI 呼び出し等は各モジュールで差し替え可能（内部の _call_openai_api を patch する等）。
- コードの設計はテスト容易性を考慮しており、外部 API 呼び出しを注入・モックしやすく作られています。

---

もし README に追加したい内容（実運用ガイド、CI/CD、詳細なテーブルスキーマ、サンプル .env.example、依存バージョンなど）があれば教えてください。必要に応じて追記します。