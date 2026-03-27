# KabuSys

日本株向けの自動売買／研究プラットフォーム用ライブラリ。データのETL、ニュースの収集・NLPによるセンチメント評価、マーケットレジーム判定、ファクター計算、監査ログ/発注トレーサビリティなどを提供します。

主な設計方針：
- ルックアヘッドバイアスを防ぐ（内部で datetime.today() に依存しない処理設計）
- DuckDB を用いたローカルデータプラットフォーム（冪等保存・トランザクション管理）
- API 呼び出しはリトライ・レート制御・フェイルセーフあり
- ETL・品質チェック・監査ログなど運用観点を考慮

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート基準）
  - 必須設定の検証（settings オブジェクト）

- Data（データプラットフォーム）
  - J-Quants API クライアント（株価・財務・市場カレンダー等の取得）
  - ETL パイプライン（差分取得・保存・品質チェック）
  - 市場カレンダー管理（営業日判定、next/prev_trading_day 等）
  - ニュース収集（RSS → 前処理 → raw_news 保存、SSRF 対策・サイズ制限）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ／トレーサビリティ（signal_events / order_requests / executions テーブル）
  - 汎用統計ユーティリティ（Zスコア正規化 等）

- AI（LLM を用いた処理）
  - ニュースセンチメント解析（銘柄単位に集約し OpenAI で評価、ai_scores に保存）
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュース LLM センチメントを合成）

- Research（研究用ツール）
  - ファクター計算（モメンタム・バリュー・ボラティリティなど）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

---

## 必要条件（Prerequisites）

- Python 3.10 以上
- 必要な Python パッケージ（例）
  - duckdb
  - openai
  - defusedxml

（プロジェクトでは typing の新しい構文や型アノテーションを使用しているため Python 3.10+ を推奨します）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成（例）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

3. 依存パッケージをインストール
   - 簡易例:
     ```
     pip install duckdb openai defusedxml
     ```
   - 実際は requirements.txt / pyproject.toml があればそちらを利用してください。

4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を置くと自動読み込みされます（`.env.local` は `.env` より優先）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. 必須環境変数（例）
   - J-Quants / kabu / Slack / DB 関連：
     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     KABU_API_PASSWORD=xxxxx
     KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 必要に応じて
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development  # development / paper_trading / live
     LOG_LEVEL=INFO
     ```
   - `.env.example` を用意している場合はそれを参考に作成してください（プロジェクトにない場合は上の変数を参考にしてください）。

---

## 基本的な使い方（コード例）

以下はライブラリ関数の代表的な呼び出し例です。実行前に必要な環境変数や DB の初期化を行ってください。

- DuckDB 接続例（デフォルトパスを使用）
  ```py
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行
  ```py
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # ETL を今日の日付で実行（品質チェックあり）
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュースセンチメントをスコア化して ai_scores テーブルに保存
  ```py
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY を使用
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定（market_regime テーブルへ書き込み）
  ```py
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログの初期化（監査用 DuckDB を作成してスキーマを作る）
  ```py
  from pathlib import Path
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db(Path("data/audit.duckdb"))
  # tables created: signal_events, order_requests, executions
  ```

- 研究系関数の利用（ファクター計算）
  ```py
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
  value = calc_value(conn, target_date=date(2026, 3, 20))
  vol = calc_volatility(conn, target_date=date(2026, 3, 20))
  ```

注意：
- OpenAI の呼び出しは rate limit / retry ロジックを持っていますが API キーは環境変数 `OPENAI_API_KEY` か関数引数で渡してください。
- J-Quants の API 呼び出しは `JQUANTS_REFRESH_TOKEN` を用い、内部で id_token を取得してページネーションを処理します。

---

## ディレクトリ構成（要約）

リポジトリは src/kabusys 以下にモジュール群が配置されています。主要なファイル・モジュールは以下の通りです。

- src/kabusys/
  - __init__.py
  - config.py                                # 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                             # ニュースセンチメント解析（ai_scores）
    - regime_detector.py                      # マーケットレジーム判定（market_regime）
  - data/
    - __init__.py
    - jquants_client.py                       # J-Quants API クライアント & DuckDB 保存
    - pipeline.py                             # ETL パイプライン（run_daily_etl 等）
    - etl.py                                  # ETL インターフェース再エクスポート
    - calendar_management.py                  # 市場カレンダー管理・営業日判定
    - news_collector.py                        # RSS 収集・前処理・保存
    - quality.py                               # データ品質チェック
    - stats.py                                 # 汎用統計関数（zscore_normalize）
    - audit.py                                 # 監査ログ（signal/order/execution）スキーマ初期化
    - pipeline.py                              # ETL フロー（run_prices_etl 等）
  - research/
    - __init__.py
    - factor_research.py                       # モメンタム/ボラティリティ/バリュー
    - feature_exploration.py                   # 将来リターン・IC・統計サマリー

（上記は主要ファイルの概観。詳細な補助モジュールやユーティリティ関数も含まれます）

---

## 運用上の注意 / 補足

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）で行われます。CI／テストで自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DB 書き込みは冪等（ON CONFLICT / DELETE→INSERT）を基本としているため再実行に対して堅牢です。
- ニュース収集には SSRF・XML 注入・Gzip bomb 等の防御を実装していますが、運用環境では RSS ソースのホワイトリスト運用を推奨します。
- 実口座での発注・監査ログ運用は十分にテストし、リスク制御（max position、ドローダウン制限等）を別途実装してください。

---

## 開発・テストのヒント

- OpenAI / J-Quants 呼び出しはモジュール内のラッパー関数をモックしてテスト可能です（score_news 内で _call_openai_api を差し替える等）。
- DuckDB をインメモリで使うことでユニットテストを簡単に回せます（db_path=":memory:"）。
- settings は必須キー未設定で ValueError を投げます。テスト中は環境変数を一時的に差し替えるか `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用してください。

---

もし README に追加したい具体的な使用例（cron ジョブ設定、Slack 通知の実装例、kabu ステーション連携例、CI 設定など）があれば、目的に合わせてサンプルを追記します。