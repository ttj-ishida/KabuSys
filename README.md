# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）・データ品質チェック・ニュース収集・AI ベースのニュースセンチメント評価・リサーチ（ファクター計算）・監査ログ（トレーサビリティ）など、トレーディングシステムに必要な共通機能を提供します。

---

## 概要

KabuSys は以下の目的を持つモジュール群で構成されています。

- J-Quants API から株価・財務・マーケットカレンダーを差分取得して DuckDB に保存する ETL
- raw_prices / raw_financials / raw_news 等のデータ品質チェック
- RSS ベースのニュース収集と銘柄紐付け
- OpenAI（gpt-4o-mini）を用いたニュース NLP によるセンチメント評価（銘柄単位、マクロ判定）
- 市場レジーム判定（ETF 1321 の MA とマクロセンチメントを合成）
- 研究用途のファクター計算・特徴量解析ユーティリティ
- 監査ログ（signal → order_request → execution の追跡用テーブル）初期化ユーティリティ

設計上の特徴:
- ルックアヘッドバイアス防止（API 呼び出し・日付参照の扱いに配慮）
- 冪等性（DB への保存は ON CONFLICT DO UPDATE / DO NOTHING を活用）
- API 呼び出しに対するリトライ / バックオフ / レート制御の実装
- テスト容易性（モジュール単位で差し替え可能な内部呼び出し）

---

## 機能一覧

- 環境設定管理（kabusys.config）
  - .env 自動ロード（プロジェクトルート検出、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - 必須環境変数チェック
- データ ETL（kabusys.data.pipeline / jquants_client）
  - fetch / save / 差分更新・バックフィルロジック
  - run_daily_etl による一括 ETL 実行
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合などの検出
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得・前処理・ID 正規化（SSRF 対策、gzip 上限、tracking params 除去）
- AI モジュール（kabusys.ai）
  - score_news: 銘柄ごとのニュースセンチメントを OpenAI に問い合わせて ai_scores へ保存
  - score_regime: ETF 1321 の MA とマクロニュースから市場レジーム判定（bull/neutral/bear）
- リサーチ（kabusys.research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー等
- 監査ログ（kabusys.data.audit）
  - 監査スキーマ初期化、監査専用 DB 初期化ユーティリティ
- ユーティリティ（kabusys.data.stats 等）
  - zscore 正規化など共通統計関数

---

## 前提 / 必要環境

- Python 3.10+
- 必要パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリの urllib 等を利用しているため特別な HTTP クライアントは不要）
- J-Quants API アクセス用のリフレッシュトークン
- OpenAI API キー（ニュース NLP / レジーム判定で使用）

パッケージ化の方法はプロジェクトの pyproject.toml / requirements を参照してください。開発時は以下のようにインストールすることが多いです:

pip install -r requirements.txt
# または
pip install -e .

（requirements.txt / pyproject.toml がプロジェクトに含まれている前提です）

---

## 環境変数

主に次の環境変数を利用します（kabusys.config.Settings 参照）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意 / 既定値あり:
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト "development"）
- LOG_LEVEL — "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"（デフォルト "INFO"）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト "http://localhost:18080/kabusapi"）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト "data/kabusys.duckdb"）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト "data/monitoring.db"）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime の引数に渡さない場合は環境変数を参照）

.env 自動ロード:
- リポジトリルートの `.env` と `.env.local` が自動でプロジェクト読み込み時に環境変数へ反映されます。
- 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（例）

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo>

2. Python 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール
   pip install -r requirements.txt
   （requirements.txt がない場合は duckdb/openai/defusedxml 等を個別にインストール）

4. 環境変数の設定
   - `.env.example` を参照して `.env` を作成してください（リポジトリに .env.example がある想定）。
   - 必須変数（JQUANTS_REFRESH_TOKEN 等）を設定します。
   - 例:
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-xxxx
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678

5. DuckDB データベース準備（初回のみ）
   - 必要に応じてスキーマ作成用ユーティリティを用意してください（project 内に schema 初期化関数があればそれを使用）。
   - 監査ログ専用 DB 初期化:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

---

## 使い方（代表的な API）

以下は代表的な呼び出し例です（簡易サンプル）。

- 設定の参照:
  from kabusys.config import settings
  print(settings.jquants_refresh_token)

- ETL（日次 ETL）実行:
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントスコア算出（銘柄単位）:
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY は環境変数参照

- 市場レジーム判定:
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログスキーマ初期化:
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")

- ニュース RSS 取得（低レベルユーティリティ）:
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")

- カレンダー・営業日判定:
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  is_td = is_trading_day(conn, date(2026, 3, 20))
  next_td = next_trading_day(conn, date(2026, 3, 20))

注意:
- OpenAI 呼び出し（score_news / score_regime）は API キーを引数で渡すことができます（api_key="..."）。渡さない場合は環境変数 OPENAI_API_KEY を参照します。
- 各関数は DuckDB 接続を受け取ります（duckdb.connect(...) の返り値）。テスト時はモック差し替えができます。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイル / モジュールの構成です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py            — 環境変数・設定管理
  - ai/
    - __init__.py         — score_news を公開
    - news_nlp.py         — ニュース NLP（銘柄別スコア）
    - regime_detector.py  — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（fetch / save / auth / rate limit）
    - pipeline.py         — ETL パイプライン（run_daily_etl 等）
    - etl.py              — ETL の公開型（ETLResult）
    - news_collector.py   — RSS ニュース収集
    - calendar_management.py — マーケットカレンダー管理・営業日判定
    - quality.py          — データ品質チェック
    - stats.py            — 共通統計ユーティリティ（zscore_normalize 等）
    - audit.py            — 監査ログ（スキーマ定義 / 初期化）
  - research/
    - __init__.py
    - factor_research.py  — ファクター計算（momentum / value / volatility）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - research/*            — 研究用ユーティリティ群
  - その他（strategy / execution / monitoring 等の名前空間が __init__ で公開される想定）

（実際のツリーはリポジトリ内のファイルを参照してください）

---

## 開発・運用上の注意

- ルックアヘッドバイアス防止:
  - モジュールの多くは `date` / `target_date` を引数として受け取り、内部で現在時刻を直接参照しない設計です。バックテストや再現性のある処理ではこの点に注意してください。
- 自動環境ロード:
  - パッケージ読み込み時にリポジトリルートの `.env` / `.env.local` を自動ロードします。テスト時に影響させたくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- API レート・リトライ:
  - J-Quants クライアントは固定間隔によるスロットリングとリトライを実装しています。過剰な同時呼び出しは避けてください。
- セキュリティ:
  - news_collector は SSRF 対策（リダイレクト検査 / プライベート IP ブロック）や XML の defusedxml を使用しています。運用で異常があればログを確認してください。
- DB 書き込み:
  - DuckDB の executemany に関する互換性（空リスト不可など）へ配慮した実装があります。DuckDB のバージョン依存に注意してください。

---

## 参考 / デバッグ

- ログレベルは LOG_LEVEL 環境変数で制御できます（INFO / DEBUG 等）。
- 各モジュールは logger 名を持っているため、必要に応じてロギング設定を行ってください。

---

もし README に追加したい具体的な「実行スクリプト例」や「.env.example のサンプル」、「CI / デプロイ手順」などがあればお知らせください。必要に応じて追記します。