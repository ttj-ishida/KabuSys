# KabuSys

日本株自動売買システムのライブラリ群です。データ収集（J-Quants / RSS）、ETL、データ品質チェック、ファクター計算、AI を用いたニュースセンチメント評価、監査ログ（発注〜約定のトレーサビリティ）など、量的投資・運用用の基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は、日本株の自動売買インフラを構成するためのモジュール群です。主な役割は以下の通りです。

- J-Quants API からのデータ取得（株価日足、財務情報、マーケットカレンダー）
- RSS を使ったニュース収集と前処理
- 日次 ETL パイプライン（差分取得・保存・品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）
- AI（OpenAI）を使用したニュースセンチメント / 市場レジーム判定
- 監査ログ（signal → order_request → execution）用スキーマ生成・初期化
- 環境変数による設定管理（.env 自動読み込み機能あり）

設計上の重要な方針として、バックテストやモデル評価におけるルックアヘッドバイアスを避ける実装（date の明示的指定や DB クエリの排他条件）や、API 呼び出しのリトライ／フォールバック（失敗時の安全停止）を重視しています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション・レート制御・トークン自動リフレッシュ・DuckDB への冪等保存）
  - pipeline: 日次 ETL パイプライン（run_daily_etl など）
  - news_collector: RSS フィード収集・正規化（SSRF 保護・サイズ制限・URL 正規化）
  - calendar_management: 市場カレンダー管理・営業日判定ユーティリティ
  - quality: データ品質チェック群（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログスキーマ作成 / 初期化（signal, order_requests, executions）
  - stats: 汎用統計ユーティリティ（z-score 正規化）
- research/
  - factor_research: Momentum / Value / Volatility 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（スピアマン）計算、統計サマリー、ランキング
- ai/
  - news_nlp.score_news: ニュースを銘柄別に集約して OpenAI に投げ、ai_scores テーブルに書き込む
  - regime_detector.score_regime: ETF（1321）MA とマクロニュースの LLM 評価を合成して市場レジーム判定を実行
- config: 環境変数 / .env 読み込み・検証（自動 .env ロード、必須キーチェック）
- その他: ETL 結果を表す ETLResult 型など

---

## 必要要件（例）

最低限必要な Python パッケージ（抜粋）:

- Python 3.10+
- duckdb
- openai
- defusedxml

（実際のプロジェクトでは packaging に requirements.txt / pyproject.toml を用意してください）

---

## セットアップ手順

1. リポジトリのクローン / 配布パッケージを配置

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml

4. 環境変数 / .env を準備
   - プロジェクトルートに `.env`（および `.env.local` があれば優先）を置くと自動でロードされます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   代表的なキー (.env の例):
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - OPENAI_API_KEY=your_openai_api_key
   - KABU_API_PASSWORD=your_kabu_api_password
   - SLACK_BOT_TOKEN=your_slack_token
   - SLACK_CHANNEL_ID=your_slack_channel
   - KABUSYS_ENV=development       # 有効値: development, paper_trading, live
   - LOG_LEVEL=INFO
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi

   注意: Settings で必須になっている環境変数が未設定の場合、アクセス時に ValueError が発生します。

5. データディレクトリの作成（必要に応じて）
   - mkdir -p data

---

## 使い方（簡単な例）

以下は基本的な利用例です。実際にはアプリケーションやバッチジョブからこれらの関数を呼び出します。

- DuckDB 接続を作成する例:
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する:
  ```python
  from kabusys.data.pipeline import run_daily_etl

  # target_date を指定することでルックアヘッドバイアスを回避できます
  result = run_daily_etl(conn, target_date=None)  # None = 今日
  print(result.to_dict())
  ```

- ニュースをスコアリングして ai_scores に書き込む:
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written: {written}")
  ```

- 市場レジーム判定を実行する:
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用の DB を初期化する:
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # あるいは既存 conn に対してスキーマを追加する:
  # from kabusys.data.audit import init_audit_schema
  # init_audit_schema(conn)
  ```

- 研究用ファクター計算の例:
  ```python
  from datetime import date
  from kabusys.research import calc_momentum, calc_value, calc_volatility

  m = calc_momentum(conn, date(2026, 3, 20))
  v = calc_value(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  ```

- 環境設定の参照:
  ```python
  from kabusys.config import settings
  print(settings.env, settings.is_live, settings.duckdb_path)
  ```

---

## 環境変数と自動 .env 読み込み

- 実行時、`kabusys.config` はプロジェクトルート（.git または pyproject.toml を基準）を探して `.env` と `.env.local` を自動的に読み込みます。
  - 読み込み優先度: OS 環境変数 > .env.local > .env
  - テスト等で自動読み込みを抑制する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 必須の環境変数（アクセス時に例外を投げるもの）は settings のプロパティで定義されています（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）。
- `KABUSYS_ENV` の有効値: `development`, `paper_trading`, `live`（その他は ValueError）

---

## トラブルシューティング

- "環境変数 'X' が設定されていません" エラー:
  - .env にキーがあるか、または環境変数がプロセスに渡されているか確認してください。
- OpenAI API 呼び出しエラー / レスポンスパース失敗:
  - ネットワーク断やレート制限はモジュール側でリトライ・フォールバックしますが、長時間失敗する場合は API キーやネットワーク接続、レスポンスの形式を確認してください。
- DuckDB の executemany 空リストエラー:
  - 一部の保存処理は DuckDB のバージョン差分を考慮して空パラメータを送らない実装になっています。自作処理で同様の問題が出る場合は送るパラメータを検査してください。

---

## ディレクトリ構成（主要ファイル）

以下は本コードベースの主要モジュールとファイル構成（抜粋）です。

- src/kabusys/
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
    - etl.py (ETLResult re-export)
    - calendar_management.py
    - news_collector.py
    - stats.py
    - quality.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py

各モジュールの責務はファイル先頭のドキュメント文字列（docstring）に詳細が記載されています。関数の挙動や引数仕様、フォールバック動作については該当モジュールの docstring と実装を参照してください。

---

## 開発・拡張のヒント

- OpenAI 呼び出し部分はテスト容易性のために _call_openai_api を内部で定義しており、unit test 側でモック差し替えが可能です。
- ETL / データ取得は差分方式（最終取得日を基準）になっており、backfill_days で過去 N 日を再取得して API 側の後出し修正に対応します。
- DuckDB に保存する際は冪等性（ON CONFLICT DO UPDATE 等）を保つ実装になっています。schema 変更を行う場合、既存データや UNIQUE 制約に注意してください。

---

必要に応じて README に追加したい内容（例: 実際の requirements.txt、CI / デプロイ手順、ハードウェア要件、運用上の注意点など）があれば教えてください。README を用途に合わせて拡張します。