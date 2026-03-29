# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォーム向けライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI 経由）、ファクター計算、監査ログ（約定トレーサビリティ）など、運用に必要な基盤処理群を提供します。

バージョン: 0.1.0

---

## 概要

主な目的は以下です。

- J-Quants API からの差分取得と DuckDB への冪等保存（ETL）
- RSS ベースのニュース収集と前処理（SSRF/サイズ制限対策あり）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント / 市場レジーム判定
- ファクター算出（モメンタム・バリュー・ボラティリティ等）と研究ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution）の初期化と管理
- 環境変数 / .env による設定管理（自動読み込み対応）

設計方針として、バックテスト時のルックアヘッドバイアスを避けるために、内部処理は明示的な target_date を受け取り、date.today() 等に依存しないようにしています。また外部 API 呼び出しはリトライやフェイルセーフを備えています。

---

## 機能一覧

- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（fetch / save 系関数、トークン自動リフレッシュ、レート制御）
  - ニュース収集（RSS → raw_news、URL 正規化・SSRF 対策・サイズ制限）
  - 市場カレンダー管理（営業日判定、next/prev_trading_day、calendar_update_job）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ初期化（audit スキーマ、init_audit_db）
  - 汎用統計ユーティリティ（zscore 正規化）
- ai
  - ニュース NLP（銘柄毎のセンチメントを OpenAI でスコアリング: score_news）
  - 市場レジーム判定（ETF 1321 の MA200 乖離とマクロニュース LLM を合成: score_regime）
- research
  - ファクター計算（momentum / value / volatility）
  - 特徴量探索（将来リターン計算、IC 計算、統計サマリー）
- config
  - 環境変数 / .env の自動読み込みと設定アクセス（settings オブジェクト）

---

## セットアップ手順（開発環境想定）

1. リポジトリをクローン

   git clone <repo-url>
   cd <repo-root>

2. Python 仮想環境を作成・有効化（例）

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .\.venv\Scripts\activate   # Windows（PowerShell）

3. 必要なパッケージをインストール

   プロジェクトでは以下の主要依存が使用されています（代表例）。実プロジェクトでは requirements.txt / pyproject.toml を参照してください。

   - duckdb
   - openai
   - defusedxml

   例:

   pip install duckdb openai defusedxml

4. 環境変数を準備

   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env`（および任意で `.env.local`）を置くと自動で読み込まれます。読み込み順は:

   OS 環境変数 > .env.local > .env

   自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用）。

   必須の環境変数（少なくともこれらを設定してください）:

   - JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン
   - OPENAI_API_KEY         — OpenAI の API キー（AI 機能を使う場合）
   - KABU_API_PASSWORD      — kabuステーション API を使う場合のパスワード
   - SLACK_BOT_TOKEN        — Slack 通知を使う場合
   - SLACK_CHANNEL_ID       — Slack チャンネル ID

   任意 / デフォルト:
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
   - LOG_LEVEL (DEBUG | INFO | ...) — デフォルト INFO
   - KABUS_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）

5. データベース初期化（監査テーブルなど）

   監査ログ用 DB を初期化する例:

   from kabusys.config import settings
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db(settings.duckdb_path)  # Path または ":memory:"
   conn.close()

---

## 使い方（短いコード例）

以下は代表的な呼び出し例です。すべて Python スクリプト内で実行できます。

- DuckDB 接続作成

  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行（市場カレンダー、株価、財務、品質チェック含む）

  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントのスコアリング（OpenAI API キーが環境変数にある前提）

  from datetime import date
  from kabusys.ai.news_nlp import score_news
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")

- 市場レジーム評価

  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログスキーマを既存 DuckDB に追加（トランザクションあり）

  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)

- 研究用ファクター計算例

  from datetime import date
  from kabusys.research.factor_research import calc_momentum
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  # records は各銘柄ごとの dict のリスト

注意:
- AI 関連関数は OpenAI API を呼び出します。API キーの設定と利用制限にご注意ください。
- ETL / J-Quants クライアントはネットワークを使います。rate limit（120 req/min）やリトライ動作を組み込んでいます。

---

## 環境変数と .env の挙動

- 自動読み込み対象ファイル: プロジェクトルートの `.env` と `.env.local`
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - `.env.local` は `.env` を上書きする（ローカル専用設定）
- 自動読み込みを無効化する: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- .env のパース仕様:
  - 空行・コメント（#）を無視
  - export KEY=val 形式に対応
  - シングル／ダブルクォート、エスケープ、インラインコメントの処理あり

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                     — 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py                  — ニュースセンチメント（score_news）
  - regime_detector.py           — 市場レジーム判定（score_regime）
- research/
  - __init__.py
  - factor_research.py           — Momentum / Value / Volatility 等
  - feature_exploration.py       — 将来リターン / IC / 統計サマリー
- data/
  - __init__.py
  - jquants_client.py            — J-Quants API クライアント（fetch/save）
  - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
  - etl.py                       — ETLResult 再エクスポート
  - news_collector.py            — RSS 収集・前処理
  - calendar_management.py       — 市場カレンダー管理（営業日判定等）
  - quality.py                   — データ品質チェック
  - stats.py                     — zscore_normalize 等
  - audit.py                     — 監査ログスキーマ定義 / init_audit_db
- research/ (上記)
- その他モジュール（monitoring, strategy, execution 等は __all__ に含める設計）

---

## 注意事項 / ベストプラクティス

- OpenAI API や J-Quants のキーは外部に漏れないように管理してください。運用環境では環境変数管理（Vault 等）を推奨します。
- ETL は外部 API に依存するため、実行時のネットワークエラーや API 制限に備えた監視を行ってください。
- AI モジュールはレスポンスパース失敗時にフェイルセーフ（スコア=0）で継続する設計ですが、重要な決定に使う場合はヒューマンレビューや二重チェックを推奨します。
- DuckDB スキーマは一部関数で前提（テーブル名・カラム）があります。運用前にスキーマ整備・初期化を行ってください。

---

## さらに知りたいとき

- コード内の docstring / コメントには設計方針や詳細な挙動が記載されています。各モジュールのドキュメント（関数 docstring）を参照してください。
- テストや CI を組む場合は、環境変数の自動読み込みをオフにしてテスト用の設定を注入することを推奨します（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

---

README はここまでです。必要であれば、利用例を増やしたサンプルスクリプト（ETL バッチ、ニュース収集ジョブ、監査 DB 初期化スクリプト）や想定される requirements.txt を作成します。どのサンプルが欲しいか教えてください。