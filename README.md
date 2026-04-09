# KabuSys

KabuSys は日本株向けのデータプラットフォーム兼自動売買基盤のライブラリ群です。  
J-Quants / RSS / OpenAI 等の外部データを取り込み、ETL・品質チェック・特徴量計算・ニュース NLP・市場レジーム判定・監査ログの管理など、アルゴリズム取引のための機能を提供します。

バージョン: 0.1.0

---

## 主な機能一覧

- 環境変数 / .env 管理（自動ロード機能）
- J-Quants API クライアント
  - 株価日足（OHLCV）取得と DuckDB への冪等保存
  - 財務データ取得と保存
  - JPX マーケットカレンダー取得と保存
- ETL パイプライン（差分取得 / 保存 / 品質チェック）
  - run_daily_etl を通じてカレンダー・株価・財務の差分更新を実行
- データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
- ニュース収集（RSS）と前処理（SSRF 対策、トラッキング除去）
- ニュース NLP（OpenAI）による銘柄別センチメントスコアリング
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、統計）
- 監査ログ（signal / order_request / executions）のスキーマ初期化と管理
- 各種ユーティリティ（カレンダー判定、統計正規化等）

---

## 必要な環境変数（主なもの）

以下はこのコードベースが参照する主な環境変数の例です。プロジェクトルートの `.env` / `.env.local` で管理できます（自動読み込みあり。無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE: paper trading の挙動（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH: Paper trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH / KILL_FLAG_PATH 等の監視関連設定

設定はコード上の `kabusys.config.settings` 経由で参照できます（例: `settings.jquants_refresh_token`）。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンして仮想環境を作成
   - python >= 3.10 を推奨
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate

2. 依存パッケージのインストール  
   （requirements.txt はプロジェクトに合わせて作成してください。最低限必要なパッケージ例を示します）

   - 推奨パッケージ:
     - duckdb
     - openai
     - defusedxml
     - requests（必要に応じて）
   - 例:
     - pip install duckdb openai defusedxml

3. 環境変数を設定  
   - プロジェクトルートに `.env` を作成し上記の必須キーを設定してください（例: JQUANTS_REFRESH_TOKEN=xxx）。
   - 自動ロード: パッケージはプロジェクトルート（`.git` または `pyproject.toml` が存在するディレクトリ）から `.env` / `.env.local` を自動読み込みします。テストや特殊用途では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化できます。

4. DuckDB の初期化（監査DB の例）
   - 監査スキーマだけを初期化する場合:
     - python
       - from kabusys.data.audit import init_audit_db
       - conn = init_audit_db("data/audit.duckdb")
     - これにより監査用テーブルとインデックスが作成されます（UTC タイムゾーン設定あり）。

5. （任意）データベーススキーマの初期化  
   - ETL で使う `raw_prices` / `raw_financials` / `market_calendar` 等のテーブルは ETL 用初期化スクリプトから作成するか、別途用意してください。監査スキーマのみは `init_audit_db` で作れます。

---

## 使い方（主要な API とサンプル）

- DuckDB 接続例
  - import duckdb
  - from kabusys.config import settings
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行
  - from kabusys.data.pipeline import run_daily_etl
  - from kabusys.config import settings
  - conn = duckdb.connect(str(settings.duckdb_path))
  - result = run_daily_etl(conn, target_date=None, id_token=None)
  - print(result.to_dict())

  run_daily_etl は
  1) カレンダー ETL（lookahead）  
  2) 株価 ETL（差分＋バックフィル）  
  3) 財務 ETL（差分＋バックフィル）  
  4) 品質チェック（オプション）
  を順に実行し、ETLResult を返します。

- ニュース NLP（銘柄別スコア算出）
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - conn = duckdb.connect(str(settings.duckdb_path))
  - n = score_news(conn, target_date=date(2026,3,20), api_key=None)
  - print(f"scored {n} codes")

  - OpenAI API キーは `api_key` 引数で渡すか、環境変数 `OPENAI_API_KEY` を設定してください。

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - conn = duckdb.connect(str(settings.duckdb_path))
  - score_regime(conn, target_date=date(2026,3,20), api_key=None)

  - この関数は ETF 1321 の 200 日 MA 乖離とマクロニュースの LLM センチメントを合成して market_regime テーブルへ書き込みます。

- 監査スキーマ初期化
  - from kabusys.data.audit import init_audit_db
  - conn = init_audit_db("data/audit.duckdb")
  - これにより signal_events / order_requests / executions といった監査テーブルが作成されます。

- J-Quants のトークン取得（内部で使用）
  - from kabusys.data.jquants_client import get_id_token
  - token = get_id_token()  # settings.jquants_refresh_token を用いる

---

## 自動 .env ロードの挙動

- パッケージロード時にプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を探索し、見つかればそのルートにある `.env` と `.env.local` を読み込みます。
- 読み込み順: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

.env ファイルの取り扱いは堅牢に実装されており、コメント・クォート・export プレフィックス等に対応します。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（銘柄別センチメント）
    - regime_detector.py     — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント & 保存ロジック
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult 再エクスポート
    - quality.py             — データ品質チェック
    - news_collector.py      — RSS 収集 / 前処理
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py     — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - research パッケージは Data/Prices を参照して研究用途の集計を行います。

---

## 実運用での注意点 / ベストプラクティス

- OpenAI / J-Quants の API キーは環境変数か関数引数で確実に渡してください。キーが無いと関連機能は ValueError を投げます。
- ETL と研究コードは Look-ahead bias を避けるよう設計されています（target_date を外部から渡し、内部で date.today() に頼らない等）。
- DuckDB への INSERT は多くの場所で ON CONFLICT による冪等保存を行っています。部分失敗時でも既存データを不要に消さない工夫がありますが、運用前にスキーマとマイグレーションを整備してください。
- news_collector は SSRF / XML Bomb 対策を組み込んでいますが、RSS ソースは信頼できるものを設定してください。
- 大量 API 呼び出しはレート制限に注意（J-Quants は 120 req/min）。jquants_client は内部で RateLimiter を実装していますが、運用スケジュールを計画してください。

---

## 例: 最小ワークフロー（手順）

1. 仮想環境を作る・依存を入れる
2. .env に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY 等を配置
3. DuckDB ファイルを指定（デフォルトは data/kabusys.duckdb）
4. Python スクリプトから:
   - conn = duckdb.connect("data/kabusys.duckdb")
   - from kabusys.data.pipeline import run_daily_etl
   - run_daily_etl(conn)

---

README の内容はコードの概要に基づいた最小限のドキュメントです。実運用やデプロイ時にはさらに以下を用意してください。

- requirements.txt / poetry/pyproject.toml（依存・バージョン固定）
- DB スキーマ初期化スクリプト（raw_prices 等の DDL）
- 運用用設定例 (.env.example)
- 実行スケジュール（cron / systemd / CI）・監視／ロギング設定

追加で README に記載したい情報（具体的な DDL、.env.example、CI 設定例 など）があれば教えてください。必要に応じて追記します。