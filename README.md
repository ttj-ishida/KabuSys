# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
株価・財務・ニュースのETL、ニュースセンチメントのAI評価、ファクター計算、マーケットカレンダー管理、監査ログなど、アルゴリズムトレーディングおよびリサーチに必要な機能をモジュール単位で提供します。

---

## 主な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API からの日次株価（OHLCV）取得・保存
  - 財務データ（四半期BS/PL）取得・保存
  - JPX マーケットカレンダー取得・保存
  - 差分更新・バックフィル・品質チェック（欠損／スパイク／重複／日付整合性）
- ニュース収集・NLP
  - RSS からニュース収集（SSRF 対策、トラッキングパラメータ除去、受信サイズ制限）
  - OpenAI を用いたニュースごとのセンチメント評価（gpt-4o-mini、JSON Mode）
  - 銘柄別の AI スコア ai_scores への書き込み（バッチ処理、リトライ、検証）
- 市場レジーム判定
  - ETF（1321）の200日移動平均乖離とマクロニュースのLLMセンチメントを合成し、
    日次で market_regime を判定（bull / neutral / bear）
- リサーチ / ファクター計算
  - Momentum / Value / Volatility 等のファクター計算
  - 将来リターン計算、IC（情報係数）、ファクター統計サマリー
  - Zスコア正規化ユーティリティ
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブル定義・初期化
  - 発注フローの UUID ベースのトレース設計
- 設定管理
  - .env ファイル / 環境変数からの設定読み込み（自動ロード、優先順位: OS env > .env.local > .env）
  - 必須環境変数チェック、環境種別（development/paper_trading/live）・ログレベル検証

---

## 必要要件（依存関係）

- Python 3.10+
- 主要ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ（urllib, json, datetime 等）を利用

具体的なバージョンはプロジェクトの pyproject.toml / requirements に合わせてください。

---

## 環境変数（重要）

以下は本コードベースで参照される主な環境変数です（必須のものに注意）。

必須（実行する機能に依存して設定してください）:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン（ETL）
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン（通知機能利用時）
- SLACK_CHANNEL_ID — Slack チャンネル ID（通知機能利用時）
- KABU_API_PASSWORD — kabuステーション API パスワード（発注機能等）
- OPENAI_API_KEY — OpenAI API キー（AI 機能: news_nlp / regime_detector）

任意 / デフォルト値あり:
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視用 DB パス（デフォルト data/monitoring.db）

自動 .env 読み込みについて:
- パッケージは起点ファイルから親ディレクトリを探索して `.git` または `pyproject.toml` のあるプロジェクトルートを特定し、以下の順で自動読み込みします:
  1. OS 環境変数（既存）を尊重
  2. .env（override=False、未設定キーのみセット）
  3. .env.local（override=True、既存の OS 環境変数は保護）
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順

1. Python 環境を作成（推奨: venv / pyenv）
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクト配布の requirements.txt / pyproject.toml があればそれに従ってください）
   - 開発用: pip install -e .

3. 環境変数 / .env を用意
   - ルートに .env（および任意で .env.local）を作成。少なくとも JQUANTS_REFRESH_TOKEN と OPENAI_API_KEY を設定してください。
   - 例:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb

4. データディレクトリ作成（必要に応じて）
   - mkdir -p data

5. DuckDB 初期化（監査ログ用）
   - Python スクリプトから init_audit_db を呼ぶ（下記参照）

---

## 使い方（簡単な例）

以下は主要な操作例です。実行は Python REPL / スクリプト内で行います。

- DuckDB 接続の確立（設定ファイルからパスを取得）
  - from kabusys.config import settings
    import duckdb
    conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する
  - from kabusys.data.pipeline import run_daily_etl
    from kabusys.config import settings
    import duckdb, datetime
    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=datetime.date(2026, 3, 20))
    print(result.to_dict())

- ニュースの AI スコアリング（score_news）
  - from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect(str(settings.duckdb_path))
    n = score_news(conn, target_date=datetime.date(2026, 3, 20))
    print(f"scored {n} codes")

  - 注意: OPENAI_API_KEY が環境変数に設定されているか、api_key 引数で渡す必要があります。

- 市場レジーム判定（score_regime）
  - from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect(str(settings.duckdb_path))
    score_regime(conn, target_date=datetime.date(2026, 3, 20))

  - 内部で gpt-4o-mini を呼びます。APIキーは同様に必要です。

- 監査ログ DB を初期化する
  - from kabusys.data.audit import init_audit_db
    conn_audit = init_audit_db("data/audit.duckdb")
    # conn_audit を使って監査テーブルへアクセスできます

- J-Quants から直接データを取得したい場合（低レベル）
  - from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
    token = get_id_token()  # 環境の JQUANTS_REFRESH_TOKEN を使って取得
    records = fetch_daily_quotes(id_token=token, date_from=date(2026,1,1), date_to=date(2026,3,1))

---

## 実装上の注意点 / 設計方針（抜粋）

- ルックアヘッドバイアス対策
  - 各モジュール（AI評価・ETL・リサーチ）は datetime.today() を直接参照しないよう設計されています。必ず target_date を引数として受け取り、履歴のみを参照します。
- 冪等性
  - ETL の保存は ON CONFLICT DO UPDATE 等で冪等に行われ、重複を上書きして一貫した状態を保ちます。
- フェイルセーフ
  - AI API 呼び出しや外部 API の失敗は部分失敗として扱い、可能な限り処理を継続する設計（フォールバック値や警告ログ）です。
- セキュリティ
  - RSS 取得では SSRF 対策、受信サイズ制限、defusedxml を利用した XML サニタイズなどを実装しています。
- リトライ & レート制御
  - J-Quants クライアントはレート制限（120 req/min）に対応する RateLimiter、および 401 リフレッシュ / 5xx や 429 に対する指数バックオフを備えています。
- OpenAI 呼び出し
  - news_nlp / regime_detector は gpt-4o-mini を JSON Mode で利用する想定。レスポンスのバリデーションとリトライを実装しています。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/
      - __init__.py
      - jquants_client.py
      - pipeline.py
      - etl.py
      - quality.py
      - stats.py
      - news_collector.py
      - calendar_management.py
      - audit.py
      - pipeline.py
      - etl.py
      - audit.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/
      - ...（ファクター／リサーチ関数）
    - (その他)
      - strategy/ (戦略層; エントリは __all__ に含むが実装は用途に応じて拡張)
      - execution/ (発注実装)
      - monitoring/ (監視・アラート)

※ 上記は現コードベースから抽出したファイル構成の抜粋です。実際のプロジェクトルートには pyproject.toml / .git / README.md 等が含まれる想定です。

---

## よくある操作例（コマンド）

- 開発環境セットアップ
  - python -m venv .venv
  - . .venv/bin/activate
  - pip install -e ".[dev]"  # (もし extras があれば)

- ETL を毎日実行するジョブ（例）
  - 実運用ではスケジューラ（cron / Airflow / Prefect 等）から Python スクリプトを呼び出して run_daily_etl を実行します。

---

## サポート / 貢献

- バグ報告や改善提案は Issue を立ててください。
- コントリビューション時はテスト（ユニットテスト）と静的型チェックを推奨します。
- セキュリティに関わる報告はプライベートにお知らせください。

---

以上が README の概要です。必要であれば、具体的な .env.example、pyproject.toml の推奨設定、サンプルスクリプト（ETL 実行・監査 DB 初期化・AI スコアリングのサンプル）を追補します。どの情報を加えれば良いか教えてください。