KabuSys — 日本株自動売買基盤（README）
=================================

概要
----
KabuSys は日本株のデータパイプライン（ETL）、ニュースNLP（LLMベースのセンチメント）、市場レジーム判定、リサーチ／ファクター計算、監査ログ（発注→約定トレーサビリティ）を統合した内部ライブラリです。  
主に DuckDB をデータ格納に使い、J-Quants / OpenAI / RSS など外部リソースと連携して運用・研究用途に用いることを想定しています。

主な特徴（機能一覧）
------------------
- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート基準）、設定値は kabusys.config.settings 経由で取得可能
- データ取得・ETL
  - J-Quants API から株価（日次OHLCV）・財務データ・JPX カレンダーを差分取得して DuckDB に保存（冪等）
  - run_daily_etl 等の ETL エントリポイントを提供
  - 品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集・NLP（LLM）
  - RSS 取得・整形（SSRF 対策 / トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini 想定）を用いた銘柄毎ニュースセンチメント score_news
  - マクロニュースと ETF（1321）の MA200乖離を合成した市場レジーム判定 score_regime
- リサーチ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリー、Zスコア正規化ユーティリティ
- 監査ログ（監査テーブル）
  - signal_events / order_requests / executions 等の監査スキーマを初期化する関数（init_audit_schema / init_audit_db）
  - 発注の冪等性キーとトレーサビリティ設計済み
- J-Quants クライアント
  - レートリミット、リトライ、401時の自動トークンリフレッシュ、ページネーション対応
- 安全設計
  - ルックアヘッドバイアス回避（内部で datetime.today() を安易に参照しない設計）
  - SSRF / XML 攻撃対策（defusedxml、ホスト検査、リダイレクト検証）
  - API エラー時のフォールバック（フェイルセーフ）や指数バックオフ

サポートする環境
----------------
- Python 3.10+（型アノテーションの | 演算子を使用しているため）
- 必須外部ライブラリ（最低限）:
  - duckdb
  - openai
  - defusedxml

セットアップ手順
---------------
1. Python 仮想環境の作成（推奨）
   - Unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell):
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1

2. 必要パッケージをインストール
   - 例（最低限）:
     - pip install duckdb openai defusedxml
   - 開発用に requirements.txt を用意する場合は上のパッケージを記載してください。
   - 開発中に pip install -e . で editable install する場合は、パッケージ配布設定があれば利用できます。

3. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml の位置）に .env または .env.local を置くと自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主要な環境変数例（.env）
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - OPENAI_API_KEY=your_openai_api_key
     - KABU_API_PASSWORD=your_kabu_api_password
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development  # development / paper_trading / live
     - LOG_LEVEL=INFO
   - 注意: settings.* プロパティは未設定時に例外を投げる項目があります（必須のキーには _require を使用）。

使い方（簡単なコード例）
----------------------

- 基本的な DuckDB 接続と ETL 実行
  - python コンソールやスクリプト内で:
    - from datetime import date
      import duckdb
      from kabusys.config import settings
      from kabusys.data.pipeline import run_daily_etl
    - conn = duckdb.connect(str(settings.duckdb_path))
    - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    - print(result.to_dict())

- ニュースのスコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY でも可、引数で指定も可能）
  - from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
  - conn = duckdb.connect(str(settings.duckdb_path))
  - n = score_news(conn, target_date=date(2026, 3, 20))
  - print(f"scored {n} codes")

- 市場レジーム判定
  - from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime
  - conn = duckdb.connect(str(settings.duckdb_path))
  - score_regime(conn, target_date=date(2026, 3, 20))

- 監査用 DuckDB の初期化（監査テーブルを作る）
  - from kabusys.data.audit import init_audit_db
  - conn = init_audit_db("data/audit.duckdb")  # :memory: でインメモリも可

