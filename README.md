# KabuSys

日本株向けの自動売買・データ基盤ライブラリ群です。データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集・NLP、研究（ファクター計算）、市場レジーム判定、監査ログなどを含むモジュール構成になっています。

---

## 概要

KabuSys は日本株の自動売買システム／データプラットフォームのコア機能を提供する Python パッケージです。主な目的は以下です。

- J-Quants API から株価・財務・市場カレンダー等の差分取得と DuckDB への保存（ETL）
- ニュース収集（RSS）と LLM を用いた記事センチメント分析（銘柄別 ai_score 作成）
- 日次 ETL、データ品質チェック、監査ログ（注文→約定のトレーサビリティ）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC 計算 等）
- 市場レジーム判定（ETF MA と マクロニュースの LLM スコアの合成）

設計上の特徴：
- Look-ahead バイアスを防ぐ設計（内部で現在日時に無条件依存しない）
- DuckDB を中心としたローカル DB 利用
- 冪等（idempotent）な DB 保存（ON CONFLICT / DELETE→INSERT による置換）
- 外部 API 呼び出しはリトライ・バックオフ・レート制御を組み込み

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save / token refresh / rate limiter）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / calendar_update_job）
  - ニュース収集（RSS fetch + 前処理 + SSRF 対策）
  - データ品質チェック（欠損、重複、スパイク、日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore 正規化）
- ai
  - ニュース NLP（score_news）: gpt-4o-mini を使った銘柄別センチメントスコア算出
  - 市場レジーム判定（score_regime）: ETF 1321 の MA とマクロニュース LLM でレジーム判定
- research
  - ファクター計算（momentum / value / volatility 等）
  - 特徴量探索（forward returns, IC, factor summary, rank）
- config
  - 環境変数管理（.env 自動読み込み、Settings オブジェクト経由で安全に参照）

---

## セットアップ手順

前提
- Python 3.10+（本コードは | 型などを使用しているため 3.10 以上を推奨）
- ネットワークアクセス（J-Quants / OpenAI 等）

1. リポジトリをクローン
   - git clone ... （プロジェクトルートに .git または pyproject.toml があることを想定）

2. 仮想環境を作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 必須パッケージ（代表例）:
     - duckdb
     - openai
     - defusedxml
   - pip install duckdb openai defusedxml
   - 開発時は pip install -e . を使ってパッケージを編集可能インストール

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください）

4. 環境変数（.env）を準備
   - プロジェクトルートの `.env` または `.env.local` に必要な設定を記述できます。
   - 自動読み込み: config モジュールはプロジェクトルート（.git または pyproject.toml）を基準に `.env` / `.env.local` を自動読み込みします。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須の環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード
- SLACK_BOT_TOKEN: Slack Bot トークン（通知用）
- SLACK_CHANNEL_ID: Slack チャンネル ID
- OPENAI_API_KEY: OpenAI API キー（ai.score_news / regime で使用）

オプション（デフォルト付き）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト "http://localhost:18080/kabusapi"）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト "data/kabusys.duckdb"）
- SQLITE_PATH: SQLite（モニタリング）パス（デフォルト "data/monitoring.db"）
- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト "development"）
- LOG_LEVEL: "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"（デフォルト "INFO"）

例 (.env)
    JQUANTS_REFRESH_TOKEN=xxxx
    OPENAI_API_KEY=sk-xxxx
    KABU_API_PASSWORD=your_kabu_pwd
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C01234567
    DUCKDB_PATH=data/kabusys.duckdb
    KABUSYS_ENV=development

---

## 使い方（簡単な例）

- DuckDB 接続を用意して ETL を実行する（日次 ETL）

    from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_daily_etl
    from kabusys.config import settings

    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニュース NLP（銘柄別スコアを ai_scores テーブルに書き込む）

    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    from kabusys.config import settings

    conn = duckdb.connect(str(settings.duckdb_path))
    n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key None → OPENAI_API_KEY を利用

- 市場レジーム判定

    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime
    from kabusys.config import settings

    conn = duckdb.connect(str(settings.duckdb_path))
    score_regime(conn, target_date=date(2026,3,20), api_key=None)

- 監査ログ DB 初期化（監査専用 DB を作る）

    from kabusys.data.audit import init_audit_db
    from kabusys.config import settings

    conn = init_audit_db(settings.duckdb_path)  # ":memory:" も可

- ニュース RSS をフェッチする（保存ロジックは ETL 側と組み合わせる）

    from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
    articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")

- 設定値参照

    from kabusys.config import settings
    print(settings.duckdb_path)
    print(settings.is_live)

- 研究用ユーティリティ（例: モメンタム計算）

    from kabusys.research.factor_research import calc_momentum
    result = calc_momentum(conn, target_date=date(2026,3,20))

注意:
- OpenAI 呼び出し（news_nlp / regime_detector）は API 呼び出し回数やレスポンスの仕様に依存します。テストでは該当関数をモックすることが想定されています。
- ETL / DB 書き込みは冪等設計ですが、本番運用前にテスト DB で動作確認してください。

---

## ディレクトリ構成（抜粋）

プロジェクトは src/kabusys 以下にモジュールを配置しています。主要ファイル：

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数 / Settings
  - ai/
    - __init__.py
    - news_nlp.py                   -- ニュースセンチメント（OpenAI）
    - regime_detector.py            -- 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py             -- J-Quants API クライアント（fetch / save）
    - pipeline.py                   -- ETL パイプラインと ETLResult
    - etl.py                        -- ETL 型の再公開（ETLResult）
    - calendar_management.py        -- 市場カレンダー管理
    - news_collector.py             -- RSS 収集・前処理
    - stats.py                      -- 統計ユーティリティ（zscore）
    - quality.py                    -- データ品質チェック
    - audit.py                      -- 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py            -- モメンタム / バリュー / ボラティリティ
    - feature_exploration.py        -- forward returns, IC, summary, rank
  - research/（上記ファイル群）
  - その他（strategy / execution / monitoring の将来的なモジュールに対応）

---

## 運用上の注意

- 環境変数の自動読み込み:
  - config モジュールはプロジェクトルートの `.env` → `.env.local` の順で自動読み込みします（OS 環境変数を優先）。
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時などに便利です）。
- OpenAI / J-Quants / kabu API 等の外部 API キーは厳重に管理してください（無闇なログ出力やコミットを避ける）。
- DuckDB スキーマや監査テーブルは init_audit_schema / init_audit_db を用いて事前に初期化して運用してください。
- ETL は部分失敗許容で各ステップ独立にエラーハンドリングされます。結果は ETLResult に格納されますのでログ監視やアラートに活用してください。
- 本リポジトリのコードはバックテスト・本番発注ロジックとは切り離す設計です。実際の発注や本番口座接続時は十分な検証と安全策（サンドボックス・paper_trading 環境）を実施してください。

---

## 参考・拡張ポイント

- strategy / execution / monitoring: README に記載のとおりパッケージ化されており、戦略のシグナル生成・注文発行・モニタリング機能の実装を容易に追加できます。
- テスト: ai モジュールの OpenAI 呼び出し部分はテスト用に差し替え（mock）しやすい構成です。
- 性能: DuckDB をコアに据えており、大量データをローカルで高速に集計可能です。必要に応じてパーティショニングやインデックスの追加を検討してください。

---

もし README に追加してほしい具体的な項目（例: CI 設定、詳しいスキーマ定義、実行例のスクリーンショット、requirements.txt 内容など）があれば教えてください。必要に応じて追記・整形します。