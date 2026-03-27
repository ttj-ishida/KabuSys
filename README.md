# KabuSys

KabuSys は日本株向けの自動売買／データプラットフォームのコードベースです。  
ETL（J-Quants からのデータ収集）、ニュース収集・LLM によるセンチメント評価、ファクター計算、監査ログ（トレーサビリティ）、市場カレンダー管理、監視・発注インターフェースなどの基盤機能を備えています。

バージョン: 0.1.0

---

## 概要

主な目的は「現実の日本株データを蓄積・品質管理し、ニュースや指標（ファクター）を用いて売買判断や研究を行う」ための共通基盤を提供することです。  
設計方針として、バックテストでのルックアヘッドバイアス回避、ETL の冪等性、外部 API のリトライ・レート制限対応、LLM 呼び出しのフェイルセーフ等を重視しています。

---

## 機能一覧

- 設定管理
  - .env ファイルと OS 環境変数の自動読み込み（優先順位: OS > .env.local > .env）
  - 必須環境変数チェック（settings オブジェクト）
  - 自動読み込み無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

- データプラットフォーム（data モジュール）
  - J-Quants API クライアント（ページネーション / レート制御 / リトライ / トークンリフレッシュ対応）
  - ETL パイプライン（価格・財務・カレンダーの差分取得、品質チェック）
  - 市場カレンダー管理（営業日判定、next/prev_trading_day 等）
  - ニュース収集（RSS、SSRF 対策、前処理、冪等保存）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ（signal_events, order_requests, executions）と初期化ユーティリティ
  - 監査用 DuckDB 初期化ヘルパー

- AI（ai モジュール）
  - news_nlp: ニュース記事群を OpenAI（gpt-4o-mini）で銘柄別センチメントスコア化し `ai_scores` に保存
  - regime_detector: ETF（1321）200日 MA 乖離とマクロニュース（LLM）を合成して市場レジーム（bull/neutral/bear）を判定・保存

- 研究（research モジュール）
  - ファクター生成（モメンタム・バリュー・ボラティリティ等）
  - 特徴量探索（将来リターン計算、IC、統計サマリー、ランク変換）
  - 共通統計ユーティリティ（zscore 正規化）

- ユーティリティ
  - DuckDB ベースでのデータ永続化（デフォルトパスは設定で変更可）
  - ロギングレベル設定（`LOG_LEVEL`）
  - 環境別フラグ（`KABUSYS_ENV`: development / paper_trading / live）

---

## 必要な環境変数

主要な環境変数（README の例）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略可、デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI 呼び出しに使用（ai.score_news / ai.score_regime で使用）
- DUCKDB_PATH: DuckDB データベースファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（例: monitoring 用、デフォルト: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

.env 自動読み込みの挙動:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して `.env` と `.env.local` を読み込みます。
- `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動読み込みを無効化できます。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. Python 環境の用意
   - 推奨 Python: 3.10+（typing の | 表現等を使用）
   - 仮想環境を作成して有効化:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml

   （プロジェクトが requirements.txt を提供する場合は `pip install -r requirements.txt`）

4. 環境変数の準備
   - プロジェクトルートに `.env` または `.env.local` を作成してください。
   - 例（.env.example）:

     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=your_openai_api_key
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

5. データディレクトリの作成（必要に応じて）
   - mkdir -p data

---

## 使い方（主要 API と実行例）

以下は Python スクリプトなどから利用する例です。各関数は duckdb の接続オブジェクト（duckdb.connect() の戻り値）を受け取ります。

- DuckDB 接続を作る

  from pathlib import Path
  import duckdb
  db_path = Path("data/kabusys.duckdb")
  conn = duckdb.connect(str(db_path))

- 日次 ETL を実行する

  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- News NLP（銘柄別ニュースセンチメント）を実行する

  from datetime import date
  from kabusys.ai.news_nlp import score_news
  # OPENAI_API_KEY は環境変数に設定か、api_key 引数で渡す
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込んだ銘柄数: {written}")

- 市場レジーム判定を実行する

  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ（audit）スキーマを初期化する

  from kabusys.data.audit import init_audit_db, init_audit_schema
  # 監査専用 DB を作成して接続を取得
  audit_conn = init_audit_db("data/audit.duckdb")
  # または既存接続に対して:
  init_audit_schema(conn, transactional=True)

- J-Quants API を直接呼ぶ（デバッグ等）

  from kabusys.data import jquants_client as jq
  records = jq.fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,3,20))
  jq.save_daily_quotes(conn, records)

注意:
- LLM（OpenAI）呼び出しを行う機能は `OPENAI_API_KEY` を必要とします。環境変数で指定するか、API 関数の `api_key` 引数へ直接渡してください。
- AI モジュールは API エラー時にフォールバック（スコア 0.0）するフェイルセーフを持ちますが、API 料金・レートに注意してください。
- ETL / API 呼び出しはネットワーク依存のためリトライやログを必ず確認してください。

---

## ディレクトリ構成

主要ファイル / ディレクトリ（src/kabusys をルートとした概観）:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境設定と .env 自動読み込みロジック（settings）
  - ai/
    - __init__.py
    - news_nlp.py            # ニュースの LLM スコアリング（ai_scores へ書き込み）
    - regime_detector.py     # マクロ + ETF MA で市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント（取得 + DuckDB 保存）
    - pipeline.py           # ETL パイプライン（run_daily_etl 等）
    - etl.py                # ETLResult 再エクスポート
    - news_collector.py     # RSS ニュース収集（SSRF 対策、前処理）
    - calendar_management.py# 市場カレンダー管理（営業日判定など）
    - quality.py            # データ品質チェック
    - stats.py              # 統計ユーティリティ（zscore_normalize）
    - audit.py              # 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py    # モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py# 将来リターン / IC / 統計サマリー
  - monitoring/ (※コードベースにある想定のモジュール)
  - strategy/ (戦略層は別途実装)
  - execution/ (注文実行層は別途実装)

（上記は主要モジュールの抜粋です。各モジュールに詳細な関数ドキュメントがあります。）

---

## 実運用上の注意点

- 本コードベースは「取引の意思決定」を支援するプラットフォームを提供しますが、実際の発注やマネージメントは慎重に検証してください。live 環境（KABUSYS_ENV=live）では特に注意が必要です。
- OpenAI や J-Quants など外部 API の料金、レート制限に注意してください。jquants_client と AI モジュールはリトライとレート制御を実装していますが、運用設計を必ず行ってください。
- データの整合性・品質チェック（data.quality）を ETL 後に必ず実行し、重大な問題が出た場合は処理を停止・通知するフローを導入してください。
- DuckDB のバージョンによるパラメータバインドの制限（executemany と空リストなど）に注意してありますが、実運用での DB バージョン差異は監視してください。

---

## 貢献と開発

- コーディング規約に従い、ユニットテストと静的解析を追加してください。
- 外部 API 呼び出しはモック化してユニットテストを作成することを推奨します（コード内でモック差し替えポイントを意図的に用意しています）。

---

README に記載の無い具体的な利用方法や、特定のモジュールの詳細な使い方・API 例が必要であれば、どの機能に関するドキュメントを優先して欲しいか教えてください。必要に応じて使用例やコマンドラインスクリプトのテンプレートも作成します。