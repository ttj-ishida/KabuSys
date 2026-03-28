# KabuSys

日本株向け自動売買／データプラットフォーム用ライブラリ。  
マーケットデータETL、ニュースNLP（LLM）によるセンチメント評価、レジーム判定、ファクター計算、データ品質チェック、監査ログなどの機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下のような機能群を持つ内部ツールキットです。

- J-Quants API を用いた株価・財務・カレンダー等の差分取得と DuckDB への保存（ETL）
- RSS ニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini）を用いたニュースの銘柄別センチメント評価（news_nlp）
- ETF（1321）とマクロニュースを組み合わせた市場レジーム判定（regime_detector）
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と研究用ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal_events / order_requests / executions）のスキーマ定義・初期化
- 環境変数／.env の自動読み込みと一元設定管理

設計方針として、バックテストでのルックアヘッドバイアスを避けるために日付参照は明示的な引数（target_date）で行うこと、外部 API の失敗はフェイルセーフ（ゼロやスキップ）で続行すること、DuckDB を用いてローカルにデータを保持すること、などが採用されています。

---

## 主な機能一覧

- ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants クライアント（kabusys.data.jquants_client）: 認証・ページネーション・レート制御・保存ロジック
- ニュース収集 / 前処理
  - fetch_rss / preprocess_text / news -> raw_news 保存（kabusys.data.news_collector）
  - SSRF / サイズ / トラッキング除去等の対策実装
- ニュースNLP（LLM）
  - score_news(conn, target_date, api_key=None)（kabusys.ai.news_nlp）
  - バッチ処理、レスポンス検証、スコアクリップ、部分失敗時の保護
- レジーム判定（市場センチメント統合）
  - score_regime(conn, target_date, api_key=None)（kabusys.ai.regime_detector）
  - ETF (1321) の MA200 乖離とマクロニュース（LLM）を組み合わせる
- 研究用ユーティリティ
  - ファクター計算（momentum / value / volatility）
  - forward_returns / calc_ic / factor_summary / zscore_normalize
- データ品質チェック
  - check_missing_data / check_duplicates / check_spike / check_date_consistency / run_all_checks（kabusys.data.quality）
- 監査ログ
  - init_audit_schema / init_audit_db（kabusys.data.audit）
  - signal_events / order_requests / executions テーブル、インデックス定義

---

## 必要条件

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml

（実行環境に合わせて適切なパッケージをインストールしてください。requirements.txt があればそれを使用してください）

---

## セットアップ手順（開発環境向け）

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存関係インストール（例）
   - pip install duckdb openai defusedxml

   またはプロジェクトに依存ファイルがあれば:
   - pip install -e .

3. 環境変数 / .env の準備
   - プロジェクトルート（pyproject.toml または .git があるディレクトリ）に `.env` と `.env.local` を配置すると自動読み込みされます（優先度: OS 環境 > .env.local > .env）。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時等）。

   例: .env.example
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # OpenAI
   OPENAI_API_KEY=sk-...

   # kabuステーション API
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # Slack（通知等で使用）
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

   # DB パス（省略時デフォルト）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 環境設定
   KABUSYS_ENV=development  # development | paper_trading | live
   LOG_LEVEL=INFO
   ```

4. DuckDB データベースや監査DBを初期化（必要に応じて）
   - 監査DBを作る例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```

---

## 使い方（代表的な API）

以下は短い利用例です。各関数の詳細はソースコードの docstring を参照してください。

- DuckDB 接続の作成（デフォルトパスは settings.duckdb_path）
  ```python
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL の実行（市場カレンダー・株価・財務・品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントのスコア付け（LLM 必須）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None -> OPENAI_API_KEY を参照
  print(f"scored {count} symbols")
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- ファクター計算（研究用途）
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date
  mom = calc_momentum(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  ```

- データ品質チェックの実行
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026, 3, 20))
  for i in issues:
      print(i)
  ```

- 監査スキーマの初期化（既存 DB に追加）
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（LLM 呼び出しが必要な処理で必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注連携がある場合必須）
- KABU_API_BASE_URL: kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知に使用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 開発環境識別 (development | paper_trading | live)
- LOG_LEVEL: ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みを無効化（1）

設定管理は kabusys.config.Settings 経由でアクセスできます（例: from kabusys.config import settings; settings.duckdb_path）。

---

## 注意点 / 運用上のポイント

- LLM（OpenAI）を利用する処理（news_nlp, regime_detector）は API キーと通信可能な環境が必要です。API 呼び出しはリトライやフォールバック（失敗時スコア=0.0）を備えていますが、レート・コストに注意してください。
- J-Quants API はレート制限が設定されています。jquants_client は固定間隔スロットリングおよびリトライを実装しています。
- データの「ルックアヘッドバイアス回避」が設計方針にあり、target_date を明示して処理することが推奨されています。
- news_collector は RSS の SSRF 対策・サイズチェック・XML 強化対策（defusedxml）を実装しています。外部 URL を扱うためネットワークやセキュリティ設定に注意してください。
- DuckDB の executemany の仕様差に注意（実装内で回避済みの箇所あり）。
- 監査ログは削除しない前提で設計されています（ON DELETE RESTRICT 等）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - calendar_management.py
    - etl.py
    - pipeline.py
    - stats.py
    - quality.py
    - audit.py
    - jquants_client.py
    - news_collector.py
    - (その他 jquants_client の補助ロジック等)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - (strategy / execution / monitoring パッケージは __all__ に宣言されているが、別途実装を想定)

---

## 開発・テストのヒント

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml）を起点に行われます。テスト時に .env の自動読み込みを避けたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しは内部で _call_openai_api を経由しており、ユニットテストでは patch してエミュレートできます（kabusys.ai.news_nlp._call_openai_api など）。
- ネットワーク依存の箇所（J-Quants / RSS / OpenAI）はモックして単体テストを作成すると安定します。

---

## 参考

- コード内の docstring（各モジュール・関数）に詳細な仕様と設計方針が記載されています。実装や運用時はそちらを参照してください。

---

もし README に追加したい利用例（CLI スクリプト、docker-compose、CI 設定など）があれば教えてください。用途に合わせて具体例を追記します。