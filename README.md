# KabuSys

日本株の自動売買・リサーチ基盤ライブラリ（KabuSys）の README。  
このリポジトリはデータ取得（J-Quants）、ETL、ニュース NLP（OpenAI）、リサーチ用ファクター計算、監査ログ（DuckDB）などを備えたモジュール群から構成されています。

---

## プロジェクト概要

KabuSys は日本株向けのデータプラットフォーム兼研究・自動売買支援ライブラリです。主な目的は以下です。

- J-Quants API から株価・財務・カレンダー等を差分取得して DuckDB に保存する ETL パイプライン
- RSS ニュース収集と OpenAI を用いた記事／マクロセンチメント評価（銘柄別 ai_score、日次の市場レジーム判定）
- 研究用ユーティリティ（モメンタム／バリュー／ボラティリティ等のファクター計算、将来リターン／IC 計算）
- データ品質チェック、監査ログ（signal → order_request → execution のトレーサビリティ）
- kabuステーション API 経由の発注（実装モジュール群の公開）および監視用ユーティリティ

設計上のポイント:
- ルックアヘッドバイアスを避ける（関数内で datetime.today()/date.today() を安易に参照しない）
- API 呼び出しにはリトライとバックオフを導入（J-Quants, OpenAI）
- DuckDB を中心とした冪等保存（ON CONFLICT / DELETE→INSERT の方針）
- セキュリティ：RSS収集での SSRF 回避、XML の安全パース等

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート探索）
  - 必須設定のプロパティ取得（settings オブジェクト）
- データ取得（jquants_client）
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, fetch_listed_info
  - 保存関数: save_daily_quotes, save_financial_statements, save_market_calendar（DuckDB へ冪等保存）
- ETL（pipeline）
  - run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl（日次一括）
  - ETLResult による実行結果管理・品質チェック連携
- ニュース処理（news_collector, news_nlp）
  - RSS フィード収集・前処理・raw_news 保存
  - OpenAI による銘柄別センチメントスコア（score_news）
  - 市場マクロセンチメントと ETF(1321) MA を合成した日次レジーム判定（score_regime）
- 研究（research）
  - calc_momentum, calc_value, calc_volatility
  - calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize
- カレンダー管理（calendar_management）
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- データ品質チェック（quality）
  - 欠損、スパイク、重複、日付不整合チェック（run_all_checks）
- 監査ログ（audit）
  - 監査用テーブル定義・初期化（init_audit_schema, init_audit_db）
- ユーティリティ（data.stats など）

---

## セットアップ手順

1. Python 環境の準備
   - Python 3.10 以上を推奨（型注釈で union | を使用）
   - 仮想環境を作成することを推奨
     - 例: python -m venv .venv && source .venv/bin/activate

2. 依存ライブラリのインストール
   - 要件ファイルがある場合は `pip install -r requirements.txt` を推奨します。
   - 主な外部依存（少なくとも次をインストールしてください）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

3. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env`（およびローカル上書き用の .env.local）を配置します。自動ロードはデフォルトで有効です（無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

   必須の環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - SLACK_BOT_TOKEN: Slack 通知を使う場合の Bot トークン
   - SLACK_CHANNEL_ID: 通知先チャンネル ID
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注機能を使う場合）
   - OPENAI_API_KEY: OpenAI を使う場合（score_news/score_regime に必要）

   任意（デフォルト値あり）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: DEBUG/INFO/...
   - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると .env 自動ロードを無効化
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）

   .env の解析はシェル風の export KEY=val、クォート、コメントをサポートします。

4. データベース準備（監査ログなど）
   - 監査用 DB を初期化する例:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")

---

## 使い方（主要な例）

以降は最小限の Python スニペット例です。実行前に必要な環境変数を設定してください（特に OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN）。

- DuckDB 接続を作る（デフォルト path は settings.duckdb_path）:
  - import duckdb
  - from kabusys.config import settings
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する:
  - from kabusys.data.pipeline import run_daily_etl
  - from datetime import date
  - result = run_daily_etl(conn, target_date=date(2026,3,20))
  - print(result.to_dict())

- ニュースのスコアリング（OpenAI が必要）:
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - count = score_news(conn, target_date=date(2026,3,20))
  - print(f"scored {count} codes")

  - 注意: API キーを関数引数で渡すことも可能: score_news(conn, d, api_key="XXX")

- 市場レジームの判定:
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - score_regime(conn, target_date=date(2026,3,20))  # OpenAI API キーは環境変数 OPENAI_API_KEY か api_key 引数

- 研究用ファクター計算:
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  - momentum = calc_momentum(conn, target_date=date(2026,3,20))
  - volatility = calc_volatility(conn, target_date=date(2026,3,20))

- カレンダー関連:
  - from kabusys.data.calendar_management import is_trading_day, next_trading_day
  - is_trading = is_trading_day(conn, date(2026,3,20))
  - next_day = next_trading_day(conn, date(2026,3,20))

- 監査テーブル初期化（既存接続に適用）:
  - from kabusys.data.audit import init_audit_schema
  - init_audit_schema(conn, transactional=True)

- デバッグ / ログレベル設定:
  - LOG_LEVEL 環境変数でログレベルを指定（例: LOG_LEVEL=DEBUG）

---

## 注意点 / 運用上の要点

- OpenAI 呼び出し
  - score_news / score_regime は OpenAI API（gpt-4o-mini を想定）を使用します。API キーは環境変数 OPENAI_API_KEY または関数引数で渡してください。
  - API 失敗時はフェイルセーフとして 0.0 にフォールバックする動作が組み込まれています（完全失敗を避けるため）。

- 自動 .env ロード
  - パッケージ初期化時にプロジェクトルートを探索して `.env` / `.env.local` を自動読み込みします。テスト等で無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- ルックアヘッドバイアス対策
  - コード内の ETL / スコアリング / ファクター計算は基本的に target_date を引数に取る形式で、内部で現在時刻を直接参照しないように設計されています。バックテスト用途では target_date を使って時刻制約を厳密に行ってください。

- セキュリティ
  - RSS 収集では SSRF 対策（リダイレクト検査・プライベートアドレス拒否）や defusedxml による XML パース保護を実施しています。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py         — ニュース NLP（score_news, calc_news_window）
    - regime_detector.py  — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（fetch / save）
    - pipeline.py         — ETL パイプライン（run_daily_etl 等）
    - etl.py              — ETLResult の再エクスポート
    - stats.py            — 統計ユーティリティ（zscore_normalize）
    - quality.py          — 品質チェックモジュール
    - calendar_management.py — 市場カレンダー管理
    - news_collector.py   — RSS 収集・前処理
    - audit.py            — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py  — Momentum/Value/Volatility 等
    - feature_exploration.py — 将来リターン / IC / サマリー
  - ai/、research/、data/ に関するテストユーティリティや補助関数は各モジュール内に記載

（上記はコードベースから抽出した主要ファイル一覧です。実際のプロジェクトルートには pyproject.toml / requirements.txt などが存在することが想定されます。）

---

## よくある操作のコマンド例

- 仮想環境作成 + 依存インストール（例）
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install duckdb openai defusedxml

- 簡易的に ETL を手動実行する Python スクリプト:
  - from datetime import date
    import duckdb
    from kabusys.config import settings
    from kabusys.data.pipeline import run_daily_etl
    conn = duckdb.connect(str(settings.duckdb_path))
    res = run_daily_etl(conn, target_date=date.today())
    print(res.to_dict())

---

## 開発・テストについて

- モジュールの多くは外部 API 依存（OpenAI / J-Quants / RSS）を含むため、単体テストでは HTTP 通信や外部呼び出しをモックすることを推奨します。実装内でも _call_openai_api や _urlopen などをモック可能な設計になっています。
- 自動 .env 読み込みはテストで挙動を変えたい場合 KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。

---

必要であれば README にサンプル .env.example、requirements.txt の候補、CI 実行例（ETL のスケジューリングやバックテスト連携）などの追記も可能です。どの情報を追加しますか？