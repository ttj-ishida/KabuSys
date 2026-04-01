# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を使用したセンチメント評価）、リサーチ用ファクター計算、監査ログ（注文／約定トレーサビリティ）などを含んだモジュール群を提供します。

主な設計方針は「ルックアヘッドバイアスを避ける」「DuckDB を中心としたローカルデータ管理」「API 呼び出しに対する堅牢なリトライ/フェイルセーフ」「DB への冪等保存（ON CONFLICT ベース）」です。

---

目次
- プロジェクト概要
- 機能一覧
- 必要条件
- セットアップ手順
- 使い方（簡易サンプル）
- 環境変数（.env 例）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は、日本株自動売買システムのための共通ライブラリ群です。  
主に以下を目的とします。

- J-Quants API からのデータ取得（株価日足・財務・カレンダー）
- RSS ニュース収集・前処理と OpenAI によるニュースセンチメント評価
- 市場レジーム判定（ETF の MA とマクロニュースの組合せ）
- ファクター計算・特徴量解析（モメンタム、ボラティリティ、バリュー等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- DuckDB を用いたローカルデータベース運用

---

## 機能一覧

- data/
  - jquants_client: J-Quants API クライアント（取得・保存・トークン自動更新・レート制御）
  - pipeline: 日次 ETL 実行（差分取得・保存・品質チェック）
  - news_collector: RSS フィード取得と前処理（SSRF/サイズ対策あり）
  - calendar_management: JPX カレンダー管理・営業日ロジック
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - audit: 監査用テーブル定義と初期化
  - stats: 汎用統計ユーティリティ（Z スコア正規化）
- ai/
  - news_nlp.score_news: ニュースをバッチで LLM に送り銘柄ごとの ai_score を算出して ai_scores に書き込み
  - regime_detector.score_regime: ETF（1321）MA とマクロニュースを組み合わせて市場レジームを判定し market_regime に保存
- research/
  - factor_research: モメンタム / ボラティリティ / バリュー等の計算
  - feature_exploration: 将来リターン計算、IC、統計サマリー 等

---

## 必要条件

- Python 3.9+
- 必要な主要パッケージ（例）
  - duckdb
  - openai （OpenAI Python SDK）
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、RSS ソース）
- J-Quants のリフレッシュトークン、OpenAI API キー 等の環境変数

（上記はコードから推定した主要依存です。実際のプロジェクトでは pyproject.toml / requirements.txt を参照してください。）

---

## セットアップ手順

1. リポジトリをクローン / 取得

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール（例）
   - pip install duckdb openai defusedxml

   （パッケージ一覧がある場合は pip install -r requirements.txt や pip install -e . を利用してください）

4. 環境変数設定
   - プロジェクトルートに .env を作成すると自動読み込みされます（モジュール起動時に .env → .env.local の順で取り込み）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. DuckDB の初期化（監査 DB など）
   - Python から init_audit_db を呼んで初期テーブルを作成できます（下記参照）。

---

## 簡単な使い方（サンプル）

以下は Python スクリプト/REPL からの利用例です。すべての API は DuckDB 接続（duckdb.connect(...)）を受け取ります。

- ETL（日次パイプライン）を実行する
  ```python
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを算出（OpenAI API キーは OPENAI_API_KEY 環境変数か api_key 引数で指定）
  ```python
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings
  import duckdb
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込んだ銘柄数:", n_written)
  ```

- 市場レジーム判定（ETF 1321 を基に LLM を用いる）
  ```python
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログテーブルの初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn は初期化済みの DuckDB 接続
  ```

- 市場カレンダー更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  conn = duckdb.connect(str(settings.duckdb_path))
  calendar_update_job(conn)
  ```

注意:
- OpenAI 呼び出しには API キーが必要です（環境変数 OPENAI_API_KEY を設定するか、関数の api_key 引数に渡してください）。
- J-Quants はリフレッシュトークン（JQUANTS_REFRESH_TOKEN）が必要です。
- ETL 実行時は J-Quants API のレート制約に従います。

---

## 環境変数 (.env 例)

以下は本ライブラリで参照される主要環境変数の一覧（.env に設定可能）。必要に応じて値を追加してください。

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（LLM 呼び出し時に利用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite のパス（デフォルト: data/monitoring.db）
- PID_FILE_PATH: 実行時 PID ファイルパス（デフォルト: data/execution.pid）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値（パーセント）
- KABUSYS_ENV: 環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL: ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)

.env の自動ロード:
- パッケージの config モジュールはプロジェクトルート（.git または pyproject.toml を探索）から .env/.env.local を自動読み込みします。
- テストなどで自動ロードを抑制するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## ディレクトリ構成（概略）

src/kabusys/
- __init__.py
- config.py                        -- 環境設定の読み込み/検証
- ai/
  - __init__.py
  - news_nlp.py                    -- ニュースセンチメント計算（OpenAI 使用）
  - regime_detector.py             -- 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py              -- J-Quants API クライアント / DuckDB 保存
  - pipeline.py                    -- ETL パイプライン（run_daily_etl 等）
  - calendar_management.py         -- 市場カレンダー管理 / 営業日ロジック
  - news_collector.py              -- RSS 収集・前処理
  - quality.py                     -- データ品質チェック
  - stats.py                       -- 汎用統計ユーティリティ
  - audit.py                       -- 監査テーブル DDL / 初期化
  - etl.py                         -- ETLResult の再エクスポート
- research/
  - __init__.py
  - factor_research.py             -- モメンタム / ボラティリティ / バリュー等
  - feature_exploration.py         -- 将来リターン / IC / 統計サマリー

（上記は主要モジュールと責務の概略です。詳細は各ファイルの docstring を参照してください。）

---

## 運用上の注意・設計メモ

- ルックアヘッドバイアス防止のため、ほとんどの関数は内部で date.today()/datetime.now() を直接参照せず、target_date を引数で受け取ります。バッチ処理やバックテストでの再現性を確保できます。
- OpenAI の呼び出しはリトライやレスポンス検証を行い、エラー時はフェイルセーフ（0.0 にフォールバック等）を採っていますが、API キーと利用料金に注意してください。
- J-Quants の API はレート制限（120 req/min）に対してモジュール内で RateLimiter を用いて制御しています。
- DuckDB を利用しているため大容量データもローカルで効率的に扱えます。DB スキーマは save_* / init_audit_schema 等で冪等に作成されます。

---

## 貢献 / 開発

- コードベースの各ファイルにドキュメント文字列（docstring）が豊富に記載されています。新機能追加や修正時は docstring とテストの整合性を保ってください。
- 自動テスト / CI を導入する場合、環境変数の自動ロードを抑止する `KABUSYS_DISABLE_AUTO_ENV_LOAD` を利用するとよいです。

---

ご不明点や README に追記して欲しい具体的な利用シナリオがあれば教えてください。README を利用用途（開発用、運用用、デプロイ手順など）に合わせて拡張します。