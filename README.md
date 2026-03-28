# KabuSys

日本株自動売買プラットフォームのライブラリ実装（パッケージ）です。データ取得（J-Quants）、ETL、ニュース NLP、市場レジーム判定、リサーチ/ファクター計算、監査ログなど、取引システムを構成するコア機能をモジュール化して提供します。

## 特徴（機能一覧）
- 環境変数 / .env 管理（自動ロード、.env.local 上書き対応）
- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダー取得
  - レート制限・リトライ・トークン自動リフレッシュ対応
  - DuckDB へ冪等に保存（ON CONFLICT DO UPDATE）
- ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - 差分取得、バックフィル、品質チェック（quality モジュール）
- データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
- ニュース収集（RSS -> raw_news）と前処理（SSRF 対策、トラッキング除去、サイズ制限）
- ニュース NLP（OpenAI を使った銘柄単位センチメントスコアリング）
  - バッチ処理、JSON Mode、リトライとバリデーション実装
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM センチメントの合成）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC 計算、Z スコア正規化）
- 監査ログ（signal_events, order_requests, executions）用 DuckDB スキーマ初期化ユーティリティ
- DuckDB ベースのローカルデータストア設計（監査ログ専用 DB 生成も可能）

## 前提条件
- Python 3.10 以上（型ヒントで PEP 604 の `X | Y` を使用）
- 主要依存ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / OpenAI / RSS フィード 等）

必要なパッケージはプロジェクトの配布方法に応じて requirements.txt / pyproject.toml に記載してください。

## 環境変数（主要）
以下はコード内で必須または参照される主要な環境変数です。実行前に .env ファイルか OS 環境変数で設定してください。

必須（未設定時は ValueError で失敗）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API 用パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV — execution 環境（development / paper_trading / live）。デフォルト: development
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）。デフォルト: INFO
- KABU_API_BASE_URL — kabu API のベース URL。デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH — DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
- SQLITE_PATH — SQLite（監視用）パス。デフォルト: data/monitoring.db
- OPENAI_API_KEY — OpenAI API キー（ニュース NLP / レジーム判定で使用・関数引数からも注入可）

.env 自動読み込み:
- パッケージはプロジェクトルート（.git または pyproject.toml を検出）を基に `.env` と `.env.local` を自動で読み込みます。
- 読み込み優先度: OS 環境変数 > .env.local > .env
- 自動ロード無効化: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

## セットアップ

1. リポジトリをクローン / コピー
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix)
   - .venv\Scripts\activate     (Windows)
3. 依存パッケージをインストール（例）
   - pip install duckdb openai defusedxml
   - または pip install -e .（プロジェクトに pyproject / setup がある場合）
4. `.env` を作成
   - プロジェクトルートに .env を置くと自動で読み込まれます（前述の優先度ルールに従う）。
   - 例（.env.example）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - OPENAI_API_KEY=your_openai_api_key
     - KABU_API_PASSWORD=xxxxx
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567
     - KABUSYS_ENV=development

注意: センシティブな値は `.env.local` に置き、リポジトリに含めないようにしてください。

## 使い方（主な API と実行例）

下記は Python REPL / スクリプトから直接呼び出す簡単な例です。duckdb コネクションを作成して各モジュールを呼び出します。

- 日次 ETL を実行する（run_daily_etl）
  - 目的: 市場カレンダー、株価、財務データを差分取得して保存、品質チェックを実行
  - 例:

    from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニュースセンチメント（１日分）を LLM でスコアリングして ai_scores テーブルに書き込む
  - 例:

    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_API_KEY")
    print("書き込んだ銘柄数:", n_written)

- 市場レジーム判定を行い market_regime テーブルへ書き込む
  - 例:

    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_API_KEY")

- 監査ログ用の DuckDB を初期化する
  - 例:

    from kabusys.data.audit import init_audit_db

    conn = init_audit_db("data/audit_kabusys.duckdb")
    # conn を使って order_requests / signal_events / executions にアクセス可能

- J-Quants データ取得（単体）例
  - 例:

    from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

    # 明示的に id_token を取得してページネーション等で再利用することが可能
    token = get_id_token()
    records = fetch_daily_quotes(id_token=token, date_from=date(2026,1,1), date_to=date(2026,1,31))

各関数は例外処理やログ出力を行うため、実運用では try/except とログ監視を併用してください。

## 実装上のポイント / 注意点
- ルックアヘッドバイアス対策:
  - モジュール（news_nlp, regime_detector, pipeline 等）は内部で datetime.today() を無闘に参照せず、呼び出し側から target_date を渡す設計になっています。
- 冪等性:
  - J-Quants の保存関数や監査ログ初期化は冪等になるよう ON CONFLICT / INSERT ... DO UPDATE、あるいは CREATE IF NOT EXISTS を使用しています。
- フェイルセーフ:
  - LLM 呼び出しや外部 API は失敗時に例外を投げずフォールバック（0.0 やスキップ）する箇所が多く、ETL 全体を停止させない設計です。
- .env のパースは POSIX-ish なフォーマットをサポートし、クォート・コメント・export prefix 等に対応しています。

## ディレクトリ構成
以下はパッケージ内部の主要ファイル・モジュール構成（抜粋）です。

- src/
  - kabusys/
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
      - stats.py
      - quality.py
      - calendar_management.py
      - news_collector.py
      - audit.py
      - pipeline.py
      - etl.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/
      - __init__.py
    - (その他 strategy / execution / monitoring 用モジュールはパッケージ公開候補)

各モジュールは責務が明確に分かれており、データ取得・保存、NLP、研究用途、監査ログなどを分離して実装しています。

## 開発 / テスト
- 自動環境変数ロードはテスト時に邪魔になる場合があるため、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動読み込みを無効化できます。
- OpenAI 呼び出しやネットワークアクセスを伴う箇所は、ユニットテストでモック可能（関数単位で置き換え可能に設計されています）。

---

この README はコードベースの主要機能と使い方をまとめた概略です。詳細な仕様（DataPlatform.md / StrategyModel.md 等）が別途ある前提で実装されているため、実運用時はそちらのドキュメントや DB スキーマ定義、運用ポリシー（リトライ / 監視 / ログ）を参考にしてください。必要であれば、導入手順（systemd ジョブ / cron / Airflow などでの定期実行）や .env.example のテンプレートを追加で作成します。