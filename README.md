KabuSys
=======

概要
----
KabuSys は日本株の自動売買 / データ基盤 / 研究用ユーティリティをまとめた Python パッケージです。  
J-Quants API からのデータ取得と DuckDB を用いた永続化、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログスキーマなど、実運用・研究の両面を意識したモジュール群を提供します。

主な特徴
--------
- データ取得(ETL)
  - J-Quants API から株価日足 / 財務データ / 市場カレンダーを差分で取得し DuckDB に保存
  - ページネーション・レート制御・リトライ・トークン自動更新対応
- データ品質
  - 欠損・スパイク・重複・日付不整合などの品質チェック機能
- ニュース NLP
  - RSS 収集・前処理・OpenAI を用いた銘柄ごとのニュースセンチメント計算（ai_scores への書き込み）
  - LLM 呼び出しはリトライとレスポンスバリデーションを備える
- 市場レジーム判定
  - ETF(1321) の 200 日 MA 乖離とマクロニュースの LLM センチメントを合成して日次のレジーム判定
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリューなどのファクター計算
  - 将来リターン計算、IC（Spearman）やファクター統計サマリー
  - Z-score 正規化などの統計ユーティリティ
- 監査ログ（トレーサビリティ）
  - signal → order_request → execution の階層を保持する監査スキーマ（DuckDB）を初期化するユーティリティ

依存関係（代表）
----------------
本リポジトリのコードは標準ライブラリに加え、以下のライブラリを想定しています（バージョンは適宜指定してください）:
- python >= 3.10（型注釈で PEP 604 等を使用）
- duckdb
- openai
- defusedxml

その他、Slack 通知や HTTP クライアント等を使う場合は追加ライブラリが必要になることがあります。

セットアップ手順
----------------
1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   開発用にパッケージを編集可能インストールする場合（リポジトリルートに pyproject.toml がある想定）:
   - pip install -e .

3. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml がある場所）に .env または .env.local を置くと、自動で読み込まれます。
   - 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

必須の環境変数（代表）
---------------------
以下は本プロジェクト内で参照される主要な環境変数です。実行する機能に応じて設定してください。

- JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD      — kabuステーション API のパスワード（注文連携等で使用）
- SLACK_BOT_TOKEN        — Slack 通知用 Bot トークン（通知機能を使う場合）
- SLACK_CHANNEL_ID       — Slack 通知先チャンネル ID
- OPENAI_API_KEY         — OpenAI 呼び出しで使用（news_nlp / regime_detector）
- DUCKDB_PATH            — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            — SQLite 監視 DB パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV            — 環境 (development|paper_trading|live)、デフォルト development
- LOG_LEVEL              — ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)

例（.env）
----------
# .env（プロジェクトルート）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb

使い方（代表的なコード例）
------------------------

- DuckDB 接続を作る
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL を実行する
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn, target_date=None)  # target_date を指定可
  - print(result.to_dict())

- ニュースセンチメント（ai_scores）を作成する
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - n = score_news(conn, target_date=date(2026,3,20))  # OpenAI API キーは env または api_key 引数で指定

- 市場レジーム判定を実行する
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - score_regime(conn, target_date=date(2026,3,20))  # OpenAI API キーは env または api_key 引数で指定

- 監査ログスキーマを初期化する（別 DB にすること推奨）
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")
  - # これで監査テーブルが作成される

- 研究用ファクターを計算する
  - from kabusys.research.factor_research import calc_momentum
  - from datetime import date
  - records = calc_momentum(conn, target_date=date(2026,3,20))

- 研究用ユーティリティ（Z-score）
  - from kabusys.data.stats import zscore_normalize
  - normalized = zscore_normalize(records, columns=["mom_1m", "mom_3m"])

注意点 / 実装上の設計方針
----------------------
- ルックアヘッドバイアス防止
  - モジュールの多くは内部で datetime.today() / date.today() を直接参照せず、明示的な target_date 引数で処理対象日を受け取ります。バックテストや再現性が重要な処理に配慮しています。
- フェイルセーフ
  - 外部 API 呼び出しが失敗しても、極力例外を投げずフォールバック（0.0 やスキップ）して処理を続ける実装が多くあります。運用側はログと返り値で状況を把握してください。
- 冪等性
  - DuckDB への保存は ON CONFLICT DO UPDATE（可能な範囲）で実装されており、再実行に安全な設計になっています。
- テスト容易性
  - 外部呼び出し箇所（OpenAI 呼び出し、HTTP fetch など）は内部関数をモック可能な形に分離しています。

ディレクトリ構成（概要）
-----------------------
以下は主要モジュールの構成（src/kabusys 配下）です。実際のファイル数は多いですが、ここでは主要部を抜粋します。

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数読み込み・設定管理
  - ai/
    - __init__.py
    - news_nlp.py            # ニュースNLP（記事集約・LLM 呼び出し・ai_scores 書き込み）
    - regime_detector.py     # 市場レジーム判定（MA + LLM 合成）
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント（取得・保存）
    - pipeline.py           # ETL パイプライン（run_daily_etl 等）
    - quality.py            # データ品質チェック
    - news_collector.py     # RSS 収集・前処理
    - calendar_management.py# 市場カレンダー管理（営業日判定等）
    - stats.py              # 統計ユーティリティ（zscore）
    - audit.py              # 監査ログスキーマ・初期化
    - etl.py                # ETL 公開インターフェース
  - research/
    - __init__.py
    - factor_research.py    # ファクター計算（momentum/value/volatility）
    - feature_exploration.py# 将来リターン・IC・統計サマリー
  - ai/ (上記)
  - monitoring/, strategy/, execution/ (パッケージ公開対象として __all__ で列挙されていますが、必要に応じて実装を追加)

ライセンス / 貢献
-----------------
この README にはライセンス情報を含めていません。実際のリポジトリでは LICENSE ファイルを置いてください。  
バグ報告や機能追加は Issue / Pull Request を通してお願いします。

補足（トラブルシューティング）
------------------------------
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行われます。CI やテストで自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しは内部でリトライや 5xx 判定を行いますが、API キーやレート制限に注意してください（API コストも考慮）。
- DuckDB を操作する際は並列トランザクション等に注意してください。監査スキーマの初期化関数には transactional 引数があります（DuckDB はネストトランザクションをサポートしないため呼び出し側のトランザクション設計に留意）。

以上。用途に応じて README に追記・調整してください。必要であればセットアップ用の requirements.txt や example .env.example を作成することをおすすめします。