# KabuSys

KabuSys は日本株向けの自動売買／データ基盤ライブラリです。  
DuckDB ベースのデータパイプライン（ETL）、ニュースの収集と NLP スコアリング、マーケットカレンダー管理、リサーチ用ファクター計算、監査ログ用スキーマ、J-Quants / kabu ステーションとの連携ユーティリティなどを含みます。

---

## プロジェクト概要

主な目的は次のとおりです。

- J-Quants API から株価・財務・カレンダー等を差分取得して DuckDB に保存する日次 ETL パイプライン
- RSS ニュースの収集・前処理・銘柄紐付け（news_collector）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（news_nlp）や市場レジーム判定（regime_detector）
- 監査ログ（信号→発注→約定）を記録する監査テーブルの初期化ユーティリティ
- 研究（research）モジュール：モメンタム・バリュー・ボラティリティなどのファクター計算、将来リターンやIC計算、Zスコア正規化 など
- データ品質チェック（欠損・スパイク・重複・日付整合性）

設計上の方針として、Look-ahead バイアスの回避、冪等性（ON CONFLICT DO UPDATE 等）、API の堅牢なリトライ／レート制御、安全対策（SSRF 防止、XML の安全パース）を重視しています。

---

## 機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（fetch_* / save_*）
  - マーケットカレンダー管理（is_trading_day, next_trading_day, prev_trading_day, calendar_update_job）
  - ニュース収集（fetch_rss, preprocess_text, URL 正規化、SSRF/サイズ制限対策）
  - 品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
  - 監査ログ初期化 / DB 作成（init_audit_schema, init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - ニュース NLP（score_news） — OpenAI を利用した銘柄単位センチメント算出
  - 市場レジーム判定（score_regime） — ETF (1321) の MA とマクロニュースからレジーム判定
- research/
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- config.py
  - .env ファイル（.env, .env.local）からの環境変数ローディング（自動ロードを無効化するフラグあり）
  - settings オブジェクトで設定値を提供

---

## 必要要件（概略）

- Python 3.10+
- 依存ライブラリ（主なもの）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、RSS フィード等）

（実際の requirements はプロジェクトの packaging に合わせて用意してください）

---

## セットアップ手順

1. リポジトリをクローン／取得
   - 例: git clone <repo-url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - pip install duckdb openai defusedxml
   - もしくはプロジェクトに requirements.txt / pyproject.toml があればそれに従ってインストール

4. パッケージをインストール（編集可能モード）
   - プロジェクトルートに pyproject.toml または setup があれば:
     - pip install -e .

5. 環境変数 / .env の準備
   - プロジェクトルートに .env（または .env.local）を作成します。自動で .env を読み込みます。
   - 必須の環境変数（config.Settings が参照）
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
     - KABU_API_PASSWORD — kabu API 接続パスワード（kabu ステーション連携用）
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — Slack チャンネル ID
   - 任意（OpenAI を使う場合は必須）
     - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime で利用）
   - その他
     - KABUSYS_ENV (development | paper_trading | live)（デフォルト: development）
     - LOG_LEVEL（DEBUG/INFO/...）
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視用 sqlite、デフォルト data/monitoring.db）
   - 自動ロードを無効にするには:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

6. DuckDB 初期スキーマ等の準備
   - audit 用 DB 初期化例（python REPL などで）:

     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

   - ETL 用のメインデータベースは settings.duckdb_path を使うのが便利です。

---

## 使い方（簡単なコード例）

以下は Python スクリプト・REPL での簡単な利用例です。

- DuckDB に接続して日次 ETL を実行する

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(__import__("kabusys").config.settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントの算出（OpenAI API キー必須）

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"wrote {n_written} ai scores")

- 市場レジームスコアの算出（OpenAI API キー必須）

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")

- 監査 DB 初期化

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # これで監査テーブル(signal_events, order_requests, executions) が作成されます

- RSS フィード取得（news_collector）

  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles[:5]:
      print(a["id"], a["datetime"], a["title"])

ノート:
- OpenAI 呼び出しは内部で exponential backoff やレスポンスバリデーションを行います。テスト時はモックしやすいように _call_openai_api を patch できるようになっています。
- ETL / 保存処理は冪等（ON CONFLICT DO UPDATE）で実装されています。

---

## 設定 / 環境変数

主要な環境変数（settings が参照）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- OPENAI_API_KEY (ai 機能を使う場合に必須)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)

.env の読み込みについて:
- 自動読み込み順: OS 環境 > .env.local > .env
- 自動読み込みを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py         — ニュース NLP（score_news）
  - regime_detector.py  — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py   — J-Quants API クライアント / save_* / fetch_*
  - pipeline.py         — ETL パイプライン（run_daily_etl 等）
  - etl.py              — ETLResult の再エクスポート
  - calendar_management.py — マーケットカレンダー管理
  - news_collector.py   — RSS 収集・前処理
  - quality.py          — データ品質チェック
  - stats.py            — 統計ユーティリティ（zscore_normalize）
  - audit.py            — 監査ログスキーマ・初期化
- research/
  - __init__.py
  - factor_research.py  — calc_momentum / calc_value / calc_volatility
  - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank

---

## 注意事項 / ベストプラクティス

- Look-ahead バイアス回避: モジュールの多くは内部で date.today() や datetime.today() を直接参照しないよう設計されています。バックテストでは必ず明示的な target_date を指定してください。
- OpenAI 利用: レスポンスが JSON であることを前提にしています。API キーの管理は環境変数に置き、テスト時は API 呼び出し部分をモックしてください（各モジュールで _call_openai_api を差し替え可能）。
- J-Quants API: rate limit（120 req/min）遵守のためモジュール内で簡易 RateLimiter を実装しています。また 401 発生時はリフレッシュして再試行する仕組みがあります。
- セキュリティ: news_collector は SSRF 対策（リダイレクト検査・プライベート IP 拒否）、XML パースに defusedxml を使用、レスポンスサイズ制限を入れています。
- DuckDB の executemany は空リストを渡せないバージョンの問題に配慮した実装が行われています。

---

## テスト / 開発

- OpenAI 呼び出しや外部 API 呼び出しを伴う箇所は、unittest.mock.patch を使って _call_openai_api や kabusys.data.news_collector._urlopen、jquants_client._request などを差し替えて単体テストを行うことを推奨します。
- settings の自動 .env 読み込みはテスト時に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

---

この README はコードベースの主要な使い方と設計意図を簡潔にまとめたものです。詳細な API 使用法やスキーマ定義、運用手順は別途ドキュメント（Design/Platform/Strategy ドキュメント）を参照してください。必要であれば README に追加したい利用シナリオや CLI / Docker の例を教えてください。