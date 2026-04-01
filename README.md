# KabuSys

バージョン: 0.1.0

KabuSys は日本株のデータプラットフォームとリサーチ／自動売買に必要なユーティリティ群をまとめたライブラリです。J-Quants や kabuステーション、OpenAI（LLM）などと連携して、データ取得（ETL）・品質チェック・ニュース NLP・市場レジーム判定・ファクター計算・監査ログ管理を行うことを想定しています。

主な設計方針
- ルックアヘッドバイアスを防ぐ（内部で date.today()/datetime.today() を直接参照しない設計）
- DuckDB を中心としたローカル DB でのイディオム（冪等保存、トランザクション管理）
- 外部 API 呼び出しはリトライ・レート制御・フェイルセーフを備える
- テスト容易性を考慮して API 呼び出し部分は差し替え可能に設計

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（必要に応じて無効化可能）
  - 必須設定の取得とバリデーション

- データ ETL（J-Quants）
  - 株価日足（OHLCV）取得・保存（fetch / save）
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存
  - 差分更新・バックフィル・品質チェックを含む日次 ETL パイプライン（run_daily_etl）

- データ品質チェック
  - 欠損（OHLC）検出、主キー重複、前日比スパイク検出、日付不整合チェック
  - QualityIssue による検出結果の収集

- ニュース収集 / NLP
  - RSS 取得（SSRF 対策、gzip、サイズ制限、追跡パラメータ除去）
  - ニュースの前処理（URL 除去・空白正規化）
  - OpenAI（gpt-4o-mini）を利用した銘柄別ニュースセンチメント（score_news）
  - 市場マクロニュースと ETF（1321）MA 乖離を用いた市場レジーム判定（score_regime）

- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（calc_momentum / calc_volatility / calc_value）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
  - z-score 正規化ユーティリティ

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions を含む監査スキーマの初期化と専用 DB 作成（init_audit_schema / init_audit_db）

- J-Quants クライアント
  - 認証（リフレッシュトークン→IDトークン）、ページネーション対応、レート制御、リトライ、DuckDB への冪等保存ユーティリティ

---

## セットアップ手順

前提
- Python 3.9+（typing 拡張を使用しているため Python 3.9 以降を推奨）
- DuckDB を利用（ローカルファイルまたはメモリ DB）

1. リポジトリをクローン（あるいは本パッケージをプロジェクトへ配置）
   - 例: git clone ...

2. 仮想環境を作成して有効化
   - macOS / Linux:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate

3. 必要なライブラリをインストール
   - 最小例:
     - pip install duckdb openai defusedxml
   - 実運用では他に requests 等を追加する場合があります（コードは標準ライブラリ urllib を使用していますが、依存関係に合わせて調整してください）。

4. 環境変数を設定
   - .env（プロジェクトルート）または OS 環境変数で以下を設定してください（必須は _で示す）:

     必須:
     - JQUANTS_REFRESH_TOKEN (J-Quants のリフレッシュトークン)
     - SLACK_BOT_TOKEN (Slack 通知を使う場合)
     - SLACK_CHANNEL_ID (Slack 通知チャネル)
     - KABU_API_PASSWORD (kabuステーション API パスワード)

     推奨/任意:
     - OPENAI_API_KEY (news_nlp / regime_detector で使う OpenAI API キー。score_* に引数で渡すことも可能)
     - KABUSYS_ENV (development | paper_trading | live; デフォルト development)
     - LOG_LEVEL (DEBUG/INFO/...)
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると .env 自動読み込みを無効化できます
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視用 DB 等、デフォルト data/monitoring.db）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

   - .env の自動読み込み順序:
     - OS 環境変数 > .env.local > .env
     - パッケージ内部でプロジェクトルート（.git または pyproject.toml）を探索して自動ロードします

5. データベース等の初期化（必要に応じて）
   - 監査ログ専用 DB の初期化:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")

