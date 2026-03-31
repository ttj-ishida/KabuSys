# KabuSys

KabuSys は日本株向けの自動売買 / データ基盤ライブラリです。J-Quants と各種 RSS / OpenAI を組み合わせてデータ収集・品質チェック・特徴量計算・ニュース NLP・市場レジーム判定・監査ログ管理などを行うことを目的としています。

主な設計方針は「ルックアヘッドバイアス防止」「冪等性」「堅牢な API リトライ/レート制御」「DuckDB を用いたローカルデータ管理」「外部システム（発注等）への直接アクセスを研究・実行レイヤーで分離」です。

## 機能一覧
- データ取得 / ETL
  - J-Quants からの株価（日足）・財務・マーケットカレンダー取得（RateLimiter、ページネーション、トークン自動リフレッシュ、冪等保存）
  - ETL パイプライン（差分取得・バックフィル・品質チェック）
- データ品質チェック
  - 欠損（OHLC）検出、スパイク検出、重複チェック、日付整合性チェック
- ニュース収集・NLP
  - RSS 収集（SSRF 対策、URL 正規化、トラッキング除去、前処理）
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメントスコアリング（銘柄別バッチ処理）
- 市場レジーム判定
  - ETF（1321）の 200 日移動平均乖離とマクロニュースセンチメントを合成して日次のレジーム判定（bull/neutral/bear）
- リサーチ / ファクター計算
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- 監査ログ / トレーサビリティ
  - signal_events / order_requests / executions を記録する監査スキーマの初期化ユーティリティ（DuckDB）
- 設定管理
  - .env / .env.local / OS 環境変数からの読み込み（自動ロードを無効化するオプションあり）

## セットアップ手順

前提: Python 3.10+（型ヒントに Union 演算子等を利用）、pip、git が使えること。

1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作る（推奨）
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 必須（主なもの）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml
   - 開発・実行向けにパッケージ化されている場合:
     - pip install -e .

4. 環境変数（.env）を準備
   - プロジェクトルートに .env/.env.local を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば自動ロードを無効化できます）。
   - 必須環境変数（少なくとも以下は必要）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL 用）
     - SLACK_BOT_TOKEN — Slack 通知が必要な処理で必要
     - SLACK_CHANNEL_ID — Slack 通知先チャンネルID
     - KABU_API_PASSWORD — kabuステーション API を使う場合に必要
   - OpenAI を使う機能を利用する場合:
     - OPENAI_API_KEY — AI 評価用（score_news / score_regime 等）。関数呼び出し時に api_key 引数で明示することも可能。
   - そのほか（デフォルト値あり）:
     - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT, KABUSYS_ENV, LOG_LEVEL

5. DuckDB 用ディレクトリ作成（必要なら）
   - settings.duckdb_path の親ディレクトリが存在しない場合は作成しておく（多くの初期化ユーティリティは自動で作成します）。

## 使い方（基本例）

以下は Python スクリプト/REPL での利用例です。

- ETL（日次 ETL を実行）
  - 例:
    - from datetime import date
      import duckdb
      from kabusys.data.pipeline import run_daily_etl
      from kabusys.config import settings
      conn = duckdb.connect(str(settings.duckdb_path))
      result = run_daily_etl(conn, target_date=date(2026, 3, 20))
      print(result.to_dict())

- ニュースセンチメントのスコアリング（score_news）
  - from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect(str(settings.duckdb_path))
    # OPENAI_API_KEY が環境変数に設定されていない場合は api_key=... を渡す
    written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
    print(f"書き込み銘柄数: {written}")

- 市場レジームの判定（score_regime）
  - from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect(str(settings.duckdb_path))
    score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 監査 DB の初期化（監査専用の DuckDB を作る）
  - from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
    # 以降 conn をアプリケーションの監査ログ書き込みに使用

- ファクター計算 / リサーチユーティリティ
  - from datetime import date
    import duckdb
    from kabusys.research import calc_momentum, calc_value, calc_volatility
    conn = duckdb.connect(str(settings.duckdb_path))
    mom = calc_momentum(conn, date(2026,3,20))
    vol = calc_volatility(conn, date(2026,3,20))
    val = calc_value(conn, date(2026,3,20))

注意:
- API キーを引数として渡せる関数も多く、テスト時は環境変数に依存しないように呼び出し側で注入できます。
- 各 AI 呼び出しは内部でリトライ・フォールバック（失敗時は中立スコア 0.0）等を行います。致命的な例外は通常呼び出し側へ伝播します。

## 環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN — 必須（J-Quants のリフレッシュトークン）
- OPENAI_API_KEY — OpenAI API を使う場合に必要（関数引数で上書き可能）
- KABU_API_PASSWORD — kabu ステーション API のパスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知に使用
- DUCKDB_PATH — デフォルトデータベースパス（data/kabusys.duckdb）
- SQLITE_PATH — 監視用 sqlite パス（data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視に関する設定
- KABUSYS_ENV — development / paper_trading / live のいずれか
- LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env の自動ロードを無効化

.env の読み込みについて:
- 自動読み込みの優先順は OS 環境 > .env.local > .env です。
- .env のパーサは export KEY=val 形式、クォート内のエスケープ等に対応します。

## ディレクトリ構成（抜粋）
（主要モジュールと役割を示します）

- src/kabusys/
  - __init__.py                — パッケージ定義（__version__ 等）
  - config.py                  — 環境変数 / 設定管理
  - ai/
    - __init__.py              — AI 関連の公開 API
    - news_nlp.py              — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py       — 市場レジーム判定（MA + マクロセンチメント）
  - data/
    - __init__.py
    - calendar_management.py   — マーケットカレンダー管理・営業日判定
    - etl.py                   — ETL の公開インターフェース（ETLResult）
    - pipeline.py              — 日次 ETL パイプライン（prices/financials/calendar）
    - stats.py                 — 汎用統計ユーティリティ（z-score）
    - quality.py               — データ品質チェック
    - audit.py                 — 監査スキーマ初期化 / DB 初期化
    - jquants_client.py        — J-Quants API クライアント（取得・保存）
    - news_collector.py        — RSS 収集・前処理・保存
  - research/
    - __init__.py
    - factor_research.py       — モメンタム / バリュー / ボラティリティ等
    - feature_exploration.py   — 将来リターン計算 / IC / 統計サマリ
  - その他（strategy / execution / monitoring 等のモジュールは __all__ に含まれているが、本コードベースの一部に実装が想定されます）

## 開発メモ / トラブルシューティング
- 環境変数が足りない場合、Settings プロパティは ValueError を投げます。エラーメッセージに従って .env を整備してください。
- OpenAI 呼び出しはリトライ・バックオフを持ちますが、API キーやクォータ切れではスコアが 0.0 にフォールバックすることがあります。動作を確認する場合はログを DEBUG に上げてください。
- DuckDB に対する executemany の空リスト渡しは一部バージョンでエラーになるため、該当箇所では事前に空チェックがされています（pipeline/news_nlp 等）。
- RSS 取得は SSRF 対策やレスポンスサイズ制限を行っています。外部の不正なフィードを扱う場合は注意してください。
- audit.init_audit_schema は transactional オプションを持ちます。DuckDB のトランザクション挙動に注意して呼び出してください（ネストトランザクション非対応）。

---

この README はコードベースの主要機能と使い方の概要をまとめたものです。実際の運用やデプロイ時には .env の取り扱い、API キー管理（シークレットストア利用）、バックアップ、監視・アラート設計など追加の運用設計が必要です。必要であれば導入ガイドや運用チェックリストの追加も作成します。