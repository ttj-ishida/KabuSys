# KabuSys

日本株向けのデータ基盤・研究・AI支援を備えた自動売買システムのライブラリ群です。  
ETL（J-Quants連携）・ニュース収集/前処理・AI（ニュースセンチメント/市場レジーム判定）・リサーチ用のファクタ計算・監査ログなどを含みます。

---

## プロジェクト概要

KabuSys は日本株運用のための以下を目的としたモジュール群を提供します。

- J-Quants API を用いた株価/財務/カレンダーの差分ETL（DuckDB保存・冪等処理）
- RSSベースのニュース収集と前処理（SSRF対策・トラッキング除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄毎）とマクロセンチメントを組み合わせた市場レジーム判定
- 研究用のファクター計算／特徴量探索／統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ初期化ユーティリティ
- 環境変数ベースの設定管理（.env 自動ロード）

設計方針として、ルックアヘッドバイアス防止、冪等性、堅牢なエラーハンドリング（フェイルセーフ）、テスト性を重視しています。

---

## 主な機能一覧

- data
  - jquants_client: J-Quants API クライアント（レート制御・リトライ・ページネーション・DuckDB保存）
  - pipeline: 日次 ETL パイプライン（run_daily_etl 等）
  - news_collector: RSS から raw_news 収集（SSRF対策、正規化、前処理）
  - calendar_management: JPX カレンダー管理・営業日判定
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログテーブル定義・初期化（init_audit_schema / init_audit_db）
  - stats: Zスコア正規化などの統計ユーティリティ
- ai
  - news_nlp.score_news: ニュースをまとめて LLM に投げ、銘柄ごとの ai_score を ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF 1321 の MA 偏差とマクロセンチメントを合成して market_regime を生成
- research
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算
  - feature_exploration: 将来リターン計算、IC（スピアマン）計算、統計サマリー、ランク変換
- config
  - 環境変数の自動読み込み（プロジェクトルートの .env / .env.local）と Settings API

---

## 必要要件

- Python 3.10+
- 主なライブラリ（例）:
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ以外の依存はプロジェクト側で requirements.txt を用意している想定です。実行環境に合わせてインストールしてください。

例:
    python -m venv .venv
    source .venv/bin/activate
    pip install duckdb openai defusedxml

（プロジェクトに requirements.txt があればそれを使用してください）

---

## 環境変数（必須 / 推奨）

必須（Settings から参照される主要なキー）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL用）
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注等用）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（ai モジュール実行時。関数に api_key を渡すことも可能）

オプション:
- KABU_API_BASE_URL — kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — デフォルトの DuckDB パス（data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（data/monitoring.db）
- KABUSYS_ENV — 環境 (development | paper_trading | live)（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）

.env の自動ロード:
- パッケージ import 時にプロジェクトルート（.git または pyproject.toml を探索）を基に .env / .env.local を自動で読み込みます。
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で利用）。

簡易 .env 例:
    JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
    OPENAI_API_KEY=sk-...
    KABU_API_PASSWORD=your_kabu_password
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C01234567
    DUCKDB_PATH=data/kabusys.duckdb
    KABUSYS_ENV=development

---

## セットアップ手順

1. リポジトリをクローン
    git clone <repo-url>
    cd <repo>

2. 仮想環境を作成・有効化（推奨）
    python -m venv .venv
    source .venv/bin/activate

3. 依存をインストール
    pip install -r requirements.txt
   または必要なパッケージを個別インストール:
    pip install duckdb openai defusedxml

4. 環境変数設定
   プロジェクトルートに .env を作成して上記の必須キーを設定します。
   開発時は .env.local を用いてローカル上書きも可能です。

5. DuckDB / 監査DB 初期化（任意）
   監査スキーマを初期化する例:
    python -c "import duckdb; from kabusys.data.audit import init_audit_db; init_audit_db('data/audit.duckdb')"

6. （任意）ETL 実行のために J-Quants トークンを準備する:
   settings.jquants_refresh_token が必要です（.env に設定しておくか、直接関数に渡す）。

---

## 使い方（簡単なコード例）

- DuckDB 接続を作成して日次 ETL を実行する:
    from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date(2026,3,20))
    print(result.to_dict())

- ニュースセンチメントをスコアリングして ai_scores に保存:
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    written = score_news(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY は環境変数か api_key 引数で指定
    print("written:", written)

- 市場レジームを判定して market_regime に保存:
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,3,20))

- ファクター計算（研究用途）:
    from datetime import date
    import duckdb
    from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

    conn = duckdb.connect("data/kabusys.duckdb")
    mom = calc_momentum(conn, date(2026,3,20))
    val = calc_value(conn, date(2026,3,20))
    vol = calc_volatility(conn, date(2026,3,20))

- RSS フィード取得（ニュース収集の一部）:
    from kabusys.data.news_collector import fetch_rss
    articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
    for a in articles:
        print(a["id"], a["title"], a["datetime"])

注意:
- AI モジュールは OpenAI API を呼び出します。API キーは環境変数 OPENAI_API_KEY か、関数の api_key 引数で渡してください。
- ETL / データ処理は DuckDB のスキーマ（raw_prices / raw_financials / raw_news 等）が整っていることを前提とします。スキーマの初期化はプロジェクト側で提供されているスクリプトを利用してください（本コードベース内に schema 初期化ユーティリティが同梱されている想定）。

---

## テスト／デバッグのヒント

- 環境変数の自動ロードを無効化:
    export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  単体テストで .env の自動ロードを避けたい場合に有効です。

- OpenAI 呼び出しのモック:
  ai モジュール内部の _call_openai_api 関数を unittest.mock.patch などで差し替えることで外部APIコールを模擬できます。

- DuckDB の executemany に空リストを渡すとエラーになるバージョンの挙動を考慮して、コード中では空チェックが入っています。手動でテストする際もパラメータが空でないことを確認してください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
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
  - news_collector.py
  - calendar_management.py
  - quality.py
  - stats.py
  - audit.py
  - (その他: schema 初期化ユーティリティ等)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- monitoring/ (README に含める想定のモジュール群がある場合)

各モジュールの概要:
- config.py: 環境変数の読み込み・Settings API（自動 .env 読込）
- data/jquants_client.py: J-Quants API 連携 & DuckDB 保存ロジック
- data/pipeline.py: ETL の高レベル実行（run_daily_etl 等）
- data/news_collector.py: RSS 収集・正規化・保存補助
- data/calendar_management.py: JPX カレンダー管理・営業日ロジック
- data/quality.py: データ品質チェック
- data/audit.py: 監査ログテーブル DDL と初期化
- ai/news_nlp.py: ニュースを LLM で銘柄別センチメント化
- ai/regime_detector.py: ETF + マクロニュースで市場レジーム判定
- research/*: ファクター計算・統計分析ユーティリティ

---

## ライセンス / コントリビューション

（ここにプロジェクトのライセンスや貢献方法を記載してください。例: MIT, CONTRIBUTING.md へのリンク等）

---

README は主要な利用パターンを簡潔にまとめたものです。詳細な API の仕様やスキーマ、運用手順（プロダクションでの ETL スケジューリング、監視、発注フロー等）は別途ドキュメント（Design / DataPlatform / Strategy docs）を参照してください。必要であれば README に追記・サンプルスクリプトや schema 初期化手順を追加できます。