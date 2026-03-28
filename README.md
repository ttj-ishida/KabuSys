KabuSys — 日本株自動売買 / データ基盤ライブラリ
=================

概要
----
KabuSys は日本株向けのデータ収集・品質管理・ファクター計算・AI（ニュース）スコアリング・市場レジーム判定・監査ログなどを備えた内部ライブラリ群です。ETL パイプラインや J-Quants / RSS / OpenAI 連携、DuckDB を使ったデータ保存・検査・分析処理を提供し、取引戦略や実際の発注ロジック（別モジュール）と組み合わせて利用できます。

主な設計方針（抜粋）
- ルックアヘッドバイアスを避けるため、内部で date.today()/datetime.today() に依存しない実装を優先。
- API 呼び出しはリトライ・バックオフ・レート制御などのフェイルセーフを備える。
- DuckDB へは冪等（ON CONFLICT / upsert）で保存する。
- ニュース収集は SSRF 対策やサイズ上限、XML の安全パースを実施。

機能一覧
--------
- 環境設定管理
  - .env ファイルの自動ロード（プロジェクトルート検出）
  - 必須環境変数チェック（settings オブジェクト）

- データ ETL（jquants_client + pipeline）
  - J-Quants API から株価日足 / 財務データ / JPX カレンダー取得（ページネーション対応）
  - 差分取得・バックフィル・品質チェックを含む日次 ETL（run_daily_etl）
  - DuckDB への冪等保存関数（save_* 系）

- データ品質チェック
  - 欠損、スパイク（前日比）、重複、日付整合性チェック（run_all_checks）

- マーケットカレンダー管理
  - 営業日判定・前後営業日取得・範囲内営業日列挙・カレンダー更新ジョブ

- ニュース収集・NLP（OpenAI 連携）
  - RSS 収集（SSRF 対策・サイズ制限・正規化）と raw_news への保存支援
  - 銘柄別ニュース統合 → OpenAI でセンチメント評価（score_news）
  - マクロニュース + ETF MA200 乖離を合成した市場レジーム判定（score_regime）

- リサーチ / ファクター
  - Momentum / Volatility / Value 等のファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー、Z-score 正規化

- 監査ログ（トレーサビリティ）
  - signal_events, order_requests, executions などの監査テーブル初期化・DB生成（init_audit_schema / init_audit_db）

セットアップ手順
----------------

前提
- Python 3.10+（コードは型注釈や newer union 型を使用）
- DuckDB を利用するための環境
- J-Quants / OpenAI の API キーなど外部資格情報

1) 仮想環境を作成・有効化（例）
- Unix/macOS:
  - python -m venv .venv
  - source .venv/bin/activate
- Windows (PowerShell):
  - python -m venv .venv
  - .\.venv\Scripts\Activate.ps1

2) パッケージのインストール
- 開発時はプロジェクト内で editable install を推奨:
  - pip install -e .
- 必要な外部パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外が必要な場合は pyproject.toml / requirements を参照）

3) 環境変数 / .env の設定
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env を置くと自動で読み込まれます。
- 自動ロードを無効にする場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 主要な環境変数（例）
  - JQUANTS_REFRESH_TOKEN=あなたの_jquants_リフレッシュトークン
  - OPENAI_API_KEY=あなたの_OpenAI_APIキー
  - KABU_API_PASSWORD=kabuステーション API パスワード
  - SLACK_BOT_TOKEN=Slack ボットトークン（通知用）
  - SLACK_CHANNEL_ID=Slack 送信先チャンネルID
  - DUCKDB_PATH=data/kabusys.duckdb（デフォルト）
  - SQLITE_PATH=data/monitoring.db（デフォルト）
- .env のパースはシェル風記法（export を含む行、引用符、# コメント）に対応します。

使い方（代表的な例）
-------------------

基本的な DuckDB 接続
- import duckdb
- conn = duckdb.connect(str(settings.duckdb_path))