---

## 使い方（簡単な例）

以下はライブラリの代表的な機能の使用例です。実運用では適切なロギング設定や例外処理を追加してください。

- DuckDB 接続を作る（デフォルトパスを settings から取得）
  - from kabusys.config import settings
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL（run_daily_etl）
  - from kabusys.data.pipeline import run_daily_etl
  - from kabusys.config import settings
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))
  - result = run_daily_etl(conn, target_date=None)  # target_date を指定するとその日の ETL を行う
  - print(result.to_dict())

- ニュースセンチメントスコアを生成（score_news）
  - from kabusys.ai.news_nlp import score_news
  - import duckdb
  - from datetime import date
  - conn = duckdb.connect(str(settings.duckdb_path))
  - n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="あなたのOPENAIキー")
  - print(f"書き込み銘柄数: {n_written}")

- 市場レジーム判定（score_regime）
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - conn = duckdb.connect(str(settings.duckdb_path))
  - score_regime(conn, target_date=date(2026, 3, 20), api_key="あなたのOPENAIキー")

- 監査 DB の初期化（init_audit_db）
  - from kabusys.data.audit import init_audit_db
  - conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリが無ければ自動作成されます

- ファクター計算 / リサーチ
  - from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
  - res = calc_momentum(conn, target_date=date(2026,3,20))
  - 正規化: from kabusys.data.stats import zscore_normalize; zscore_normalize(res, ["mom_1m", "mom_3m"])

注意点
- OpenAI を使う箇所（news_nlp, regime_detector）は API 呼び出しに失敗した場合フェイルセーフ（スコア 0.0 等）で継続する設計ですが、API キーが未設定の場合は ValueError を送出します。
- ETL の run_daily_etl は内部で market calendar を先に取得し、営業日に調整してから株価・財務データを更新します。

---

## 環境変数例 (.env)

プロジェクトルートに .env（および必要なら .env.local）を作成して管理します。例:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO

※ 実際の運用ではシークレットは安全に管理してください（CI/CD のシークレットストアやシステム環境変数等を利用）。

---

## ディレクトリ構成

主要なファイル・モジュール構成（src/kabusys 以下の抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                       # 環境設定読み込み・Settings
  - ai/
    - __init__.py
    - news_nlp.py                    # ニュース NLP（score_news）
    - regime_detector.py             # マーケットレジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py              # J-Quants API クライアント（fetch/save）
    - pipeline.py                    # ETL パイプライン（run_daily_etl 等）
    - etl.py                         # ETLResult の再エクスポート
    - calendar_management.py         # 市場カレンダー管理
    - news_collector.py              # RSS ニュース収集
    - stats.py                       # z-score 正規化 等
    - quality.py                     # データ品質チェック
    - audit.py                       # 監査ログ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py             # Momentum / Volatility / Value
    - feature_exploration.py         # 将来リターン / IC / summary / rank

---

## 開発・テストに関するメモ

- 環境変数の自動読み込みはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に行われます。テスト時に自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI への呼び出し部分は内部でラップされているため、ユニットテスト時は該当関数（例: kabusys.ai.news_nlp._call_openai_api）を patch/mocking して API 依存を切り離せます。
- DuckDB のバージョン差異に注意：一部 executemany の挙動やリストバインドはバージョン依存の問題が発生し得るため pipeline 等で互換性考慮コードが書かれています。

---

## ライセンス / 注意事項

- 本リポジトリは内部ドキュメント（StrategyModel.md / DataPlatform.md 等）に基づく実装を含みます。実取引で使用する際は十分な検証・リスク管理を行ってください。
- 実運用での API キーやシークレットの管理、個人情報・機密データの取扱いは適切に行ってください。

---

不明点や README に追加したい利用例があれば教えてください。README をプロジェクトの実際のパッケージ配布手順（pyproject.toml、requirements.txt、セットアップスクリプト）に合わせて調整できます。