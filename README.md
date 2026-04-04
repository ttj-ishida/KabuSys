KabuSys — 日本株自動売買プラットフォーム
=====================================

概要
----
KabuSys は日本株のデータ収集（J-Quants）、品質チェック、ファクター計算、ニュースNLP（OpenAI）によるセンチメント評価、監査ログ管理等を備えた研究・運用向けライブラリ群です。  
DuckDB を中心としたローカルデータプラットフォームと、J-Quants / OpenAI を組み合わせて ETL → 解析 → シグナル生成 → 発注（発注関連は本コードベースの別モジュールで実装想定）までのパイプライン構築を支援します。

主な機能
--------
- データ取得（J-Quants API）
  - 株価日足（OHLCV）、財務（四半期）データ、JPX マーケットカレンダー取得（jquants_client）
  - レート制限／トークン自動リフレッシュ／ページネーション対応
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新、バックフィル、品質チェック（欠損・スパイク・重複・日付不整合）
  - ETL 実行結果を ETLResult に集約
- ニュース収集（news_collector）
  - RSS 収集、URL 正規化、メモリ・SSRF 対策、raw_news への冪等保存サポート
- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を使った銘柄別ニュースセンチメント算出（バッチやレスポンス検証、リトライ付き）
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF(1321) の 200 日 MA 乖離 + マクロニュースセンチメントを合成して市場レジーム（bull/neutral/bear）判定
- 研究用ツール群（kabusys.research）
  - モメンタム／ボラティリティ／バリュー等のファクター計算、将来リターン、IC 計算、Zscore 正規化
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブルを含む監査スキーマの初期化と DB 作成ユーティリティ
- 設定管理（kabusys.config）
  - .env / .env.local / 環境変数からの設定読み込み（自動ロード）、必須変数チェック

動作環境（概略）
----------------
- Python 3.10+（typing の "X | Y" 構文を使用）
- 主要依存ライブラリ:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス: J-Quants API、OpenAI API（必要に応じて）

セットアップ手順
--------------
1. Python 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (UNIX) / .venv\Scripts\activate (Windows)

2. 必要パッケージのインストール
   - pip install duckdb openai defusedxml
   - その他テスト／開発用には追加パッケージが必要になる場合があります。

3. プロジェクト配置
   - 本コードは src/kabusys 配下に配置されています。通常はパッケージルートに pyproject.toml または .git があれば kabusys.config が自動的にプロジェクトルートを検出して .env ファイルを読み込みます。

4. 環境変数 / .env の用意
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env を作成してください。
   - 主要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - OPENAI_API_KEY=your_openai_api_key
     - KABU_API_PASSWORD=your_kabu_password
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi  (必要に応じて)
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - KILL_FLAG_CLEAR_ON_START=0
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO

   - 自動 .env 読み込みを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時等）。

使い方（API 例）
---------------

- DuckDB 接続の取得（例）
  - import duckdb
  - from kabusys.config import settings
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行（prices / financials / calendar / quality をまとめて実行）
  - from kabusys.data.pipeline import run_daily_etl
  - from datetime import date
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- ニューススコアリング（特定日）
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - written = score_news(conn, target_date=date(2026, 3, 20))
  - print(f"書き込み銘柄数: {written}")

- 市場レジーム判定（特定日）
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは環境変数または api_key 引数で指定

- 監査 DB の初期化
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db(settings.duckdb_path)  # ":memory:" も可

- 設定取得例
  - from kabusys.config import settings
  - print(settings.jquants_refresh_token)  # 未設定なら ValueError

注意点 / 実装上の挙動
-------------------
- .env ファイルパーサは shell 風の export KEY=val、クォート、コメントのルールなどに対応しています。詳細は kabusys.config の実装を参照してください。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を基準に行います。プロジェクトルートが見つからない場合は自動ロードをスキップします。
- OpenAI 呼び出し（news_nlp, regime_detector）はリトライ＆バックオフ、レスポンスバリデーションを行います。API 失敗時はフェイルセーフ（スコア 0.0 など）で継続する設計です。
- J-Quants クライアントはレート制限（120 req/min）を守るための内部 RateLimiter、401 発生時のトークン自動リフレッシュ、ページネーション対応を持ちます。
- DuckDB への保存は基本的に冪等（ON CONFLICT DO UPDATE / DO NOTHING）で行われます。
- すべての日時処理はルックアヘッドバイアス回避のため、外部から渡された target_date を基準に処理を行い、内部で datetime.today() を安易に参照しない方針です（ただし一部ユーティリティは date.today を使用）。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
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
  - calendar_management.py
  - news_collector.py
  - quality.py
  - stats.py
  - audit.py
  - (その他：etl/export 等を想定)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research モジュールは zscore_normalize などのユーティリティと組み合わせてファクター研究・評価を行います。

運用上のヒント
--------------
- 初回は DUCKDB のスキーマ（raw_prices, raw_financials, market_calendar, raw_news, ai_scores, ai_scores など）を適切に作成しておく必要があります。audit.init_audit_schema / init_audit_db は監査テーブルを自動作成します。
- バッチ運用（cron / systemd timer 等）で run_daily_etl を定期実行し、ETLResult をログや監視システムに送るのが一般的です。
- OpenAI API を使う処理はコストがかかるため、実行頻度やバッチサイズ（news_nlp の _BATCH_SIZE 等）を運用に合わせて調整してください。
- 開発・テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して明示的に環境を注入すると安全です。

ライセンス・貢献
----------------
本リポジトリ上のライセンス情報、コントリビューションルールはプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（ここでは明示されていません）。

補足
----
- README に記載したサンプルはライブラリ内部の docstring / ログメッセージに基づく抜粋です。細かな引数や戻り値の仕様は各モジュール（kabusys.data.pipeline, kabusys.ai.news_nlp, kabusys.ai.regime_detector, kabusys.data.jquants_client など）の docstring を参照してください。
- 実運用前に小さなテストデータセットで ETL / NLP / レジーム判定のフローを end-to-end で確認することを推奨します。

必要であれば、README に含める具体的な .env.example、DuckDB スキーマ作成 SQL、あるいは CI / systemd ユニットのサンプルを作成します。どれを追加しますか？