日次 ETL を実行する
- from kabusys.data.pipeline import run_daily_etl
- from kabusys.config import settings
- from datetime import date
- conn = duckdb.connect(str(settings.duckdb_path))
- result = run_daily_etl(conn, target_date=date(2026, 3, 20))
- print(result.to_dict())

ニュース（銘柄）センチメントを算出する
- from kabusys.ai.news_nlp import score_news
- score_count = score_news(conn, target_date=date(2026, 3, 20), api_key="…")  # api_key 省略時は OPENAI_API_KEY 環境変数

市場レジーム判定（MA200 + マクロセンチメント）
- from kabusys.ai.regime_detector import score_regime
- score_regime(conn, target_date=date(2026,3,20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用

ファクター計算（研究用途）
- from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
- mom = calc_momentum(conn, target_date=date(2026,3,20))
- vol = calc_volatility(conn, target_date=date(2026,3,20))
- val = calc_value(conn, target_date=date(2026,3,20))

品質チェック
- from kabusys.data.quality import run_all_checks
- issues = run_all_checks(conn, target_date=date(2026,3,20))
- for i in issues: print(i)

監査ログテーブル初期化（注文監査用 DB）
- from kabusys.data.audit import init_audit_db
- audit_conn = init_audit_db("data/audit.duckdb")

ニュース RSS 収集（低レベル）
- from kabusys.data.news_collector import fetch_rss
- articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")

注意点 / トラブルシューティング
--------------------------------
- OpenAI 呼び出し
  - OPENAI_API_KEY が設定されているか確認してください。関数呼び出し時に api_key を渡すこともできます。
  - API エラー時はモジュール内でリトライ／フォールバック（例: macro_sentiment=0.0）する設計です。

- J-Quants
  - JQUANTS_REFRESH_TOKEN を .env に設定してください。get_id_token() が自動的にトークンを取得します。
  - API レート制限（120 req/min）に対応するためモジュール内でスロットリングを行います。

- .env 自動ロード
  - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を読み込みます。
  - テストや特殊な実行環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動ロードを無効化できます。

- DuckDB executemany の注意
  - DuckDB のバージョンによっては executemany に空リストを渡すとエラーになるため、ライブラリは事前に空チェックを行っています。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                      — 環境設定と .env 読み込み
- ai/
  - __init__.py
  - news_nlp.py                   — ニュースの OpenAI スコアリング（score_news）
  - regime_detector.py            — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - calendar_management.py        — 市場カレンダー管理（is_trading_day など）
  - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
  - jquants_client.py             — J-Quants API クライアント（fetch / save 系）
  - news_collector.py             — RSS 取得・前処理
  - quality.py                    — データ品質チェック
  - stats.py                      — 汎用統計ユーティリティ（zscore_normalize）
  - audit.py                      — 監査ログテーブル初期化
  - etl.py                        — ETLResult 再エクスポート
- research/
  - __init__.py
  - factor_research.py            — Momentum / Volatility / Value 計算
  - feature_exploration.py        — 将来リターン / IC / 統計サマリー
- research/*（ユーティリティの再エクスポート）
- その他（strategy / execution / monitoring）モジュールは __all__ に準備あり（実装は別途）

開発・貢献
-----------
- テストや CI を追加・実行する際は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して環境干渉を避けてください。
- OpenAI 呼び出し箇所は _call_openai_api のパッチ差し替えでモック可能です（ユニットテスト向け）。

ライセンス / その他
-------------------
- 本リポジトリに含まれるライセンス情報（LICENSE）があればそちらを参照してください。
- 外部サービス（J-Quants、OpenAI、Slack など）の利用に際しては各サービスの利用規約に従ってください。

補足（よくあるコマンド）
- 仮想環境作成: python -m venv .venv
- 開発インストール: pip install -e .
- DuckDB コンソール起動: python -c "import duckdb; print(duckdb.connect('data/kabusys.duckdb').tables())"

以上。README の改善点や追加してほしいサンプル（CLI 実行例・CI 設定・詳細なスキーマなど）があれば教えてください。