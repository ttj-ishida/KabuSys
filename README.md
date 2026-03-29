# KabuSys

日本株向け自動売買・データ基盤ライブラリ（KabuSys）

短い概要:
- 株価・財務・ニュースのETL、データ品質チェック、特徴量計算、ニュース/NLP スコアリング（OpenAI）、市場レジーム判定、監査ログ（発注→約定トレーサビリティ）などを含むモジュール群です。主にバックオフィスのデータパイプラインやリサーチ、戦略実行基盤として利用することを想定しています。

---

## 主な機能（抜粋）

- データ取得/保存（J-Quants API 経由）
  - 株価日足（OHLCV）、財務（四半期）、JPX カレンダー、上場銘柄一覧
  - DuckDB に対する冪等保存（ON CONFLICT DO UPDATE）
- ETL パイプライン
  - 差分取得、バックフィル、品質チェック（欠損・スパイク・重複・日付不整合）
  - run_daily_etl による一括処理
- ニュース収集
  - RSS 取得・前処理・raw_news 保存、ニュースと銘柄の紐付け
  - SSRF/大容量レスポンス対策、トラッキングパラメータ除去等のセキュリティ実装
- ニュース NLP / LLM スコアリング
  - gpt-4o-mini（JSON Mode）を用いた銘柄別センチメント（score_news）
  - マクロ記事を使った市場レジーム判定（score_regime）
  - API エラー時のリトライ・フォールバック（安全側: スコア 0 等）
- リサーチ用ユーティリティ
  - ファクター計算（モメンタム・バリュー・ボラティリティ等）
  - 将来リターン計算、IC 計算、Zスコア正規化 等
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブルの初期化・管理
  - 発注→約定までの UUID ベースのトレーサビリティ
- 環境・設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - settings オブジェクト経由で設定値にアクセス

---

## セットアップ手順（開発用）

※ プロジェクトは一般的な Python パッケージ構成（src 配下）を想定しています。以下は一例です。

1. Python 環境準備
   - 推奨: Python 3.10+（ソース内の型注釈に基づく）
   - 仮想環境を作成・有効化:
     ```bash
     python -m venv .venv
     source .venv/bin/activate  # macOS / Linux
     .venv\Scripts\activate     # Windows
     ```

2. 依存パッケージをインストール
   - main に必要なライブラリ（例）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     ```bash
     pip install duckdb openai defusedxml
     ```
   - （プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください）

3. パッケージをインストール（開発モード）
   - プロジェクトルートで:
     ```bash
     pip install -e .
     ```
   - （セットアップファイルがあることを前提。なければ PYTHONPATH に src を追加するか、開発用に直接 import してください。）

4. 環境変数設定
   - 環境変数は .env / .env.local または OS 環境変数から読み込まれます。
   - 自動読み込みを無効化する場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主要な必須環境変数（代表例）:
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
     - KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
     - SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot Token
     - SLACK_CHANNEL_ID (必須) — 通知先チャネルID
     - OPENAI_API_KEY (推奨) — OpenAI 呼び出しに使用（score_news / score_regime）
   - 任意 / デフォルト有り:
     - KABUSYS_ENV = development | paper_trading | live  (デフォルト: development)
     - LOG_LEVEL = DEBUG | INFO | ... (デフォルト: INFO)
     - KABUSYS_DISABLE_AUTO_ENV_LOAD = 1（自動 .env ロードを無効化）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）

   - .env の例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
     OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

---

## 使い方（代表的な呼び出し例）

以下は Python REPL / スクリプトからの利用例です。DuckDB 接続は duckdb.connect() で取得します。

1. ETL（run_daily_etl）
   ```python
   from datetime import date
   import duckdb
   from kabusys.data.pipeline import run_daily_etl

   conn = duckdb.connect("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(result.to_dict())
   ```

2. ニュースセンチメントスコア（score_news）
   ```python
   from datetime import date
   import duckdb
   from kabusys.ai.news_nlp import score_news

   conn = duckdb.connect("data/kabusys.duckdb")
   written = score_news(conn, target_date=date(2026, 3, 20))
   print(f"書込銘柄数: {written}")
   ```

