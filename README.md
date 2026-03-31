KabuSys — 日本株データプラットフォーム / 自動売買基盤
==================================================

概要
----
KabuSys は日本株向けのデータ収集（ETL）、品質チェック、特徴量計算、ニュースNLP（LLM）によるセンチメントスコアリング、及び市場レジーム判定・監査ログ等を備えた自動売買・リサーチ基盤です。DuckDB を主なローカルデータストアとして利用し、J-Quants API・RSS ニュース・OpenAI（gpt-4o-mini）を外部データソースとして組み合わせる設計になっています。

主な機能
--------
- ETL（デイリーの差分取得）
  - 株価日足（OHLCV）、財務データ、JPXマーケットカレンダーの差分取得と DuckDB への冪等保存
  - データ品質チェック（欠損、重複、スパイク、日付不整合）
- ニュース収集 / 前処理
  - RSS フィード取得、URL 正規化、記事保存（raw_news / news_symbols）
  - SSRF／gzip／XML 攻撃対策を考慮した頑健な実装
- ニュースNLP（AI）
  - 銘柄単位のニュース統合センチメント（score_news）
  - マクロニュース + ETF 移動平均乖離を用いた市場レジーム判定（score_regime）
  - OpenAI の JSON mode を使った丸め込み検証・リトライ制御
- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、ファクター統計サマリー
- 監査ログ（Audit）
  - signal_events / order_requests / executions を含む監査テーブルの初期化・管理（冪等）
- J-Quants クライアント
  - レート制御、トークン自動リフレッシュ、ページネーション対応、DuckDB への保存ユーティリティ

セットアップ手順
----------------

前提
- Python 3.10+（typing の構文と挙動に依存）
- ネットワークアクセス（J-Quants API、OpenAI、RSS）

1. リポジトリをクローンして開発環境を作る
   - 推奨: 仮想環境を作成してからインストール
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install -e .   または requirements.txt があれば pip install -r requirements.txt
   - 主な依存例:
     - duckdb
     - openai
     - defusedxml
   （プロジェクトの packaging / pyproject に依存リストがある想定）

3. 環境変数 / .env
   - プロジェクトルート（.git または pyproject.toml の位置）に .env を置くと自動読み込みされます。
   - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時など）。
   - 必須（代表例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 用。関数引数でも渡せます）
     - KABU_API_PASSWORD: kabuステーション API のパスワード（発注実装がある場合）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: 通知用（プロジェクトで利用する場合）
   - 任意:
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（モニタリング DB 等、デフォルト data/monitoring.db）
     - KABUSYS_ENV（development|paper_trading|live、デフォルト development）
     - LOG_LEVEL（DEBUG|INFO|...、デフォルト INFO）

   例 .env（簡易）
   - JQUANTS_REFRESH_TOKEN=xxxx
   - OPENAI_API_KEY=sk-xxxx
   - KABU_API_PASSWORD=your_password
   - SLACK_BOT_TOKEN=xoxb-...
   - SLACK_CHANNEL_ID=C0123456
   - DUCKDB_PATH=data/kabusys.duckdb
   - KABUSYS_ENV=development

初期化・データベース準備
- 監査ログ専用 DB を作成する例:
  - Python スニペット:
    - from kabusys.data.audit import init_audit_db
      conn = init_audit_db("data/audit_duckdb.db")
- DuckDB メイン DB は設定されたパス（settings.duckdb_path）で接続して利用します。

使い方（主要な操作例）
--------------------

基本的にモジュールの関数を組み合わせて使います。以下は代表的な例です。

1) 日次ETL 実行（価格・財務・カレンダー取得 + 品質チェック）
- Python 例:
  - import duckdb
    from kabusys.config import settings
    from kabusys.data.pipeline import run_daily_etl
    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn)
    print(result.to_dict())

  - run_daily_etl は ETLResult を返します。id_token を直接渡して J-Quants 認証を指定可能。

2) ニュースセンチメントスコアを生成（AI）
- 必要: OpenAI API キー（環境変数 OPENAI_API_KEY または api_key 引数）
- Python 例:
  - from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    n_written = score_news(conn, target_date=date(2026,3,20))
    print("書き込んだ銘柄数:", n_written)

3) 市場レジーム判定（ETF 1321 + マクロニュース）
- Python 例:
  - from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,3,20))

4) 監査テーブルの初期化（既存接続に追加）
- Python 例:
  - from kabusys.data.audit import init_audit_schema
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    init_audit_schema(conn, transactional=True)

注意点・設計上の留意事項
-----------------------
- Look-ahead バイアス対策:
  - モジュール内の多くの処理は date 引数や DB の過去データに基づき、datetime.today() を直接参照しない設計です（テストやバックテストでの公平性確保）。
- 環境変数の自動ロード:
  - config モジュールはプロジェクトルートの .env / .env.local を自動で読み込みます。テストで干渉する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- OpenAI 呼び出し:
  - レスポンスの JSON パース／フォーマットを厳密に検証します。API 失敗時はフェイルセーフ（ゼロスコアやスキップ）を基本方針としています。
- J-Quants API:
  - レートリミット（120 req/min）を厳守するための RateLimiter と再試行ロジックがあります。401 はトークン自動リフレッシュ対応。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py
  - 環境変数読み込み・settings オブジェクト
- ai/
  - __init__.py
  - news_nlp.py        — ニュースの LLM スコアリング（score_news）
  - regime_detector.py — マクロ + MA200 を用いた市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py  — J-Quants API クライアント、DuckDB 保存ユーティリティ
  - pipeline.py        — ETL パイプライン（run_daily_etl, run_prices_etl, ...）
  - quality.py         — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - news_collector.py  — RSS 取得・前処理・保存
  - calendar_management.py — 市場カレンダー管理（is_trading_day, next_trading_day 等）
  - stats.py           — 共通統計ユーティリティ（zscore_normalize）
  - audit.py           — 監査ログ（テーブル定義・init）
  - etl.py             — ETLResult の公開再エクスポート
- research/
  - __init__.py
  - factor_research.py — モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py — forward returns, IC, factor_summary, rank

開発・テスト
------------
- 自動環境変数ロードを無効化する:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI 呼び出しはテストでモック可能:
  - news_nlp._call_openai_api / regime_detector._call_openai_api を patch して挙動を固定化できます。
- DuckDB をインメモリ（":memory:"）で用いるとユニットテストが容易です。

ライセンス・貢献
----------------
- この README はコードベースの概要と使い方を説明するためのドキュメントです。実運用前に API キーや決済まわり（発注ロジック）について十分な確認を行ってください。
- 貢献は PR ベースで受け付ける想定です。コード品質・テストカバレッジ・ドキュメント整備を重視してください。

問い合わせ
----------
- 実装内容や使い方で不明点があれば、該当モジュールの docstring（ファイル冒頭）を参照してください。各関数は入力・出力・副作用について詳細な説明が付与されています。