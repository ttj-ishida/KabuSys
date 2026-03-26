# KabuSys

日本株向けの自動売買・データプラットフォームライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP によるセンチメント分析、ファクター計算、監査ログ（発注/約定トレーサビリティ）などを含んだモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータ収集・品質チェック・特徴量生成・ニュースNLP・市場レジーム判定・監査ログ管理を行うためのライブラリ群です。主な目的は以下です。

- J-Quants API を用いた株価・財務・カレンダーの差分 ETL（DuckDB 保存）
- RSS ベースのニュース収集と OpenAI を使った銘柄別センチメントスコア算出
- ETF とマクロニュースを組み合わせた市場レジーム判定
- ファクター計算（モメンタム、ボラティリティ、バリュー等）と研究支援ユーティリティ
- 監査用テーブル（signal / order_request / executions）の生成と初期化
- データ品質チェック（欠損・重複・スパイク・日付不整合）

設計上、ルックアヘッドバイアスを避けるために `date` / `target_date` ベースで処理を行い、日時の自動参照（datetime.today() 等）に依存しない実装が多数あります。

---

## 機能一覧（抜粋）

- 環境変数/設定管理（自動でプロジェクトルートの `.env` / `.env.local` を読み込む仕組み）
- J-Quants クライアント
  - 株価日足（OHLCV）取得 / 保存（fetch/save）
  - 財務データ取得 / 保存
  - マーケットカレンダー取得 / 保存
  - レート制御・リトライ・トークンリフレッシュ対応
- ETL パイプライン
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - ETLResult を返す（品質チェック結果含む）
- データ品質チェック（quality.run_all_checks 等）
- ニュース収集（RSS）と前処理（URL除去・正規化・SSRF 対策）
- ニュース NLP（OpenAI を利用、JSON Mode）
  - `score_news(conn, target_date, api_key=None)`：銘柄ごとの ai_scores 書き込み
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースセンチメント）
  - `score_regime(conn, target_date, api_key=None)`：market_regime への書き込み
- 研究用ユーティリティ
  - Factor 計算（calc_momentum / calc_volatility / calc_value）
  - 将来リターン計算、IC（Spearman）、統計サマリー、Z スコア正規化
- 監査ログ（audit）
  - `init_audit_schema` / `init_audit_db` による監査テーブル初期化

---

## セットアップ手順

以下はローカル開発や簡易実行用の手順です。プロジェクトの packaging / requirements は環境に応じて調整してください。

1. Python 環境準備
   - 推奨 Python 3.10+（コードは型注釈に Python 3.10 の構文を利用）
   - 仮想環境作成を推奨:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 必要パッケージの一例:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください）

3. パッケージを編集可能モードでインストール（開発時）
   - pip install -e .

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を配置すると自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。
   - 主要な環境変数（必須 / 推奨）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD : kabu API パスワード（必須）
     - KABU_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN : Slack 通知に使う Bot トークン（必須）
     - SLACK_CHANNEL_ID : Slack チャンネル ID（必須）
     - OPENAI_API_KEY : OpenAI を使う場合に必要（news_nlp / regime_detector）
     - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH : 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV : environment ("development" / "paper_trading" / "live")（デフォルト: development）
     - LOG_LEVEL : ログレベル ("DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL")（デフォルト: INFO）

   - .env の書式は shell の KEY=value に準拠しています。クォートやコメントのパースに対応しています。

5. DB の初期化（監査DB例）
   - Python REPL などで:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")
   - `init_audit_db` は親ディレクトリを自動作成します。

---

## 使い方（主要な例）

以下は代表的な使い方例です。実行は適切に設定された環境変数と duckdb ファイルが必要です。

- DuckDB 接続の取得（簡易）
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行（run_daily_etl）
  - from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    from kabusys.config import settings
    import duckdb
    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026,3,20))
    print(result.to_dict())

- ニュースセンチメントスコアを生成（score_news）
  - from kabusys.ai.news_nlp import score_news
    from kabusys.config import settings
    import duckdb
    conn = duckdb.connect(str(settings.duckdb_path))
    # OPENAI_API_KEY が環境に設定されていれば api_key 引数は不要
    n_written = score_news(conn, target_date=date(2026,3,20))
    print(f"書き込んだ銘柄数: {n_written}")

- 市場レジーム判定（score_regime）
  - from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect(str(settings.duckdb_path))
    score_regime(conn, target_date=date(2026,3,20))

- 監査スキーマ初期化
  - from kabusys.data.audit import init_audit_schema, init_audit_db
    conn = init_audit_db("data/audit.duckdb")
    # または既存接続で
    # init_audit_schema(conn, transactional=True)

- ニュース RSS 取得
  - from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
    articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
    for a in articles:
        print(a["title"], a["datetime"])

注意点:
- OpenAI API 呼び出しは外部ネットワークを使います。APIキーは環境変数 OPENAI_API_KEY を設定してください。テスト時は内部の _call_openai_api をモックする設計になっています。
- ETL/保存は DuckDB に対する INSERT ... ON CONFLICT を利用し冪等性を保証しています。
- 日時周りは Look-ahead バイアスを避ける設計（target_date を明示）です。バッチ実行やバックテストの際は target_date の扱いに注意してください。

---

## ディレクトリ構成（主要ファイルと概要）

（ルートは src/kabusys 以下）

- __init__.py
  - パッケージエクスポート: data, strategy, execution, monitoring
- config.py
  - 環境変数読み込み / Settings を提供（.env 自動読み込み、必須キーチェック）
- ai/
  - __init__.py
  - news_nlp.py：銘柄毎ニュースをまとめて OpenAI に送り ai_scores に書き込むロジック
  - regime_detector.py：ETF 1321 の MA200 乖離 + マクロニュースで市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py：J-Quants API クライアント（取得・保存ロジック・レート制御）
  - pipeline.py：run_daily_etl 等の ETL パイプライン
  - etl.py：ETLResult の再エクスポート
  - news_collector.py：RSS の取得・前処理・保存補助
  - calendar_management.py：市場カレンダー管理・営業日ロジック
  - stats.py：zscore_normalize 等の統計ユーティリティ
  - quality.py：データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py：監査ログ（シグナル・発注・約定）テーブル定義と初期化
- research/
  - __init__.py
  - factor_research.py：モメンタム/ボラティリティ/バリュー等のファクター計算
  - feature_exploration.py：forward returns, IC, factor summary, rank 等
- その他
  - strategy/, execution/, monitoring/（README の先頭で __all__ に含まれている可能性のある領域。実装は今後追加または別モジュールに依存）

---

## 注意事項・運用上のヒント

- 自動環境変数読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基準に行います。CI やテストで自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI を使う機能は外部APIコストが発生します。バッチ実行ではコストとレートに注意してください（各モジュールでリトライ/レート制御が実装されています）。
- DuckDB を永続化する場合は DUCKDB_PATH を設定し、バックアップ・ローテーションを検討してください。
- ETL は各ステップごとに例外をキャッチして継続する設計です。`ETLResult` の `errors` / `quality_issues` を確認して運用判断してください。
- tests を実行する際は OpenAI 呼び出しや HTTP の外部接続をモックすることを推奨します（コード内に差し替えや patch を想定した実装あり）。

---

もし README に追記したい項目（例: CI の設定、具体的な SQL スキーマ、サンプル .env.example の内容、インストール可能なパッケージ一覧）があれば教えてください。必要に応じて README を拡張します。