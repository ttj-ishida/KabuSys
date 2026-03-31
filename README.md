# KabuSys

日本株向け自動売買／データ基盤ライブラリ（KabuSys）のREADMEです。  
このリポジトリはデータ取得・品質チェック・特徴量計算・AIによるニュース分析・市場レジーム判定・監査ログなどを含む、バックテスト／実運用に使える基盤コンポーネント群を提供します。

## プロジェクト概要
- 目的: J-Quants や RSS 等から日本株データを取得し、DuckDB に蓄積。品質チェック、ファクター計算、ニュースNLP（OpenAI）によるセンチメント評価、日次ETL、自動売買監査ログなどを行うためのユーティリティ群。
- 設計方針の要点:
  - ルックアヘッドバイアスを避ける（関数は内部で date.today() を直接参照しない等）
  - DuckDB を中心に SQL + Python で処理（Pandas等に依存しない）
  - 外部 API 呼び出しは堅牢なリトライ／レート制御を実装
  - 冪等（idempotent）な DB 保存処理（ON CONFLICT / DELETE→INSERT など）
  - OpenAI（gpt-4o-mini 等）を用いた JSON Mode による解析（news_nlp / regime_detector）

## 機能一覧
主な提供機能（モジュール別）
- kabusys.config
  - 環境変数の読み込み（.env / .env.local の自動ロード、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - アプリ設定（J-Quants, kabuAPI, Slack, DBパス, 監視閾値, 環境モード等）
- kabusys.data
  - jquants_client: J-Quants API からのデータ取得・DuckDB への保存（株価、財務、カレンダーなど）
  - pipeline / etl: 日次 ETL（差分取得・保存・品質チェック）
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - news_collector: RSS からの記事収集（SSRF対策、トラッキング除去、前処理）
  - calendar_management: JPX カレンダー管理・営業日判定・カレンダー更新ジョブ
  - audit: 監査ログテーブル定義・初期化（signal_events / order_requests / executions）
  - stats: 汎用統計（Zスコア正規化等）
- kabusys.ai
  - news_nlp.score_news: ニュース記事を銘柄別に集約して OpenAI でセンチメントを算出し ai_scores に書き込む
  - regime_detector.score_regime: ETF(1321)のMA乖離とマクロニュースセンチメントを合成して市場レジーム (bull/neutral/bear) を判定・保存
- kabusys.research
  - ファクター計算（momentum, value, volatility）や特徴量探索（forward returns, IC, summary, rank）

## セットアップ手順（開発向け）
前提: Python 3.10+（型ヒントに | 型記法を利用）、Git が利用できることを想定します。

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージのインストール
   - 必須パッケージ（代表例）:
     - duckdb
     - openai
     - defusedxml
     - 依存関係やテスト用パッケージはプロジェクトの requirements.txt / pyproject.toml を参照してください。
   - 例:
     - pip install duckdb openai defusedxml

   （注）リポジトリに pyproject.toml / requirements.txt がある場合はそれに従ってください。開発用途では pip install -e . で editable install を行うことが多いです。

3. 環境変数 / .env 設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API 用パスワード
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
     - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で必要）
   - その他オプション:
     - KABUSYS_ENV: development / paper_trading / live
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
     - DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH 等（設定クラスでデフォルト指定あり）

   - サンプル .env（プロジェクト用に編集して保存）
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABU_API_PASSWORD=your_kabu_password
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     ```

4. DuckDB 初期化（監査DBなど）
   - 監査ログ用 DB 初期化例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - schema を他の用途で初期化するユーティリティは各モジュール（data.schema に相当するもの）を参照してください。

## 使い方（代表的な操作例）
以下はライブラリの関数を直接呼び出す簡単な使用例です。実行は Python スクリプトやジョブで行います。

- DuckDB 接続を作成して日次ETLを実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントスコアを計算して ai_scores に書き込む
  ```python
  from kabusys.ai.news_nlp import score_news
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY が環境変数にある場合は api_key を省略可能
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written: {n_written}")
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査スキーマ初期化（トランザクション付き）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn は監査テーブルが作成された DuckDB 接続
  ```

- 設定参照例
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

注意点:
- OpenAI API 呼び出しを行う関数は api_key 引数でキーを渡すか、環境変数 OPENAI_API_KEY を設定してください。未設定時は ValueError を送出します。
- J-Quants の API トークン取得は jquants_client.get_id_token を利用します。settings.jquants_refresh_token を設定してください。

## 監視・運用
- kabusys.config の設定で PID ファイルや CPU/メモリ/ディスク閾値を設定できます（PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT）。
- KABUSYS_ENV によって環境モード（development / paper_trading / live）を切り替え、is_live/is_paper/is_dev の判定が可能です。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml を探索）を基準に行われます。テストなどで無効にする際は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

## ディレクトリ構成（主要ファイル）
以下はソースツリー（src/kabusys）内の主要モジュールと役割の一覧です。

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py            - ニュースの NLP スコアリング（OpenAI 経由で ai_scores を更新）
    - regime_detector.py     - ETF MA とマクロニュースから市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py      - J-Quants API クライアント（取得 + DuckDB 保存）
    - pipeline.py            - ETL パイプライン（run_daily_etl 等）
    - etl.py                 - ETL インターフェース（ETLResult の再エクスポート）
    - quality.py             - データ品質チェック（欠損・スパイク・重複・日付整合性）
    - stats.py               - 汎用統計ユーティリティ（zscore_normalize 等）
    - news_collector.py      - RSS 収集・前処理（SSRF対策・正規化）
    - calendar_management.py - JPX カレンダー管理（営業日判定・更新ジョブ）
    - audit.py               - 監査ログテーブル定義・初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py     - Momentum / Value / Volatility 等のファクター計算
    - feature_exploration.py - forward returns, IC, factor summary, rank 等

（ソースコードはさらに細かい関数・ユーティリティを多数含みます。上記は概要です。）

## よくあるトラブルと対処
- 環境変数未設定で ValueError が発生する
  - settings の _require が必須変数の未設定時にエラーを出します。README のサンプル .env を参考に必須値を設定してください。
- OpenAI 呼び出しでエラーが発生する
  - APIキー設定（OPENAI_API_KEY）を確認。レートや 5xx は内部でリトライしますが、上限に達するとログに警告が出ます。
- J-Quants API の 401 が出る
  - jquants_client はリフレッシュトークンから id_token を自動取得します。settings.jquants_refresh_token を確認してください。
- RSS 取得でリダイレクトや内部アドレスが弾かれる
  - news_collector は SSRF 対策でプライベートアドレスや非 http/https スキームをブロックします。合法な公開 RSS を使用してください。

## 貢献・拡張
- 新しい ETL 対象や品質チェックを追加する場合は data/ 以下にモジュールを追加し、pipeline.run_daily_etl に組み込んでください。
- AI プロンプトやモデルを調整する場合は ai/news_nlp.py / ai/regime_detector.py の定数やプロンプト定義を編集してください。
- テストを書く際は config の自動 .env 読み込みを KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化すると分離が容易です。OpenAI 呼び出しや外部 HTTP はモック可能なように設計されています（内部 _call_openai_api 等を patch）。

---

この README はコードベースの主要機能と使い方を要約したものです。具体的な API の細かい挙動や追加のユーティリティは各モジュールの docstring を参照してください。必要であれば、各機能のサンプルスクリプトや運用手順を別途まとめます。