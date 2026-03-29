# KabuSys

KabuSys は日本株向けのデータパイプライン、リサーチ、AI ベースのニュース解析、監査ログ、ETL 等を備えた自動売買・研究プラットフォームのライブラリ群です。本リポジトリはモジュール単位で以下の主要機能を提供します。

- データ取得・ETL（J-Quants API 経由）
- 市場カレンダー管理（JPX）
- ニュース収集と LLM による銘柄センチメント解析
- 市場レジーム判定（ETF + マクロニュース）
- ファクター計算・特徴量探索（研究用）
- 監査ログ（signal → order → execution トレース）
- データ品質チェック、統計ユーティリティ

以下は開発者・利用者向けの README（日本語）です。

---

目次
- プロジェクト概要
- 機能一覧
- 前提 / 依存関係
- セットアップ手順
- 環境変数（.env）例
- 使い方（代表的な API 呼び出し例）
- ディレクトリ構成（主要ファイルの説明）
- 注意点 / 設計方針メモ

---

プロジェクト概要
- KabuSys は DuckDB をストレージに用い、J-Quants からの株価・財務データ、RSS ニュース、マーケットカレンダー等を ETL により取り込み、研究・信号生成・監査ログを実現する Python パッケージです。
- OpenAI（gpt-4o-mini 等）の JSON Mode を用いてニュースセンチメントや市場レジームを自動評価する機能を備えています（API キーが必要）。

機能一覧（主要）
- data.jquants_client
  - J-Quants API からのデータ取得（株価 / 財務 / カレンダー）
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）
  - レート制限・リトライ・トークンリフレッシュ対応
- data.pipeline
  - 日次 ETL（run_daily_etl）: カレンダー → 株価 → 財務 → 品質チェック
  - 個別 ETL ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
  - ETLResult による実行レポート
- data.news_collector
  - RSS 取得・正規化、SSRF 対策、テキスト前処理、raw_news への保存
- data.calendar_management
  - market_calendar を用いた営業日判定・次営業日/前営業日・SQ 判定等
- data.quality
  - 欠損、重複、スパイク、日付不整合などの品質チェック
- data.audit
  - signal / order_request / executions の監査テーブル定義と初期化
- ai.news_nlp
  - ニュースを銘柄ごとに集約し LLM でセンチメント評価（score_news）
  - バッチ化・スコア検証・リトライ
- ai.regime_detector
  - ETF（1321）の MA200 乖離とマクロニュースセンチメントを合成し日次で市場レジーム判定（score_regime）
- research.*
  - ファクター計算（モメンタム / バリュー / ボラティリティ）と特徴量解析ユーティリティ
- config
  - 環境変数読み込み（.env / .env.local を自動読み込み。CWD 依存しないプロジェクトルート検出）
  - settings インスタンス経由で必要設定を取得

前提 / 依存関係（代表）
- Python 3.10+
- duckdb
- openai（OpenAI Python SDK、JSON Mode を利用）
- defusedxml
- その他（標準ライブラリ：urllib, gzip, hashlib 等）

推奨インストール例（venv を使用）
1. 仮想環境作成
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージインストール（例）
   - pip install duckdb openai defusedxml

注: requirements.txt は本リポジトリに含まれていないため、プロジェクト内で追加の依存がある場合は適宜追記してください。

セットアップ手順

1) リポジトリをクローン／チェックアウト
   - git clone <repo-url>
   - cd <repo-root>

2) .env を用意
   - ルート（.git や pyproject.toml があるディレクトリ）に .env を配置すると自動読み込みされます（読み込みはパッケージ import 時に実行）。
   - 自動読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

3) 主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN=...
   - OPENAI_API_KEY=...
   - KABU_API_PASSWORD=...                (kabu station API 利用時)
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi  (任意)
   - SLACK_BOT_TOKEN=...
   - SLACK_CHANNEL_ID=...
   - KABUSYS_ENV=development|paper_trading|live
   - LOG_LEVEL=INFO
   - DUCKDB_PATH=data/kabusys.duckdb       (デフォルト)
   - SQLITE_PATH=data/monitoring.db       (デフォルト)
   例は下の「環境変数（.env）例」を参照してください。

4) DuckDB 初期化（監査ログなど）
   - Python REPL またはスクリプトで監査テーブルを初期化できます。
     例:
       from kabusys.data.audit import init_audit_db
       conn = init_audit_db("data/audit.duckdb")

