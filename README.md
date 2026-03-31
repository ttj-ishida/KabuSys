# KabuSys

KabuSys は日本株向けの自動売買・データ基盤ライブラリ群です。J-Quants からのデータ取得、DuckDB を用いた保存・品質チェック、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（発注/約定のトレーサビリティ）などを提供します。

主な対象
- 日次 ETL（株価、財務、カレンダー）
- ニュース収集と LLM による銘柄センチメント算出
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- ファクター計算・特徴量解析（Research 用）
- 監査ログスキーマの初期化・管理

---

## 機能一覧

- 環境設定管理
  - .env 自動ロード（プロジェクトルート検出、.env/.env.local）
  - 必須環境変数チェック（Settings クラス）
- データ取得 / ETL
  - J-Quants API クライアント（差分取得・ページネーション・再試行・レート制御）
  - ETL パイプライン（run_daily_etl、個別ジョブ）
  - カレンダー更新ジョブ（JPX カレンダー）
  - ニュース収集（RSS、SSRF 対策、前処理、冪等保存）
- データ品質管理
  - 欠損・重複・スパイク・日付不整合チェック（quality モジュール）
- AI（LLM）統合
  - ニュース NLP（銘柄ごとのセンチメント算出: score_news）
  - 市場レジーム判定（ETF 1321 MA とニュースセンチメントの合成: score_regime）
  - OpenAI API 呼び出しはリトライやバックオフ考慮
- リサーチ / ファクター
  - Momentum / Volatility / Value 等の定量ファクター計算
  - 将来リターン計算、IC（Spearman）、統計サマリー、Zスコア正規化
- 監査（Audit）
  - signal_events / order_requests / executions テーブル定義
  - 監査 DB 初期化ユーティリティ（init_audit_db / init_audit_schema）

---

## 必要な環境変数

主に以下の環境変数がコード中で参照されます（必須は明記）:

必須
- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン（get_id_token に使用）
- SLACK_BOT_TOKEN — Slack 通知を使う場合
- SLACK_CHANNEL_ID — Slack 通知対象チャンネル
- KABU_API_PASSWORD — kabu ステーション API パスワード（kabu 関連を使う場合）

任意（デフォルトあり）
- KABUSYS_ENV — 実行環境 ("development" / "paper_trading" / "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG","INFO","...")（デフォルト: INFO）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など

注意:
- パッケージは起動時にプロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動ロードします。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ...

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必要最低限（例）:
     - pip install duckdb openai defusedxml
   - その他プロジェクトに合わせて追加パッケージが必要な場合があります（Slack SDK 等）。

4. パッケージを編集可能モードでインストール（プロジェクトルートで）
   - pip install -e .

5. .env ファイルを用意
   - プロジェクトルートに .env を作成し、必要なキーを設定します。例:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - OPENAI_API_KEY=your_openai_api_key
     - SLACK_BOT_TOKEN=xxx
     - SLACK_CHANNEL_ID=C01234567
     - KABU_API_PASSWORD=your_password

6. データベースディレクトリを作成（必要に応じて）
   - mkdir -p data

---

## 使い方（主要 API と実行例）

以下は Python REPL やスクリプトから利用する最小の例です。

- DuckDB 接続を作る（設定に従う）
  - from kabusys.config import settings
    import duckdb
    conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を回す
  - from kabusys.data.pipeline import run_daily_etl
    from datetime import date
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニュース NLP（ai スコア）を実行
  - from kabusys.ai.news_nlp import score_news
    from datetime import date
    n = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key None→OPENAI_API_KEY を参照
    print("written codes:", n)

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
    from datetime import date
    score_regime(conn, target_date=date(2026,3,20))

- 監査 DB を初期化（別ファイルで専用 DB を用意する場合）
  - from kabusys.data.audit import init_audit_db
    audit_conn = init_audit_db("data/audit.duckdb")

- ファクター計算（研究用途）
  - from kabusys.research import calc_momentum, calc_value, calc_volatility
    from datetime import date
    mom = calc_momentum(conn, date(2026,3,20))
    vol = calc_volatility(conn, date(2026,3,20))
    val = calc_value(conn, date(2026,3,20))

注意点
- OpenAI を呼ぶ処理（score_news, score_regime）は API キー（OPENAI_API_KEY または引数）を必要とします。
- LLM 呼び出しはリトライ／フェイルセーフを備えていますが、テスト時は内部の API 呼び出し関数をモックすることを推奨します（モジュール内で _call_openai_api を patch 可能）。
- ETL / データ操作は DuckDB のスキーマに依存します。既存データベースに対する操作前にスキーマの準備を行ってください。

---

## 開発・テスト時のヒント

- .env 自動ロードを無効にする:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば自動的な .env 読み込みをスキップできます（テストで環境汚染を避けるため）。
- OpenAI 呼び出しのモック:
  - unittest.mock.patch を用いて kabusys.ai.news_nlp._call_openai_api や kabusys.ai.regime_detector._call_openai_api を差し替えられます。
- DuckDB をメモリで使う:
  - duckdb.connect(":memory:") で一時 DB を使えばテストが容易です。

---

## 主なディレクトリ構成

プロジェクトの主要ファイル・モジュールは以下のとおりです（src/kabusys 配下）:

- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py        — ニュース NLP（score_news）
  - regime_detector.py — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py  — J-Quants API クライアント（fetch / save）
  - pipeline.py        — ETL パイプライン（run_daily_etl 等）
  - etl.py             — ETLResult 再エクスポート
  - calendar_management.py — 市場カレンダー管理
  - news_collector.py  — RSS ニュース収集と保存
  - quality.py         — データ品質チェック
  - stats.py           — 汎用統計ユーティリティ（zscore_normalize）
  - audit.py           — 監査ログスキーマ初期化（init_audit_db）
- research/
  - __init__.py
  - factor_research.py — モメンタム/ボラティリティ/バリュー計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー
- その他: monitoring / execution / strategy などの上位モジュールが __all__ に想定されています（実装の有無はコードベースによる）

---

## 注意事項 / 設計上のポイント

- Look-ahead bias 防止
  - ほとんどの関数は内部で datetime.today() / date.today() を直接参照しないよう設計されており、必ず target_date を明示して使うことを想定しています。
- 冪等性
  - J-Quants から取得したデータの保存は ON CONFLICT を用いた冪等的な実装です（再実行しても上書きされる）。
- フェイルセーフ
  - LLM 呼び出しや外部 API のエラー時には、可能な限り処理を継続し安全なデフォルト（例: macro_sentiment=0.0）でフォールバックします。
- セキュリティ
  - news_collector は SSRF 対策（プライベートホスト検査、リダイレクト検査）や XML パーサの安全化（defusedxml）を実装しています。

---

README に書かれている以外の使い方や追加の運用スクリプトが必要であれば、特定の例（ETL のスケジューリング、Slack 通知の統合、kabu ステーションとの接続例など）を示した補足ドキュメントを作成します。必要な項目を教えてください。