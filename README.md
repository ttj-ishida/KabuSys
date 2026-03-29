# KabuSys

日本株向け自動売買・データプラットフォームライブラリ（KabuSys）。  
ETL、データ品質チェック、ニュース収集・NLP、AIベースの市場レジーム判定、リサーチ用ファクター計算、監査ログ（トレーサビリティ）等のユーティリティを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムのための内部ライブラリ群です。主な目的は次のとおりです。

- J-Quants API を用いた株価・財務・カレンダー等の差分ETL
- DuckDB を用いたローカルデータストア管理
- ニュース収集（RSS）と LLM（OpenAI）を用いたセンチメント解析
- 市場レジーム判定（マクロニュース + ETF MA200乖離）
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と研究補助ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 発注〜約定までの監査ログ（トレーサビリティ）スキーマと初期化

設計上の特徴:
- Look-ahead バイアス対策（内部で date.today() / datetime.today() を不用意に参照しない等）
- API 呼び出しにリトライ / レートリミットなどの堅牢性処理を実装
- DuckDB へ冪等（idempotent）に保存（ON CONFLICT 等を使用）
- ニュース収集で SSRF / XML 攻撃対策を実装（URL検証・defusedxml 等）

---

## 主な機能一覧

- ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
- データ品質チェック
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks（kabusys.data.quality）
- ニュース収集
  - fetch_rss / news 前処理 / 保存ロジック（kabusys.data.news_collector）
- AI ニュース NLP
  - score_news（kabusys.ai.news_nlp）: OpenAI を使った銘柄別センチメント集約
- 市場レジーム判定
  - score_regime（kabusys.ai.regime_detector）: ETF(1321)のMA200乖離 + マクロニュースで判定
- リサーチ / ファクター計算
  - calc_momentum / calc_value / calc_volatility（kabusys.research.factor_research）
  - calc_forward_returns / calc_ic / factor_summary / rank（kabusys.research.feature_exploration）
- データアクセス / J-Quants クライアント
  - fetch_* / save_*（kabusys.data.jquants_client）
- カレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job（kabusys.data.calendar_management）
- 監査ログ（Audit）
  - init_audit_schema / init_audit_db（kabusys.data.audit）
- 汎用ユーティリティ
  - zscore_normalize（kabusys.data.stats）、設定管理（kabusys.config.Settings）

---

## セットアップ手順

前提:
- Python 3.10 以上（PEP 604 の union 表記や型ヒントを使用しているため）
- ネットワーク経由の API（J-Quants / OpenAI）を使用するため、それらの API キーが必要

1. リポジトリをクローン／コピー
   - （パッケージ化されている場合は pip インストールでも可）

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要なパッケージをインストール
   - ここでは代表的な依存を示します:
     - pip install duckdb openai defusedxml
   - 実プロジェクトでは requirements.txt / pyproject.toml を参照してください

4. 環境変数（.env）を用意
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（kabusys.config が自動ロード）
   - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセット

5. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN: Slack ボットトークン（必須）
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime を使う場合）
   - 任意 / デフォルト:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（デフォルト）

例 .env（最小）
- .env.example のように作成してください（実際の値は安全に管理すること）:
  - JQUANTS_REFRESH_TOKEN=xxxx
  - OPENAI_API_KEY=xxxx
  - KABU_API_PASSWORD=xxxx
  - SLACK_BOT_TOKEN=xoxb-...
  - SLACK_CHANNEL_ID=C01234567

---

## 使い方（基本例）

※ すべての例は仮想環境内で実行してください。DuckDB はファイルを自動作成します。

1. DuckDB 接続を用意して日次 ETL を実行する
   - Python REPL / スクリプト例:
     - from datetime import date
       import duckdb
       from kabusys.data.pipeline import run_daily_etl
       conn = duckdb.connect("data/kabusys.duckdb")
       res = run_daily_etl(conn, target_date=date(2026,3,20))
       print(res.to_dict())

2. ニュースのセンチメント（銘柄別）を計算する
   - from datetime import date
     import duckdb
     from kabusys.ai.news_nlp import score_news
     conn = duckdb.connect("data/kabusys.duckdb")
     n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # env OPENAI_API_KEY が使われる
     print("written:", n_written)

3. 市場レジーム判定を実行する
   - from datetime import date
     import duckdb
     from kabusys.ai.regime_detector import score_regime
     conn = duckdb.connect("data/kabusys.duckdb")
     score_regime(conn, target_date=date(2026,3,20), api_key=None)  # OPENAI_API_KEY を使用

4. 監査ログ用 DB を初期化する
   - from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     # これで監査テーブルが作成されます

5. カレンダー関連ユーティリティ例
   - from datetime import date
     import duckdb
     from kabusys.data.calendar_management import is_trading_day, next_trading_day
     conn = duckdb.connect("data/kabusys.duckdb")
     print(is_trading_day(conn, date(2026,3,20)))
     print(next_trading_day(conn, date(2026,3,20)))

警告:
- OpenAI / J-Quants の API 呼び出しはコストやレート制限があるため、キー・呼び出し回数を管理してください。
- 本ライブラリはバックテスト用のデータ取得／前処理等を含みますが、本番の発注ロジックと組み合わせる場合は必ず追加のリスク管理・検証を行ってください。

---

## 設定管理について（自動 .env 読み込み）

- kabusys.config モジュールは自動的にプロジェクトルート（.git または pyproject.toml を探索）を見つけ、.env と .env.local を次の優先度で読み込みます:
  - OS 環境変数 > .env.local > .env
- .env.local は .env の上書き用（ローカル機密やテスト用）
- 自動読み込みを無効にする場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- 必須取得関数は _require を通し未設定時は ValueError を発生させます

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースの LLM センチメント解析（score_news）
    - regime_detector.py
      - ETF MA200 とマクロニュースで市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（fetch/save、認証、レート制御）
    - pipeline.py
      - ETL パイプライン（run_daily_etl 等）と ETLResult
    - etl.py
      - ETLResult の再エクスポート
    - calendar_management.py
      - マーケットカレンダー管理・営業日判定
    - news_collector.py
      - RSS フィード取得と前処理（SSRF/サイズ制限/defusedxml 対策）
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py
      - 監査ログ（signal_events, order_requests, executions）のスキーマ定義・初期化
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py
      - モメンタム / バリュー / ボラティリティ等の計算
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリー、ランク変換など

各モジュールにはドキュメント文字列（docstring）で設計方針・処理フロー・重要な注意点が書かれています。実運用ではこれらを参照してください。

---

## 注意事項 / 運用上のアドバイス

- データの時刻解釈（UTC / JST）に注意してください。news_collector は raw_news.datetime を UTC naive で扱います。ETL と分析処理はソースの仕様に合わせて調整してください。
- OpenAI 呼び出しはレスポンスの検証（JSON Mode による厳密パース）とリトライ・クリッピング処理を組み込んでいますが、モデルの出力変化や API 仕様変更に応じた追加検証が必要です。
- DuckDB へのバルク書き込みでは executemany の挙動（空リストの扱い等）に注意しています。DuckDB のバージョンに依存するため、運用環境のバージョン管理を推奨します。
- 発注系の監査ログは「削除しない前提」です。監査トレースの保全方針を設計段階で明確にしてください。

---

## 参考

- モジュール内 docstring に機能詳細・設計方針・処理フロー・パラメータ仕様が記載されています。各機能を利用する前に該当モジュールのドキュメント文字列を参照してください。

---

必要であれば README にサンプル .env.example、requirements.txt、簡単な CLI の使い方（ユースケース別スクリプト例）を追加します。どの情報をさらに詳しく追記しますか？