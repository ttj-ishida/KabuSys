KabuSys — 日本株自動売買プラットフォーム（README）
概要
- KabuSys は日本株向けのデータプラットフォーム・リサーチ・AI支援（ニュースNLP）・監査ログ・ETL 等を組み合わせた自動売買基盤のライブラリ群です。
- 主に DuckDB をデータレイヤとして用い、J-Quants API からマーケットデータを取り込み、ニュースを収集・LLMでスコア化し、ファクタ計算や市場レジーム判定を行います。
- コードベースはモジュール化されており、データ取得（data）、リサーチ（research）、AI（ai）、監査・注文管理（data.audit / execution 想定）などの機能を提供します。

主な機能一覧
- ETL（data.pipeline）
  - J-Quants からの株価・財務・カレンダーの差分取得、保存、品質チェック（quality）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl を提供
- ニュース収集（data.news_collector）
  - RSS フィード取得、テキスト前処理、raw_news への冪等保存、銘柄紐付け
  - SSRF対策・サイズ制限・トラッキングパラメータ除去 等の安全処理を実装
- ニュース NLP（ai.news_nlp）
  - OpenAI（gpt-4o-mini）による銘柄毎ニュースセンチメント算出（score_news）
  - 時間ウィンドウは前日15:00 JST～当日08:30 JST に相当する UTC 範囲で処理
- 市場レジーム判定（ai.regime_detector）
  - ETF(1321) の 200日移動平均乖離（重み70%）とマクロ記事の LLMセンチメント（重み30%）を合成し bull/neutral/bear を判定（score_regime）
  - LLM 呼び出しはリトライ・フェイルセーフを備える（API失敗時は中立寄せ）
- リサーチ / 特徴量（research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン算出、IC（Information Coefficient）、ファクターサマリ等（feature_exploration）
- データ品質チェック（data.quality）
  - 欠損、重複、スパイク、日付不整合の検出と QualityIssue API
- 監査ログ（data.audit）
  - signal_events, order_requests, executions テーブルの初期化ヘルパー（init_audit_schema / init_audit_db）
  - UUID ベースのトレーサビリティ設計、UTC タイムスタンプ

前提／要件
- Python 3.10 以上（型アノテーションに X | None を使用）
- DuckDB（python duckdb パッケージ）
- OpenAI SDK（openai パッケージ）を使用（AI モジュール）
- ネットワークアクセス（J-Quants API、RSS、OpenAI）
- 必要な依存はプロジェクトの requirements.txt 等で管理してください（この README の配布物に別途記載がない場合は pip install -r requirements.txt を想定）。

重要な環境変数（必須/任意）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード（execution 用）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack 送信先チャンネル ID
- OPENAI_API_KEY (必須 for AI functions) — OpenAI クライアントの API キー（score_news/score_regime で参照）
- KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意) — デフォルト: data/monitoring.db
- KABUSYS_ENV (任意) — development / paper_trading / live（デフォルト development）
- LOG_LEVEL (任意) — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定するとパッケージ起動時の .env 自動読み込みを無効化できます

.env の自動読み込み
- パッケージはプロジェクトルート（.git または pyproject.toml が存在）を探索し、.env → .env.local の順で自動読み込みします。
- 既存 OS 環境変数は保護され、.env.local は上書きを許可します。
- 自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください（テスト用途等）。

セットアップ手順（開発用）
1. リポジトリをチェックアウト
   - git clone ... && cd your-repo
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/Mac) / .venv\Scripts\activate (Windows)
3. 依存インストール
   - pip install -r requirements.txt
   - （開発時は pip install -e . で編集可能インストール）
   - 依存例: duckdb, openai, defusedxml
4. .env を用意（プロジェクトルート）
   - 例（.env）
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-xxxx...
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
5. データベース初期化（監査DBなど）
   - Python REPL またはスクリプトで init_audit_db を実行（下記参照）

簡単な使い方（コード例）
- DuckDB 接続の作成（デフォルトパスを settings から取得）
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニューススコアリング（OpenAI API キーが環境変数に設定されている前提）
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written scores: {written}")

- 市場レジーム判定
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026, 3, 20))  # market_regime テーブルへ書き込み

- 監査 DB 初期化（専用ファイル）
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")  # 必要に応じてパス作成される

注意点 / 補足
- AI 機能（news_nlp, regime_detector）は OpenAI API を使います。API コストとレート制限に注意してください。
- LLM 呼び出しはリトライ・タイムアウトを備えていますが、実運用ではレート制限とコスト管理を設計してください。
- ETL は差分取得を行い、保存は ON CONFLICT DO UPDATE による冪等性を担保しています。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して環境を固定し、OpenAI 呼び出しやネットワークをモックしてください（モジュール内で差し替え容易な設計あり）。
- 日付の取り扱いは look-ahead バイアスを避ける設計になっており、関数は明示的な target_date を受け取るか datetime.today() を使用する箇所を極力排除しています（ETL では date.today() を基準にする箇所あり）。

ディレクトリ構成（主なファイル/モジュール）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP（score_news 等）
    - regime_detector.py      — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（fetch/save）
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - etl.py                  — ETLResult の再エクスポート
    - news_collector.py       — RSS ニュース収集
    - quality.py              — データ品質チェック
    - stats.py                — 汎用統計ユーティリティ（zscore_normalize）
    - calendar_management.py  — 市場カレンダー管理（is_trading_day 等）
    - audit.py                — 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py      — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py  — calc_forward_returns / calc_ic / factor_summary / rank
  - ai/ , research/ 以下は研究・分析向けユーティリティとして分離

開発・テストのヒント
- OpenAI・J-Quants 呼び出し部はモック可能なヘルパー関数に分離されています。単体テストではネットワーク依存箇所を patch することを推奨します。
- DuckDB はインメモリ接続（":memory:"）が可能なので、テスト時はファイル I/O を避けて高速に実行できます。
- .env の自動読み込みを無効化するフラグを利用すると CI 上で安全に環境を管理できます。

ライセンス・著作権
- 本リポジトリにライセンス表記がある場合はそちらに従ってください。（本 README はソースコードの構成と利用方法を説明する補助ドキュメントです）

問い合わせ・貢献
- バグ報告やプルリクエストはリポジトリの issue / PR を利用してください。
- 大きな仕様変更は設計方針に影響するため事前に議論を行ってください。

以上。必要なら README に含めたい追加情報（例: 具体的な .env.example、CI 実行例、スケジューラ（cron/airflow）統合例など）を教えてください。