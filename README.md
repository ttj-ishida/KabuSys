# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買補助ライブラリ群です。J-Quants / kabuステーション / OpenAI 等と連携して、データETL、品質チェック、ニュースNLP、マーケットレジーム判定、監査ログなどを提供します。

---

## プロジェクト概要

KabuSys は日本市場向けに設計された内部ツール群で、主に以下を実現します。

- J-Quants API から株価・財務・カレンダーを差分取得して DuckDB に保存する ETL パイプライン
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース記事の収集・前処理と OpenAI を使った銘柄センチメント（ai_scores）生成
- マーケットレジーム判定（ETF 1321 の MA とマクロニュースの LLM センチメント合成）
- 研究用ファクター計算・特徴量解析ユーティリティ
- 発注・約定までの監査ログ（audit テーブル群）初期化ユーティリティ
- 安全対策（SSRF防止、API リトライ、レート制御、冪等保存 等）

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl、run_prices_etl、run_financials_etl、run_calendar_etl）
  - J-Quants クライアント（取得・保存・認証・レート制御）
  - ニュース収集器（RSS 取得、URL 正規化、SSRF 対策）
  - カレンダー管理（営業日判定、next/prev_trading_day 等）
  - データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを生成して ai_scores へ保存
  - regime_detector.score_regime: MA とマクロニュースで市場レジーム（bull/neutral/bear）を判定して market_regime へ保存
- research/
  - ファクター生成（momentum/value/volatility）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- config:
  - 環境変数管理（.env 自動読み込み、必須チェック、環境判定）

---

## 要件

- Python 3.10+
- 主要依存ライブラリ（代表例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、RSS 等）

（実際の requirements.txt はプロジェクトに合わせて用意してください）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository>
   ```

2. Python 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # Linux / macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   （プロジェクトに requirements.txt / pyproject がある場合はそれを使ってください）
   ```
   pip install duckdb openai defusedxml
   ```

4. 環境変数設定
   プロジェクトルートに `.env`（または `.env.local`）を作成して必要な環境変数を設定します。自動ロードは config モジュールでプロジェクトルート（.git または pyproject.toml を基準）から行われます。

   主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（ai モジュールを使う場合は必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注統合を行う場合）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知を使う場合
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

   .env 自動読み込みを無効化する場合:
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

---

## 使い方（代表的な例）

以下は Python から各機能を呼び出す例です。実行前に必要な環境変数（特に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY）を設定してください。

- DuckDB 接続を作る（例: ファイル DB）
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL を実行（カレンダー・株価・財務・品質チェック）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコア（OpenAI を使用）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written scores: {written}")
  ```

- 市場レジーム判定（ETF 1321 の MA + マクロニュース）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログスキーマの初期化（別 DB に監査専用を作る）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- カレンダー関連ユーティリティ
  ```python
  from datetime import date
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

注意:
- OpenAI 呼び出しはネットワーク/課金を伴います。テスト時は各モジュールの _call_openai_api をモックする設計になっています（unittest.mock.patch 等）。
- ETL / 保存処理は冪等性を考慮して実装されています（ON CONFLICT DO UPDATE 等）。

---

## 環境変数（まとめ）

必須（使う機能に応じて）
- JQUANTS_REFRESH_TOKEN
- OPENAI_API_KEY（ai.news_nlp / ai.regime_detector を使う場合）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Slack 通知を使う場合）
- KABU_API_PASSWORD（kabu API を使う場合）

任意（デフォルトあり）
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL — デフォルト: INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化（値に何か設定すれば無効化）
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi

---

## ディレクトリ構成（主なファイルと役割）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数/.env 読み込みと Settings
  - ai/
    - __init__.py
    - news_nlp.py — ニュースを LLM でスコア化して ai_scores に保存
    - regime_detector.py — マーケットレジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得/保存/認証/レート制御）
    - pipeline.py — ETL パイプライン（run_daily_etl 他）
    - etl.py — ETLResult 再エクスポート
    - news_collector.py — RSS 収集・正規化・保存
    - calendar_management.py — 市場カレンダー管理（営業日判定等）
    - quality.py — データ品質チェック
    - stats.py — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py — 監査ログ（テーブルDDL / 初期化）
  - research/
    - __init__.py
    - factor_research.py — momentum/value/volatility 等のファクター計算
    - feature_exploration.py — 将来リターン、IC、統計サマリー
  - monitoring/, execution/, strategy/, etc. — パッケージ公開のための名前空間（実装はこのリポジトリに依存）

---

## 設計上の注意点 / 実運用の留意点

- ルックアヘッドバイアス対策: モジュール内部は可能な限り datetime.today() を直接参照せず、target_date を明示的に受け取る設計です。バックテストや再現性のため、関数呼び出し時に日付を明示してください。
- 冪等性: ETL の保存処理は基本的に ON CONFLICT / DELETE→INSERT 等で冪等性を維持します。
- OpenAI / ネットワーク呼び出しはリトライ・フェイルセーフ設計（失敗時はゼロスコアやスキップを許容）になっていますが、本番での運用時はログと監視を必須にしてください。
- RSS フェッチ周りは SSRF 対策、サイズ上限、XML の安全パース（defusedxml）を実装していますが、運用環境での追加チェック（プロキシ、タイムアウト監視 等）を推奨します。

---

もし README に追加したい実行コマンド（例: CLI、cron での実行例）、依存関係ファイル（requirements.txt / pyproject.toml）の推奨内容、あるいは具体的な .env.example の雛形が必要であれば教えてください。必要に応じて追記します。