# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集と LLM を用いたニュース/市場レジーム解析、研究（ファクター計算）および監査ログ/発注監視に必要なユーティリティを提供します。

主な設計方針：
- ルックアヘッドバイアスを防ぐ（内部で date.today()/datetime.today() の直接参照を避ける設計）
- DuckDB を中心に効率的な SQL 処理でデータ処理を行う
- 外部 API 呼び出し（J-Quants / OpenAI）はリトライやレート制御を備えた実装
- ETL / 品質チェック / 監査ログの冪等性を重視

---

## 機能一覧

- 環境設定管理
  - .env / .env.local / OS 環境変数からの読み込み（自動ロード、優先順位あり）
  - 必須環境変数取得のヘルパー
- Data（データパイプライン）
  - J-Quants API クライアント（取得・保存・ページネーション・認証自動更新）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - 市場カレンダー管理（営業日判定・next/prev 営業日・calendar_update_job）
  - ニュース収集（RSS の安全取得・前処理・raw_news 保存）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログスキーマ初期化（signal_events / order_requests / executions）
- AI（OpenAI を用いた自然言語処理）
  - ニュースセンチメント解析（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）— ETF 1321 の MA + マクロニュースセンチメントを合成
- Research（研究用ユーティリティ）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化
- 監視・実行（監視や発注関連のテーブルとユーティリティを含む）

---

## セットアップ手順

※ 以下はリポジトリをローカルで動かすための基本手順です。プロジェクトの packaging / requirements は環境に合わせて適宜調整してください。

1. システム要件
   - Python 3.10+（型アノテーションでの union 表記などを使用）
   - DuckDB
   - OpenAI SDK（openai）
   - defusedxml（RSS パースで安全対策）
   - そのほか標準ライブラリ

2. 仮想環境と依存インストール（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb openai defusedxml
   # 開発用にパッケージを editable インストールする場合
   pip install -e .
   ```
   （プロジェクトに requirements.txt / pyproject.toml があればそれを使用してください）

3. 環境変数の準備
   プロジェクトルートの `.env` / `.env.local` を用意します。自動読み込みはデフォルトで有効です。無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   最小限の例（.env.example として）:
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # kabuステーション API
   KABU_API_PASSWORD=your_kabu_api_password
   # KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # OpenAI / LLM
   OPENAI_API_KEY=your_openai_api_key

   # Slack (通知用)
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=CXXXXXXXX

   # DB パス等（任意）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 実行環境
   KABUSYS_ENV=development   # development / paper_trading / live
   LOG_LEVEL=INFO
   ```

4. データベース用ディレクトリ作成（必要なら）
   ```bash
   mkdir -p data
   ```

---

## 使い方（主要な例）

以下はライブラリの主要なエントリポイントの使い方例です。実際の運用ではロギングやエラーハンドリング、スケジューリング（cron / Airflow 等）を組み合わせてください。

- DuckDB 接続を作成する例
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())
  ```

- ニュースセンチメントのスコア付け
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OPENAI_API_KEY を環境変数に置くか、api_key 引数で渡す
  count = score_news(conn, target_date=date(2026,3,20))
  print("scored:", count)
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026,3,20))
  ```

- 研究用: モメンタム計算など
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
  from datetime import date

  mom = calc_momentum(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))
  val = calc_value(conn, date(2026,3,20))
  ```

- 監査ログスキーマ初期化（別 DB に分ける場合）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # audit_conn を使って order_requests / executions の INSERT やクエリを行う
  ```

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu API のパスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 関連関数で使用、引数で上書き可）
- SLACK_BOT_TOKEN: Slack ボットトークン（通知用）
- SLACK_CHANNEL_ID: Slack チャンネル ID（通知用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live、デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

自動 .env ロードの挙動:
- 優先順位: OS 環境変数 > .env.local > .env
- 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

---

## ディレクトリ構成（主要ファイル）

リポジトリは src/kabusys 配下にパッケージ化されています。主要なサブモジュールは以下の通りです。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込みと Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py           — ニュースセンチメント解析（OpenAI）
    - regime_detector.py    — 市場レジーム判定（MA + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（取得・保存）
    - pipeline.py           — ETL の高レベル API（run_daily_etl 等）
    - etl.py                — ETL の再エクスポート（ETLResult）
    - news_collector.py     — RSS ニュース取得・前処理
    - calendar_management.py— 市場カレンダー管理（営業日判定等）
    - quality.py            — データ品質チェック
    - stats.py              — 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py              — 監査ログスキーマ初期化（signal/order/execution）
  - research/
    - __init__.py
    - factor_research.py    — momentum/volatility/value の計算
    - feature_exploration.py— 将来リターン / IC / 統計サマリー等
  - ai/、data/、research/ はそれぞれ公開 API を __all__ で整理しています。

---

## 運用上の注意点

- OpenAI / J-Quants API キーの管理は慎重に行ってください。課金・レート制限に注意。
- ETL は外部 API に依存するため、スケジューラ（cron / Airflow 等）で定期実行し、失敗ログを監視してください。
- DuckDB のバージョン差異により executemany の空リスト扱いや一部の SQL 挙動が異なる可能性があります（コード内で注意喚起あり）。
- ニュース収集では SSRF / XML Bomb 等の対策を実装していますが、運用上のセキュリティは追加で検討してください。
- KABUSYS_ENV により本番（live）・紙運用（paper_trading）・開発（development）の振る舞いを切替可能です。特に live では発注ロジック等の扱いに注意してください。

---

## 貢献・テスト

- ユニットテストや統合テストは各モジュールの外部依存（OpenAI・J-Quants・ネットワーク）をモックして実行してください。
- config モジュールは KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動ロードを無効化できます（テスト時に便利）。

---

もし README に追記したい使用例（具体的な ETL スケジュール例や Airflow DAG、Slack 通知例、kabu 発注フローなど）があれば教えてください。必要に応じてサンプルコードや運用チェックリストを追加します。