# KabuSys — 日本株自動売買プラットフォーム（README）

このリポジトリは「KabuSys」と名付けられた日本株向けデータプラットフォーム兼自動売買基盤の一部実装です。主にデータのETL、データ品質チェック、ニュースNLP（LLMによるセンチメント）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（トレーサビリティ）などの機能を提供します。

以下はプロジェクトの概要、機能一覧、セットアップ手順、使い方の例、およびディレクトリ構成の説明です。

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要APIの例）
- 環境変数（.env）の例
- ディレクトリ構成（主要ファイルの説明）

---

プロジェクト概要
- KabuSys は日本株のデータパイプラインと自動売買周辺機能をまとめたライブラリ群です。
- J-Quants API からの株価・財務・カレンダー取得、RSSによるニュース収集、OpenAI を用いたニュースセンチメント／市場レジーム判定、ファクター計算、品質チェック、監査ログ管理などを提供します。
- DuckDB をデータ格納エンジンとして利用する想定です（監査用DBも DuckDB）。

機能一覧
- データ取得 & ETL
  - J-Quants API クライアント（差分取得、ページネーション、認証リフレッシュ、レートリミット、リトライ）
  - 日次ETL パイプライン（市場カレンダー／株価日足／財務データの差分取得・保存）
- データ品質チェック
  - 欠損データ、スパイク（急騰・急落）、重複、日付不整合チェック
- ニュース収集 & NLP
  - RSS フィード取得（SSRF対策、サイズ上限、URL 正規化、記事ID生成）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント（score_news）
  - マクロニュース + ETF(1321)のMA乖離を合成した市場レジーム判定（score_regime）
- リサーチ / ファクター
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions のテーブル定義と初期化ユーティリティ
  - 冪等性と監査性を重視した設計
- 設定管理
  - .env 自動読み込み（プロジェクトルート特定ロジック）と Settings クラス経由の参照

セットアップ手順（ローカル開発向け）
1. Python 仮想環境を作成
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストール
   - このリポジトリに requirements.txt がない場合、主要依存は次の通りです：
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml
   - パッケージをローカル開発用にインストールする場合（プロジェクトルートに pyproject.toml/setup.cfg がある想定）:
     - pip install -e .

3. 環境変数の設定
   - プロジェクトルートに .env/.env.local を作成して必要な環境変数を設定します（下部に例あり）。
   - 自動読み込みを無効にしたいテスト時などは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

4. DuckDB ファイルや監査DB用ディレクトリを用意
   - デフォルトの DuckDB パスは data/kabusys.duckdb（Settings.duckdb_path）です。
   - 監査用DBの初期化ユーティリティも提供しています（kabusys.data.audit.init_audit_db）。

使い方（例）
- 共通準備
  - settings を使ってパス等を取得できます。
    - from kabusys.config import settings
    - settings.duckdb_path など

- DuckDB 接続を作る
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次ETL を実行する
  - from datetime import date
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - result は ETLResult オブジェクトで、取得・保存件数や品質チェックの結果・エラーを持ちます。

- ニュースのスコアリング（OpenAI 必須）
  - from datetime import date
  - from kabusys.ai.news_nlp import score_news
  - scores_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...") 
    - api_key を None にすると環境変数 OPENAI_API_KEY が使われます。
  - 戻り値は書き込んだ銘柄数（int）。

- 市場レジーム判定（OpenAI + DAO）
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")

- 監査DBの初期化
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")  # :memory: も可

- ファクター計算（リサーチ）
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  - momentum = calc_momentum(conn, target_date=date(2026, 3, 20))

- データ品質チェックの実行
  - from kabusys.data.quality import run_all_checks
  - issues = run_all_checks(conn, target_date=date(2026, 3, 20))

設定（主な環境変数）
- 必須（Settings クラス経由で _require() を呼ぶため未設定だと ValueError になる）
  - JQUANTS_REFRESH_TOKEN : J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD     : kabuステーション API パスワード（発注等に使用）
  - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
  - SLACK_CHANNEL_ID      : Slack チャンネル ID
  - OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime で使用）
