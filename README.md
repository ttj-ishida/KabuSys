KabuSys — 日本株自動売買 / データ基盤ライブラリ
=================================

プロジェクト概要
---------------
KabuSys は日本株向けのデータプラットフォーム・リサーチ・AI解析・監査ログを統合するライブラリ群です。  
主に以下の用途を想定しています。

- J-Quants からの株価・財務・カレンダー等の差分 ETL
- RSS ニュース収集と銘柄紐付け
- OpenAI を用いたニュース NLP（銘柄別センチメント）および市場レジーム判定
- 研究用ファクター計算（モメンタム／バリュー／ボラティリティ等）
- 監査（signal → order → execution）用の DuckDB スキーマ初期化と操作
- データ品質チェック（欠損・スパイク・重複・日付不整合）

特徴
----
- DuckDB を中心としたローカル DB 管理（ETL 保存・監査ログ）
- J-Quants API クライアント（トークン自動リフレッシュ、レート制限、リトライ）
- OpenAI（gpt-4o-mini 想定）によるニューススコアリングと市場レジーム判定（JSON Mode を利用）
- ニュース収集は SSRF/XXE 対策を実装（defusedxml、ホスト検査、レスポンス上限等）
- ETL/品質チェック/監査スキーマは冪等性を重視（ON CONFLICT / DELETE→INSERT など）
- プロジェクトルートから .env / .env.local を自動読み込み（環境変数管理）

セットアップ手順
----------------
前提:
- Python 3.10 以上を推奨（型アノテーションに X | None を使用）
- DuckDB を利用するためネイティブ環境でのビルド要件は各自確認してください

1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存関係をインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt を使用）

4. パッケージを開発インストール（任意）
   - pip install -e .

環境変数（必須/任意）
--------------------
自動でプロジェクトルートの .env および .env.local（存在すれば）を読み込みます。
自動読み込みを無効化する場合:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主要な環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注系で使用）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 bot token
- SLACK_CHANNEL_ID: Slack チャンネル ID
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト data/monitoring.db）
- PID_FILE_PATH: 実行監視用 PID ファイルパス
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_ENV: development | paper_trading | live
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL

使い方（概略）
--------------

以下は基本的な利用例です。実行前に必要な環境変数（上記）を設定してください。

1) DuckDB 接続の作成（監査 DB 初期化など）
- Python から:
  - import duckdb
  - from kabusys.config import settings
  - conn = duckdb.connect(str(settings.duckdb_path))
  - ※監査専用 DB を使いたい場合は kabusys.data.audit.init_audit_db(db_path)

2) 日次 ETL 実行（株価・財務・カレンダー取得）
- from kabusys.data.pipeline import run_daily_etl
- result = run_daily_etl(conn, target_date=some_date, id_token=None)
- result は ETLResult オブジェクト（取得数・保存数・品質問題一覧等）を返します

3) ニュースセンチメントのスコアリング（OpenAI 必須）
- from kabusys.ai.news_nlp import score_news
- count = score_news(conn, target_date=some_date, api_key=None)
- api_key を None にすると環境変数 OPENAI_API_KEY を使用します

4) 市場レジーム判定（ETF 1321 + マクロニュース）
- from kabusys.ai.regime_detector import score_regime
- score_regime(conn, target_date=some_date, api_key=None)

5) 監査テーブル初期化（監査ログ用）
- from kabusys.data.audit import init_audit_db, init_audit_schema
- audit_conn = init_audit_db("data/audit.duckdb")  # ファイル初期化して接続を返す
- または既存 conn に対して init_audit_schema(conn, transactional=True)

6) データ品質チェック
- from kabusys.data.quality import run_all_checks
- issues = run_all_checks(conn, target_date=some_date)
- issues は QualityIssue のリスト（各チェック名・重大度・サンプル行を含む）

注意点・運用メモ
----------------
- AI モジュール（news_nlp, regime_detector）は OpenAI を呼び出します。API コスト・レート制限に注意してください。API 呼び出しはリトライ・フェイルセーフ（失敗時はスコア0やスキップ）を備えていますが、運用上の監視を推奨します。
- J-Quants API はレート制限（120 req/min）を守るために内部でスロットリングを行います。大量のページネーション取得を行う場合は時間がかかります。
- news_collector は RSS 取得時に SSRF / XML 攻撃対策を実装していますが、外部ソースを追加する際は URL の妥当性を検証してください。
- ETL や解析関数は「ルックアヘッドバイアス」を避ける設計です。target_date の扱いに注意してバックテスト時のデータ取得順序を守ってください。
- .env の自動読み込み順序: OS 環境変数 > .env.local > .env。テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定します。

ディレクトリ構成（主要ファイル）
-------------------------------
以下は src/kabusys 以下の主なモジュールと概要です。

- __init__.py
  - パッケージ初期化。公開サブパッケージを定義。

- config.py
  - 環境変数の自動読み込み (.env / .env.local)、設定アクセス用 Settings クラス。

- ai/
  - news_nlp.py: ニュースの銘柄別センチメントスコア算出（OpenAI 利用）
  - regime_detector.py: ETF 1321 の MA200 とマクロニュースの LLM 結果を合成して市場レジーム判定
  - __init__.py: ai モジュールのエクスポート

- data/
  - jquants_client.py: J-Quants API クライアント（取得・保存ロジック）
  - pipeline.py: ETL パイプライン（run_daily_etl 等）
  - etl.py: ETLResult の再エクスポート
  - news_collector.py: RSS 収集・前処理・raw_news 保存
  - calendar_management.py: 市場カレンダー管理・営業日ロジック
  - stats.py: 汎用統計ユーティリティ（zscore_normalize など）
  - quality.py: データ品質チェック群と QualityIssue クラス
  - audit.py: 監査ログ（signal/order/execution）スキーマ初期化・ユーティリティ

- research/
  - factor_research.py: モメンタム／ボラティリティ／バリュー等のファクター計算
  - feature_exploration.py: 将来リターン計算、IC（Spearman）計算、統計サマリー
  - __init__.py: 主要関数の再エクスポート

補足（開発者向け）
-----------------
- 単体テストを書く場合、OpenAI や外部 HTTP 呼び出しはパッチ（unittest.mock）で差し替える設計になっています（各モジュールは _call_openai_api や _urlopen をラップしています）。
- DuckDB に対する executemany の挙動（空リスト不可）などドライバ固有の注意がコード内にあります。実行時のバージョン依存に留意してください。
- 型ヒントとドキュメント文字列を重視しているため、関数ごとに設計方針・前提・戻り値が明記されています。ドキュメントはコード内コメント（日本語）を参照してください。

ライセンス・貢献
----------------
（この README にライセンス情報がなければプロジェクトルートの LICENSE を参照ください）  
外部 API キーやトークンの管理には十分注意して、クレデンシャルをリポジトリに含めないでください。

お問い合わせ
------------
不具合報告や改善提案は issue を立てるか、リポジトリのメンテナにお問い合わせください。

以上。必要であれば README のサンプル .env.example や具体的な実行スクリプト例（systemd / cron / GitHub Actions 用ジョブなど）も作成します。どの例が必要か教えてください。