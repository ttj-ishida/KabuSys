KabuSys
=======

KabuSys は日本株向けのデータプラットフォーム／リサーチ／自動売買補助ライブラリです。  
J-Quants からのデータ取得、ニュース収集・NLP スコアリング、ファクター計算、ETL、監査ログスキーマなどを提供します。

主な目的
- J-Quants API を用いた株価・財務・市場カレンダーの差分 ETL
- RSS ニュースの収集と LLM による銘柄別センチメント（ai_scores）算出
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- 研究用ファクター計算（モメンタム / ボラティリティ / バリュー 等）
- 監査ログ（signal → order_request → execution）スキーマ初期化・管理
- データ品質チェック（欠損・スパイク・重複・日付不整合）

機能一覧
- data/
  - ETL（daily ETL, prices / financials / calendar の差分取得）
  - J-Quants クライアント（ページネーション、トークンリフレッシュ、レート制限、保存用関数）
  - market calendar 管理（営業日判定、next/prev/get_trading_days）
  - news_collector（RSS 取得・正規化・保存。SSRF/サイズ/トラッキング対策あり）
  - quality（欠損 / スパイク / 重複 / 日付不整合チェック）
  - audit（監査ログテーブル作成 / init_audit_db）
  - stats（zscore 正規化ユーティリティ）
- ai/
  - news_nlp.score_news: 指定ウィンドウのニュースを集約し OpenAI で銘柄ごとスコア化、ai_scores へ保存
  - regime_detector.score_regime: ETF (1321) の MA200 乖離とマクロニュースの LLM センチメントを合成して market_regime へ保存
- research/
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: forward returns 計算、IC、統計サマリー 等
- config.py
  - .env 自動ロード（プロジェクトルート検出、.env / .env.local）、環境変数ラッパー settings

セットアップ手順（開発環境向け）
1. リポジトリをクローン
   - git clone <リポジトリ URL>

2. 仮想環境を作成・有効化（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 最低依存（本リポジトリに requirements.txt が無い場合）:
     - pip install duckdb openai defusedxml
   - 実際の開発環境では追加パッケージ（logging 設定、テスト用ツール等）を別途導入してください。
   - パッケージとしてインストール可能なら:
     - pip install -e .

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env ファイルを置くと自動で読み込まれます（.env.local は上書き）。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数
- 必須
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（jquants_client.get_id_token に使用）
  - SLACK_BOT_TOKEN : Slack 通知を使う場合の Bot トークン
  - SLACK_CHANNEL_ID : Slack 通知先チャンネル ID
  - KABU_API_PASSWORD : kabu API 連携に必要なパスワード
- OpenAI
  - OPENAI_API_KEY : news_nlp / regime_detector などで使用（関数引数で明示的に渡すことも可）
- データベースパス（省略可、デフォルトあり）
  - DUCKDB_PATH : data/kabusys.duckdb（デフォルト）
  - SQLITE_PATH : data/monitoring.db（デフォルト）
- 実行環境・ログ
  - KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

.env の例（.env.example を参考に作成）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

使い方（コード例）
- DuckDB 接続を作成して ETL を実行する
  - Python REPL / スクリプト例:
    from datetime import date
    import duckdb
    from kabusys.config import settings
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date.today())
    print(result.to_dict())

- ニュースセンチメントのスコアリング（ai_scores への書き込み）
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect(str(settings.duckdb_path))
    written = score_news(conn, target_date=date(2026, 3, 20))  # OpenAI キーは環境変数から取得
    print(f"書き込み銘柄数: {written}")

- 市場レジーム判定
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect(str(settings.duckdb_path))
    score_regime(conn, target_date=date(2026, 3, 20))

- 研究用ファクター計算（例: モメンタム）
    from datetime import date
    import duckdb
    from kabusys.research.factor_research import calc_momentum
    conn = duckdb.connect(str(settings.duckdb_path))
    momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
    print(len(momentum))

- 監査 DB 初期化
    from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")  # ディレクトリは自動作成されます

設計上の注意点 / 重要事項
- Look-ahead bias 回避: モジュールの多くは内部で date.today()/datetime.today() に依存しない設計（target_date を明示）です。バックテスト・再現性を保つため target_date を明示してください。
- OpenAI 呼び出し:
  - news_nlp / regime_detector は gpt-4o-mini を想定し JSON mode を利用します。API レートとコストに注意してください。
  - API エラー時はフェイルセーフ（スコア 0 など）で継続する実装が多くありますが、結果の意味合いを確認してください。
- J-Quants クライアント:
  - レート制限（120 req/min）やトークンリフレッシュ、リトライを実装しています。ID トークンの管理はモジュール内部キャッシュで行われます。
- RSS ニュース収集:
  - SSRF・Gzip bomb・トラッキングパラメータ除去・Content-Length チェック等の対策を実装しています。外部フィードを追加する場合は信頼性と著作権に注意してください。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
    - etl.py (ETLResult 再エクスポート)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/__init__.py は主要な関数を再エクスポート
- その他
  - pyproject.toml / setup.cfg 等（プロジェクトにあれば）

開発 / 貢献
- バグ報告 / プルリクエスト歓迎。変更を加える際はユニットテストと簡潔な説明を添えてください。
- コードスタイル: ログ出力、例外処理、トランザクション管理に注意して実装しています。既存のパターンに合わせてください。

ライセンス
- このリポジトリに LICENSE ファイルが含まれる想定です。利用前にライセンス条項を確認してください。

FAQ / よくある使い方
- .env の自動ロードが動作しない
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を設定していないか確認してください。パッケージがインストールされる環境では __file__ を基準にプロジェクトルートを検出します（.git または pyproject.toml が目印）。
- OpenAI の API キーを明示的に渡したい
  - score_news / score_regime の api_key 引数に生のキー文字列を渡せます（テスト向け）。省略時は OPENAI_API_KEY 環境変数を参照します。

以上がこのコードベースの概要と基本的な使い方です。必要があれば、セットアップ時の具体的な requirements.txt、サンプル .env.example、あるいは ETL の運用手順（cron / Airflow などへの組み込み例）を追記しますので教えてください。