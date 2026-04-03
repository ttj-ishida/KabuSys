# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。J-Quants / kabuステーション / OpenAI を組み合わせて、
データETL、ニュースNLP、ファクター計算、監査ログ、マーケットカレンダー管理などを提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計されたライブラリ群です。主な目的は次のとおりです。

- J-Quants API からの株価・財務・上場銘柄・マーケットカレンダーの差分取得と DuckDB への保存（ETL）
- RSS によるニュース収集と前処理（raw_news）
- OpenAI（gpt-4o-mini 等）によるニュースセンチメント評価（銘柄ごとの ai_score、マクロセンチメント）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースセンチメントの合成）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）と統計ユーティリティ
- データ品質チェック、マーケットカレンダー管理、監査ログ（発注・約定トレーサビリティ）
- kabuステーション などへの発注・実行（別モジュール想定）

設計上の共通方針:
- ルックアヘッドバイアス対策（target_date を明示、date.today を隠蔽）
- DuckDB を中心に SQL + Python で効率的に処理
- API 呼び出しはリトライ・レートリミット制御・フォールバックを備える
- 冪等性を重視（ON CONFLICT による上書き等）

---

## 機能一覧

主な機能（モジュール別）

- kabusys.config
  - .env / 環境変数管理、自動ロード（.env < .env.local、OS 環境変数優先）
  - 必須設定取り出しと検証（Settings クラス）
- kabusys.data
  - ETL: 差分取得・保存・品質チェック（data.pipeline.run_daily_etl など）
  - J-Quants クライアント（data.jquants_client）：fetch / save / 認証・リトライ・レート制御
  - market_calendar 管理（calendar_management）
  - news_collector: RSS 取得・前処理・SSRF 保護・記事ID生成
  - quality: 欠損・スパイク・重複・日付不整合チェック（QualityIssue）
  - audit: 監査ログ（signal_events / order_requests / executions）スキーマ初期化
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価して ai_scores に書き込む
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロニュースを合成して market_regime に書き込む
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## セットアップ手順

前提:
- Python 3.9+ を想定（typing の union 表記などに依存）。実運用では最新版の Python を推奨します。
- DuckDB を利用するためローカルストレージが必要。

1. リポジトリをクローン / checkout
   - 例: git clone ... && cd project

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必須例（実際の requirements.txt がある場合はそれを使用してください）:
     - pip install duckdb openai defusedxml
   - 開発用途: linters / test ライブラリ等を追加

4. パッケージを開発モードでインストール（任意）
   - pip install -e .

5. 環境変数 / .env の準備
   - プロジェクトルート（pyproject.toml または .git を基準）に `.env` / `.env.local` を配置すると自動で読み込まれます（kabusys.config）。
   - 自動読み込みを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - OPENAI_API_KEY=sk-...
     - KABU_API_PASSWORD=...
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - LOG_LEVEL=INFO
     - KABUSYS_ENV=development  # development | paper_trading | live

6. データディレクトリの作成（必要に応じて）
   - mkdir -p data

---

## 使い方（基本例）

以下は Python REPL / スクリプトでの簡単な利用例です。

- 設定の参照
  - from kabusys.config import settings
  - print(settings.duckdb_path, settings.jquants_refresh_token)

- DuckDB 接続を作成
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行（市場カレンダー / 株価 / 財務 / 品質チェック）
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn, target_date=None)  # target_date を指定することで任意日実行可
  - print(result.to_dict())

- ニュースセンチメント（ai_scores への書き込み）
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - n_written = score_news(conn, target_date=date(2026, 3, 20))  # target_date に対するウィンドウを処理
  - print("written:", n_written)

- 市場レジーム判定（market_regime への書き込み）
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - score_regime(conn, target_date=date(2026, 3, 20))

- 監査DB 初期化（監査ログ用 DuckDB）
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")  # :memory: も可

- 研究: ファクター計算
  - from kabusys.research.factor_research import calc_momentum
  - from datetime import date
  - momentum = calc_momentum(conn, target_date=date(2026,3,20))
  - # z-score 正規化
  - from kabusys.data.stats import zscore_normalize
  - normed = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])

注意点:
- OpenAI を使用する関数は api_key 引数を受け取りますが、指定しない場合は環境変数 OPENAI_API_KEY を参照します。
- 全ての「target_date」はルックアヘッドバイアスを避けるため明示的に扱われます。date.today() に依存しない実装です。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
- KABU_API_PASSWORD: kabuステーション API パスワード
- KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると .env 自動ロードを無効化

.env の読み込み優先順位:
- OS 環境変数 > .env.local > .env

---

## ディレクトリ構成

主要なファイルとモジュール構成（src/kabusys 以下を抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数 / 設定管理
  - ai/
    - __init__.py            # score_news を公開
    - news_nlp.py            # ニュースセンチメント（銘柄別 ai_scores）
    - regime_detector.py     # 市場レジーム判定（market_regime）
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント: fetch / save / get_id_token
    - pipeline.py            # ETL パイプライン（run_daily_etl 他）
    - calendar_management.py # market_calendar 関連ユーティリティ
    - news_collector.py      # RSS 取得・前処理（raw_news 生成）
    - quality.py             # データ品質チェック
    - stats.py               # 統計ユーティリティ（zscore_normalize）
    - audit.py               # 監査ログ（スキーマ & 初期化）
    - etl.py                 # ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py     # calc_momentum / calc_value / calc_volatility
    - feature_exploration.py # calc_forward_returns / calc_ic / factor_summary / rank
  - ai/*, research/* にテスト対象のロジックやユーティリティが含まれます。

（実際のリポジトリでは tests/、scripts/、docs/ などが存在する可能性があります）

---

## 実運用上の注意

- API キー・トークン類は安全に管理してください（.env はバージョン管理対象から除外）。
- OpenAI の利用はコストが発生します。batch サイズ・呼び出し頻度を調整してください。
- J-Quants のレート制限（120 req/min）を守る実装が含まれていますが、大量取得やパラレル実行時は追加の制御が必要です。
- DuckDB のファイルパスはバックアップ・排他制御を考慮してください（複数プロセスの同時書き込み等）。
- audit スキーマは監査目的で削除しない設計です。Migration/Schema 管理を確実に行ってください。
- テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を使い .env 自動ロードを無効化できます。

---

必要であれば、README に動作例（コマンドラインスクリプト、systemdユニット、Dockerfile、requirements.txt）や
API の詳細（関数仕様・引数・戻り値の表）を追加で作成できます。どの情報を優先して追加しますか？