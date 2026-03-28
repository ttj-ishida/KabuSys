# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP スコアリング、ファクター計算、監査ログ／発注トレーサビリティ、マーケットカレンダー管理、バックテスト・リサーチ用ユーティリティなどを含みます。

---

## 主な特徴（機能一覧）

- データ取得（J-Quants API）
  - 株価日足（OHLCV）、財務データ、上場銘柄リスト、JPX カレンダーの差分取得（ページネーション対応、リトライ・レート制御つき）
  - DuckDB への冪等保存（ON CONFLICT / UPDATE）
- ETL パイプライン
  - 日次 ETL（calendar / prices / financials）と品質チェックの一括実行
  - 部分失敗に強い設計（各ステップは独立したエラーハンドリング）
- ニュース収集（RSS） & ニュース NLP（OpenAI）
  - RSS 取得、前処理、raw_news / news_symbols への保存
  - 記事を銘柄ごとに集約して OpenAI（gpt-4o-mini）でセンチメント評価（JSON Mode）
  - レスポンス検証、スコアクリップ、バッチ処理、リトライ
- 市場レジーム判定（AI + テクニカル）
  - ETF（1321）の200日移動平均乖離とマクロニュースセンチメントを合成して日次で 'bull'/'neutral'/'bear' を判定
- 研究・ファクター計算
  - Momentum / Volatility / Value 等の定量ファクターを DuckDB 上で計算
  - 将来リターン計算、IC（Spearman）やファクター統計サマリ
- データ品質チェック
  - 欠損、スパイク、重複、将来日付や非営業日のデータ検出
- 監査ログ（audit）
  - signal → order_request → execution の階層的トレーサビリティ用テーブル定義・初期化
  - 発注冪等性を前提としたスキーマ設計

---

## 必要条件

- Python 3.9+
- 主要依存パッケージ（一例）
  - duckdb
  - openai
  - defusedxml

必要に応じて pyproject.toml / requirements.txt を用意している想定です。実行環境に合わせてインストールしてください。

例:
pip install duckdb openai defusedxml

---

## 環境変数 / 設定

このパッケージは環境変数（またはプロジェクトルートの `.env`, `.env.local`）から設定を読み込みます。自動読み込みは、パッケージルート（.git または pyproject.toml がある階層）を探索して行われます。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数:

- JQUANTS_REFRESH_TOKEN - J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD - kabu API パスワード（必須）
- KABU_API_BASE_URL - kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN - Slack ボットトークン（必須）
- SLACK_CHANNEL_ID - Slack チャンネル ID（必須）
- DUCKDB_PATH - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH - SQLite（monitoring）ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV - 環境 ('development' / 'paper_trading' / 'live')（デフォルト: development）
- LOG_LEVEL - ログレベル（'DEBUG','INFO','WARNING','ERROR','CRITICAL'）
- OPENAI_API_KEY - OpenAI 呼び出し用 API キー（AI モジュールで使用）

.env ファイルの読み込みルール:
- OS 環境変数 > .env.local > .env の順で優先
- `.env.local` は `.env` を上書きする（override）

設定オブジェクトは `kabusys.config.settings` としてアクセス可能です。

---

## セットアップ手順（例）

1. リポジトリをクローン / 配布パッケージを展開
2. Python 仮想環境を作成・有効化
3. 依存パッケージをインストール
   - 例: pip install -r requirements.txt
   - または: pip install duckdb openai defusedxml
4. プロジェクトルートに `.env`（および任意で `.env.local`）を作成して必要な環境変数を設定
   - 例:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
5. DuckDB 用データディレクトリを準備（settings.duckdb_path の親ディレクトリを作成）
   - 例: mkdir -p data

---

## 使い方（主要 API と実行例）

以下は基本的な利用例です。実行前に `settings` の必須値（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY など）を設定してください。

