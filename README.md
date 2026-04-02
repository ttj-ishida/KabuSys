# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。本リポジトリはデータETL、ニュース収集・NLP、ファクター計算、研究ユーティリティ、監査ログおよび J-Quants / Kabuステーション 連携等の機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的を持つコンポーネント群を集めた Python パッケージです。

- J-Quants API からの差分 ETL（株価・財務・マーケットカレンダー）
- ニュース収集（RSS）および LLM を使ったニュースセンチメントスコアリング
- 市場レジーム判定（MA 乖離 + マクロニュースセンチメント）
- ファクター計算・特徴量探索・IC 計算
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- DuckDB ベースのデータ保存・処理

設計方針のポイント:
- ルックアヘッドバイアス対策（内部で date.today() を直接参照しない等）
- 冪等（idempotent）操作：DB への保存は ON CONFLICT / DELETE→INSERT を利用
- 外部 API 呼び出しはリトライやレート制御、フェイルセーフを実装
- テスト容易性を意識した API（API キー注入、関数差し替えが可能）

---

## 主な機能一覧

- data
  - pipeline.run_daily_etl: 日次 ETL（カレンダー・株価・財務・品質チェック一括）
  - jquants_client: J-Quants API クライアント（取得 / 保存関数、認証・リトライ・レート制御）
  - news_collector: RSS 収集、前処理、raw_news テーブルへの保存（SSRF 防止などセキュリティ配慮）
  - calendar_management: JPX カレンダーの管理・営業日判定ユーティリティ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査テーブル初期化・監査 DB 作成ユーティリティ
  - stats: 汎用統計（zscore_normalize 等）
- ai
  - news_nlp.score_news: ニュースを LLM（gpt-4o-mini）で銘柄ごとにセンチメント化して ai_scores に書き込む
  - regime_detector.score_regime: ETF (1321) の MA200 乖離とマクロニュースセンチメントを合成して市場レジーム判定を行う
- research
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター算出
  - feature_exploration: 将来リターン計算、IC、統計サマリー、ランク関数など

---

## 必要な環境変数

主要な必須設定（少なくとも ETL や AI を使う際に必要）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client が内部で ID トークンを取得）
- KABU_API_PASSWORD: kabuステーション連携で利用するパスワード
- SLACK_BOT_TOKEN: Slack 通知用トークン（通知機能を使う場合）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
- OPENAI_API_KEY: OpenAI（LLM）呼び出しに必要。score_news / score_regime の引数でも渡せます。

設定用その他:
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: デフォルト data/monitoring.db
- PID_FILE_PATH, CPU_THRESHOLD_PCT など監視設定

.env の自動ロード:
- パッケージはプロジェクトルート（.git または pyproject.toml を検出）を起点に .env を自動読み込みします。
- 読み込み順: OS 環境 > .env.local > .env
- 自動読み込みを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## セットアップ手順

1. Python 環境
   - 推奨: Python 3.10 以降（ソースの型アノテーションに依存）
   - 仮想環境を作ってください:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - 必要ライブラリ（例）:
     - duckdb
     - openai
     - defusedxml
   - pip でインストール:
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt や pyproject.toml がある場合はそちらを使用してください）

3. 環境変数設定
   - リポジトリルートに .env を作成（例）:
     - JQUANTS_REFRESH_TOKEN=...
     - OPENAI_API_KEY=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
   - 必要に応じて DUCKDB_PATH 等も設定できます。

4. データディレクトリの作成（デフォルト）
   - mkdir -p data

5. 監査ログ DB 初期化（任意）
   - Python REPL またはスクリプトで:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")

---

## 使い方（代表的な利用例）

以下はコードから各機能を呼ぶ最小例です。すべて DuckDB 接続を渡して動かします。

- 日次 ETL を実行する
  - 目的: カレンダー・株価・財務の差分取得と品質チェック
  - 例:
    - import duckdb, datetime
      from kabusys.data.pipeline import run_daily_etl
      conn = duckdb.connect("data/kabusys.duckdb")
      result = run_daily_etl(conn, target_date=datetime.date(2026, 3, 20))
      print(result.to_dict())

- ニュースセンチメントをスコア化（AI）
  - 例:
    - import duckdb, datetime
      from kabusys.ai.news_nlp import score_news
      conn = duckdb.connect("data/kabusys.duckdb")
      n = score_news(conn, datetime.date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY が環境にある想定
      print(f"scored {n} codes")

- 市場レジーム判定（AI + MA200）
  - 例:
    - import duckdb, datetime
      from kabusys.ai.regime_detector import score_regime
      conn = duckdb.connect("data/kabusys.duckdb")
      score_regime(conn, datetime.date(2026, 3, 20), api_key=None)

- 監査スキーマを初期化する
  - 例:
    - from kabusys.data.audit import init_audit_db
      conn = init_audit_db("data/audit.duckdb")

- ファクター計算（研究用）
  - 例:
    - import duckdb, datetime
      from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
      conn = duckdb.connect("data/kabusys.duckdb")
      mom = calc_momentum(conn, datetime.date(2026, 3, 20))
      print(len(mom))

注意点:
- score_news / score_regime は OpenAI API キーが必要（引数で明示的に渡すか OPENAI_API_KEY 環境変数を設定）。
- jquants_client は J-Quants のトークン（JQUANTS_REFRESH_TOKEN）を必要とします。
- 実行前に対象の DuckDB に必要なスキーマ・テーブルが存在することを確認してください（ETL 実行時に必要に応じてスキーマ初期化を行う設計になっている場合があります）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
  - .env 自動ロード、settings オブジェクト（環境変数ラッパー）
- ai/
  - __init__.py (score_news エクスポート)
  - news_nlp.py — ニュースの LLM センチメント化（score_news）
  - regime_detector.py — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - calendar_management.py — JPX カレンダー管理・営業日ユーティリティ
  - pipeline.py — ETL パイプライン（run_daily_etl など）
  - etl.py — ETLResult の再エクスポートインターフェース
  - stats.py — 汎用統計ユーティリティ（zscore_normalize）
  - quality.py — データ品質チェック（QualityIssue 等）
  - audit.py — 監査ログテーブル定義・初期化（init_audit_schema / init_audit_db）
  - jquants_client.py — J-Quants API クライアント（取得 / 保存 / 認証 / レート制御）
  - news_collector.py — RSS 収集、前処理、raw_news への保存（SSRF 防止など）
- research/
  - __init__.py
  - factor_research.py — モメンタム・バリュー・ボラティリティ計算
  - feature_exploration.py — forward returns, IC, factor_summary, rank

上記以外にも execution / monitoring / strategy 等のパッケージが __all__ に含まれている想定（パッケージ構成に応じて追加実装あり）。

---

## 実運用上の注意

- 本コードベースは実際の発注ロジックや証券会社 API 呼び出しを直接行わない部分・行う部分が混在する可能性があります。ライブ運用時は十分なテスト、リスク管理、二重化防止（idempotency）、監査ログの確認を行ってください。
- OpenAI / J-Quants など外部 API の呼び出しは課金やレート制限の対象です。API キー管理やコスト管理を適切に行ってください。
- データベースファイル（DuckDB）のバックアップとスキーマ管理を適切に行ってください。
- .env に機密情報を保管する場合はアクセス権限に注意してください。

---

もし README に追加したいサンプルスクリプト、CI 設定、開発用の依存リスト（requirements.txt / pyproject.toml）や、各テーブルのスキーマ定義（DDL）の抜粋が必要であれば教えてください。必要に応じて README に追記します。