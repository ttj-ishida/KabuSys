# KabuSys

日本株向けの自動売買・データ基盤ライブラリセットです。  
ETL（J-Quants → DuckDB）、ニュース収集・NLP（OpenAI を利用したセンチメント）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（トレース）などを一貫して提供します。

主な想定用途：
- データ基盤（株価・財務・カレンダー）のバッチ ETL
- ニュースを用いた銘柄別 AI スコアリング
- 市場レジーム判定（ETF + マクロニュース）
- 研究（ファクター計算・IC/統計解析）
- 発注周りの監査ログ管理（DuckDB）

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数のラッパー（kabusys.config.settings）
- データ ETL（kabusys.data.pipeline / jquants_client）
  - J-Quants API から日次株価・財務・市場カレンダーを差分取得して DuckDB に保存
  - レート制御、リトライ、トークン自動リフレッシュ（401 対応）
  - ETL の結果を表す ETLResult
- データ品質チェック（kabusys.data.quality）
  - 欠損・スパイク・重複・日付整合性検査
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、正規化、SSRF 対策、記事の前処理と保存
- AI（kabusys.ai）
  - score_news: 銘柄別ニュースセンチメントを OpenAI で評価して ai_scores に書き込み
  - score_regime: ETF（1321）200日MA乖離とマクロニュースセンチメントを合成して market_regime に書き込み
  - 両関数は OpenAI API（gpt-4o-mini）を JSON mode で利用、リトライとフォールバック処理あり
- 研究モジュール（kabusys.research）
  - momentum/value/volatility 等のファクター計算、将来リターン計算、IC（Spearman）計算、統計サマリー
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions のテーブル DDL と初期化ユーティリティ
  - init_audit_db で専用 DuckDB を初期化可能
- 汎用ユーティリティ
  - z-score 正規化（kabusys.data.stats）など

---

## セットアップ手順

前提：Python 3.9+（型表記に合わせて）、インターネット接続（API 呼び出しのため）

1. リポジトリをクローン（パッケージルートに pyproject.toml か .git があることを想定）
   - git clone ...

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトで requirements.txt / pyproject.toml がある場合はそちらを利用してください）
   
4. パッケージを開発モードでインストール（任意）
   - pip install -e .

5. 環境変数を設定（.env を作成）
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須の主な環境変数（最低限）：
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 実行時）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（jquants_client）
- SLACK_BOT_TOKEN — Slack 連携（必要な場合）
- SLACK_CHANNEL_ID — Slack 連携（必要な場合）
- KABU_API_PASSWORD — kabuステーション API パスワード（必要な場合）

オプション／デフォルト値のあるもの（環境変数名）：
- KABU_API_BASE_URL（default: http://localhost:18080/kabusapi）
- DUCKDB_PATH（default: data/kabusys.duckdb）
- SQLITE_PATH（default: data/monitoring.db）
- PID_FILE_PATH（default: data/execution.pid）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
- KABUSYS_ENV（development / paper_trading / live）
- LOG_LEVEL（DEBUG, INFO, ...）

例（.env）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（代表的な例）

以下は簡易的な使用例です。実行前に必要な環境変数を設定してください。

- DuckDB 接続を作って日次 ETL を実行する
  - from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_daily_etl
    from kabusys.config import settings

    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニューススコアリングを実行する
  - from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    from kabusys.config import settings

    conn = duckdb.connect(str(settings.duckdb_path))
    n_written = score_news(conn, target_date=date(2026, 3, 20))
    print(f"scored {n_written} codes")

  - score_news は内部で OpenAI API（OPENAI_API_KEY）を使用します。API 呼び出しに失敗した場合はフォールバックして処理を継続します。

- 市場レジーム判定を実行する
  - from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime
    from kabusys.config import settings

    conn = duckdb.connect(str(settings.duckdb_path))
    score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ DB を初期化する
  - from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
    # conn を使ってテーブルにアクセスできます

- 環境設定を参照する
  - from kabusys.config import settings
    print(settings.duckdb_path, settings.is_live)

注意点：
- 多くの関数は「Look-ahead bias」を防ぐために内部で date.today() を直接参照しない設計になっています。target_date を明示的に与えて使うことを推奨します（バックテスト時に重要）。
- OpenAI の呼び出しはリトライや JSON パース堅牢化を行っていますが、API レート・課金に注意してください。
- jquants_client はリクエストレート制御（120 req/min）とトークンの自動リフレッシュを備えています。

---

## ディレクトリ構成（主なファイル）

src/kabusys/
- __init__.py — パッケージ定義（version）
- config.py — 環境変数・.env 自動ロード・settings オブジェクト
- ai/
  - __init__.py — ai パブリック API（score_news をエクスポート）
  - news_nlp.py — ニュースセンチメント（score_news）と関連ユーティリティ
  - regime_detector.py — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch / save 関数）
  - pipeline.py — ETL pipeline（run_daily_etl 等）
  - etl.py — ETLResult 再エクスポート
  - calendar_management.py — マーケットカレンダー管理（is_trading_day 等）
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - quality.py — データ品質チェック
  - audit.py — 監査ログ DDL と初期化ユーティリティ
  - news_collector.py — RSS 収集・前処理
- research/
  - __init__.py — 研究向け API エクスポート
  - factor_research.py — momentum / value / volatility 等のファクター
  - feature_exploration.py — 将来リターン計算 / IC / 統計サマリー

その他：
- settings や .env 自動ロードは kabusys.config が担います。プロジェクトルート（.git または pyproject.toml があるディレクトリ）から .env/.env.local が読み込まれます。

---

## 開発者向け情報 / 注意事項

- 自動 .env ロードはプロジェクトルートを __file__ の親から探索して行います。テストや特別な状況で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB に対する一括書き込みでは executemany を利用しており、バージョン差異（例: 空リストの executemany の取り扱い）に注意した実装になっています。
- OpenAI 呼び出しは JSON Mode を利用し厳密な JSON を期待しますが、実世界では余計なテキストが混ざるケースも考慮して復元ロジックを用意しています。
- 外部ネットワークアクセスを行う箇所（RSS、J-Quants、OpenAI）ではタイムアウト、リトライ、リトライバックオフ、SSRF 対策などの安全策を入れていますが、運用時はプロキシやネットワーク制限、API レート/課金の観点から監視を行ってください。

---

必要であれば、README に以下を追加できます：
- 各テーブル（raw_prices, raw_financials, raw_news, ai_scores, market_regime, market_calendar, signal_events 等）のスキーマ一覧
- 実運用のデプロイ手順（Systemd / コンテナ化 / スケジューラ設定 など）
- ロギング・モニタリング設定例（Slack 通知フローなど）

補足や特定セクションの追記をご希望であれば教えてください。