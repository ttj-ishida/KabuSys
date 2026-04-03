# KabuSys

日本株向け自動売買・データ基盤ライブラリ（KabuSys）。  
ETL（J-Quants）による市場データ収集、ニュース収集・NLP（OpenAI）によるセンチメント解析、ファクター計算、監査ログ（発注〜約定追跡）、マーケットカレンダー管理など、戦略開発・研究・運用に必要な機能群を提供します。

バージョン: 0.1.0

---

## 主要機能一覧

- データ取得 / ETL
  - J-Quants API クライアント（ページネーション、レートリミット、トークン自動リフレッシュ）
  - 日足（OHLCV）、財務データ、マーケットカレンダー取得と DuckDB への冪等保存
  - 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- データ品質管理
  - 欠損、スパイク（急変動）、重複、日付不整合のチェック（QualityIssue レポート）
- ニュース収集・NLP
  - RSS 取得（SSRF対策・トラッキングパラメータ除去・XML防御）
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント算出（銘柄別）
  - ニュース時間ウィンドウ計算（JST基準）
- 市場レジーム判定
  - ETF(1321) の MA200 乖離とマクロニュースセンチメントを合成して市場レジーム（bull/neutral/bear）を判定・保存
- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ、Zスコア正規化
- 監査 / トレーサビリティ
  - signal_events / order_requests / executions を含む監査テーブル定義・初期化
  - 監査用 DuckDB 初期化ユーティリティ
- マーケットカレンダー管理
  - JPX カレンダーの差分取得と営業日判定ユーティリティ（next/prev/is_trading_day 等）
- 設定管理
  - .env / .env.local / OS 環境変数からの設定読み込み（自動ロードを無効化するフラグあり）

---

## 必要要件（想定）

（プロジェクトに付属の requirements.txt がない場合の目安）
- Python 3.10+
- パッケージ（主に）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ: urllib, datetime, json など

環境により追加パッケージが必要となる場合があります。実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください。

---

## 環境変数（主なもの）

必須・重要な環境変数やデフォルト値を示します。

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用。関数引数で上書き可能）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START: 監視/プロセスマネジメント関連
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_ENV: 環境 ("development" / "paper_trading" / "live")（デフォルト: development）
- LOG_LEVEL: ログレベル ("DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL")

.env 自動読み込み:
- パッケージはプロジェクトルート（.git または pyproject.toml を探索）を起点に `.env` と `.env.local` を自動で読み込みます。
- 読み込み順: OS 環境変数 > .env.local > .env
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須変数が未設定の場合、settings プロパティ（kabusys.config.Settings）が ValueError を投げます。

---

## セットアップ手順（例）

1. リポジトリをクローン
   - git clone ...; cd your-repo

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール（プロジェクト提供の方法に従ってください）
   - pip install duckdb openai defusedxml
   - またはプロジェクトに requirements.txt / pyproject.toml があれば:
     - pip install -r requirements.txt
     - pip install -e .  （パッケージとしてインストールする場合）

4. 環境変数を設定
   - .env を作成して必須変数（JQUANTS_REFRESH_TOKEN など）を記載してください。
   - 例: .env
     - JQUANTS_REFRESH_TOKEN=...
     - OPENAI_API_KEY=...
     - DUCKDB_PATH=data/kabusys.duckdb

5. データベースディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## 使い方（主要な API 例）

以下はライブラリの主要ユースケース例です。実行前に settings（環境変数）が正しくセットされていることを確認してください。

- 共通インポート例
  - from kabusys.config import settings

- DuckDB に接続して日次 ETL を実行
  - import duckdb
    from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    from kabusys.config import settings

    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニュースセンチメントを計算して ai_scores に保存
  - from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    from kabusys.config import settings

    conn = duckdb.connect(str(settings.duckdb_path))
    written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY は env または引数で指定
    print("written:", written)

- 市場レジーム判定を実行
  - from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime
    from kabusys.config import settings

    conn = duckdb.connect(str(settings.duckdb_path))
    score_regime(conn, target_date=date(2026, 3, 20))

