# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。ETL（J-Quantsからのデータ取得）・データ品質チェック・ニュースNLP・市場レジーム判定・リサーチ用ファクター計算・監査ログ等のコンポーネントを提供します。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（例）
- 環境変数一覧
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株のデータ取得・前処理・特徴量生成・AIによるニュースセンチメント評価・市場レジーム判定・監査ログ管理までをカバーする内部ライブラリです。DuckDB をデータ格納に使用し、J-Quants API / RSS / OpenAI を利用するコンポーネントが含まれます。設計方針として Look-ahead バイアス防止、冪等性、フォールバックの堅牢性を重視しています。

---

## 主な機能

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（取得・保存・認証・ページング・レート制御）
  - カレンダー管理（営業日判定、next/prev_trading_day 等）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - ニュース収集（RSS -> raw_news、SSRF対策・正規化）
  - 監査ログテーブル初期化（signal_events / order_requests / executions）
  - 統計ユーティリティ（zscore 正規化）
- ai/
  - ニュースNLP（銘柄ごとのセンチメントを OpenAI により算出、ai_scores へ書込）
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースセンチメントで日次判定）
- research/
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリなど
- config.py
  - .env 自動読み込み（プロジェクトルートを .git / pyproject.toml で検出）
  - 環境変数ラッパー（settings）

設計上のポイント:
- DuckDB 接続を受け取る関数群により副作用を限定
- API 呼び出しはリトライ/バックオフ/フェイルセーフ設計
- Look-ahead バイアスを避けるため datetime.now()/today() を内部で直接参照しない設計（関数に target_date を渡す）

---

## セットアップ手順

前提:
- Python 3.10+（型注釈に union 型等を使用）
- DuckDB、OpenAI SDK、defusedxml 等の依存

例（開発環境）:

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（requirements.txt がある前提）
   - pip install -r requirements.txt

   代表的な依存例（requirements.txt がない場合の最低限）:
   - pip install duckdb openai defusedxml

3. パッケージをインストール（編集可能モード）
   - pip install -e .

4. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env を置くと自動で読み込まれます。
   - テストや強制的に自動読み込みを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 環境変数一覧

必須（本番動作に必要）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード（発注等で使用）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack チャンネル ID

任意 / デフォルトあり
- KABUSYS_ENV: development | paper_trading | live (default: development)
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL (default: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動読み込みを無効化
- KABUSYS 用 DB パスなど（defaults below）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PID_FILE_PATH: data/execution.pid

OpenAI
- OPENAI_API_KEY: news_nlp / regime_detector が利用（関数引数で上書き可能）

注意:
- config.Settings は .env を自動で読み込みます（優先順: OS 環境 > .env.local > .env）。
- .env のパースはシェル風の export KEY=val やクォート、コメントに対応しています。

---

## 使い方（簡単な例）

以下は Python REPL / スクリプトからの利用例です。

- DuckDB 接続（デフォルトパスを settings から取得）
  ```python
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  res = run_daily_etl(conn, target_date=date(2026,3,20))
  print(res.to_dict())
  ```

- ニューススコアリング（OpenAI API キーは引数または OPENAI_API_KEY 環境変数）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
  ```

- 監査DBの初期化（監査専用DBを新規作成）
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  # init_audit_schema は init_audit_db が行う
  ```

- 研究モジュールの利用（ファクター計算例）
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum
  momentum = calc_momentum(conn, target_date=date(2026,3,20))
  ```

---

## 注意点・実装上の設計メモ

- 多くの関数は target_date を引数に受け、内部で現在時刻を参照しない設計（ルックアヘッドバイアス回避）。
- OpenAI 呼び出しはリトライ・JSON モードの検証・フォールバックを行う。テスト時は内部の _call_openai_api をモック可能。
- J-Quants クライアントはレートリミッタ・トークン自動リフレッシュ・ページネーション対応。
- news_collector は SSRF・XML Bombe などの脅威対策（defusedxml、ホストチェック）を備える。
- DuckDB 用の INSERT は冪等（ON CONFLICT DO UPDATE）で設計されている。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - pipeline.py
  - etl.py (ETLResult re-export)
  - jquants_client.py
  - calendar_management.py
  - stats.py
  - quality.py
  - audit.py
  - news_collector.py
  - (その他 jquants_client 内の保存関数など)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- monitoring/ (パッケージは __all__ に含められているが実装はコードベースに依存)

（注）上記は主なファイルの一覧です。詳細は各モジュールの docstring を参照してください。

---

## 開発 / テストに関するヒント

- .env 自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI API の呼び出しをテストで差し替える場合、kabusys.ai.* モジュール内の _call_openai_api を unittest.mock.patch でモック可能です。
- DuckDB の一時的なテスト DB は ":memory:" を使用できます（init_audit_db 等でサポート）。
- logging を有効化して詳細を確認するとトラブルシュートが容易です（LOG_LEVEL を DEBUG に設定）。

---

必要であれば README にコマンド例（systemd ユニット、cron ジョブ、Slack 通知のサンプル）、.env.example のテンプレート、あるいは API レスポンス例・ER 図を追加できます。どの情報を追加したいか教えてください。