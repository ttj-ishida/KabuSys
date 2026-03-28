# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。データ収集（J‑Quants / RSS）、ETL、データ品質チェック、研究用ファクター計算、AI（ニュースセンチメント、マーケットレジーム判定）、監査ログ（発注〜約定トレーサビリティ）などを一貫して提供します。

主にバックオフィスのバッチ処理やリサーチ環境、戦略開発の基盤として利用することを想定しています。

## 主な機能

- 環境変数・設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須設定のラップ（settings オブジェクト）

- データ取得・ETL（kabusys.data）
  - J‑Quants API クライアント（株価・財務・市場カレンダー・上場銘柄情報）
  - 差分 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - ニュース収集（RSS → raw_news、SSRF 対策、トラッキングパラメータ除去）
  - マーケットカレンダー管理（営業日判定、next/prev/get_trading_days）
  - 監査ログ（signal_events / order_requests / executions）の初期化・管理（DuckDB）

- AI 用ユーティリティ（kabusys.ai）
  - ニュースセンチメント集約（gpt-4o-mini を想定、JSON mode で応答取得）
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースセンチメントの合成）

- 研究用ツール（kabusys.research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化

- 汎用ユーティリティ
  - 統計ユーティリティ（zscore_normalize）
  - DuckDB を前提とした冪等保存ロジック、トランザクション制御、ログ出力パターン

## 必須環境・依存関係

- Python >= 3.10（PEP 604 の型合成や from __future__ annotations を使用）
- 推奨パッケージ（最低限）
  - duckdb
  - openai
  - defusedxml

例（pip）：  
pip install duckdb openai defusedxml

プロジェクト固有の追加依存があれば requirements.txt を用意してください。

## セットアップ手順

1. リポジトリをクローン／配置

2. Python 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml

4. 環境変数（.env）を用意
   - プロジェクトルート（pyproject.toml または .git がある階層）に `.env` または `.env.local` を配置すると自動読み込みされます（自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 最低限必要なキー（例）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - KABU_API_PASSWORD=your_kabus_api_password
     - SLACK_BOT_TOKEN=your_slack_token
     - SLACK_CHANNEL_ID=your_slack_channel_id
     - OPENAI_API_KEY=your_openai_api_key (AI 機能を使う場合)
     - (任意) KABUSYS_ENV=development|paper_trading|live
     - (任意) LOG_LEVEL=INFO|DEBUG|...

   例（.env）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUS_API_PASSWORD=secret
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB データベースファイルのディレクトリ作成（必要に応じて）
   - mkdir -p data

## 使い方（主要な操作例）

以下は最小限の利用例です。各関数は DuckDB の接続オブジェクト（duckdb.connect() の戻り値）を受け取ります。

- ETL（日次バッチ実行）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントスコア（AI 呼び出しが必要）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None で env の OPENAI_API_KEY を使用
  print("書き込み銘柄数:", written)
  ```

- 市場レジーム評価
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB の初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- 研究用ファクター計算
  ```python
  from kabusys.research.factor_research import calc_momentum
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
  print(len(momentum), momentum[:3])
  ```

- カレンダー／営業日ヘルパー
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  from datetime import date
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

注意点:
- AI 機能（news_nlp / regime_detector）は OpenAI API（gpt-4o-mini 等）を利用します。環境変数 OPENAI_API_KEY を設定してください。
- J‑Quants API を使う処理は JQUANTS_REFRESH_TOKEN を必要とします。
- DuckDB に対する INSERT/UPDATE は多くが冪等（ON CONFLICT）で安全に設計されています。

## 設定項目（主要）

- 環境変数から読み込まれるプロパティ（kabusys.config.Settings 経由）
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (省略時 "http://localhost:18080/kabusapi")
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
  - DUCKDB_PATH (既定: data/kabusys.duckdb)
  - SQLITE_PATH (既定: data/monitoring.db)
  - KABUSYS_ENV (development | paper_trading | live)（既定: development）
  - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)

自動読み込み:
- プロジェクトルート（.git または pyproject.toml のあるディレクトリ）にある `.env` と `.env.local` を読み込みます。OS 環境変数が優先され、.env.local は override=True で上書きします。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

## ディレクトリ構成（概要）

以下はパッケージ内の主要ファイルと役割（src/kabusys 配下）です。

- __init__.py
  - パッケージのバージョンと公開モジュール

- config.py
  - 環境変数と settings オブジェクト

- ai/
  - news_nlp.py        : ニュースを LLM でスコアリングして ai_scores に書き込むロジック
  - regime_detector.py : マクロセンチメントと ETF MA200 を合成して市場レジーム判定

- data/
  - jquants_client.py      : J‑Quants API クライアント（取得 + DuckDB 保存）
  - pipeline.py            : ETL パイプライン（run_daily_etl 等）
  - etl.py                 : ETLResult の再エクスポート
  - calendar_management.py : 市場カレンダー管理（営業日判定など）
  - stats.py               : 統計ユーティリティ（zscore_normalize）
  - quality.py             : データ品質チェック（欠損・スパイク・重複・日付不整合）
  - news_collector.py      : RSS 収集・前処理・raw_news 保存
  - audit.py               : 監査ログ（signal_events, order_requests, executions）スキーマ初期化

- research/
  - factor_research.py     : Momentum / Volatility / Value 等のファクター計算
  - feature_exploration.py : 将来リターン・IC・統計要約・ランク関数
  - __init__.py

- その他ユーティリティ（data.stats, data.etl など）

## 開発・運用上の注意

- ルックアヘッドバイアス対策:
  - 多くのモジュールは date パラメータを受け取り、内部で datetime.today() を直接参照しない設計です。バックテストや研究での利用はこの点を尊重してください。

- リトライ・フェイルセーフ:
  - 外部 API 呼び出し（J‑Quants / OpenAI）はリトライ機構とフェイルセーフ（失敗時は 0.0 にフォールバック、または処理をスキップ）を組み込んでいます。ログを参照して異常を監視してください。

- DB トランザクション:
  - クリティカルな書き込み（市場レジームや ai_scores など）は BEGIN/DELETE/INSERT/COMMIT の構造で冪等性を保っています。DuckDB の executemany に空リストを渡すと失敗するバージョンがあるため、実装で考慮しています。

## 貢献・拡張

- 新しいデータソースの追加（RSS ソース、API）の場合は news_collector / jquants_client を拡張してください。
- AI モデルを差し替える際は ai モジュールの _call_openai_api 周りを注入可能にすることでテストやモデル切替が容易になります（現在もテストで差し替え可能な設計）。
- 監査ログや発注フローを拡張する場合は data.audit のスキーマ設計方針（冪等性・削除不可・UTC タイムスタンプ）に従ってください。

---

不明点や README に追記してほしい具体的なサンプル（例: systemd ジョブ、Airflow DAG、CI 用の手順など）があれば教えてください。必要に応じて README に追記・例を追加します。