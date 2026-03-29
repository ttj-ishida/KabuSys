# KabuSys

日本株自動売買プラットフォーム用ライブラリ / ツール群

このリポジトリは、J-Quants や RSS / OpenAI 等を組み合わせて日本株向けのデータパイプライン・ファクター計算・ニュース NLP・市場レジーム判定・監査ログ等を提供する内部ライブラリ群です。ETL、データ品質チェック、AI ベースのニュースセンチメント、レジーム判定、監査テーブル初期化など、アルゴリズムトレーディングの基盤機能を想定しています。

バージョン: 0.1.0

---

## 主要機能

- データ取得 / ETL
  - J-Quants API から株価（OHLCV）、財務データ、JPX カレンダーを差分取得して DuckDB に保存
  - 差分更新 / バックフィル、ページネーション、トークン自動リフレッシュ、レート制御（120 req/min）
- データ品質チェック
  - 欠損値、スパイク（急変）、重複、日付不整合などの検出
- ニュース収集
  - RSS フィードの安全な取得（SSRF 対策、gzip 上限、トラッキング除去）と raw_news テーブルへの冪等保存
- ニュース NLP（OpenAI）
  - 銘柄ごとにニュースをまとめて LLM に投げ、センチメント（ai_scores）を保存
  - レスポンス検証・スコアクリップ・バッチ送信・リトライ制御を実装
- 市場レジーム判定（AI + テクニカル）
  - ETF（1321）の 200 日 MA 乖離とマクロニュースセンチメントを合成して market_regime に書き込み
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算、将来リターン、IC 計算、Zスコア正規化
- 監査ログ（トレース）
  - signal_events / order_requests / executions 等の監査テーブルを DuckDB に冪等で作成・初期化
- 設定管理
  - .env 自動ロード（プロジェクトルート推定）、必須環境変数チェック、環境（development/paper_trading/live）管理

---

## セットアップ手順（ローカル開発向け）

前提:
- Python 3.10 以上（PEP 604 の `X | Y` 型などを使用）
- DuckDB を利用（ローカルファイルまたは :memory:）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成・有効化
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 必要なパッケージをインストール
   - 最低限の依存:
     ```
     pip install duckdb openai defusedxml
     ```
   - 開発用に requirements.txt / pyproject がある場合はそちらを利用してください（本コードベースでは仮想環境に直接必要ライブラリをインストールしてください）。

4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` または `.env.local` を置くと自動読み込みされます（自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 最低限必要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN: Slack Bot トークン（必須）
     - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
   - オプション:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると .env の自動読み込みを無効化できます
     - DUCKDB_PATH: DuckDB のファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite のパス（デフォルト data/monitoring.db）

   - .env の一例:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

5. 初期 DB 構造（監査ログなど）を用意
   - 監査ログ専用 DB を初期化する例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     # conn を使って以降の操作が可能
     ```

---

## 使い方（代表的な API）

以下はライブラリの代表的な使い方例です。実環境ではログ設定やエラーハンドリングを適切に追加してください。

- 日次 ETL を実行（DuckDB 接続を作成して実行）
  ```python
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # デフォルトで今日の日付を対象に ETL を実行
  print(result.to_dict())
  ```

- ニュースセンチメント（OpenAI）でスコアを付与
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  cnt = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"scored {cnt} stocks")
  ```

- 市場レジーム判定（1321 を参照）を実行
  ```python
  from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査スキーマの初期化（既存接続に監査テーブルを追加）
  ```python
  from kabusys.data.audit import init_audit_schema
  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

- 研究用: モメンタム計算や Z スコア正規化
  ```python
  from kabusys.research.factor_research import calc_momentum
  from kabusys.data.stats import zscore_normalize
  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, date(2026, 3, 20))
  normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])
  ```

---

## 重要な設計ポイントと運用注意

- Look-ahead バイアス対策:
  - バックテストや信頼性のため、各モジュールは内部で date.today()/datetime.today() を不用意に参照しないよう設計されています。target_date を明示的に渡して使用してください。
- 冪等性:
  - J-Quants データ保存やニュース保存、監査テーブル初期化などは冪等性（ON CONFLICT / INSERT ... DO UPDATE 等）に配慮しています。
- レート制御・リトライ:
  - J-Quants クライアントは固定間隔のスロットリングと指数バックオフを備えています。
  - OpenAI 呼び出し部はレート制限・ネットワークエラー・5xx に対するリトライと適切なフォールバック（ゼロスコア等）を行います。
- セキュリティ:
  - RSS の収集では SSRF 対策（リダイレクト先検査・プライベートアドレス拒否）や XML の安全パーシング（defusedxml）を利用しています。
- 環境変数自動ロード:
  - パッケージはプロジェクトルートの `.env` / `.env.local` を自動的に読み込みます（必要に応じ `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化）。

---

## ディレクトリ構成（主要ファイルの概要）

（src/kabusys 以下を想定）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定管理。自動 .env 読み込み、settings オブジェクトの公開。
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースの集約・OpenAI でのセンチメント評価、ai_scores テーブルへ書き込み
    - regime_detector.py
      - ETF（1321）の MA 乖離とマクロニュースを合成して market_regime を計算
  - data/
    - __init__.py
    - calendar_management.py
      - 市場カレンダー管理・営業日の判定・calendar_update_job
    - etl.py
      - ETLResult 再エクスポート（pipeline.ETLResult）
    - pipeline.py
      - 日次 ETL 実行（run_daily_etl）、個別 ETL ジョブ（prices/financials/calendar）
    - stats.py
      - zscore_normalize などの統計ユーティリティ
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py
      - 監査ログ（signal_events, order_requests, executions）の DDL・初期化関数
    - jquants_client.py
      - J-Quants API との通信、取得・保存ロジック（fetch_* / save_*）
    - news_collector.py
      - RSS フィード取得・前処理・raw_news への保存（SSRF 対策、XML 安全パース）
  - research/
    - __init__.py
    - factor_research.py
      - Momentum / Value / Volatility 等のファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC（スピアマン）計算、統計サマリー
  - monitoring/ (README には示されていないが __all__ に含まれる可能性あり)
  - execution/, strategy/ 等（プロジェクト内で売買ロジック・実行エンジンが想定される場所）

---

## ライセンス / 貢献

この README はコードベースの説明を目的としています。実際のライセンス・貢献ガイドライン（CONTRIBUTING.md）や .env.example、pyproject.toml / requirements.txt が存在する場合はそちらを参照してください。

---

何か特定の利用シナリオ（ETL スケジューリング、監視・アラート設定、バックテスト連携など）について README に追記したい場合は要件を教えてください。必要に応じてサンプルスクリプトや運用手順を追加します。