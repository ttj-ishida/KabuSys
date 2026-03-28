# KabuSys

日本株自動売買システム用のライブラリ群（データプラットフォーム、リサーチ、AI ニュース解析、監査ログなど）。  
このリポジトリは ETL、ニュース収集・NLP、ファクター計算、研究用ユーティリティ、監査用テーブル定義などを含み、バックテスト／運用のデータ基盤と研究ワークフローをサポートします。

バージョン: 0.1.0

---

## 主要な機能

- データ ETL（J-Quants API 経由）
  - 日次株価（OHLCV）、財務データ、JPX マーケットカレンダーの差分取得・保存
  - DuckDB へ冪等保存（ON CONFLICT / UPDATE）
  - 品質チェック（欠損・重複・スパイク・日付不整合）
- カレンダー管理
  - 営業日判定、前後営業日検索、レンジ内営業日取得
  - JPX カレンダーの夜間差分更新ジョブ
- ニュース収集（RSS）
  - RSS フィードの取得・前処理・raw_news への冪等保存
  - SSRF / XML Bomb / レスポンスサイズ制限等の安全対策
- ニュース NLP（OpenAI）
  - 銘柄別ニュースを LLM（gpt-4o-mini）でセンチメント評価し ai_scores に保存
  - レート制限・リトライ・レスポンスバリデーション対応
- 市場レジーム判定（MA200 + マクロセンチメント合成）
  - ETF 1321 の 200 日 MA 乖離とマクロニュースセンチメントを組み合わせて daily に判定
- 監査ログ（監査テーブル群）
  - signal_events / order_requests / executions 等のスキーマ定義・初期化ユーティリティ
  - 監査用 DuckDB の初期化関数を提供
- 研究用ユーティリティ
  - モメンタム・ボラティリティ・バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、Z-score 正規化、統計サマリー

---

## 動作環境・依存関係（概要）

- Python 3.10+
- 主要ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- その他: 標準ライブラリで多く実装されていますが、実行環境に合わせて上記パッケージをインストールしてください。

例:
pip install duckdb openai defusedxml

（プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使ってください）

---

## 環境変数（必須 / 主要）

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

必須（使用する機能に応じて）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL 実行に必須）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 呼び出し時に必要。関数に api_key を渡すことも可）
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注を行うモジュールで使用）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID — Slack 通知に使用

任意（デフォルト値あり）:
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — デフォルト data/monitoring.db

サンプル .env（例）:
export JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順（簡易）

1. Python 環境作成（推奨: venv）
   python -m venv .venv
   source .venv/bin/activate

2. 依存ライブラリをインストール
   pip install duckdb openai defusedxml

   （プロジェクトに pyproject.toml がある場合は pip install -e . を推奨）

3. 環境変数設定
   プロジェクトルートに `.env` を作成するか、OS 環境変数を設定する。
   必要なトークン類（JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY 等）を用意。

4. データディレクトリ作成（必要に応じて）
   mkdir -p data

5. DuckDB 接続の確認
   ライブラリから DuckDB を開いて問題なく接続できるか確認します（下記 Usage 参照）。

---

## 基本的な使い方（コード例）

以下は主要 API の使い方サンプルです。実行には前述の環境変数が必要です。

- ETL（日次パイプライン）を実行する:
  from datetime import date
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())

- ニューススコア生成（LLM を使って銘柄ごとにスコア）:
  from datetime import date
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))
  from kabusys.ai.news_nlp import score_news
  count = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key None → 環境変数 OPENAI_API_KEY を使用
  print(f"Scored {count} codes")

- 市場レジーム判定:
  from datetime import date
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026,3,20), api_key=None)

- 監査ログ DB の初期化:
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")  # ":memory:" も可

- ファクター計算（研究用）:
  from datetime import date
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))
  from kabusys.research.factor_research import calc_momentum
  res = calc_momentum(conn, target_date=date(2026,3,20))
  # res は dict のリスト

- 設定参照:
  from kabusys.config import settings
  print(settings.duckdb_path, settings.env)

注意:
- score_news / score_regime は OpenAI API をコールします。api_key を引数で渡すか OPENAI_API_KEY を環境変数で設定してください。
- ETL / save 系は DuckDB のスキーマ（raw_prices 等）が前提です。スキーマ初期化はプロジェクト側のスクリプトで行ってください（スキーマ定義は data.audit などのモジュールを参考にできます）。

---

## 良く使うコマンド（例）

- ローカルで ETL を一回実行（Python スクリプトから呼ぶ例）:
  python -c "from datetime import date; import duckdb; from kabusys.config import settings; from kabusys.data.pipeline import run_daily_etl; conn=duckdb.connect(str(settings.duckdb_path)); print(run_daily_etl(conn, date.today()).to_dict())"

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
  - 環境変数の読み込みと Settings クラス（自動 .env 読み込みロジック含む）
- ai/
  - __init__.py
  - news_nlp.py            — ニュースセンチメント（OpenAI 連携、ai_scores 書き込み）
  - regime_detector.py    — 市場レジーム判定（MA200 + マクロセンチメント合成）
- data/
  - __init__.py
  - calendar_management.py — 市場カレンダー管理（営業日検索・更新ジョブ）
  - pipeline.py            — ETL パイプライン（run_daily_etl など）
  - jquants_client.py      — J-Quants API クライアント（fetch/save 関数、ID トークン自動リフレッシュ）
  - news_collector.py      — RSS 収集（セキュリティ対策つき）
  - quality.py             — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py               — 監査ログ（監査テーブル DDL / 初期化関数）
  - stats.py               — 汎用統計ユーティリティ（Z-score）
  - pipeline.py            — ETL の高レベル API / ETLResult 定義
  - etl.py                 — 簡易再エクスポート（ETLResult）
- research/
  - __init__.py
  - factor_research.py     — モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py — 将来リターン、IC、統計サマリー等
- research/... (その他の研究用モジュール)
- 他: strategy / execution / monitoring 等のパッケージが __all__ に含まれる想定

（実際のファイル位置・追加モジュールはリポジトリ全体を参照してください。）

---

## 設計上の注意点 / 運用のヒント

- Look-ahead バイアス回避:
  - 各処理は datetime.today() を直接参照しない設計や、SQL の date < target_date 条件など、バックテストでのルックアヘッドを避ける配慮がなされています。バックステスト用途では target_date を明示的に渡して利用してください。
- 冪等性:
  - J-Quants 保存関数や監査テーブル作成は冪等（ON CONFLICT / DO UPDATE）を意識して実装されています。
- フェイルセーフ:
  - LLM/API エラー時は例外を投げずフォールバック（0.0 スコア等）で継続する箇所があります。ログと監視を設定して異常検知を行ってください。
- 自動 .env 読み込み:
  - パッケージはプロジェクトルート（.git または pyproject.toml を基準）から .env / .env.local を自動読み込みします。テスト時などで無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## お問い合わせ / 贡献

- この README はコードベースの主要なユーティリティと想定される使い方の要約です。実行前に各モジュールのドキュメントストリングやログ出力を参照し、環境変数や DB スキーマが正しく構成されていることを確認してください。

--- 

以上。必要があれば各モジュールごとの詳細な API ドキュメント（引数・戻り値・例外）やセットアップ用スクリプト例、docker-compose / CI 設定のテンプレートも追加で作成します。どの部分を詳述しましょうか？