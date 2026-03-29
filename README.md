KabuSys — 日本株自動売買プラットフォーム
=====================================

概要
----
KabuSys は日本株向けのデータパイプライン、リサーチ、AIベースのニュースNLP、監査ログ／ETL／マーケットカレンダー管理などを含む自動売買基盤のライブラリ群です。  
主に DuckDB をデータレイヤに用い、J-Quants API からのデータ取得、OpenAI（gpt-4o-mini）を使ったニュースセンチメント評価、ETF を用いた市場レジーム判定、品質チェック、監査テーブル（注文→約定のトレース）等を提供します。

特徴（主な機能）
----------------
- データ収集 / ETL
  - J-Quants API からの株価（日足）、財務データ、マーケットカレンダー取得（差分更新・ページネーション対応・リトライ・レート制御）
  - ETL 集約エントリ run_daily_etl（カレンダー → 株価 → 財務 → 品質チェック）
- データ品質管理
  - 欠損チェック、スパイク（急騰・急落）検出、重複検出、日付整合性チェック
- ニュース処理 / ニュース収集
  - RSS フィードの収集・前処理（SSRF対策・トラッキング除去・サイズ制限）
  - raw_news / news_symbols の銘柄紐付け想定
- AI（OpenAI）連携
  - ニュースごとの銘柄センチメント算出（news_nlp.score_news）
  - ETF（1321）とマクロニュースを組み合わせた市場レジーム判定（regime_detector.score_regime）
  - LLM 呼び出しはリトライ・フォールバック実装あり
- 研究用ユーティリティ
  - モメンタム／バリュー／ボラティリティ等のファクター計算（research）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化
- 監査（audit）
  - signal_events / order_requests / executions 等の監査テーブルの初期化・インデックス作成（冪等）
  - 監査 DB 初期化ユーティリティ（init_audit_db）

セットアップ手順
----------------

前提
- Python 3.10 以上（PEP 604 の | 型注釈を使用）
- ネットワークアクセス（J-Quants API / OpenAI / RSS フィード）

インストール（開発用）
1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate

2. 必要パッケージをインストール
   - 最低限の推奨パッケージ:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

3. ローカルパッケージとしてインストール（ソースがパッケージ化されている前提）
   - pip install -e .

環境変数（.env）
- KabuSys はプロジェクトルートの .env / .env.local を自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- 主な必須環境変数:
  - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL 用）
  - KABU_API_PASSWORD — kabuステーション API パスワード（実行・発注関連）
  - SLACK_BOT_TOKEN — Slack 通知用（必要に応じて）
  - SLACK_CHANNEL_ID — Slack チャンネル ID
- 任意 / デフォルト:
  - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
  - KABU_API_BASE_URL — kabuAPI のベース URL（デフォルト http://localhost:18080/kabusapi）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH — SQLite（監視など）パス（デフォルト data/monitoring.db）
- 注意: Settings クラスは未設定時に ValueError を投げるプロパティがあります（必須 env は _require により検査）。

使い方（代表的な例）
-------------------

基本的な DuckDB 接続
- Python から直接呼び出す例:
  - import duckdb
  - from kabusys.config import settings
  - conn = duckdb.connect(str(settings.duckdb_path))

ETL（日次パイプライン）
- run_daily_etl を使って日次 ETL を実行（J-Quants トークンは settings で管理）:
  - from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    import duckdb
    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

ニュースセンチメント（AI）
- OpenAI API キーは環境変数 OPENAI_API_KEY に設定するか、関数引数に渡す:
  - from kabusys.ai.news_nlp import score_news
    from datetime import date
    n = score_news(conn, target_date=date(2026,3,20), api_key=None)  # 環境変数を使用
- score_news は ai_scores テーブルに日付別のスコアを書き込み、書き込んだ銘柄数を返します。

市場レジーム判定
- ETF 1321 の MA とマクロニュースセンチメントを合成して market_regime テーブルに書き込み:
  - from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,3,20), api_key=None)

監査テーブル初期化
- 監査用 DB を新規作成・初期化:
  - from kabusys.data.audit import init_audit_db
    audit_conn = init_audit_db("data/audit.duckdb")
    # audit_conn を使って監査ログを挿入・参照できます

J-Quants トークン取得（低レベル）
- from kabusys.data.jquants_client import get_id_token
  - token = get_id_token()  # settings.jquants_refresh_token を使う

ニュース収集（RSS）
- fetch_rss は単体で RSS を取得して前処理済みのニュース記事のリストを返します:
  - from kabusys.data.news_collector import fetch_rss
    articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")

注意点 / ベストプラクティス
- ルックアヘッドバイアス回避:
  - 多くの関数は date.today() を使わず引数で target_date を渡す設計になっています。バックテストや再現性のため、必ず明示的な日付を渡すことを推奨します。
- OpenAI API:
  - 呼び出し時の失敗はフォールバック（0.0）やログ出力で安全に処理する実装です。ただし API 費用やレート制御はユーザ側で管理してください。
- .env の自動読み込み:
  - テスト時に自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（抜粋）
----------------------

src/kabusys/
- __init__.py
- config.py                 — 設定・.env の自動読み込みロジック（Settings）
- ai/
  - __init__.py
  - news_nlp.py             — ニュースセンチメントスコア（score_news）
  - regime_detector.py      — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py       — J-Quants API クライアント（fetch / save / get_id_token）
  - pipeline.py             — ETL パイプライン（run_daily_etl 等）
  - etl.py                  — ETL インターフェース（ETLResult エクスポート）
  - stats.py                — Zスコア等統計ユーティリティ
  - quality.py              — 品質チェック（欠損・スパイク・重複・日付整合性）
  - news_collector.py       — RSS 収集・前処理（SSRF 対策・トラッキング除去）
  - calendar_management.py  — JPX カレンダー管理・営業日判定・更新ジョブ
  - audit.py                — 監査テーブル定義 / 初期化（init_audit_schema / init_audit_db）
- research/
  - __init__.py
  - factor_research.py      — モメンタム/バリュー/ボラティリティ計算
  - feature_exploration.py  — 将来リターン / IC / 統計サマリー / rank 等

開発・テスト
-------------
- 自動環境変数ロードは .env / .env.local をプロジェクトルートから探して行います（.git や pyproject.toml がある親ディレクトリをルートと判定）。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットして .env の読み込みを抑止できます。
- LLM 呼び出し部分は _call_openai_api をモックしてユニットテスト可能となるよう設計されています（unittest.mock.patch を利用）。

ライセンス / 貢献
-----------------
- 本 README ではライセンスファイルは明示していません。実際のリポジトリに LICENSE ファイルがある場合はそちらに従ってください。  
- バグ報告・プルリクエスト歓迎です。設計ノートや DataPlatform.md / StrategyModel.md 等の参照ドキュメントに従って実装・拡張してください。

付録：よく使うコードスニペット
----------------------------
- DuckDB 接続と ETL 実行（簡易）:
  - import duckdb
    from kabusys.config import settings
    from kabusys.data.pipeline import run_daily_etl
    conn = duckdb.connect(str(settings.duckdb_path))
    res = run_daily_etl(conn)
    print(res.to_dict())

- ニューススコア取得（OpenAI キーは環境変数 OPENAI_API_KEY に設定）:
  - from kabusys.ai.news_nlp import score_news
    from datetime import date
    n = score_news(conn, date(2026,3,20))

- レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
    score_regime(conn, date(2026,3,20))

必要であれば、この README をベースにインストール要件ファイル（requirements.txt）、例示的な .env.example、実行スクリプト（CLI）用の章なども追加できます。追加希望があれば教えてください。