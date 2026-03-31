# KabuSys

日本株向け自動売買・データ基盤ライブラリ（KabuSys）。  
J-Quants / JPX / RSS / OpenAI 等を利用してデータ収集・品質チェック・AIセンチメント評価・ファクター計算・監査ログ管理を行うためのモジュール群を提供します。

---

## 概要

KabuSys は日本株のデータパイプライン（ETL）と研究（factor/research）、および AI を用いたニュースセンチメント評価や市場レジーム判定、監査ログ（トレーサビリティ）をサポートする Python パッケージです。DuckDB を主要ストレージに用い、J-Quants API から市場データ・財務データ・カレンダーを取得、ニュースは RSS で収集して raw_news に保管、OpenAI（gpt-4o-mini 等）で記事のセンチメントを評価します。

設計方針として、バックテストでのルックアヘッドバイアス回避や冪等性（ON CONFLICT / DELETE→INSERT のパターン）、API リトライとレート制御、安全なRSS取り扱い（SSRF対策・defusedxml）等を重視しています。

---

## 機能一覧

- データ取得 / ETL
  - J-Quants からの株価（日足）、財務データ、JPX マーケットカレンダー取得（ページネーション対応）
  - 差分更新・バックフィル対応の ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- データ品質チェック
  - 欠損データ、スパイク検出、主キー重複、日付整合性チェック（quality.run_all_checks）

- ニュース収集 / NLP
  - RSS フィード取得（SSRF対策・サイズ制限・トラッキングパラメータ除去）
  - ニュースの前処理（URL除去・空白正規化）
  - OpenAI を使った銘柄ごとのニュースセンチメント評価（ai.news_nlp.score_news）

- 市場レジーム判定
  - ETF(1321) の 200 日移動平均乖離とマクロニュースの LLM センチメントを合成して日次レジーム判定（ai.regime_detector.score_regime）

- リサーチ / ファクター計算
  - Momentum / Volatility / Value などのファクター計算（research.calc_*）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー（feature_exploration）

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions の監査テーブル DDL、初期化ユーティリティ（data.audit.init_audit_db / init_audit_schema）

- ユーティリティ
  - クロスセクション Z-score 正規化（data.stats.zscore_normalize）
  - カレンダー管理（data.calendar_management）: 営業日判定・next/prev_trading_day・calendar_update_job

---

## セットアップ

前提:
- Python 3.10+（ソースは型ヒントで Python 3.10+ を想定）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

1. リポジトリをクローン（またはパッケージをプロジェクトに追加）
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要なパッケージをインストール
   - 基本的に以下のような依存が必要です（実際の requirements はプロジェクトに合わせて調整してください）:
     - duckdb
     - openai
     - defusedxml
   ```
   pip install duckdb openai defusedxml
   # または開発時は editable install (パッケージに setup.py / pyproject がある前提)
   pip install -e .
   ```

4. 環境変数のセットアップ
   - プロジェクトルート（.git または pyproject.toml を基準）に `.env` と `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可）。
   - 必須環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ETL用）
     - SLACK_BOT_TOKEN        : Slack 通知用 bot token（必要に応じて）
     - SLACK_CHANNEL_ID      : Slack チャンネル ID
     - KABU_API_PASSWORD     : kabuステーション API 用パスワード（必要に応じて）
     - OPENAI_API_KEY        : OpenAI API キー（ai.score系で必須）
   - 任意/デフォルト値:
     - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - PID_FILE_PATH (default: data/execution.pid)
     - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
     - KABUSYS_ENV (development / paper_trading / live、default: development)
     - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL、default: INFO)

   例 .env（テンプレート）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

---

## 使い方（簡単な例）

以下は Python REPL やスクリプトから呼び出す例です。DuckDB のパスは settings.duckdb_path を利用すると便利です。

- DuckDB に接続して日次 ETL を実行する
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを生成（ai.news_nlp）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY を環境変数に設定済みであれば api_key=None で動作
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込んだ銘柄数:", n_written)
  ```

- 市場レジームを判定（ai.regime_detector）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DuckDB を初期化する
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn は初期化済みの DuckDB 接続
  ```

- リサーチ用ユーティリティ
  ```python
  from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize
  from datetime import date
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026, 3, 20))
  normalized = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])
  ```

注意点:
- OpenAI 呼び出しを行う関数は api_key 引数または環境変数 OPENAI_API_KEY が必要です。
- J-Quants API 呼び出しには JQUANTS_REFRESH_TOKEN が必要です（get_id_token が使用）。
- DuckDB のテーブル構造は別途 initial schema を用意する想定です（ETL 実行前に適切なスキーマ作成が必要）。

---

## 実運用上の注意 / セキュリティ

- 機密情報（API トークン等）は .env に保存し、リポジトリに含めないでください。
- .env.local は .env より優先して読み込まれ、OS 環境変数は最優先で上書きを防ぎます。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使うと自動 .env 読み込みを無効化できます（テストや CI で便利）。
- RSS 取得では SSRF 対策や受信サイズチェックを実施していますが、外部 RSS の扱いには注意してください。
- OpenAI 等の外部 API は課金対象です。大量バッチを回す場合はレートやコストに注意してください。

---

## ディレクトリ構成

主要なファイル / モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                      # 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   # ニュースセンチメント（AI）
    - regime_detector.py            # 市場レジーム判定（AI + MA）
  - data/
    - __init__.py
    - jquants_client.py             # J-Quants API client + DuckDB 保存
    - pipeline.py                   # ETL パイプライン (run_daily_etl 等)
    - etl.py                        # ETL result export
    - news_collector.py             # RSS 収集・正規化
    - quality.py                    # 品質チェック
    - stats.py                      # 統計ユーティリティ（zscore_normalize）
    - calendar_management.py        # 市場カレンダー管理
    - audit.py                      # 監査ログ DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py            # Momentum/Volatility/Value 等
    - feature_exploration.py        # forward returns / IC / summary
  - ai/..., research/..., data/...  # （上で列挙した多数のサブ機能）

各モジュールはコメントで設計方針・API を記載しています。実際に利用する際は docstring を参照してください。

---

もし README に追加したい操作例（docker-compose、systemd サービス定義、CI 設定、SQL スキーマ定義の自動化等）があれば、その用途に合わせて具体的な手順を追記します。必要ならサンプル .env.example も作成できます。