# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP スコアリング、マーケットレジーム判定、リサーチ用ファクター計算、監査ログ（トレーサビリティ）などを備えたモジュール群を提供します。

主な設計方針：
- バックテストでのルックアヘッドバイアス回避（date/target_date ベースの設計）
- DuckDB を中心としたローカルデータベース運用
- 外部 API 呼び出し（J-Quants / OpenAI / RSS）に対する堅牢なリトライ・フォールバック
- ETL / 品質チェック / 監査ログを備えたデータプラットフォーム志向

---

## 機能一覧

- 環境設定管理
  - .env 自動読み込み（プロジェクトルート検出）
  - settings オブジェクトによる型付きアクセス（J-Quants, kabu API, Slack, DB パスなど）

- データ ETL（kabusys.data.pipeline）
  - J-Quants API からの株価（daily_quotes）、財務（statements）、市場カレンダー取得
  - 差分取得・バックフィル・冪等保存（DuckDB へ ON CONFLICT で保存）
  - 品質チェック（欠損・スパイク・重複・将来日付・非営業日データ検出）

- ニュース収集（kabusys.data.news_collector）
  - RSS 取得・正規化・SSRF 対策・トラッキング除去・raw_news への保存補助

- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を使った銘柄ごとのセンチメントスコア化
  - バッチ/チャンク送信、リトライ、レスポンス検証、ai_scores への保存処理

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（70%）とマクロニュース LLM センチメント（30%）の合成で 'bull'/'neutral'/'bear' 判定
  - LLM 呼び出しリトライ・フェイルセーフ処理

- リサーチ（kabusys.research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Z スコア正規化

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions を中心とした監査テーブル定義と初期化ユーティリティ
  - order_request_id を冪等キーとして二重発注防止を想定

- J-Quants クライアント（kabusys.data.jquants_client）
  - レートリミット制御、トークンリフレッシュ、ページネーション対応、DuckDB へ保存するユーティリティ

---

## 要件（主な外部ライブラリ）

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- その他標準ライブラリ（urllib, json, datetime, logging 等）

（実際の pyproject.toml / requirements はプロジェクトに合わせてください）

---

## セットアップ手順（ローカル）

1. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. パッケージのインストール（開発インストール）
   - pip install -e .

   もしくは必要パッケージ単体インストール例：
   - pip install duckdb openai defusedxml

3. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を作成すると自動で読み込まれます（起動時）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   .env のサンプル（.env.example）
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # Kabuステーション API
   KABU_API_PASSWORD=your_kabu_api_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # Slack（通知など）
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789

   # OpenAI
   OPENAI_API_KEY=sk-...

   # DB パス
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 動作モード (development | paper_trading | live)
   KABUSYS_ENV=development

   # ログレベル
   LOG_LEVEL=INFO
   ```

---

## 使い方（代表的な例）

以下は Python スクリプトからの利用例です。実行前に .env に必要な鍵を用意してください（または明示的に関数に渡す）。

- DuckDB 接続準備（例）
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL 実行（市場カレンダー → 株価 → 財務 → 品質チェック）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのスコアリング（OpenAI API キーは環境変数または引数）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("written:", n_written)
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（監査専用 DB を作る）
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可
  ```

- リサーチ用ファクター計算（例：モメンタム）
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  print(len(records), "銘柄の計算結果を取得")
  ```

- 設定の参照（settings）
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.is_paper, settings.is_live)
  ```

注意点：
- OpenAI 呼び出しは API 制限・課金対象です。API キーの取り扱いに注意してください。
- 実際に発注や本番での取引を行うモジュール（execution 等）が存在する場合は、必ず paper_trading で十分テストしてから live モードへ移行してください。
- ETL / API 呼び出しはネットワーク・API 側エラーを想定したリトライやフォールバックが実装されていますが、ログ確認・監視を必ず行ってください。

---

## 環境変数と設定（settings）

kabusys.config.Settings を通じて以下の主要設定にアクセスできます（例）：
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN（必須）
- SLACK_CHANNEL_ID（必須）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- KABUSYS_ENV（development / paper_trading / live）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）

自動読み込みはプロジェクトルートの `.env` / `.env.local` を読み込みます。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成

（主要ファイルのみ抜粋。実際のリポジトリには pyproject.toml, tests 等が含まれる想定）

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
      - news_collector.py
      - calendar_management.py
      - quality.py
      - stats.py
      - audit.py
      - (その他 data 関連ユーティリティ)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/__init__.py
    - (strategy/, execution/, monitoring/ などのパッケージは __all__ に含まれますが、ここには主要モジュールを示しています)

各モジュールの役割：
- ai/*.py: OpenAI を用いた NLP・マーケット判定ロジック
- data/jquants_client.py: J-Quants API クライアント（取得 + DuckDB 保存）
- data/pipeline.py: 日次 ETL パイプラインのエントリポイント
- data/news_collector.py: RSS 収集と前処理
- data/quality.py: データ品質チェック
- data/audit.py: 監査ログスキーマ初期化
- research/*.py: ファクター算出・統計解析ユーティリティ

---

## 運用上の注意

- 本リポジトリは実運用での発注・資金管理に関わるコードを含む可能性があります。実際に発注を行う場合は、必ず isolation（paper_trading 環境）での徹底的な検証を行ってください。
- データベースファイル（DuckDB）はバックアップやマイグレーション手順を検討してください。
- OpenAI / J-Quants の API キーは外部から漏洩しないよう秘匿してください。
- ログ（LOG_LEVEL）を適切に設定し、障害時の原因解析に備えてください。

---

もし README に含めたい追加の利用例（例：具体的な ETL スケジュール cron 系の例、Slack 通知の使い方、Kabu ステーションへの約定フローなど）があれば、対象のユースケースに合わせて追記します。