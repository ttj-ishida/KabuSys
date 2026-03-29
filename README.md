# KabuSys

日本株向け自動売買／データ基盤ライブラリ（KabuSys）のドキュメントです。  
このリポジトリはデータ収集・ETL、データ品質チェック、ニュースNLP（LLMによるセンチメント）、市場レジーム判定、研究用ファクター計算、監査ログなどのモジュール群を提供します。

## プロジェクト概要
KabuSys は以下を目的とした Python パッケージです。

- J-Quants API からの株価／財務／マーケットカレンダー取得と DuckDB への差分保存（ETL）
- ニュース RSS の収集と前処理、銘柄紐付け
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価（銘柄別 ai_score、マクロセンチメント）
- ETF とマクロセンチメントを合成した市場レジーム判定（bull/neutral/bear）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）と統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注→約定までをトレースする監査ログ用スキーマ（DuckDB）

設計上の特徴：
- Look-ahead バイアス回避のため、処理内で datetime.today()/date.today() を不用意に参照しない設計
- DuckDB を用いた高速なローカルデータレイク運用
- OpenAI 呼び出しはリトライ・エラーハンドリングを備え、テスト時に差し替え可能

---

## 主な機能一覧
- kabusys.data
  - ETL（run_daily_etl/run_prices_etl/run_financials_etl/run_calendar_etl）
  - J-Quants API クライアント（fetch_*/save_*）
  - 市場カレンダー管理（is_trading_day / next_trading_day / get_trading_days / calendar_update_job）
  - ニュース収集（fetch_rss）と前処理
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
  - 統計ユーティリティ（zscore_normalize）
- kabusys.ai
  - news_nlp.score_news: 銘柄毎のニュースセンチメントを OpenAI で評価して ai_scores に書き込み
  - regime_detector.score_regime: ETF (1321) の MA200 乖離とマクロニュースを合成して market_regime を更新
- kabusys.research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- kabusys.config
  - .env 自動読み込みと Settings クラス（環境変数の集中管理）

---

## セットアップ手順

前提
- Python 3.9+（typing の一部機能を利用）
- システムに DuckDB を使える環境

1. リポジトリをクローン
   - git clone ... （適宜）

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール
   - 主要な外部依存:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml
   - プロジェクトがパッケージ化されていれば:
     - pip install -e .

4. 環境変数設定
   - プロジェクトルートに `.env`（または `.env.local`）を置くと、自動的にロードされます（自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須環境変数（Settings が参照するもの）:
     - JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD      — kabuステーション API のパスワード（発注等で使用）
     - SLACK_BOT_TOKEN        — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID       — Slack チャンネル ID
   - 任意（デフォルト値あり）:
     - KABU_API_BASE_URL      — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH            — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH            — 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV            — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL              — DEBUG/INFO/...（デフォルト: INFO）
     - OPENAI_API_KEY         — OpenAI API キー（score_news/score_regime 呼び出し時にも指定可）
   - サンプル .env (README 用):
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

5. データベース初期化（監査ログスキーマ）
   - 例:
     ```python
     import duckdb
     from kabusys.data.audit import init_audit_db

     conn = init_audit_db("data/audit.duckdb")
     # または既存の接続を渡してスキーマのみ初期化
     conn = duckdb.connect("data/kabusys.duckdb")
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn, transactional=True)
     ```

---

## 使い方（主要な呼び出し例）

以下はライブラリを直接インポートして利用する例です。多くの関数は duckdb の接続オブジェクト（duckdb.DuckDBPyConnection）と target_date（日付）を受け取ります。

- 日次 ETL 実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントスコアリング（OpenAI 必須）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written scores: {n_written}")
  # api_key を引数で与えることも可能
  # score_news(conn, target_date, api_key="sk-...")
  ```

- 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- ファクター計算（研究向け）
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026, 3, 20))
  value = calc_value(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  ```

- データ品質チェック
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i)
  ```

- RSS フィード収集（news_collector.fetch_rss）
  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  ```

注記:
- OpenAI 呼び出し部分はテスト容易性のため内部呼び出しをモックできます（モジュールの _call_openai_api を patch）。
- score_news/score_regime は api_key を引数で与えるか、環境変数 OPENAI_API_KEY を参照します。

---

## ディレクトリ構成（主要ファイル）
（src/kabusys 配下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings (自動 .env ロード)
  - ai/
    - __init__.py
    - news_nlp.py           — ニュース NLU / LLM スコアリング
    - regime_detector.py    — 市場レジーム判定ロジック
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント + 保存処理
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - etl.py                — ETLResult 再エクスポート
    - news_collector.py     — RSS 収集・前処理
    - calendar_management.py— 市場カレンダー（is_trading_day 等）
    - stats.py              — 共通統計ユーティリティ（zscore_normalize）
    - quality.py            — データ品質チェック
    - audit.py              — 監査ログスキーマ（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py    — Momentum / Value / Volatility の計算
    - feature_exploration.py— 将来リターン・IC・統計サマリー等
  - ai/__init__.py
  - research/__init__.py

---

## 追加の注意事項 / ベストプラクティス
- 自動 .env ロードはデフォルトで有効です。CI / テスト時に無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 本コードベースはバックテストや研究用途を想定した設計方針（Look-ahead バイアス回避や取得日時の記録）を取り入れています。バックテストで使用する場合は ETL により過去時点までのデータを適切に準備してから利用してください。
- OpenAI 呼び出しには課金・レート制限・利用ポリシーが存在します。APIキーの管理と利用量の監視を行ってください。
- J-Quants API のレート制限（120 req/min）に合わせて内部で RateLimiter を実装していますが、大量取得時は十分な間隔で実行してください。
- DuckDB への executemany で空リストを渡すとエラーになるバージョンの挙動を考慮して実装されています。DuckDB バージョンに依存する細かい挙動に注意してください。

---

## 開発・テストについて
- OpenAI API 呼び出し箇所は単体テストでモックする設計になっています（例: unittest.mock.patch で kabusys.ai.news_nlp._call_openai_api を差し替え）。
- network IO を伴う外部 API はテスト時にフェイクサーバやレスポンス固定で検証することを推奨します。
- logging の出力は Settings.log_level で制御できます。

---

ご不明点があれば、実行したいケース（ETL、news scoring、regime scoring 等）を教えてください。具体的なサンプルコードやトラブルシュート手順を追加します。