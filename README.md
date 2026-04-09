# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム向けライブラリ群です。データ収集（J-Quants / RSS）、ETL、データ品質チェック、ニュース NLP（OpenAI）、市場レジーム判定、ファクター計算・リサーチ、監査ログなど、アルゴリズム取引基盤の主要コンポーネントを提供します。

バージョン: 0.1.0

## 主な特徴（概要）

- データ取得・ETL
  - J-Quants API から株価日足・財務情報・市場カレンダーを差分取得（ページネーション対応）
  - DuckDB に冪等（ON CONFLICT DO UPDATE）で保存
  - 日次 ETL パイプライン（run_daily_etl）を提供
- データ品質管理
  - 欠損、スパイク（急騰/急落）、重複、日付不整合などのチェック機能（quality モジュール）
- ニュース収集と NLP
  - RSS 取得・前処理（SSRF 対策、トラッキングパラメータ除去、URL 正規化）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント（ai.news_nlp.score_news）
  - マクロニュースと MA 乖離を合成した市場レジーム判定（ai.regime_detector.score_regime）
- リサーチ / ファクター
  - Momentum / Volatility / Value 等のファクター計算（research.factor_research）
  - 将来リターン、IC（Information Coefficient）、統計サマリー等（research.feature_exploration）
  - z-score 正規化ユーティリティ（data.stats）
- 監査ログ（Audit）
  - signal → order_request → execution までのトレーサビリティを保持する監査テーブルの初期化・管理（data.audit）
- 設定管理
  - .env / .env.local / OS 環境変数から設定を自動読み込み（config.Settings）
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能

## 機能一覧（モジュール別）

- kabusys.config
  - 環境変数のパース、自動ロード、Settings クラス（J-Quants, kabu API, OpenAI, DB パス 等）
- kabusys.data
  - jquants_client: API 呼び出し、保存関数（save_daily_quotes 等）
  - pipeline: ETL のメイン処理（run_daily_etl 等）と ETLResult
  - quality: データ品質チェック（missing / spike / duplicates / date_consistency）
  - news_collector: RSS 収集・前処理
  - calendar_management: 市場カレンダー管理・営業日ロジック
  - audit: 監査テーブルの DDL / 初期化ユーティリティ
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: ニュースを OpenAI に投げて銘柄別スコアを生成し ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF（1321）200 日 MA 乖離とマクロニュースセンチメントを合成して market_regime に保存
- kabusys.research
  - factor_research: calc_momentum / calc_volatility / calc_value
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- ほか: execution / monitoring（実行・監視関連のインターフェース、パッケージ公開あり）

## セットアップ手順

前提: Python 3.10+（型ヒントで | が使われているため 3.10 以上を推奨）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・アクティベート（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - 必要最低限（例）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   ※ 実プロジェクトでは requirements.txt / pyproject.toml を用意している想定です。
   ローカルで編集したパッケージを開発モードでインストールする:
   - pip install -e .

4. 環境変数 (.env)
   - プロジェクトルート（.git または pyproject.toml を基準）に `.env` / `.env.local` を配置すると自動読み込みされます。
   - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須（または重要）な環境変数例:
- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu API のパスワード（利用する場合）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector を使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（任意）
- LOG_LEVEL / KABUSYS_ENV 等も利用可能

サンプル .env（必要に応じて調整してください）:
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- OPENAI_API_KEY=sk-xxxx...
- KABU_API_PASSWORD=your_kabu_password
- DUCKDB_PATH=data/kabusys.duckdb
- LOG_LEVEL=INFO

## 使い方（主なユースケース）

以下は簡単な Python スニペット例です。実行時は仮想環境を有効にし、環境変数を設定してください。

- DuckDB 接続の用意（デフォルト path は settings.duckdb_path）:
  - from pathlib import Path
    import duckdb
    from kabusys.config import settings
    conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する:
  - from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    # conn は上で作った DuckDB 接続
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニューススコア（銘柄別）を生成する:
  - from datetime import date
    from kabusys.ai.news_nlp import score_news
    count = score_news(conn, target_date=date(2026, 3, 20))
    print(f"scored {count} codes")

- 市場レジーム判定を実行する:
  - from datetime import date
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026, 3, 20))

- 監査 DB 初期化（監査専用 DB を別ファイルに作る場合）:
  - from kabusys.data.audit import init_audit_db
    audit_conn = init_audit_db("data/audit.duckdb")
    # 以降 audit_conn を発注／監査ログ保存で利用

- ファクター計算 / リサーチ:
  - from datetime import date
    from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
    momentum = calc_momentum(conn, target_date=date(2026,3,20))
    volatility = calc_volatility(conn, target_date=date(2026,3,20))

- 設定参照:
  - from kabusys.config import settings
    print(settings.paper_fill_mode)
    print(settings.is_live)

注意点:
- LLM（OpenAI）に関する関数は api_key 引数を受け取るか、環境変数 OPENAI_API_KEY を参照します。
- LLM 呼び出しは冪等性やエラー処理を備えていますが、API キーやクレジットの消費に注意してください。
- ETL / データ保存処理は DuckDB を前提に実装されています。実運用ではバックアップ・スナップショット戦略を検討してください。

## ディレクトリ構成（主要ファイル）

プロジェクトの主要なファイル群（src/kabusys 配下）を抜粋して示します:

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
    - etl.py (ETLResult re-export)
    - news_collector.py
    - quality.py
    - calendar_management.py
    - audit.py
    - stats.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/__init__.py
  - data/__init__.py

（上記以外に execution, monitoring 等のパッケージが公開インターフェースに含まれますが、ここでは主要なデータ／AI／リサーチ系を中心に抜粋しています。）

## 実装・設計上の注意点

- Look-ahead bias の回避を重視
  - 日付計算や DB クエリは target_date 未満／以前のデータのみを参照するなど、バックテストでの情報漏洩を防ぐ設計になっています。
- API 呼び出しはリトライ・バックオフ・レート制限を実装
  - J-Quants クライアントは 120 req/min のレート制限に対応する RateLimiter を実装しています。
  - OpenAI 呼び出しは 5xx / ネットワーク障害に対するリトライを備えています。
- データ保存は冪等（ON CONFLICT）を意識
  - ETL は差分更新とバックフィルを組み合わせ、DB への保存は上書き（ON CONFLICT DO UPDATE）で重複や再実行に耐性があります。
- セキュリティ考慮
  - news_collector は SSRF 対策、XML パーサの安全化（defusedxml）、受信サイズ制限などを実装しています。

## 開発・テスト

- 各モジュールは依存注入や内部関数差し替え（例: _call_openai_api のモック）でテストしやすい設計です。
- 自動ロードされる .env の振る舞いは config._find_project_root / _load_env_file により実現されています。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数を使うことで自動ロードを抑止できます。

---

この README はコードベースからの抽出を元に作成しています。実際の運用・導入時は pyproject.toml / requirements.txt / CI 設定、運用ドキュメント（運用手順、監視アラート、バックアップ方針、API クォータ管理など）を合わせて整備してください。質問や追加ドキュメントの要望があれば教えてください。