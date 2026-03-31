# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
データ収集（J-Quants / RSS）、ETL、データ品質チェック、監査ログ、研究用ファクター計算、AI によるニュース評価・市場レジーム判定など、投資戦略実装に必要な機能群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API から株価・財務・カレンダーを取得する ETL パイプライン
- RSS からのニュース収集と前処理、銘柄紐付け
- OpenAI を用いたニュースの NLP スコアリング（銘柄別センチメント）
- ETF ベースの長期移動平均とマクロニュースの合成による市場レジーム判定
- DuckDB を使ったデータ保存・監査ログ（order/signal/execution）
- 研究用途のファクター計算・統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 環境設定の .env 自動読み込み（任意で無効化可能）

設計上、バックテスト時のルックアヘッドバイアス回避や、API 呼び出し失敗時のフェイルセーフを重視しています。

---

## 主な機能一覧

- データ取得・ETL
  - J-Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ対応）
  - 日次 ETL（prices / financials / market_calendar）
  - 差分取得・バックフィル対応

- データ管理
  - DuckDB ベースの保存・冪等保存（ON CONFLICT）
  - 監査ログスキーマ（signal_events / order_requests / executions）
  - 市場カレンダー管理（営業日判定・next/prev/get_trading_days）

- ニュース処理 & AI
  - RSS 収集（SSRF 対策、URL 正規化、トラッキング除去）
  - ニュース前処理（URL 除去、空白正規化）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメント（score_news）
  - マクロニュース × ETF MA200 を合成した市場レジーム判定（score_regime）

- 研究用ユーティリティ
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Spearman）計算、Z スコア正規化
  - 統計サマリー機能

- データ品質チェック
  - 欠損、スパイク、重複、将来日付・非営業日検出
  - QualityIssue データクラスによる問題収集

- 設定管理
  - .env/.env.local 自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェックを行う Settings API

---

## セットアップ手順

以下は開発環境での一般的な手順です。環境や運用方法に応じて調整してください。

1. リポジトリをクローン

   ```bash
   git clone <リポジトリURL>
   cd <リポジトリ>
   ```

2. Python 仮想環境を作成・有効化（推奨）

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要なパッケージをインストール

   requirements.txt がある場合:

   ```bash
   pip install -r requirements.txt
   ```

   ない場合、主要な依存パッケージの例:

   ```bash
   pip install duckdb openai defusedxml
   ```

   （プロジェクトに合わせて追加の依存をインストールしてください）

4. パッケージをインストール（開発モード）

   ```bash
   pip install -e .
   ```

5. 環境変数の設定

   リポジトリルートに `.env`（と必要に応じて `.env.local`）を作成してください。必須の環境変数例:

   - JQUANTS_REFRESH_TOKEN: J‑Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
   - SLACK_BOT_TOKEN: Slack Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 用）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

   自動ロードを無効にする（テスト時など）場合:

   ```bash
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

---

## 使い方（基本例）

以下は主な API の簡単な使用例です。各関数は duckdb の接続オブジェクト（duckdb.connect(...)）を受け取ります。

1. DuckDB 接続を作成

   ```python
   import duckdb
   from kabusys.config import settings

   conn = duckdb.connect(str(settings.duckdb_path))
   ```

2. 日次 ETL 実行

   ```python
   from kabusys.data.pipeline import run_daily_etl
   from datetime import date

   res = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(res.to_dict())
   ```

3. ニュースの AI スコアリング（銘柄別センチメント）

   ```python
   from kabusys.ai.news_nlp import score_news
   from datetime import date

   count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
   print(f"scored {count} codes")
   ```

4. 市場レジーム判定

   ```python
   from kabusys.ai.regime_detector import score_regime
   from datetime import date

   score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
   ```

   - OpenAI API キーは api_key 引数か環境変数 OPENAI_API_KEY を使用します。未設定時は ValueError が発生します。

5. 監査ログ DB 初期化（監査専用 DB）

   ```python
   from kabusys.data.audit import init_audit_db

   audit_conn = init_audit_db("data/audit.duckdb")
   ```

6. 研究用ファクター計算

   ```python
   from kabusys.research.factor_research import calc_momentum
   from datetime import date

   factors = calc_momentum(conn, target_date=date(2026, 3, 20))
   ```

7. データ品質チェック

   ```python
   from kabusys.data.quality import run_all_checks
   issues = run_all_checks(conn, target_date=date(2026, 3, 20))
   for issue in issues:
       print(issue.check_name, issue.severity, issue.detail)
   ```

注意:
- 各関数は「ルックアヘッドバイアス」を避けるため内部で date.today() を直接参照しない設計になっています。必ず target_date を明示するか、関数のドキュメントに従ってください。
- OpenAI 呼び出しはネットワークエラーや 5xx を想定してリトライやフォールバックを行いますが、API キーは正しく設定してください。

---

## 主要な環境変数

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（オプション, デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / regime_detector 用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視）ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL: ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)

設定は .env / .env.local から自動読み込みされます（プロジェクトルート判定: .git または pyproject.toml）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## ディレクトリ構成

主要ファイルとモジュールの概要（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py         -- ニュースセンチメント（OpenAI）
    - regime_detector.py  -- ETF MA200 + マクロニュースによる市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py   -- J-Quants API クライアント（取得・保存）
    - pipeline.py         -- ETL パイプライン (run_daily_etl 等)
    - etl.py              -- ETLResult の再エクスポート
    - news_collector.py   -- RSS 収集・前処理
    - calendar_management.py -- 市場カレンダー管理（営業日判定等）
    - quality.py          -- データ品質チェック
    - stats.py            -- Zスコア等の統計ユーティリティ
    - audit.py            -- 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py  -- Momentum / Volatility / Value の計算
    - feature_exploration.py -- 将来リターン・IC・統計サマリー等
  - research/（その他、分析ヘルパ）
  - ...（strategy / execution / monitoring 等のパッケージが __all__ に含まれる想定）

この README に含めていないファイルやサブモジュールもあります。コードベースの docstring や各モジュール先頭に設計方針・使用法が記載されていますので、詳細は該当ファイルを参照してください。

---

## テスト & モックについて

- OpenAI の呼び出しはモジュール内で _call_openai_api のようなラッパー関数を使用しており、ユニットテストでは該当関数を patch して差し替えることでネットワーク呼び出しをモックできます。
  - 例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api", return_value=...)
- news_collector のネットワークは kabusys.data.news_collector._urlopen をモック可能です。
- J-Quants の API 呼び出しは jquants_client._request をモックすると容易にテストできます。

---

## 開発者向け注意点

- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、コード中で空チェックを行っています（互換性の保障）。
- 時刻は可能な限り UTC で扱う（DB の TIMESTAMP は UTC 前提）。
- データ更新は冪等（ON CONFLICT / DELETE→INSERT のパターン）を意識してください。
- ルックアヘッドバイアスを避けるため、日付処理は target_date を明示して行います。

---

必要に応じて README にサンプル .env.example、requirements.txt、実行スクリプト例（systemd / cron / Airflow のタスク定義）等を追記できます。追加の要望があれば教えてください。