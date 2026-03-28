KabuSys
=======

日本株向けのデータプラットフォーム & 自動売買補助ライブラリです。  
ETL（J-Quants -> DuckDB）、ニュース収集・NLP（OpenAI）によるセンチメント付与、研究用ファクター計算、監査ログスキーマなどを揃え、調査から実運用（モニタリング / 発注監査）までの基盤を提供します。

主な目的
- J-Quants API から株価・財務・マーケットカレンダーを差分取得して DuckDB に保存
- RSS ニュースを収集して raw_news に保存、OpenAI を使った銘柄別センチメント付与
- 市場レジーム判定（ETF の MA とマクロニュースを統合）
- 研究（ファクター計算・将来リターン・IC 等）
- 監査ログ（signal → order_request → executions）のスキーマ初期化・管理
- データ品質チェック（欠損・スパイク・重複・日付不整合）

機能一覧
- data.jquants_client: J-Quants API クライアント（取得・保存・認証・レート制御・リトライ）
- data.pipeline / etl: 日次 ETL パイプライン（カレンダー、株価、財務、品質チェック）
- data.news_collector: RSS 収集（SSRF 対策、gzip 対応、トラッキング除去、前処理）
- data.quality: 品質チェック（欠損・重複・スパイク・日付不整合）
- data.calendar_management: 市場カレンダー管理（営業日判定、前後営業日探索、夜間バッチ）
- data.audit: 監査ログ用スキーマ初期化（冪等、UTCタイムスタンプ）
- data.stats: 汎用統計ユーティリティ（Zスコア正規化 等）
- ai.news_nlp: ニュースをグルーピングして OpenAI に送り銘柄別スコア化（JSON Mode）
- ai.regime_detector: ETF とマクロニュースから市場レジーム（日次）判定
- research.*: ファクター計算・特徴量探索（Momentum、Value、Volatility、forward returns、IC、summary）

前提 / 依存
- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ（urllib, json, datetime 等）

セットアップ手順（例）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (macOS/Linux) or .venv\Scripts\activate (Windows)

2. パッケージのインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトを editable に使う場合）pip install -e .

   あるいは requirements.txt を作り
   - pip install -r requirements.txt

3. 環境変数設定
   - プロジェクトルートに .env（または .env.local）を作成すると自動読み込みします（config.py の自動ロード）。
   - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

必須の環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client.get_id_token で使用）
- KABU_API_PASSWORD: kabuステーション API のパスワード（将来的な発注など）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで使用）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live) （デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）

使い方（代表的な例）

- 基本的な DuckDB 接続と ETL 実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースに対する銘柄別 AI スコア付与
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-xxxx")
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定（ETF 1321 の MA とマクロニュース統合）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-xxxx")
  ```

- 監査ログ DB の初期化
  ```python
  from kabusys.data.audit import init_audit_db
  from pathlib import Path

  audit_conn = init_audit_db(Path("data/audit.duckdb"))
  ```

- ファクター計算（研究用）
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, target_date=date(2026, 3, 20))
  val = calc_value(conn, target_date=date(2026, 3, 20))
  vol = calc_volatility(conn, target_date=date(2026, 3, 20))
  ```

設定周りの注意
- kabusys.config はプロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を自動読み込みします。テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- settings オブジェクト経由で設定を取得できます（例: from kabusys.config import settings; settings.duckdb_path）。

設計上の重要ポイント（簡潔）
- ルックアヘッドバイアス対策: 多くの関数が target_date を引数に取り、内部で date.today() を参照しないよう設計されています。
- 冪等性: ETL の保存処理は ON CONFLICT (DuckDB) を用いて上書きし、再実行での二重保存を防止します。
- フェイルセーフ: 外部 API（OpenAI、J-Quants）失敗時はリトライやフォールバック（ゼロスコア等）を行い、処理継続を優先する箇所が多くあります。
- セキュリティ: news_collector では SSRF 対策、XML の defusedxml、受信サイズ上限、URL 正規化（トラッキング除去）を行っています。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                    -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                -- ニュース NLP（銘柄別スコア化）
    - regime_detector.py         -- 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py          -- J-Quants API クライアント（取得/保存）
    - pipeline.py                -- ETL パイプライン（run_daily_etl 等）
    - etl.py                     -- ETLResult 型の再エクスポート
    - news_collector.py          -- RSS 収集器
    - calendar_management.py     -- 市場カレンダー管理
    - quality.py                 -- データ品質チェック
    - stats.py                   -- 統計ユーティリティ（zscore_normalize）
    - audit.py                   -- 監査ログスキーマ初期化
    - (その他 jquants_client 用の保存関数等)
  - research/
    - __init__.py
    - factor_research.py         -- モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py     -- forward returns / IC / summary / rank

運用上のヒント
- OpenAI 呼び出しは API 利用料が発生します。テスト時は API 呼び出し関数をモックしてください（各 ai モジュールでは _call_openai_api を簡単にパッチ可能な設計です）。
- DuckDB ファイルはデフォルト data/kabusys.duckdb。バックアップやファイル配置には注意してください。監査ログは別 DB に分けることも可能です。
- run_daily_etl は品質チェックを実行可能（デフォルト true）。品質問題は QualityIssue として収集され、ETLResult に格納されます。

ライセンス / 貢献
- 本リポジトリのライセンス・貢献フローは含まれていません。プロジェクトに合わせて LICENSE / CONTRIBUTING を追加してください。

問い合わせ / サポート
- 実装詳細や API の変更点に関する質問は、コード内の docstring とログメッセージが詳しい情報源です。まずはローカルで DuckDB を作成し ETL を少量実行して挙動を確認してください。

以上。必要があれば、README にチュートリアル（例: 初期データロード手順、cron によるスケジューリング例、監視用 SQL クエリ例）を追加します。どのトピックを補足しますか？