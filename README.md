# KabuSys

日本株向けの自動売買 / データ基盤ユーティリティ群を集めたライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース NLP（OpenAI）、市場レジーム判定、監査ログなどを含みます。

## プロジェクト概要
- DuckDB を中心としたローカルデータプラットフォーム（raw_prices / raw_financials / raw_news / ai_scores / market_regime / market_calendar / audit テーブル群）を想定。
- J-Quants API を用いた株価・財務・カレンダーの差分取得（レートリミット・リトライ・トークン自動更新対応）。
- RSS ベースのニュース収集と前処理（SSRF 対策、トラッキング除去、ID生成）。
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄単位）とマクロセンチメントを評価し、AI スコア／市場レジームを生成。
- 研究用ファクター計算・特徴量探索ユーティリティ（モメンタム、ボラティリティ、バリュー、IC、forward returns）。
- データ品質チェック（欠損・重複・スパイク・日付不整合）を ETL 内で実行。
- 発注〜約定までを追跡する監査ログスキーマ（冪等キー・UTC タイムスタンプ等）。

設計上の特徴として、「ルックアヘッドバイアス回避（内部で date.today() 等を無条件参照しない）」「冪等性」「フェイルセーフ（API 失敗時のフォールバック）」が重視されています。

---

## 主な機能一覧
- データ収集 / ETL
  - J-Quants からの差分取得（株価 / 財務 / カレンダー）
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
- データ品質チェック
  - check_missing_data, check_duplicates, check_spike, check_date_consistency, run_all_checks
- ニュース収集・NLP
  - RSS 取得と前処理（news_collector.fetch_rss, preprocess_text）
  - 銘柄別ニュースセンチメント計算（ai.news_nlp.score_news）
- 市場レジーム判定
  - ETF(1321)のMA200乖離 + マクロセンチメントの合成（ai.regime_detector.score_regime）
- 研究用ユーティリティ
  - ファクター計算（research.calc_momentum / calc_value / calc_volatility）
  - 将来リターン・IC・ファクターサマリ（research.feature_exploration）
  - zscore_normalize（data.stats）
- 監査ログ（注文〜約定トレース）
  - init_audit_db / init_audit_schema による監査 DB 初期化
- 環境設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート判定）および Settings API（kabusys.config.settings）

---

## セットアップ手順

前提: Python 3.10+（typing | の注釈があるため）を想定します。

1. リポジトリをクローン／配置
   - 例: git clone ... && cd <project_root>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必須（コード内 import より）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトに setup/pyproject があれば pip install -e . でインストール）

4. 環境変数 / .env を準備
   - プロジェクトルートに .env を置くと自動で読み込まれます（.env.local は .env を上書き）。
   - 自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. 必要な環境変数（代表）
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
   - KABU_API_BASE_URL: kabu API ベース URL（省略可、デフォルト http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - OPENAI_API_KEY: OpenAI 呼び出しで未指定時に使われる（ai.* モジュール）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用途の SQLite パス（デフォルト data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）

   例 .env（必要に応じて .env.local で上書き）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   KABU_API_PASSWORD=secret
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

---

## 使い方（基本例）

以下はいくつかの代表的な利用例です。実行は Python REPL、スクリプト、あるいはワーカーの中で行います。

- DuckDB 接続を作成して ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（ai_scores）を計算する
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"scored {count} stocks")
  ```

- マーケットレジーム評価（market_regime テーブルへ書き込み）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査用 DuckDB を初期化する
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # テーブルが作成され、UTC タイムゾーン設定も行われます
  ```

- 市場カレンダー関数の利用例
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

注意:
- ai.* の API 呼び出しは OPENAI_API_KEY または関数引数での api_key 指定が必要です。
- 多くの関数は「指定した target_date を明示する」設計で、実行時の現在時刻（ルックアヘッド）を防ぐ配慮がなされています。

---

## 開発 / テストのヒント
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探して実行されます。ユニットテスト等で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し部は内部で _call_openai_api という関数を呼んでおり、ユニットテストでは patch で差し替え可能です（kabusys.ai.news_nlp._call_openai_api など）。
- J-Quants 呼び出しは RateLimiter とリトライを含みますが、外部 API を叩くテストでは get_id_token や _request をモックするとよいです。

---

## ディレクトリ構成（主要ファイル）
- src/kabusys/__init__.py
- src/kabusys/config.py
  - 環境変数管理（.env 自動ロード / Settings）
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py      — ニュースセンチメント（銘柄別 ai_scores）
  - regime_detector.py — マクロ + MA200 による市場レジーム判定
- src/kabusys/data/
  - __init__.py
  - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
  - pipeline.py            — ETL（run_daily_etl 他）
  - jquants_client.py      — J-Quants API クライアント（fetch_* / save_*）
  - news_collector.py      — RSS 収集・前処理
  - quality.py             — データ品質チェック
  - stats.py               — zscore_normalize 等の統計ユーティリティ
  - audit.py               — 監査ログスキーマ初期化
  - etl.py                 — ETL の公開インターフェース再エクスポート
- src/kabusys/research/
  - __init__.py
  - factor_research.py     — モメンタム / ボラティリティ / バリュー
  - feature_exploration.py — forward returns / IC / rank / factor_summary
- その他: 実運用に必要なスクリプトやワーカーはプロジェクトレイヤーで追加してください。

---

## 注意事項 / ベストプラクティス
- 本ライブラリは実運用の発注部分や実際のブローカー API との統合を含みません（監査ログ・発注要求テーブルはあるが、実ブローカー連携は別実装を想定）。
- OpenAI を利用する部分はコスト・レイテンシに注意してください。API 失敗時は多くの箇所でフォールバック（スコア 0.0 など）するよう設計されていますが、品質や安全設計はプロジェクト要件に合わせて拡張してください。
- ETL やニュース収集はスケジューラ（cron / Airflow / Prefect 等）で運用するのを想定しています。
- データベースファイル（DUCKDB_PATH）は適切なバックアップと同期ポリシーを検討してください。

---

この README はコード内のドキュメント文字列と設計方針に基づいて作成しました。必要があれば利用例の拡張、CI/デプロイ手順、具体的な SQL スキーマ（テーブル定義）やサンプル .env.example を追加します。どの項目を詳しく追記しますか？