- オプション（デフォルト値あり）
  - KABUSYS_ENV (development | paper_trading | live) — デプロイ環境
  - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
  - DUCKDB_PATH（default: data/kabusys.duckdb）
  - SQLITE_PATH（default: data/monitoring.db）
  - PID_FILE_PATH（default: data/execution.pid）
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT（監視閾値）
- 自動 .env 読み込み挙動
  - プロジェクトルート (.git または pyproject.toml を起点) に .env / .env.local を置くと自動読み込み（OS 環境変数優先）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能

.env の例
（プロジェクトルートに .env を作成して設定してください）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxx
SLACK_CHANNEL_ID=C0123456789
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意点 / 設計方針（抜粋）
- Look-ahead bias（ルックアヘッド）対策
  - 各処理は内部で datetime.today()/date.today() を直接参照しないように設計されており、処理対象日（target_date）を明示的に渡すことを想定しています。
- フェイルセーフ
  - OpenAI API の失敗や一部の外部API障害はフォールバック（スコア=0 等）で続行する設計です。重大なDB書き込みエラー等は例外として伝播します。
- 冪等性
  - ETL の保存処理は基本的に ON CONFLICT DO UPDATE 等の冪等化を行っています（DuckDB 上の実装に依存）。

ディレクトリ構成（src/kabusys 配下の主要モジュール）
- __init__.py
  - パッケージのバージョン情報と公開サブパッケージ一覧
- config.py
  - .env 自動読み込み、Settings クラス（すべての主要設定を取得）
- ai/
  - __init__.py
  - news_nlp.py : ニュースを銘柄単位に集約してOpenAIでセンチメントを算出し ai_scores に書込む
  - regime_detector.py : ETF(1321)のMA乖離とマクロニュースセンチメントを合成して market_regime に書込む
- data/
  - __init__.py
  - jquants_client.py : J-Quants API クライアント（取得・保存・認証・レート制御）
  - pipeline.py : ETL パイプライン（run_daily_etl 等）と ETLResult
  - etl.py : ETL レイヤーの公開インターフェース（ETLResult を再エクスポート）
  - quality.py : データ品質チェック（欠損・スパイク・重複・日付不整合）
  - news_collector.py : RSS 取得・前処理・raw_news への保存補助
  - calendar_management.py : 市場カレンダーの管理・営業日判定・calendar_update_job
  - stats.py : 汎用統計（zscore_normalize 等）
  - audit.py : 監査テーブル定義と初期化ユーティリティ
- research/
  - __init__.py
  - factor_research.py : モメンタム / ボラティリティ / バリュー等のファクター計算
  - feature_exploration.py : 将来リターン計算・IC・統計サマリー・ランク処理
- その他
  - ai・data・research 配下に多数のユーティリティ実装と SQL を含む

開発・運用上の補足
- OpenAI 呼び出しは JSON Mode を想定しており、レスポンスのパースやリトライ処理が実装済みです。単体テストでは内部の _call_openai_api をモックすることを想定しています。
- RSS の取得は SSRF 対策（リダイレクト検査／プライベートIP拒否）・レスポンスサイズ制限・XMLパース防御（defusedxml）を備えます。
- J-Quants API クライアントはレート制御と 401 の自動リフレッシュ、ページネーション対応、リトライロジックを実装しています。
- DuckDB のバージョンや executemany の空リスト挙動に関してコメントが複数あります。運用時は DuckDB のバージョンに注意してください。

ライセンスや貢献ガイドなど
- 本 README に記載のないライセンス情報・貢献ルールがあればリポジトリのルートにある LICENSE / CONTRIBUTING を参照してください（本コードダンプでは含まれていません）。

問い合わせ
- 実装や API の使い方で不明点があれば、関係者に問い合わせるか、実装ファイルの docstring を参照してください。各モジュールは詳細な docstring と設計方針を含んでいます。

以上。README に追加したい具体的なコマンド、CI のセットアップ、もしくは利用シナリオ（デモジョブ／cron設定）の例があれば教えてください。それに合わせて追記します。