5) ETL の実行（サンプル）
   - run_daily_etl を呼ぶことで日次 ETL（カレンダー・価格・財務・品質チェック）を実行できます。
     例スクリプト:
       import duckdb
       from datetime import date
       from kabusys.data.pipeline import run_daily_etl
       conn = duckdb.connect("data/kabusys.duckdb")
       res = run_daily_etl(conn, target_date=date(2026,3,20))
       print(res.to_dict())

環境変数（.env）例
- プロジェクトルートに .env（または .env.local）を置くと自動で読み込まれます。
- .env.example（参考）
  JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
  OPENAI_API_KEY=sk-...
  KABU_API_PASSWORD=your_kabu_password
  KABU_API_BASE_URL=http://localhost:18080/kabusapi
  SLACK_BOT_TOKEN=xoxb-...
  SLACK_CHANNEL_ID=C12345678
  KABUSYS_ENV=development
  LOG_LEVEL=INFO
  DUCKDB_PATH=data/kabusys.duckdb
  SQLITE_PATH=data/monitoring.db

使い方（主要 API の例）
- 設定読み出し
  from kabusys.config import settings
  print(settings.duckdb_path, settings.is_live)

- ETL（日次）
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())

- ニューススコア（LLM）
  from kabusys.ai.news_nlp import score_news
  import duckdb
  from datetime import date
  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
  print("scored:", n_written)

- 市場レジーム判定
  from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

- 監査 DB 初期化（別 DB にする or :memory:）
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # tables created and TimeZone set to UTC

- 研究用ファクター計算
  from kabusys.research import calc_momentum, calc_value, calc_volatility
  conn = duckdb.connect(str(settings.duckdb_path))
  momentum = calc_momentum(conn, target_date=date(2026,3,20))

ディレクトリ構成（主要ファイルの説明）
- src/kabusys/__init__.py
  - パッケージの基本情報（__version__ 等）
- src/kabusys/config.py
  - 環境変数の自動読み込み（.env / .env.local）と Settings クラス
- src/kabusys/ai/
  - news_nlp.py: ニュースを LLM でスコアリング（score_news）
  - regime_detector.py: ETF の MA とマクロニュースで市場レジーム判定（score_regime）
- src/kabusys/data/
  - jquants_client.py: J-Quants API クライアント（fetch / save 関数群）
  - pipeline.py: ETL パイプライン（run_daily_etl 等）
  - news_collector.py: RSS 収集と正規化
  - calendar_management.py: 営業日ロジック・calendar_update_job
  - quality.py: データ品質チェック、QualityIssue 型
  - audit.py: 監査ログテーブルの DDL と初期化ユーティリティ
  - stats.py: zscore_normalize 等の統計ユーティリティ
  - etl.py: ETLResult の再エクスポート
- src/kabusys/research/
  - factor_research.py: momentum / value / volatility の計算
  - feature_exploration.py: forward returns / IC / summary / rank
- その他
  - 多くのモジュールは DuckDB 接続を受け取り SQL と Python を組み合わせて処理します。

注意点 / 設計方針メモ
- ルックアヘッドバイアス対策:
  - 各種処理（ニュースウィンドウ、MA 計算、ETL）で明示的に target_date を受け取り、内部で datetime.today()/date.today() に依存しない実装になっています。
- 冪等性:
  - DuckDB への保存は ON CONFLICT DO UPDATE を用いて冪等に設計しています（J-Quants 保存関数等）。
- フォールバック:
  - market_calendar が未取得の場合、営業日の判定は曜日ベースのフォールバックを使用します。
- OpenAI / J-Quants 呼び出し:
  - いずれもリトライ・バックオフ・フェイルセーフ（障害時はスコア 0.0、もしくはスキップ）を実装しています。API キー漏洩等を防ぐため .env ファイルは Git 管理しないでください。
- 自動 .env 読み込み:
  - パッケージ import 時にプロジェクトルート（.git または pyproject.toml を探索）を起点に .env/.env.local を読み込みます。テストや特殊な環境で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

よくある運用フロー（簡易）
1. .env に必要なシークレットをセットする
2. DuckDB を初期化し、ETL をスケジュール（cron / Airflow / GitHub Actions 等）
3. ETL 実行後、news_nlp・regime_detector を定期的に実行して特徴量やレジームを更新
4. strategy 層（本リポジトリ外）でシグナルを生成し、監査テーブルへ保存→注文実行へ接続

---

問題・バグ報告、機能追加提案は issue を立ててください。README に記載してほしい追加情報（例: CI, テストの実行方法、より詳細なデータスキーマ等）があれば教えてください。