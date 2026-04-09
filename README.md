# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買支援ライブラリです。J-Quants / kabuステーション / OpenAI 等と連携してデータ取得・ETL、ニュースNLP、レジーム判定、ファクター計算、監査ログ生成などを行います。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群を提供します。

- J-Quants API からの株価・財務・カレンダー等の差分ETL
- RSSベースのニュース収集と OpenAI によるニュースセンチメント解析（銘柄別 ai_score）
- ETF とマクロニュースを組み合わせた市場レジーム判定（bull/neutral/bear）
- ファクター（モメンタム / バリュー / ボラティリティ等）の計算とリサーチ用ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution）のスキーマ作成ユーティリティ
- kabuステーション連携用設定と実行周りの設定管理

設計上の重要点:
- ルックアヘッドバイアスの防止（内部で date.today() を直接参照しない等）
- DuckDB をデータベースに利用（軽量で SQL が使える）
- 各種外部API呼び出しに対するリトライ・バックオフ・レートリミットやフェイルセーフ実装
- 冪等性（ETL 保存は ON CONFLICT DO UPDATE など）を重視

---

## 主な機能一覧

- data
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 系）
  - 市場カレンダー管理（営業日判定、next/prev_trading_day 等）
  - データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
  - ニュース収集（RSS -> raw_news 保存、SSRF対策、トラッキング除去）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - news_nlp.score_news(conn, target_date, api_key=None): ニュースを集約して OpenAI に投げ、ai_scores テーブルへ書き込み
  - regime_detector.score_regime(conn, target_date, api_key=None): ETF MA200乖離とマクロセンチメントから market_regime に書き込み
- research
  - calc_momentum / calc_value / calc_volatility：ファクター計算
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- config
  - 環境変数の読み込み・管理（.env / .env.local の自動読み込み、Settings クラス）

---

## セットアップ手順

前提:
- Python 3.10+（typing のユニオン記法等を使用）
- DuckDB, OpenAI SDK 等のライブラリ（下記）

1. リポジトリをクローン
   git clone <リポジトリURL>
   cd <repo>

2. 仮想環境を作成・有効化（任意推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 依存ライブラリをインストール（例）
   pip install duckdb openai defusedxml

   ※プロジェクトに requirements.txt がある場合はそちらを使用してください。

4. 環境変数設定
   プロジェクトルートに `.env`（と必要なら `.env.local`）を作成してください。Config モジュールは自動的にプロジェクトルート（.git または pyproject.toml の親）から `.env`/.env.local を読み込みます。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   最小の必須設定（例）:
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   OPENAI_API_KEY=sk-...
   # 任意（デフォルトあり）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   LOG_LEVEL=INFO
   KABUSYS_ENV=development

   主要な環境変数（一覧）
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
   - OPENAI_API_KEY (AI機能を使う場合に必須)
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (通知等)
   - DUCKDB_PATH (default: data/kabusys.duckdb)
   - SQLITE_PATH (default: data/monitoring.db)
   - PAPER_FILL_MODE (instant|partial|never|reject, default: instant)
   - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
   - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
   - KABUSYS_ENV (development | paper_trading | live)
   - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)

5. データディレクトリ等を作成（必要なら）
   mkdir -p data

---

## 使い方（簡単な例）

以下は Python REPL やスクリプトから使うためのサンプルです。

- DuckDB 接続 & settings の利用
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（prices / financials / calendar の差分ETL + 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントスコアを算出して ai_scores に書き込む
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OPENAI_API_KEY は環境変数または api_key 引数で指定
  n = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {n}")
  ```

- 市場レジーム判定（market_regime テーブルへ書き込み）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- ファクター計算（research）
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  momentum = calc_momentum(conn, date(2026, 3, 20))
  volatility = calc_volatility(conn, date(2026, 3, 20))
  value = calc_value(conn, date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（監査専用 DB を作る）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

- デバッグ・設定参照
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_paper, settings.is_live)
  ```

注意点:
- AI 関連（news_nlp / regime_detector）は OpenAI API を使用します。APIキーを環境変数 `OPENAI_API_KEY` または関数引数に渡す必要があります。
- ETL は J-Quants API の認証に JQUANTS_REFRESH_TOKEN を使用します。初回はトークンから id_token を取得する処理が行われます。

---

## ディレクトリ構成（主なファイル/モジュール）

- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス: 環境変数管理・自動 .env ロード
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント解析 / ai_scores 書き込み
    - regime_detector.py     — ETF MA200 とマクロセンチメント合成による market_regime 判定
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch / save / get_id_token 等）
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - etl.py                — ETLResult 再エクスポート
    - news_collector.py     — RSS 取得・正規化・raw_news 保存
    - calendar_management.py— 市場カレンダー管理（is_trading_day 等）
    - quality.py            — データ品質チェック
    - stats.py              — zscore_normalize 等の統計ユーティリティ
    - audit.py              — 監査ログスキーマ初期化・init_audit_db
  - research/
    - __init__.py
    - factor_research.py     — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank
  - research から data.stats を再利用する形で結合しています。

（上記は主要モジュールの一覧です。実運用用にさらに execution/strategy/monitoring 等のパッケージが存在する設計想定です。）

---

## テスト・開発時の便利情報

- 環境変数の自動読み込み
  - プロジェクトルートに `.env` と `.env.local` を置くと、自動で読み込まれます。
  - 読み込み順: OS 環境変数 > .env.local (override=True) > .env (override=False)
  - テストで自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

- DuckDB の取り扱い
  - settings.duckdb_path で指定されたパス（デフォルト data/kabusys.duckdb）に接続します。
  - テーブルスキーマがプロジェクトに含まれている想定のため、初期化スクリプト（schema 作成）を別途用意して実行してください（audit.init_audit_db は監査用スキーマを作成します）。

- OpenAI 呼び出しの差し替え（テスト向け）
  - news_nlp._call_openai_api や regime_detector._call_openai_api を unittest.mock.patch で差し替えてモック可能です。

---

## ライセンス・貢献

このリポジトリのライセンス情報はリポジトリルートの LICENSE を参照してください（本 README には含めていません）。バグ報告やプルリクエストは歓迎します。コードの設計方針（ルックアヘッド防止・冪等性・フェイルセーフ等）を尊重して変更をお願いします。

---

## 問い合わせ

不明点や導入サポートが必要な場合はリポジトリの Issue を立ててください。README の例以外に、運用用スクリプトや systemd ユニットなどを用意することを推奨します。