3. 市場レジーム判定（score_regime）
   ```python
   from datetime import date
   import duckdb
   from kabusys.ai.regime_detector import score_regime

   conn = duckdb.connect("data/kabusys.duckdb")
   score_regime(conn, target_date=date(2026, 3, 20))
   ```

4. 監査ログ DB 初期化（audit）
   ```python
   from kabusys.data.audit import init_audit_db

   conn = init_audit_db("data/audit.duckdb")
   # conn を使って監査テーブルにアクセスできます
   ```

5. 設定値参照
   ```python
   from kabusys.config import settings
   print(settings.duckdb_path)           # Path オブジェクト
   print(settings.is_live)
   ```

注意点:
- score_news / score_regime は OpenAI（gpt-4o-mini）を使用するため OPENAI_API_KEY が必要です。テスト時は内部の _call_openai_api をモックして差し替え可能です（コード中にそのための注記があります）。
- J-Quants API 呼び出しには JQUANTS_REFRESH_TOKEN が必須です。
- ETL は外部 API 呼び出しを伴うため、ネットワーク環境や API レート制限に注意してください（J-Quants: 120 req/min を想定した RateLimiter 実装あり）。

---

## スケジューリング例

- nightly ETL（cron 例）
  - 毎日深夜に run_daily_etl を実行して DuckDB を更新し、品質チェックを行う運用が想定されています。
  - systemd / cron / Airflow / Prefect 等のジョブスケジューラに組み込み可能です。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を想定）

- kabusys/__init__.py
  - パッケージメタ情報（__version__）とサブパッケージの公開設定

- kabusys/config.py
  - 環境変数の自動読み込み (.env / .env.local) と settings オブジェクト

- kabusys/ai/
  - __init__.py
  - news_nlp.py      — ニュースの LLM スコアリングと関連ユーティリティ
  - regime_detector.py — マクロセンチメント + MA を使った市場レジーム判定

- kabusys/data/
  - __init__.py
  - jquants_client.py  — J-Quants API クライアント + DuckDB 保存ロジック
  - pipeline.py        — ETL パイプライン（run_daily_etl 等）
  - etl.py             — ETLResult の再エクスポート
  - news_collector.py  — RSS 収集・前処理・保存ロジック
  - calendar_management.py — 市場カレンダー管理 / 営業日判定ユーティリティ
  - stats.py           — zscore_normalize 等の統計ユーティリティ
  - quality.py         — 品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py           — 監査ログ（テーブルDDL／初期化ユーティリティ）

- kabusys/research/
  - __init__.py
  - factor_research.py     — モメンタム / バリュー / ボラティリティ計算
  - feature_exploration.py — 将来リターン / IC / ランク / 統計サマリー

---

## 開発・テスト上の注意

- 時刻の扱い:
  - 多くのモジュールは datetime.today() / date.today() を内部で参照しない設計（ルックアヘッドバイアス防止）。関数に target_date を渡して deterministic に処理できます。
- OpenAI 呼び出し:
  - テストでは kabusys.ai.news_nlp._call_openai_api や kabusys.ai.regime_detector._call_openai_api を unittest.mock.patch 等で差し替えてください。
- DuckDB executemany の空リスト制約への配慮がコード内にあるため、直接 SQL を叩く場合の互換性や空データ処理に注意してください。
- RSS 収集では SSRF 対策・受信バイト数上限・gzip 解凍上限等の安全対策が実装されています。

---

## ライセンス / 貢献

- 本リポジトリのライセンスや貢献ルールはリポジトリルートの LICENSE / CONTRIBUTING を参照してください（本サンプルには含まれていません）。

---

README の補足や使用シナリオ（CI 設定、運用監視、Slack 通知の組み込み等）についてさらに詳しいドキュメントが必要であれば、用途に合わせて追加で作成します。どの部分を深掘りしますか？