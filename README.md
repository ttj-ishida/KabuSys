# KabuSys

日本株向けのデータプラットフォーム / 自動売買支援ライブラリです。  
DuckDB をデータ層に用い、J-Quants API や RSS / LLM（OpenAI）を組み合わせてデータ収集（ETL）・品質チェック・ニュース NLP・市場レジーム判定・監査ログ管理などを行えます。

---

## 主な特徴（機能一覧）

- ETL（日次）パイプライン
  - J-Quants から株価（OHLCV）・財務・マーケットカレンダーを差分取得して DuckDB に保存
  - 差分取得 / バックフィル / 品質チェック機能を提供
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合の検出（QualityIssue を返す）
- ニュース収集（RSS）
  - RSS 収集、前処理、raw_news / news_symbols への冪等保存
  - SSRF 対策・サイズ制限・トラッキングパラメータ除去などの安全対策を実装
- LLM を用いたニュースセンチメント解析
  - 銘柄ごとにニュースを集約し OpenAI（gpt-4o-mini）でセンチメントを算出し ai_scores テーブルへ格納
  - バッチ処理、リトライ、レスポンス検証
- 市場レジーム判定
  - ETF（1321）200日移動平均乖離 + マクロニュースセンチメントを合成して日次レジーム（bull/neutral/bear）判定
  - OpenAI 呼び出しはフェイルセーフ（失敗時は中立寄り）
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブルを初期化・管理
  - order_request_id を冪等キーとして二重発注を防止
- ユーティリティ
  - マーケットカレンダー操作（営業日判定、next/prev/get_trading_days）
  - 研究用関数（ファクター計算、将来リターン、IC、統計サマリ）
  - 汎用統計ユーティリティ（Zスコア正規化など）

---

## 要求環境（主な依存）

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- その他：標準ライブラリ（urllib, json, logging 等）

推奨: 仮想環境（venv / pipenv / poetry 等）での利用を推奨します。

---

## セットアップ手順

1. リポジトリをクローン（またはパッケージを入手）
   ```bash
   git clone <repository-url>
   cd <repository>
   ```

2. 仮想環境作成と依存インストール（例: pip）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install --upgrade pip
   pip install duckdb openai defusedxml
   # さらにテストや開発用の依存があれば追加
   ```

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそれに従ってください）

3. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml のある場所）に `.env` / `.env.local` を置くと自動で読み込まれます（自動読み込みはデフォルトで有効）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 主要な必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時に引数で渡すことも可）
     - KABU_API_PASSWORD: kabuステーション API パスワード
     - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用（必要な場合）
   - 例（.env）
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
     OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. DuckDB 初期化（必要に応じて）
   - 監査ログ用 DB 初期化:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - 通常は ETL 実行時に使用する DuckDB ファイル（settings.duckdb_path）を開いて利用します。

---

## 使い方（代表的な API / 実行例）

以下はライブラリの主要な利用例です。実行にあたっては事前に環境変数（特に OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN）が正しく設定されていることを確認してください。

- DuckDB 接続を作成して日次 ETL を実行する例
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントスコア付与（score_news）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026,3,20))
  print(f"written scores: {written}")
  # OPENAI_API_KEY を引数で渡すことも可能:
  # score_news(conn, date, api_key="sk-...")
  ```

- 市場レジーム判定（score_regime）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査ログスキーマの初期化（init_audit_schema / init_audit_db）
  ```python
  from kabusys.data.audit import init_audit_db, init_audit_schema
  # 監査専用 DB 作成
  conn = init_audit_db("data/audit.duckdb")

  # 既存接続にスキーマを追加したい場合:
  # init_audit_schema(conn, transactional=True)
  ```

- J-Quants トークン取得（低レベル）
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使って ID トークンを取得
  ```

注意点:
- LLM 関連（score_news / score_regime）は OpenAI API を利用するためコストとレート制限に注意してください。
- ETL / ニュース収集は外部 API / ネットワークを使うため、実行環境のネットワーク設定や API キーが必須です。
- 各関数は duckdb.DuckDBPyConnection を受け取るものが多いです（先に duckdb.connect を行ってください）。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 等で使用）
- KABU_API_PASSWORD — kabu API 用パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID — Slack 通知を使う場合
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV — 環境 (development / paper_trading / live)
- LOG_LEVEL — ログレベル (DEBUG / INFO / WARNING / ERROR / CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する場合に 1 を設定

config.Settings クラスを通じてコード内から参照できます（例: from kabusys.config import settings; settings.jquants_refresh_token）。

---

## ディレクトリ構成（抜粋）

リポジトリの主要ファイル/モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py          # ニュースセンチメント解析（OpenAI）
    - regime_detector.py   # 市場レジーム判定（ETF MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py    # J-Quants API クライアント（取得 + DuckDB 保存）
    - pipeline.py          # ETL パイプラインの実装（run_daily_etl 等）
    - etl.py               # ETL 公開インターフェース（ETLResult 再エクスポート）
    - news_collector.py    # RSS 収集
    - calendar_management.py # マーケットカレンダー管理
    - quality.py           # データ品質チェック
    - stats.py             # 共通統計ユーティリティ（zscore_normalize 等）
    - audit.py             # 監査ログテーブル初期化・管理
  - research/
    - __init__.py
    - factor_research.py   # ファクター計算（momentum/value/volatility）
    - feature_exploration.py # 将来リターン・IC・統計サマリ
  - ai/、research/、data/ 以下にテスト・ユーティリティが含まれる場合があります。

（上記は抜粋です。詳細はリポジトリ内のファイルツリーを参照してください）

---

## 設計上の重要ポイント / 注意事項

- ルックアヘッドバイアスへの配慮:
  - 多くの処理は date や target_date を明示的に受け取り、内部で datetime.today()/date.today() を不用意に参照しない設計になっています。バックテスト時のデータリークを防止します。
- 冪等性:
  - DB への保存は基本的に ON CONFLICT / DO UPDATE を使い冪等性を確保します（jquants_client.save_* 等）。
- フェイルセーフ:
  - LLM や外部 API 呼び出しが失敗した場合でも、処理は可能な限り継続する実装（例: macro_sentiment は失敗時 0.0）です。
- セキュリティ対策:
  - RSS 収集での SSRF 対策、defusedxml 利用、レスポンスサイズ制限などを実装しています。

---

## さらに読む / 拡張点

- strategy / execution / monitoring モジュールがパッケージの公開対象に含まれています（__all__ に定義）。戦略実装や発注フロー・監視アダプタを追加してフル自動売買へ繋げることができます。
- OpenAI の使用はコストと利用規約に注意してください。プロダクション運用時はレート管理・エラー対処・ログ出力を十分整備してください。

---

この README はコードベースの主要機能と使い方の概要を説明しています。実運用や拡張時は各モジュール内の docstring（詳細設計・パラメータ・返り値説明）を参照してください。必要であれば README を具体的な運用手順（デプロイ、cron / Airflow でのスケジューリング、監視方法）に合わせて追記します。