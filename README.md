KabuSys
=======

概要
----
KabuSys は日本株のデータパイプライン、ニュースNLP、市場レジーム判定、研究用ファクター計算、および監査/発注トレーサビリティを含む日本株向け自動売買基盤のライブラリ群です。  
主に DuckDB をデータ層に用い、J-Quants API からデータを取得して ETL → 品質チェック → 研究/戦略処理 → 発注監査ログへつなげることを想定しています。OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価や、ETF（1321）を使ったレジーム判定の機能も備えています。

主な機能
--------
- データ取得・ETL
  - J-Quants API 経由で株価（日次 OHLCV）、財務データ、上場銘柄情報、JPX カレンダーを差分取得・保存（ページネーション／レート制御／トークンリフレッシュ対応）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- データ品質チェック
  - 欠損、スパイク、重複、将来日付／非営業日データの検出と問題レポート
- ニュース収集
  - RSS フィードの収集・前処理（URL 正規化・SSRF 対策・サイズ制限など）→ raw_news 保存
- ニュースNLP（OpenAI）
  - ニュースを銘柄ごとに集約して LLM に投げ、銘柄別センチメント（ai_scores）を生成
  - タイムウィンドウ設計によりルックアヘッドバイアスを回避
- 市場レジーム判定
  - ETF 1321 の 200 日移動平均乖離（70%）とマクロニュースセンチメント（30%）を合成して日次で 'bull' / 'neutral' / 'bear' を判定し market_regime に保存
  - API フェイルセーフ（失敗時はセンチメント = 0）
- 研究用ユーティリティ
  - モメンタム、ボラティリティ、バリューなどのファクター計算
  - 将来リターン、IC（スピアマン）、統計サマリー、Zスコア正規化
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions などの監査テーブル定義と初期化ユーティリティ
  - order_request_id を冪等キーとして二重発注を防止

要求環境（推奨）
---------------
- Python 3.10 以上（ソースに | 型ヒント等を含むため）
- 主な依存パッケージ（一例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API・RSS・OpenAI）

セットアップ手順
---------------
1. リポジトリをチェックアウト / クローンし、プロジェクトルートに移動します。
2. 仮想環境を作成して有効化します（例: venv）。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストールします（requirements.txt が無ければ下記の主要パッケージを導入）。
   - pip install duckdb openai defusedxml
4. 環境変数を設定します。プロジェクトルートに .env（や .env.local）を置くと自動読み込みされます（自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須（機能による）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ETL）
     - OPENAI_API_KEY        : OpenAI API キー（ニュースNLP / レジーム判定。関数呼び出し時に api_key 引数でも渡せます）
     - （kabu 関連を使う場合）KABU_API_PASSWORD 等
   - 参照可能な設定（例）:
     - KABUSYS_ENV (development | paper_trading | live)
     - LOG_LEVEL (DEBUG | INFO | ...)
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視用 DB）
     - その他: PID_FILE_PATH, CPU/MEM/DISK thresholds 等
5. データディレクトリを準備（必要に応じて）。
   - mkdir -p data

使い方（簡単なコード例）
--------------------

- DuckDB 接続を作って日次 ETL を実行する
  - 例:
    - import duckdb
    - from datetime import date
    - from kabusys.data.pipeline import run_daily_etl
    - conn = duckdb.connect("data/kabusys.duckdb")
    - result = run_daily_etl(conn, target_date=date.today())
    - print(result.to_dict())

- OpenAI を使ったニュースセンチメントのスコア生成
  - 例:
    - from datetime import date
    - import duckdb
    - from kabusys.ai.news_nlp import score_news
    - conn = duckdb.connect("data/kabusys.duckdb")
    - n_written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY が環境変数に必要
    - print(f"scored {n_written} symbols")

- レジーム判定（ETF 1321 の MA200 とマクロセンチメントの合成）
  - 例:
    - from kabusys.ai.regime_detector import score_regime
    - from datetime import date
    - conn = duckdb.connect("data/kabusys.duckdb")
    - score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY が必要（引数でも渡せる）

- 監査用 DB 初期化
  - 例:
    - from kabusys.data.audit import init_audit_db
    - conn = init_audit_db("data/audit.duckdb")
    - # これで signal_events / order_requests / executions が作成されます

設定と自動 .env 読み込み
-----------------------
- kabusys.config.Settings は .env ファイルまたは環境変数から設定を読み込みます。
- 自動ロードの優先順位:
  - OS 環境変数 > .env.local > .env
- プロジェクトルートの判定は本モジュールのファイル位置を基準に .git または pyproject.toml を探索して行います。テスト等で自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

設計上の注意点・挙動
-------------------
- ルックアヘッドバイアス回避:
  - ニュースや price 関連の関数は内部で datetime.today() を参照しないように設計されています。呼び出し側が target_date を渡して使用します。
- OpenAI / J-Quants API はリトライやバックオフ、フェイルセーフ（API 失敗時は 0 やスキップするなど）を備えています。テストでは API 呼び出し部分をモックすることが推奨されます。
- DuckDB への複数行挿入で空リストを渡すと失敗するバージョン（0.10 系）を考慮した実装があります（executemany 前に空チェック）。
- ニュース収集には SSRF 対策・受信サイズ制限・XML の安全パーサを利用しています（defusedxml, リダイレクト検査など）。

主要モジュール / ディレクトリ構成
-------------------------------
（抜粋）ソースは src/kabusys 以下にあります。

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py            # ニュースセンチメント（OpenAI）
    - regime_detector.py     # 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント（取得・保存）
    - pipeline.py           # ETL パイプライン（run_daily_etl 等）
    - quality.py            # データ品質チェック
    - news_collector.py     # RSS 収集・前処理
    - calendar_management.py# 市場カレンダー管理 / 営業日判定
    - stats.py              # 統計ユーティリティ（zscore_normalize 等）
    - audit.py              # 監査テーブル定義・初期化
    - etl.py                # ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py    # モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py# 将来リターン・IC・統計サマリー
  - ai/__init__.py
  - research/__init__.py

データベース / テーブル（代表例）
------------------------------
- raw_prices / raw_financials / market_calendar / raw_news / news_symbols / ai_scores / prices_daily / market_regime
- 監査用: signal_events, order_requests, executions

テスト・デバッグのヒント
------------------------
- OpenAI 呼び出し部は news_nlp._call_openai_api や regime_detector._call_openai_api を unittest.mock.patch で差し替え可能です。
- 自動 .env 読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストで環境をコントロールしたい場合に便利です）。
- DuckDB を ":memory:" で使えば一時的なインメモリ DB での単体テストが可能です（例: duckdb.connect(":memory:")）。

ライセンス / 貢献
-----------------
本リポジトリのライセンス情報や貢献ガイドラインはプロジェクトルートに追加してください（README に明記されていないため、必要に応じて補足してください）。

最後に
-----
本 README はコードベースの主要機能と使い方の概要を示しています。具体的な運用（ジョブスケジューリング、監視、実際の発注連携など）は運用方針・証券会社 API（kabuステーション等）に合わせて追加実装が必要です。必要ならば「デプロイ手順」「監視・ログ設定」「発注フローの例」などの詳細ドキュメントも作成できます。希望があれば教えてください。