- ファクター計算・リサーチユーティリティ
  - from kabusys.research import calc_momentum, calc_value, calc_volatility, calc_forward_returns
  - conn = duckdb.connect(str(settings.duckdb_path))
  - mom = calc_momentum(conn, date(2026, 3, 20))
  - fwd = calc_forward_returns(conn, date(2026, 3, 20))

設定（settings）について
-----------------------
- 環境変数の自動ロード順序:
  - OS 環境変数 > .env.local > .env
- 自動ロードを無効化する場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 利用可能な主な settings プロパティ:
  - jquants_refresh_token, kabu_api_password, kabu_api_base_url
  - line_channel_access_token, line_user_id
  - duckdb_path, sqlite_path
  - pid_file_path, kill_flag_path, kill_flag_clear_on_start
  - cpu_threshold_pct, memory_threshold_pct, disk_threshold_pct
  - env (development / paper_trading / live), log_level
  - is_live / is_paper / is_dev の bool ヘルパー

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要モジュール・ファイルです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                 # 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py             # ニュースセンチメント（score_news）
    - regime_detector.py      # マーケットレジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py       # J-Quants API クライアント（fetch / save）
    - pipeline.py             # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py  # マーケットカレンダー管理、営業日判定
    - news_collector.py       # RSS 取得・前処理・保存
    - quality.py              # データ品質チェック
    - stats.py                # 統計ユーティリティ（zscore_normalize）
    - audit.py                # 監査スキーマ定義・初期化
    - etl.py                  # ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py      # momentum/value/volatility 等
    - feature_exploration.py  # 将来リターン / IC / summary
  - monitoring/                # （未表示ファイル群）監視・実行監視など想定
  - strategy/                  # （未表示ファイル群）戦略ロジック想定
  - execution/                 # （未表示ファイル群）ブローカ連携想定

運用上の注意点 / ベストプラクティス
---------------------------------
- OpenAI / J-Quants の API キーは秘密情報です。.env を git に入れないでください。
- ETL 実行はバックグラウンド・cron 等で定期化し、run_daily_etl で品質チェックの結果を確認してください。
- テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し、テスト専用の環境変数を注入してください。
- LLM 呼び出しは失敗時フォールバック（0.0）を持ちますが、コストとレート制限に注意してください（news_nlp はバッチ処理、regime_detector は記事が無ければ LLM 呼ばない）。
- DuckDB ファイルは単一ファイルで永続化されます。運用時はバックアップやファイル配置に注意してください。

よくある利用シナリオ（例）
------------------------
- データ基盤の初期セットアップ:
  - duckdb.connect(settings.duckdb_path) で接続し、必要なスキーマを作成（本プロジェクトのスキーマ定義部を実行）
  - init_audit_db で監査DBを用意
- 毎朝の自動処理:
  - run_daily_etl を実行してデータ取り込み → 品質チェック → ニューススコア → レジーム判定
- 研究用途:
  - research モジュールでファクターを計算 → zscore_normalize → IC 分析

貢献 / 開発
-----------
- 開発用依存を整え、ローカルで DuckDB を使って単体関数を実行・検証してください。
- 外部 API 呼び出しはモック可能な設計（jquants_client._request、news_nlp/_call_openai_api 等を patch）になっています。ユニットテスト作成時はモックを利用してください。

ライセンス / その他
-------------------
- 本リポジトリにライセンスファイルがある場合はそれに従ってください。
- 実運用（特に "live" モード）の場合、発注・資金管理・リスク制御は十分に検証してください。本コードはあくまでシステム基盤であり、投資アドバイスではありません。

補足
----
- README に書かれていない内部 API や細かな引数仕様は各モジュールの docstring（ソース内のコメント）を参照してください。関数レベルで処理フローやエラー処理方針が詳述されています。

必要であれば、README に含めるサンプル .env.example、requirements.txt の雛形、あるいはよく使う CLI スクリプト例（run_etl.py など）も作成します。どれを追加したいか教えてください。