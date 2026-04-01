# KabuSys

KabuSys は日本株向けのデータプラットフォームと自動売買支援ライブラリです。J-Quants API や RSS を用いたデータ収集、DuckDB ベースの ETL、ニュースの LLM によるセンチメント評価、研究用ファクター計算、監査ログ（トレーサビリティ）などを備えています。

主な目的は「データ収集 → 品質チェック → ファクター計算 → シグナル生成 → 発注（監査）」までのワークフローを安全に実装・検証できる基盤を提供することです。

バージョン: 0.1.0

---

## 主な機能（機能一覧）

- 環境設定管理
  - .env / .env.local をプロジェクトルートから自動ロード（無効化可能）
  - 必須設定の検査（Settings クラス）

- Data（ETL / Data Platform）
  - J-Quants API クライアント（差分取得、ページネーション、リトライ、トークンリフレッシュ）
  - daily quotes（株価日足）、財務データ、JPX マーケットカレンダー取得
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - マーケットカレンダー管理（営業日判定、次営業日/前営業日取得）
  - RSS ニュース収集（SSRF 対策、トラッキングパラメータ除去、冪等保存）
  - 監査ログ（signal_events / order_requests / executions）スキーマの初期化ユーティリティ

- AI（ニュース NLP / レジーム判定）
  - ニュース記事を銘柄ごとに統合して LLM（gpt-4o-mini）でセンチメントを取得し ai_scores に格納
  - マクロ指標（ETF 1321 の MA200 乖離）と LLM マクロセンチメントを合成して市場レジームを判定（bull/neutral/bear）

- Research（研究用ユーティリティ）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計サマリ
  - z-score 正規化ユーティリティ

---

## 要求環境・依存

- Python 3.10 以上（typing の union 演算子 `X | Y` を使用）
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml

※実行にあたっては OpenAI API キー、J-Quants リフレッシュトークン等の外部サービス設定が必要です。

---

## セットアップ手順

1. リポジトリをクローン（ここでは例示）
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   - requirements.txt がある場合:
     ```bash
     pip install -r requirements.txt
     ```
   - または最低限:
     ```bash
     pip install duckdb openai defusedxml
     ```

4. 環境変数を準備
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   サンプル（.env）：
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # kabuステーション API（必要なら）
   KABU_API_PASSWORD=your_kabu_api_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # OpenAI
   OPENAI_API_KEY=sk-...

   # Slack（通知用）
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789

   # データベース
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 実行環境
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（主な例）

以下は Python インタプリタ・スクリプトからモジュールを呼ぶ簡単な例です。実際の運用ではジョブスケジューラ（cron / systemd timer / Airflow 等）から呼び出すことを想定しています。

1. DuckDB 接続の作成
   ```python
   import duckdb
   conn = duckdb.connect("data/kabusys.duckdb")
   ```

2. 日次 ETL 実行
   ```python
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl

   # target_date を指定（省略すると今日）
   result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(result.to_dict())
   ```

3. ニュースのスコアリング（AI）
   ```python
   from datetime import date
   from kabusys.ai.news_nlp import score_news

   # conn は duckdb 接続
   written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
   print(f"書き込み銘柄数: {written}")
   ```

4. 市場レジーム判定
   ```python
   from datetime import date
   from kabusys.ai.regime_detector import score_regime

   score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
   ```

5. 監査ログスキーマの初期化（監査専用 DB を作る）
   ```python
   from kabusys.data.audit import init_audit_db
   conn_audit = init_audit_db("data/audit.duckdb")
   ```

6. J-Quants の ID トークン取得（直接呼び出したい場合）
   ```python
   from kabusys.data.jquants_client import get_id_token
   token = get_id_token()  # settings.jquants_refresh_token を使用
   ```

注意点:
- OpenAI 呼び出しは API の課金対象です。実行前に API キーとクォータを確認してください。
- LLM 呼び出しはリトライやフォールバックが組まれていますが、外部ネットワークの可用性に依存します。
- DuckDB の executemany に関してコード内で空リストの扱いに注意した実装（互換性維持）がされています。

---

## 推奨ワークフロー（運用例）

- 夜間バッチ（毎日）
  - run_daily_etl を実行して prices/financials/calendar を更新
  - news_collector で RSS を収集して raw_news を更新
  - score_news で AI によるセンチメント評価を実行
  - score_regime で市場レジームを判定

- 取引実行（Execution 層）
  - 戦略が生成したシグナルを監査テーブル（signal_events）に保存
  - order_requests を経由して発注し、実行情報を executions に保存

---

## 主要モジュールと責務

- kabusys.config
  - 環境変数 / .env 自動ロード、Settings クラス

- kabusys.data
  - jquants_client.py : J-Quants API クライアント・保存ロジック
  - pipeline.py      : ETL 実行フロー（run_daily_etl 等）
  - etl.py           : ETLResult の再エクスポート
  - quality.py       : データ品質チェック
  - stats.py         : z-score 等汎用統計
  - calendar_management.py : 市場カレンダー管理（営業日判定）
  - news_collector.py: RSS → raw_news（SSRF 対策・前処理）
  - audit.py         : 監査スキーマ定義・初期化

- kabusys.ai
  - news_nlp.py      : 銘柄ごとのニュースセンチメント評価（LLM）
  - regime_detector.py : 市場レジーム判定（ETF MA200 + マクロセンチメント融合）

- kabusys.research
  - factor_research.py    : Momentum / Volatility / Value 等
  - feature_exploration.py: 将来リターン, IC, 統計サマリ など

---

## ディレクトリ構成

（抜粋）プロジェクトの主要ファイル構成は以下の通りです。

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
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/ ... (その他の研究用モジュール)
    - (strategy/, execution/, monitoring/ 等が 想定されるトップレベルパッケージ)

- README.md
- pyproject.toml / setup.cfg / requirements.txt (プロジェクト依存により存在)

---

## 補足・運用上の注意

- 環境変数の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行います。テスト等で無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI や J-Quants の API 呼び出しは外部サービス依存であるため、障害時のフォールバック設計（モジュール内でのデフォルトや 0.0 のフォールバック）が含まれています。運用ではログ監視と再試行戦略を用意してください。
- news_collector は SSRF 対策、受信サイズ上限、XML パースの安全対策（defusedxml）を実装しています。RSS ソース追加時は URL の妥当性を確認してください。
- DuckDB スキーマやテーブル作成は audit.init_audit_schema 等の初期化ユーティリティを用いて行ってください。

---

この README はコードベースの主要機能・使い方をまとめた概要です。より詳細な設計・仕様（DataPlatform.md / StrategyModel.md 等）はリポジトリ内のドキュメントを参照してください。必要であれば README に具体的な CLI や systemd ユニット例、CI 設定例なども追加できます。