KabuSys
=======

概要
----
KabuSys は日本株向けのデータプラットフォーム兼リサーチ／自動売買支援ライブラリです。  
J-Quants からのデータ取得（株価・財務・市場カレンダー）、RSS ニュース収集、データ品質チェック、特徴量計算、LLM（OpenAI）を用いたニュース・マクロ分析、監査ログ（発注トレース）などの機能を提供します。  
パッケージ内部はバックテストやランド運用の両方で安全に使えるように、ルックアヘッドバイアス防止や冪等性、堅牢なエラーハンドリングを意識して設計されています。

主な機能
--------
- ETL（jquants API からの差分取得・保存）
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダーの差分取得・保存（冪等）
  - run_daily_etl を使った日次パイプライン
- ニュース収集
  - RSS フィード取得、前処理、raw_news / news_symbols テーブルへの保存
  - SSRF や Gzip bomb 対策、トラッキングパラメータ除去などを実装
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合チェック（QualityIssue 型で収集）
- カレンダー管理
  - 営業日判定・前後営業日取得・一括取得、JPX カレンダーの夜間更新ジョブ
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions を含む監査テーブルの初期化・管理
- 研究（research）
  - Momentum / Volatility / Value 等のファクター計算
  - 特徴量探索（将来リターン計算、IC 計算、統計サマリ、ランク付け）
  - z-score 正規化ユーティリティ
- AI（OpenAI）連携
  - ニュースセンチメント（ai.news_nlp.score_news）
  - 市場レジーム判定（ai.regime_detector.score_regime）
  - 両モジュールは gpt-4o-mini（JSON mode）を想定し、リトライやフェイルセーフを備える
- J-Quants クライアント
  - レート制限管理、トークン自動リフレッシュ、ページネーション対応
  - DuckDB への安全な保存（ON CONFLICT / executemany 対策）
- DB ユーティリティ
  - DuckDB 接続を介したスキーマ初期化、監査 DB 初期化ユーティリティ等

セットアップ
----------
前提:
- Python 3.10 以上（typing の新しい構文を使用）
- duckdb, openai, defusedxml などの依存パッケージ

推奨手順（開発環境）
1. リポジトリをクローン
   - git clone <repository_url>
2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）
4. パッケージを編集可能インストール（任意）
   - pip install -e .

環境変数
- 自動的にプロジェクトルートの .env → .env.local を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。  
- 必須の環境変数（コード参照）:
  - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID : Slack 通知に使用
  - KABU_API_PASSWORD : kabuステーション API のパスワード
- その他（デフォルト値あり）:
  - KABUSYS_ENV : development / paper_trading / live（default=development）
  - LOG_LEVEL : DEBUG/INFO/...
  - DUCKDB_PATH : data/kabusys.duckdb（デフォルト）
  - SQLITE_PATH : data/monitoring.db（デフォルト）
- .env の自動パースは多数の形式をサポート（export 構文、クォート、インラインコメント等）。未設定の必須変数を参照すると ValueError が発生します。

簡単な .env.example（例）
- .env.example を作成してプロジェクトルートに置くことを推奨します。例:
  JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
  OPENAI_API_KEY=your_openai_api_key
  KABU_API_PASSWORD=your_kabu_password
  SLACK_BOT_TOKEN=xoxb-...
  SLACK_CHANNEL_ID=C12345678
  KABUSYS_ENV=development
  DUCKDB_PATH=data/kabusys.duckdb

基本的な使い方
-------------
（以下は Python REPL やスクリプトでの利用例）

1) DuckDB 接続準備
- import duckdb
- from kabusys.config import settings
- conn = duckdb.connect(str(settings.duckdb_path))

2) ETL（日次パイプライン）実行
- from datetime import date
- from kabusys.data.pipeline import run_daily_etl
- res = run_daily_etl(conn, target_date=date(2026, 3, 20))
- print(res.to_dict())

3) ニューススコア（AI）実行
- from kabusys.ai.news_nlp import score_news
- count = score_news(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_API_KEY")
- print(f"scored {count} codes")

4) 市場レジーム判定（AI）実行
- from kabusys.ai.regime_detector import score_regime
- score_regime(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_API_KEY")

5) 研究系ユーティリティ
- from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
- mom = calc_momentum(conn, date(2026,3,20))
- vol = calc_volatility(conn, date(2026,3,20))
- val = calc_value(conn, date(2026,3,20))
- from kabusys.data.stats import zscore_normalize
- normed = zscore_normalize(mom, ["mom_1m", "mom_3m"])

6) カレンダー・営業日関連
- from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days
- is_trading_day(conn, date(2026,3,20))
- next_trading_day(conn, date(2026,3,20))
- get_trading_days(conn, date(2026,3,1), date(2026,3,31))

7) 監査スキーマ初期化（監査用 DB）
- from kabusys.data.audit import init_audit_db
- audit_conn = init_audit_db("data/audit.duckdb")

注意点・実装上のポイント
-----------------------
- LLM 呼び出し: OpenAI を利用する処理（news_nlp, regime_detector）はモデル gpt-4o-mini を想定。JSON Mode レスポンスをパースして使用します。API エラー時はリトライ／フォールバックを行います（フェイルセーフでスコア 0.0 等にフォールバック）。
- Look-ahead 防止: 多くの関数は datetime.today()/date.today() を内部で参照せず、target_date を明示して使用する設計です。
- 冪等性: DB への保存は ON CONFLICT DO UPDATE などで冪等に行われます。
- ニュース収集は SSRF 対策、受信サイズ上限、XML 脆弱性対策（defusedxml）を施しています。
- J-Quants クライアントはレートリミッタを実装（120 req/min）・トークン自動更新・ページネーション対応です。

ディレクトリ構成（主要ファイル）
------------------------------
- src/kabusys/
  - __init__.py
  - config.py                  (環境変数・設定管理)
  - ai/
    - __init__.py
    - news_nlp.py              (ニュースセンチメントスコアリング)
    - regime_detector.py       (マクロ + MA を用いた市場レジーム判定)
  - data/
    - __init__.py
    - calendar_management.py   (市場カレンダー管理・営業日判定)
    - etl.py                   (ETL インターフェース再エクスポート)
    - pipeline.py              (ETL パイプライン実装)
    - stats.py                 (共通統計ユーティリティ)
    - quality.py               (データ品質チェック)
    - audit.py                 (監査ログスキーマ・初期化)
    - jquants_client.py        (J-Quants API クライアント & 保存ユーティリティ)
    - news_collector.py        (RSS ニュース収集)
  - research/
    - __init__.py
    - factor_research.py       (モメンタム/ボラ/バリュー計算)
    - feature_exploration.py   (将来リターン・IC・統計)
  - research/... (その他研究補助関数)

開発・貢献
----------
- コードのスタイルやユニットテスト追加、CI/CD の整備を歓迎します。
- LLM 呼び出しのモックやネットワーク周りの抽象化はテストのしやすさを考慮して実装されています（各モジュールに _call_openai_api 等を差し替え可能な箇所あり）。

サポートされる Python バージョン
-----------------------------
- Python 3.10 以上を推奨（| 型や標準ライブラリの挙動に依存）。

最後に
-----
本 README はコードベースの概要と使い始めに必要な情報をまとめたものです。より詳しい設計方針（DataPlatform.md / StrategyModel.md に相当する文書）がある場合は併せて参照してください。README に記載の操作で不明点があれば、具体的な利用ケース（例: ETL が失敗するログ、OpenAI レスポンス例）を教えてください。