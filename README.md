# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリセットです。  
データ収集（J-Quants / RSS）、ETL、データ品質チェック、リサーチ用ファクター計算、AI を用いたニュースセンチメント評価、監査ログ（発注／約定トレーサビリティ）などを提供します。

主な設計方針
- ルックアヘッドバイアスを防ぐため、内部処理は明示的な target_date ベースで動作します（date.today() を直接参照しない設計）。
- DuckDB を中心としたローカルデータベースでデータ管理を行います。
- API 呼び出しはリトライ・レート制御・フェイルセーフを組み込み、安定性を重視しています。
- 各モジュールは冪等性（idempotency）や安全性（SSRF 対策、XML パースの安全化など）に配慮しています。

---

## 機能一覧

- 設定 / 環境変数管理
  - .env / .env.local の自動読み込み（プロジェクトルート判定：.git または pyproject.toml）
  - 必須環境変数取得のユーティリティ（Settings クラス）

- データ収集・ETL（kabusys.data）
  - J-Quants API クライアント（取得・保存・認証・レート制御・ページネーション）
  - RSS ニュース収集（SSRF 防御、URL 正規化、前処理）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - データ品質チェック（欠損・重複・スパイク・日付整合性）
  - 市場カレンダー管理（営業日判定・next/prev_trading_day 等）
  - 監査ログ（signal_events, order_requests, executions）と初期化

- リサーチ（kabusys.research）
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化

- AI モジュール（kabusys.ai）
  - ニュースセンチメント解析（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）：ETF（1321）の MA200 とマクロニュースの LLM センチメントを合成

- ユーティリティ
  - 統計ユーティリティ（zscore_normalize など）
  - DuckDB 用の監査 DB 初期化ユーティリティ

---

## 必要要件（代表）

- Python 3.10+
- duckdb
- openai
- defusedxml

（実プロジェクトでは requirements.txt / pyproject.toml に依存関係を記載してください）

---

## セットアップ手順

1. 仮想環境を作成して有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 必要パッケージをインストール
   ```
   pip install duckdb openai defusedxml
   ```
   （プロジェクトに requirements.txt / pyproject.toml がある場合はそれを利用してください）

3. 環境変数（または .env ファイル）を用意する  
   .env.example を参考に .env を作成してください。主要な環境変数は以下：

   - JQUANTS_REFRESH_TOKEN  (必須) — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD      (必須) — kabuステーション等の API パスワード
   - KABU_API_BASE_URL      (任意) — デフォルト: http://localhost:18080/kabusapi
   - SLACK_BOT_TOKEN        (必須) — Slack 通知用 Bot Token
   - SLACK_CHANNEL_ID       (必須) — Slack 通知先チャンネル ID
   - DUCKDB_PATH            (任意) — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH            (任意) — デフォルト: data/monitoring.db
   - KABUSYS_ENV            (任意) — development / paper_trading / live（デフォルト development）
   - LOG_LEVEL              (任意) — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
   - OPENAI_API_KEY         (AI 機能利用時に必要)

   補足:
   - パッケージは起動時にプロジェクトルート（.git または pyproject.toml）を探して .env/.env.local を自動読み込みします（OS 環境変数が優先）。
   - 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. データベース準備（監査ログ用）
   - 監査用 DuckDB を作成・初期化する例:
     ```python
     from kabusys.data.audit import init_audit_db
     from kabusys.config import settings

     conn = init_audit_db(settings.duckdb_path)
     ```

---

## 使い方（代表例）

以下はライブラリ機能を直接 Python から使う基本例です。実環境では適切なエントリポイント（CLI / Airflow / Cron ジョブ等）を構築して運用してください。

- 設定・環境参照
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)          # Path オブジェクト
  print(settings.is_live, settings.env)
  ```

- DuckDB 接続を開いて日次 ETL を実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの AI スコアリング（news_nlp）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings
  import os

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY は環境変数でも引数でも指定可
  count = score_news(conn, target_date=date(2026, 3, 20), api_key=os.environ.get("OPENAI_API_KEY"))
  print(f"scored {count} symbols")
  ```

- 市場レジームスコア生成（regime_detector）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を参照
  ```

- ETL の個別呼び出し（株価のみ等）
  ```python
  from kabusys.data.pipeline import run_prices_etl
  fetched, saved = run_prices_etl(conn, target_date=date(2026,3,20))
  ```

- 監査スキーマの初期化（既存接続へ追加）
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

---

## 環境変数読み込みの挙動

- 自動読み込み優先度:
  1. OS 環境変数
  2. .env.local（存在する場合、既存の OS 環境変数は保護）
  3. .env

- .env パーサは:
  - export KEY=val 形式を扱う
  - シングル／ダブルクォートを考慮した値のパース
  - コメント（#）処理（クォート内を除く）に対応

- 無効化:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みをスキップします（テスト時に便利）。

---

## 主要モジュールとディレクトリ構成

プロジェクトは src/kabusys 以下に実装ファイルが配置されています。主な構成は次の通りです。

- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス（環境変数管理、.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py
      - calc_news_window, score_news
      - OpenAI API 呼出し + レスポンスバリデーション + チャンク/リトライロジック
    - regime_detector.py
      - score_regime（MA200 とマクロニュースセンチメントを合成）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API との通信・ページネーション・保存（raw_prices, raw_financials, market_calendar）
    - pipeline.py
      - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
      - ETLResult データクラス
    - news_collector.py
      - RSS 収集・前処理・SSRF 対策・ID 生成
    - quality.py
      - データ品質チェック（欠損・重複・スパイク・日付整合性）
    - calendar_management.py
      - market_calendar 管理、営業日判定、next/prev_trading_day
    - audit.py
      - 監査テーブル DDL / 初期化（signal_events, order_requests, executions）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - etl.py
      - ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum, calc_value, calc_volatility
    - feature_exploration.py
      - calc_forward_returns, calc_ic, factor_summary, rank

---

## 運用上の注意・ベストプラクティス

- OpenAI / J-Quants API キーは安全に管理すること（環境変数 / シークレット管理サービスを利用）。
- ETL は日次バッチで実行することを想定。run_daily_etl を Cron / Airflow 等のスケジューラで呼び出すのが実運用向け。
- AI 呼び出しはコストがかかるため、batch サイズやリトライ戦略を運用環境に応じて調整してください。
- DuckDB ファイル（settings.duckdb_path）と監査ログはバックアップ・定期メンテナンスを行ってください。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みが抑制されます。また、AI 呼び出し等はモック化してユニットテストを設計してください（コード内にもモック対象の内部関数が用意されています）。

---

## 参考・問い合わせ

ソースコード内の docstring に設計方針や処理フローが詳細に記載されています。各機能を拡張する際はそれらのコメントを参照してください。

ご不明点や README の追加情報が必要であれば教えてください。README を環境に合わせてカスタマイズ（例: 実行スクリプト / systemd / Airflow 連携方法）することも可能です。