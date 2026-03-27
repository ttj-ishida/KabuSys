# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）・データ品質チェック・ニュース NLP（OpenAI）・市場レジーム判定・研究用ファクター計算・監査ログなど、取引システム/リサーチ基盤で必要な機能群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的で設計された Python パッケージです。

- J-Quants API からの株価・財務・マーケットカレンダー等の差分 ETL
- データ品質チェック（欠損、スパイク、重複、日付整合性）
- RSS ニュース収集と LLM による銘柄別センチメント付与（ai_scores）
- マクロニュースと ETF（1321）MA200乖離を合成した市場レジーム判定
- 研究用ファクター計算・前方リターン計算・IC / 統計サマリー
- 監査ログ（signal → order_request → executions）用のスキーマ初期化ユーティリティ
- DuckDB を中心としたデータ保存インターフェース

設計上のポイント:
- ルックアヘッドバイアス対策（内部で date.today() を暗黙参照しない等）
- 冪等（idempotent）な保存処理（ON CONFLICT / DELETE→INSERT 等）
- API 呼び出しのリトライ・レート制御・フォールバックを実装
- 外部ライブラリへの過度な依存を避ける（標準ライブラリ + 最小限の外部依存）

---

## 主な機能一覧

- データ ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants クライアント（kabusys.data.jquants_client）：fetch / save 関数、認証自動更新、ページネーション、レートリミット

- データ品質チェック（kabusys.data.quality）
  - 欠損（missing_data）、スパイク（spike）、重複（duplicates）、日付整合性（date_consistency）
  - run_all_checks で一括実行して問題一覧を取得

- ニュース収集・前処理（kabusys.data.news_collector）
  - RSS 取得、URL 正規化、SSRF/サイズ対策、raw_news への冪等保存想定

- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメント生成（ai_scores への書き込み）

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の MA200 乖離 + マクロニュース LLM スコアによるレジーム（bull/neutral/bear）判定

- 研究用モジュール（kabusys.research）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクターサマリー、Z-score 正規化

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の DDL と初期化ユーティリティ（init_audit_schema / init_audit_db）

- 設定管理（kabusys.config）
  - .env 自動読み込み（プロジェクトルート基準）と Settings クラスによる環境変数アクセス

---

## 必要要件 / 依存

- Python 3.10+
- 主要依存（例）
  - duckdb
  - openai
  - defusedxml

（実際のインストール要件は setup / pyproject.toml を参照してください）

---

## セットアップ手順

1. リポジトリをクローン / パッケージを配置

2. 仮想環境を作成し依存をインストール
   - 例:
     python -m venv .venv
     source .venv/bin/activate
     pip install -U pip
     pip install duckdb openai defusedxml

   ※ プロジェクトの pyproject.toml / requirements.txt があればそれに従ってください。

3. 環境変数（重要）
   必須（Settings クラスで _require を使う項目）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - SLACK_BOT_TOKEN       : Slack 通知が必要な場合
   - SLACK_CHANNEL_ID      : Slack チャネル ID
   - KABU_API_PASSWORD     : kabuステーション API を使用する場合のパスワード
   - OPENAI_API_KEY        : OpenAI を使う処理（news_nlp / regime_detector）で必要

   任意 / デフォルトあり:
   - KABUSYS_ENV (development|paper_trading|live)  デフォルト: development
   - LOG_LEVEL (DEBUG|INFO|...) デフォルト: INFO
   - DUCKDB_PATH (例: data/kabusys.duckdb)
   - SQLITE_PATH (モニタリング DB 用)

   .env / .env.local をプロジェクトルートに置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると自動ロード無効化）。

4. DuckDB ファイルや監査 DB の準備（必要に応じて）
   - 監査 DB 初期化:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

---

## 使い方（簡単な例）

以下は主要な操作の使用例です。実行前に必要な環境変数（OPENAI_API_KEY や JQUANTS_REFRESH_TOKEN 等）を設定してください。

- DuckDB 接続の作成例:

  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行（run_daily_etl）:

  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニューススコア（AI）を生成して ai_scores に書き込む:

  from kabusys.ai.news_nlp import score_news
  from datetime import date
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None -> OPENAI_API_KEY を参照
  print("written:", n_written)

- 市場レジームを判定して書き込む:

  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログスキーマを初期化（既存 DB にテーブルを作成）:

  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)

- 研究向けファクター計算:

  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date
  mom = calc_momentum(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))

- データ品質チェック:

  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i)

注意:
- OpenAI 呼び出しを行う関数は api_key 引数で明示的にキーを渡せます（テストや並列実行時に便利）。
- 多くの処理は DuckDB のテーブル存在やデータ有無を前提にしているため、スキーマ準備や初期データ取り込みが必要です。

---

## 環境変数一覧（主要なもの）

- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン（必須）
- OPENAI_API_KEY — OpenAI API キー（score_news / regime_detector などで必要）
- KABU_API_PASSWORD — kabuステーション API 用パスワード（発注連携がある場合）
- KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("INFO" 等)
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 をセットすると .env 自動ロードを無効化

---

## ディレクトリ構成

（主要モジュール・ファイルの概観）

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py               — ニュースの LLM スコアリング（ai_scores へ保存）
    - regime_detector.py        — 市場レジーム判定（1321 MA200 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント（fetch / save / auth / rate limit）
    - pipeline.py               — ETL パイプライン / run_daily_etl 等
    - quality.py                — データ品質チェック（missing/spike/duplicates/日付整合）
    - news_collector.py         — RSS 収集・前処理（SSRF/size 対策等）
    - calendar_management.py    — マーケットカレンダー管理・営業日判定・calendar_update_job
    - stats.py                  — 汎用統計（zscore_normalize）
    - etl.py                    — ETL インターフェース re-export（ETLResult）
    - audit.py                  — 監査ログ DDL / 初期化（signal/order/execution）
  - research/
    - __init__.py
    - factor_research.py        — モメンタム/バリュー/ボラティリティ等の計算
    - feature_exploration.py    — forward returns, IC, factor_summary, rank
  - monitoring/ (予想されるモジュール群: 設定により別 DB での監視) — package export に含まれるが実装は省略されている場合あり

---

## 開発 / テストに関するメモ

- .env の自動ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行います。テストで自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しや外部 API 呼び出しは各モジュールで差し替え（モック）しやすい設計になっています（例えば kabusys.ai.news_nlp._call_openai_api を patch する等）。
- DuckDB と外部 API を用いる処理はローカルでの再現やユニットテスト時に、インメモリ ":memory:" 接続やモックを使うことを推奨します。

---

## ライセンス / 貢献

（ここにプロジェクトのライセンスや貢献方法を記述してください）

---

README に不明点や追加してほしい使用例（例: kabuステーション連携、Slack 通知設定、CI 用の設定など）があればお知らせください。必要に応じて README を拡張します。