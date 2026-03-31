# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
J-Quants からのデータ取得（株価・財務・カレンダー）、ニュース収集・NLP（OpenAI）、研究用ファクター計算、監査ログ（約定トレーサビリティ）などを含むモジュール群を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（簡単なコード例）
- 環境変数（必須/任意）
- ディレクトリ構成（主要ファイルと説明）
- 補足 / 設計上のポイント

---

プロジェクト概要
- KabuSys は日本株のデータパイプライン、ニュース NLP、ファクター計算、監査ログ／発注トレーサビリティなどをまとめたライブラリです。
- ETL（J-Quants） → DuckDB での永続化 → 品質チェック → 研究／戦略評価 → 発注ログ管理、というワークフローを想定しています。
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価や市場レジーム判定機能を備えます。

主な機能
- データ取得（J-Quants API）
  - 日次株価（OHLCV）、財務データ、JPX マーケットカレンダーの差分取得・保存（ページネーション・レート制御・リトライ付き）
- ETL パイプライン
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl を提供
  - 品質チェック（欠損、スパイク、重複、日付不整合）を実行可能
- ニュース収集
  - RSS からの記事収集・前処理・raw_news への冪等保存（SSRF対策、gzip上限、トラッキング除去等）
- ニュース NLP（OpenAI）
  - 銘柄別のニュースセンチメント（ai_scores へ書き込み）
  - マクロ記事を含めた市場レジーム判定（ma200 と LLM センチメントの合成）
- 研究ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、ファクター統計サマリ、Zスコア正規化
- 監査（Audit）
  - signal_events / order_requests / executions テーブルを用いた監査ログと初期化ユーティリティ（init_audit_db / init_audit_schema）

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. Python 環境（推奨: 3.10+ / 3.11）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール
   - pip install -e .     # パッケージを開発モードでインストール
   - 主要な外部依存（明示的に必要な場合）:
     - duckdb
     - openai
     - defusedxml
   - 例: pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt がある場合はそれを利用してください）

4. データディレクトリを作成（任意）
   - mkdir -p data

5. 環境変数を設定
   - プロジェクトルートに .env を配置すると自動で読み込まれます（.env.local は .env を上書きする形で読み込まれます）。
   - 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方（簡単なコード例）
- DuckDB 接続を作って ETL を実行する例:

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュース NLP（ai_scores に書き込む）:

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY を環境変数で設定するか、api_key 引数に渡す
  n = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {n} codes")

- 市場レジーム判定（market_regime テーブルへ書き込む）:

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を使用

- 監査DBの初期化:

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # ディレクトリがなければ自動作成

環境変数（README に含めておくべき主要キー）
- 必須（Settings._require で要求される）
  - JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン（get_id_token に使用）
  - KABU_API_PASSWORD      — kabuステーション API パスワード
  - SLACK_BOT_TOKEN        — Slack 通知用 Bot トークン
  - SLACK_CHANNEL_ID       — Slack 通知チャンネル ID

- 任意（デフォルトあり / 環境による）
  - KABUSYS_ENV            — development / paper_trading / live （デフォルト development）
  - LOG_LEVEL              — DEBUG / INFO / WARNING / ERROR / CRITICAL （デフォルト INFO）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 をセットで .env 自動読み込みを無効化
  - KABU_API_BASE_URL      — kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
  - DUCKDB_PATH            — デフォルト data/kabusys.duckdb
  - SQLITE_PATH            — 監視用 sqlite path（デフォルト data/monitoring.db）
  - OPENAI_API_KEY         — OpenAI 呼び出しを行う場合に必要（score_news / score_regime にも渡せる）

サンプル .env（プロジェクトルート）:

  JQUANTS_REFRESH_TOKEN=xxxxx
  KABU_API_PASSWORD=xxxxx
  SLACK_BOT_TOKEN=xoxb-...
  SLACK_CHANNEL_ID=C01234567
  OPENAI_API_KEY=sk-...
  KABUSYS_ENV=development
  DUCKDB_PATH=data/kabusys.duckdb

ディレクトリ構成（主要ファイル・モジュール）
- src/kabusys/
  - __init__.py                — パッケージ定義（__version__=0.1.0）
  - config.py                  — 環境変数読み込み・Settings クラス（.env 自動読み込みロジック含む）
  - ai/
    - __init__.py
    - news_nlp.py              — ニュースの集約・OpenAI でのスコアリング・ai_scores への書き込み
    - regime_detector.py       — ma200 と LLM を重み合成して市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得・保存・リトライ・レート制御）
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py   — 市場カレンダー管理（営業日判定 / calendar_update_job）
    - news_collector.py        — RSS 収集 / 前処理 / raw_news へ保存（SSRF対策等）
    - quality.py               — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py                 — zscore_normalize 等の統計ユーティリティ
    - audit.py                 — 監査ログ（DDL・初期化・init_audit_db）
    - pipeline.py              — ETLResult と各 run_*_etl / run_daily_etl
    - etl.py                   — ETL インターフェース再エクスポート
  - research/
    - __init__.py
    - factor_research.py       — momentum/volatility/value 等のファクター計算
    - feature_exploration.py   — forward returns / IC / factor_summary / rank
  - research/__init__.py

（注）README 上で言及されていない補助モジュールや strategy / execution / monitoring などは将来的な拡張ポイントとして想定されています。

設計上のポイント / 注意事項
- Look-ahead bias を避ける設計が随所に組み込まれています。各スコア・ETL は target_date 引数を明示的に受け取り、内部で datetime.today() を無闇に参照しないようになっています。
- OpenAI 呼び出しは JSON mode を利用し、レスポンスのバリデーション（パース失敗や API エラー時のフォールバック）を行います。API のレート制御や再試行ロジックが組み込まれていますが、API キー管理は利用者側で行ってください。
- DuckDB を永続層に使用することでローカルでの高速な分析・ETL が可能です。初期化ユーティリティ（init_audit_db 等）を使ってスキーマを作成してください。
- news_collector は SSRF / XML Bomb / 大容量レスポンス対策を実装しています。外部 RSS を取得するため、ネットワークアクセス許可・プロキシ設定に注意してください。

拡張・運用のヒント
- CI / cron に run_daily_etl を組み込むことで夜間 ETL を自動化できます。
- score_news / score_regime はバッチ処理向けに設計されており、失敗時は安全にフォールバックするため、スケジューリングで定期実行してください。
- 監査ログ（audit）を別 DB に切り出すことで本番の監査履歴を独立して管理できます（init_audit_db）。

ライセンス・貢献
- （ここにライセンス情報やコントリビューションガイド、連絡先を追記してください）

---

README に載せた情報はコードベース（config/ai/data/research モジュール）を簡略にまとめたものです。より詳細な API 仕様・運用手順は各モジュールの docstring やコードコメント（src 以下）を参照してください。必要であれば README にサンプル .env.example、CI 設定例、デプロイ手順（systemd / kubernetes）なども追記できます。どの情報を追加しますか？