- DuckDB 接続準備（例）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # target_date を指定（省略時は今日）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP による銘柄スコアリング（score_news）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY が環境変数に設定されている場合、api_key 引数は不要
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written {n_written} ai_scores")
  ```

- 市場レジーム判定（score_regime）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  # OpenAI キーを引数で渡すことも可能
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ用 DuckDB を初期化
  ```python
  from kabusys.data.audit import init_audit_db

  # ":memory:" でインメモリ DB も可能
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- News ウィンドウ計算（テスト用ユーティリティ）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import calc_news_window

  start, end = calc_news_window(date(2026, 3, 20))
  print(start, end)  # UTC naive datetime を返す（前日 06:00 ～ 23:30 UTC）
  ```

注意点:
- AI 系（news_nlp, regime_detector）は OpenAI API を呼び出します。`OPENAI_API_KEY` を環境変数で設定するか、各関数に `api_key` を渡してください。
- AI 呼び出しは外部 API に依存するため、テスト時はモック（unittest.mock.patch）で `_call_openai_api` を差し替える想定です。
- ETL / 保存処理は冪等性を念頭に設計されていますが、DB スキーマが用意されていることが前提です。

---

## ディレクトリ構成（概要）

プロジェクトの主要なモジュール配置（src/kabusys）:

- kabusys/
  - __init__.py (パッケージ初期化)
  - config.py (環境変数・設定管理)
  - ai/
    - __init__.py (score_news を公開)
    - news_nlp.py (ニュースの集約・OpenAI によるスコアリング)
    - regime_detector.py (ETF MA + マクロ記事センチメント合成による市場レジーム判定)
  - data/
    - __init__.py
    - calendar_management.py (JPX カレンダー管理・営業日ユーティリティ)
    - etl.py (ETL エントリ公開)
    - pipeline.py (日次 ETL 実装、ETLResult)
    - stats.py (統計ユーティリティ: zscore_normalize)
    - quality.py (データ品質チェック)
    - audit.py (監査ログスキーマ初期化・audit DB ユーティリティ)
    - jquants_client.py (J-Quants API クライアント + DuckDB 保存ユーティリティ)
    - news_collector.py (RSS 取得・前処理・SSRF 対策)
    - (その他: pipeline/etl 抽象など)
  - research/
    - __init__.py (公開 API)
    - factor_research.py (Momentum/Volatility/Value 等)
    - feature_exploration.py (forward returns, IC, rank, summary)
  - ai, execution, monitoring...（パッケージ __all__ に宣言されている他モジュール群の配置想定）

（上記は主要ファイルの抜粋です。実際のファイル一覧はリポジトリを参照してください）

---

## 設計上の注意点 / ポリシー

- Look-ahead バイアス防止:
  - AI モジュールや ETL は内部で datetime.today()/date.today() を直接参照しないように設計されています（関数引数で日付を与える）。
  - DB クエリは target_date 未満 / 以前の行のみ参照する等の配慮があります。
- 冪等性:
  - J-Quants からの保存は ON CONFLICT DO UPDATE を使用しているため、再実行に耐えられます。
  - 監査ログの order_request_id は冪等キーとして設計されています。
- フェイルセーフ:
  - AI API 失敗時はゼロスコアやスキップで継続する設計（例: macro_sentiment = 0.0）。
- テスト容易性:
  - 外部 API 呼び出し部分（OpenAI / HTTP）を差し替えやすい実装になっています（内部 _call_openai_api をモック等）。

---

## 参考（追加メモ）

- 自動で .env を読み込ませたくないテストや特殊環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD` を設定してください。
- `KABUSYS_ENV` は development / paper_trading / live のいずれかを指定し、is_live / is_paper / is_dev プロパティで参照できます。

---

この README はコードベースの公開 API と主要なワークフローの概要をまとめたものです。詳細な使い方・スキーマ定義・運用手順は各モジュール（data/jquants_client.py, data/pipeline.py, ai/news_nlp.py など）の docstring を参照してください。