- J-Quants からデータを直接取得（認証・ページネーション対応）
  - from kabusys.data import jquants_client as jq
    token = jq.get_id_token()  # settings.jquants_refresh_token に依存
    records = jq.fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,1,31))
    # 保存
    conn = duckdb.connect(str(settings.duckdb_path))
    jq.save_daily_quotes(conn, records)

- RSS 取得（ニュースコレクタ）
  - from kabusys.data.news_collector import fetch_rss
    articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
    for a in articles:
        print(a["id"], a["title"], a["datetime"])

- 監査ログスキーマの初期化 / 別DBの作成
  - from kabusys.data.audit import init_audit_db
    audit_conn = init_audit_db("data/audit.duckdb")

注意:
- AI 呼び出し（OpenAI）は外部 API の料金が発生します。テスト時は関数をモックするとよいです（コード内で置換ポイントが用意されています）。
- ETL / API 呼び出しはネットワークに依存するため、エラーは例外またはログに記録されます。ETL は各ステップでエラーをハンドルし、可能な範囲で処理を継続します。

---

## 開発時のヒント・挙動

- .env の自動ロードは、パッケージルート（.git または pyproject.toml を基準）を検出して行います。テストなどで自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- settings オブジェクト（kabusys.config.settings）から各種設定を参照できます。未設定の必須値にアクセスすると ValueError を投げます。
- OpenAI 呼び出し部分（news_nlp, regime_detector）はリトライ・フォールバックを持ち、API エラー時には安全側のデフォルト（例: macro_sentiment=0.0）にフォールバックします。
- DuckDB の executemany に空リストを渡すと問題になるバージョンがあるため、コード中で空チェックを行っています。

---

## ディレクトリ構成（主なファイルと説明）

（パッケージルート: src/kabusys/）

- __init__.py
  - パッケージのエクスポート定義。バージョン情報を含む。
- config.py
  - 環境変数読み込み・設定オブジェクト（Settings）
- ai/
  - __init__.py (score_news を公開)
  - news_nlp.py: ニュースを集約して OpenAI で銘柄別センチメントを算出し ai_scores に保存するロジック
  - regime_detector.py: ETF 1321 MA200 乖離 + マクロニュースで市場レジームを判定し market_regime に保存
- data/
  - __init__.py
  - calendar_management.py: JPX カレンダー管理、営業日判定関数群
  - etl.py: ETL インターフェース再エクスポート
  - pipeline.py: ETL パイプライン（run_daily_etl 等）
  - stats.py: zscore_normalize 等の統計ユーティリティ
  - quality.py: データ品質チェック（欠損・スパイク・重複・日付整合性）
  - audit.py: 監査ログスキーマの DDL と初期化ユーティリティ
  - jquants_client.py: J-Quants API クライアント（取得・保存関数）
  - news_collector.py: RSS 収集、前処理、SSRF 対策等
- research/
  - __init__.py
  - factor_research.py: Momentum / Volatility / Value ファクター計算
  - feature_exploration.py: 将来リターン、IC、統計サマリ、ランク関数

---

## 注意事項 / ライセンス等

- 本リポジトリは取引実行（ブローカー発注）周りの実装を含む場合がありますが、運用時は十分なテストとリスク管理を行ってください。実際にマネーを動かす前に paper_trading 環境で検証してください。
- 外部 API（J-Quants / OpenAI 等）の利用に伴う認証情報、レート制限、課金には注意してください。
- ログやトレーサビリティは UTC タイムスタンプで記録されます。設計上、ルックアヘッドバイアスに注意した実装方針が各モジュールに反映されています。

---

README の内容はコードベースから要点を抜粋したものです。より詳細な使用法や CLI / デプロイ手順はプロジェクトの付属ドキュメント（もしあれば）や pyproject.toml / setup.cfg、テストコードを参照してください。必要なら、README に追加する具体的なコマンド例や CI/CD、単体テストの説明を追記します。