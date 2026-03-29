# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL によるデータ取得・品質チェック、ニュースの収集と LLM によるニュースセンチメント、ファクター計算、監査ログ（オーダー／約定トレーサビリティ）などを含みます。

主な目的は「バックテスト」「リサーチ」「ライブ監視／発注」の基盤機能を提供することです。

## 主な機能一覧
- データ ETL（J-Quants からの株価・財務・マーケットカレンダー取得）
  - 差分取得、ページネーション、トークン自動更新、レート制御、冪等保存
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（RSS → raw_news、SSRF / Gzip / サイズ上限対策、トラッキングパラメータ除去）
- ニュース NLP（OpenAI を使った銘柄毎センチメントスコアリング）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM スコアを合成）
- 研究用ユーティリティ（モメンタム / バリュー / ボラティリティ 等のファクター計算、将来リターン、IC、統計サマリ）
- 市場カレンダー管理（営業日判定、next/prev_trading_day、calendar 更新ジョブ）
- 監査ログ（signal_events / order_requests / executions の初期化・インデックス作成）
- 共通設定管理（.env 自動読み込み、環境変数必須チェック）
- 汎用統計ユーティリティ（Zスコア正規化 等）

## セットアップ手順（開発環境）
以下は最小限のセットアップ例です。プロジェクトがパッケージ化されていれば `pip install -e .` を推奨します。

1. Python 仮想環境を作成・有効化
   - bash 例:
     - python -m venv .venv
     - source .venv/bin/activate

2. 必要パッケージをインストール
   - 例（プロジェクトに requirements.txt がある場合）:
     - pip install -r requirements.txt
   - 直接インストールする場合（最低限）:
     - pip install duckdb openai defusedxml
   - 実運用ではログ、Slack、HTTP クライアント等のライブラリが追加で必要になる可能性があります。

3. 環境変数 / .env ファイルを用意
   - プロジェクトルート（pyproject.toml あるいは .git があるディレクトリ）に `.env` または `.env.local` を置くと自動読み込みされます（自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセット）。
   - 必要な環境変数の例:
     - JQUANTS_REFRESH_TOKEN=（必須: J-Quants リフレッシュトークン）
     - OPENAI_API_KEY=（OpenAI を直接参照する場合）
     - KABU_API_PASSWORD=（kabuステーション API 用）
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi（任意、デフォルトあり）
     - SLACK_BOT_TOKEN=（監視通知などで使用する場合）
     - SLACK_CHANNEL_ID=（監視通知先）
     - DUCKDB_PATH=data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH=data/monitoring.db（デフォルト）
     - KABUSYS_ENV=development|paper_trading|live（デフォルト development）
     - LOG_LEVEL=INFO|DEBUG|...（デフォルト INFO）
   - `.env.example` を参考に作成してください（README に同梱されている場合はそれを参照）。

4. データディレクトリ作成（必要に応じて）
   - 例: mkdir -p data

## 使い方（代表的な利用例）
以下はいくつかの主要 API のサンプル呼び出しです。実行前に環境変数（JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY 等）を設定してください。また DuckDB 接続はファイルパスや ":memory:" を指定できます。

- 日次 ETL を実行（株価・財務・カレンダーの差分取得 + 品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（AI）をスコア化して ai_scores テーブルへ書き込む
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key=None => 環境変数 OPENAI_API_KEY を参照
  print("written:", n_written)
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ用 DuckDB を初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- ファクター計算（研究用）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, target_date=date(2026,3,20))
  ```

- 設定の参照
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path, settings.env, settings.is_live)
  ```

注意点:
- OpenAI 呼び出しはネットワークエラーやレート制限を想定したリトライロジックを持ちますが、API キーが正しく設定されている必要があります。関数に api_key を直接渡すことも可能です。
- ETL / ニュース収集 / AI スコアリングは Look-ahead bias を避ける設計になっています（target_date 未満のみ参照など）。
- DuckDB バージョンに依存する挙動（executemany の空リスト扱い等）に注意してください（コード内に互換性対策あり）。

## ディレクトリ構成（主要ファイル）
（提供されたコードベースに基づく抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   -- ニュースの LLM によるスコアリング
    - regime_detector.py            -- マーケットレジーム判定
  - data/
    - __init__.py
    - jquants_client.py             -- J-Quants API クライアント（取得 + DuckDB への保存）
    - pipeline.py                   -- ETL パイプライン（run_daily_etl 等）
    - etl.py                        -- ETLResult 再エクスポート
    - calendar_management.py        -- マーケットカレンダー管理
    - news_collector.py             -- RSS ニュース収集
    - quality.py                    -- データ品質チェック
    - stats.py                      -- 共通統計ユーティリティ
    - audit.py                      -- 監査ログテーブル初期化
  - research/
    - __init__.py
    - factor_research.py            -- Momentum/Value/Volatility ファクター
    - feature_exploration.py        -- 将来リターン・IC・統計サマリ

（上記以外に strategy / execution / monitoring モジュールが想定されるが、今回の抜粋は主に data / ai / research に焦点を当てています）

## 環境変数（主要なもの）
- JQUANTS_REFRESH_TOKEN — 必須（J-Quants 用リフレッシュトークン）
- OPENAI_API_KEY — OpenAI 呼び出しを行う場合に必要（関数引数でも可）
- KABU_API_PASSWORD — kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知用
- DUCKDB_PATH — DuckDB のパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite（モニタリング DB）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化（1 をセット）

## 開発上の注意・トラブルシューティング
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を起点に行います。パッケージ配布後も動作するように設計されていますが、テスト時に自動読み込みを止めたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB の SQL 実行結果の日付型はモジュールで正しく date オブジェクトへ変換されますが、SQLite / 他 DB 側と連携する場合は型に注意してください。
- OpenAI のレスポンスは JSON Mode を利用し、レスポンスパースや予期しない出力に備えた堅牢化が組み込まれています。API への大量リクエストはレート制限に注意してください。
- J-Quants API の認証はリフレッシュトークン → id_token のフローを自動化しています。401 受信時は 1 回トークンをリフレッシュしてリトライします。

---

何か特定の利用例（バックテストとの組み合わせ、監視ジョブの作り方、Docker 化、CI/CD での ETL 実行方法など）を README に追記したい場合は用途に合わせてサンプルや手順を追加できます。必要な内容を教えてください。