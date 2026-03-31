KabuSys — 日本株自動売買プラットフォーム (README)
概要
- KabuSys は日本株向けのデータパイプライン、ファクター研究、ニュースNLP、マーケットレジーム判定、監査ログ等を備えた自動売買補助ライブラリです。
- DuckDB をデータ層に用い、J-Quants API からのデータ取得、RSS ニュース収集、OpenAI を用いたニュースセンチメント評価などを行います。
- バックテスト／リサーチ用途と、モニタリング・実行（発注・監査ログ）用途の両方を念頭に設計されています。

主な機能
- データ取得・ETL
  - J-Quants API から株価（日足）、財務データ、JPX マーケットカレンダーを差分取得・保存（jquants_client, pipeline）。
  - 差分更新／バックフィル、品質チェック（欠損・スパイク・重複・日付不整合）。
- ニュース収集・NLP
  - RSS 取得と前処理（news_collector）、記事の銘柄紐付け。
  - OpenAI を使った銘柄ごとのニュースセンチメントスコア算出（news_nlp）。
- 市場レジーム判定
  - ETF (1321) の 200 日移動平均乖離（70%）とマクロニュース LLM センチメント（30%）を合成して日次レジーム判定（regime_detector）。
- 研究用ファクター計算
  - Momentum / Value / Volatility 等のファクター計算、将来リターン計算、IC 計算、Zスコア正規化（research）。
- 監査・トレーサビリティ
  - signal → order_request → execution の監査テーブルを DuckDB に作成・初期化（data.audit）。
- ユーティリティ
  - カレンダー管理（営業日判定・取得・更新）、統計ユーティリティ（zscore_normalize）等。

セットアップ手順（開発環境）
1. リポジトリをクローンしてプロジェクトルートへ移動
   - git clone ...; cd <project-root>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 必須パッケージ（例）
     - duckdb
     - openai
     - defusedxml
   - pip install duckdb openai defusedxml
   - （プロジェクトに pyproject.toml / requirements.txt があれば pip install -e . または pip install -r requirements.txt）

4. 環境変数 / .env 設定
   - プロジェクトは .env / .env.local を自動でプロジェクトルートから読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須（モジュール内で require として参照されるもの）
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...  （kabuステーション関連）
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
   - OpenAI を使う場合
     - OPENAI_API_KEY=...
   - 任意（デフォルト値あり）
     - KABUSYS_ENV=development|paper_trading|live  （default: development）
     - LOG_LEVEL=INFO|DEBUG|...  （default: INFO）
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
   - 例 (.env)
     - JQUANTS_REFRESH_TOKEN=xxxxxxxx
     - OPENAI_API_KEY=sk-...
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567
     - KABU_API_PASSWORD=your_password

使い方（簡単なコード例）
- 共通準備
  - import duckdb
  - conn = duckdb.connect(str(Path("data/kabusys.duckdb")))

- 日次 ETL 実行（データ取得・保存・品質チェック）
  - from kabusys.data.pipeline import run_daily_etl
  - from datetime import date
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- ニュースセンチメントのスコア付け（OpenAI 必須）
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None → 環境変数 OPENAI_API_KEY を参照
  - print(f"scored {count} codes")

- 市場レジーム判定（OpenAI 必須）
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 監査DB 初期化（監査専用 DuckDB を作る）
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")  # :memory: も可

- 研究モジュール例（モメンタム）
  - from kabusys.research.factor_research import calc_momentum
  - from datetime import date
  - records = calc_momentum(conn, target_date=date(2026, 3, 20))

注意点 / 運用上のヒント
- 環境変数の自動読み込み
  - パッケージはプロジェクトルート（.git または pyproject.toml がある場所）から .env/.env.local を自動で読み込みます。
  - テストや特別な状況で自動読み込みを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し
  - news_nlp と regime_detector は OpenAI の Chat Completions（gpt-4o-mini 等）を利用する設計です。API 呼び出しはリトライや JSON バリデーションを行いますが、API キーは必ず設定してください。
- J-Quants API
  - get_id_token を通じて refresh token から id_token を取得します。API レート制限（120 req/min）やリトライを実装しています。
- DuckDB
  - デフォルトの DB パスは data/kabusys.duckdb。ファイルの親ディレクトリは自動作成されるように各ユーティリティで考慮されています。
- フェイルセーフ設計
  - AI API が失敗した場合、多くの処理は 0（中立）やスキップして継続するフェイルセーフ設計になっています（例: macro_sentiment=0.0、スコア不取得時はスキップ）。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py (パッケージ定義 / __version__)
  - config.py (環境変数・設定管理)
  - ai/
    - __init__.py
    - news_nlp.py (ニュース NLU / スコアリング)
    - regime_detector.py (市場レジーム判定)
  - data/
    - __init__.py
    - calendar_management.py (JPX カレンダー管理)
    - etl.py (ETL インターフェース再エクスポート)
    - pipeline.py (日次 ETL パイプライン)
    - stats.py (統計ユーティリティ：zscore_normalize 等)
    - quality.py (データ品質チェック)
    - audit.py (監査ログテーブル初期化)
    - jquants_client.py (J-Quants API クライアント及び保存関数)
    - news_collector.py (RSS 収集・前処理)
  - research/
    - __init__.py
    - factor_research.py (ファクター計算：Momentum/Value/Volatility)
    - feature_exploration.py (将来リターン・IC・統計サマリー)
  - ai, research, data などそれぞれが公開 API を持ちます（__all__ 等で整理）。

テスト・開発
- 各モジュールは外部 API 呼び出し（OpenAI, J-Quants, HTTP）を行うため、ユニットテスト時は該当関数をモックしてください。実装内でモックしやすいように API 呼び出しラッパー（例: _call_openai_api, _urlopen）を分離しています。
- 自動ロードされる .env をテストで使いたくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し、テストコード内で必要な環境変数を明示的に設定してください。

ライセンス・貢献
- （この README ではライセンス情報は省略しています。実プロジェクトに合わせて LICENSE ファイルを用意してください。）
- バグ報告や機能提案は Issue を立ててください。コントリビュート前に coding standard やテスト方針を合わせるとスムーズです。

補足
- README 内の使用例はパッケージの内部 API を直接呼ぶ形です。実運用では CLI ラッパーやジョブスケジューラ（cron / systemd timer / Airflow 等）を用いて ETL やスコア処理を定期実行することを推奨します。
- セキュリティ：API キーや機密情報は必ず安全に保管し、リポジトリに含めないでください（.gitignore に .env を追加）。

必要であれば、以下を追記できます
- より詳細な環境変数一覧（デフォルト値・説明）
- サンプル .env.example の全文
- CI / テスト実行手順、flak8/ruff/black 等の設定例
- 実運用向けのシステム構成例（監視・ロギング・バックアップ）