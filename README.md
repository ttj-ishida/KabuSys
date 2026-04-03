# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
データ収集（J-Quants）、ETL、データ品質チェック、ニュースのNLPスコアリング（OpenAI）、市場レジーム判定、監査ログ（発注・約定トレーサビリティ）などの機能を提供します。

---

## プロジェクト概要

KabuSys は以下を主目的とした Python モジュール群です。

- J-Quants API からの株価・財務・カレンダー取得と DuckDB への冪等保存
- 日次 ETL パイプライン（差分 fetch + 保存 + 品質チェック）
- ニュース収集（RSS）と AI による銘柄別センチメント評価（gpt-4o-mini を想定）
- マクロセンチメントと ETF MA200 を組み合わせた市場レジーム判定
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）と統計ユーティリティ
- 監査ログ（signal → order_request → executions）のテーブル初期化とユーティリティ
- 環境変数 / .env 自動ロードと設定管理

設計上の特徴：
- ルックアヘッドバイアスを避けるため、内部で date.today()/datetime.today() を直接参照しない関数設計
- API 呼び出しに対するリトライ・バックオフやフェイルセーフ（失敗時は安全なデフォルトで継続）
- DuckDB を主要な永続化ストアとして想定（ファイルまたは :memory:）

---

## 機能一覧

主な機能（モジュール別）

- kabusys.config
  - 環境変数/.env 自動読み込み（.env, .env.local）と Settings クラス（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY 等）
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存・トークン自動リフレッシュ・レートリミット）
  - pipeline: 日次 ETL（run_daily_etl 等）と ETLResult
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management: 市場カレンダー操作（is_trading_day, next_trading_day 等）と夜間更新ジョブ
  - news_collector: RSS 収集（SSRF対策、前処理、冪等保存の前段）
  - audit: 監査テーブル定義と初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価し ai_scores に書込
  - regime_detector.score_regime: ETF(1321) の MA200 乖離 + マクロニュースの LLM センチメントを合成して market_regime を書込
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## セットアップ手順

前提
- Python 3.9+（コード内 typing の用法を踏まえた上で適宜バージョンを合わせてください）
- DuckDB、openai、defusedxml 等の依存パッケージを使用

推奨手順（UNIX 系を想定）:

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 必要パッケージをインストール（例）
   ```
   pip install -U pip
   pip install duckdb openai defusedxml
   # もしパッケージ化されているなら編集モードでインストール
   pip install -e .
   ```

4. 環境変数 / .env の準備  
   プロジェクトルートに .env または .env.local を置くと、自動でロードされます（読み込み順: OS 環境変数 > .env.local > .env）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   例 (.env):
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # OpenAI
   OPENAI_API_KEY=your_openai_api_key

   # kabu ステーション（必要に応じて）
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # データベースパス（任意）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

5. DuckDB 初期スキーマ（監査用など）を作成する場合:
   - Python コンソールやスクリプトから `kabusys.data.audit.init_audit_db` を呼ぶことで監査 DB を初期化できます（デフォルトで UTC タイムゾーンを設定します）。

---

## 使い方（いくつかの例）

以下はライブラリの代表的な利用例です。実行は Python スクリプト／REPL で行います。

1. 設定参照
   ```python
   from kabusys.config import settings
   print(settings.duckdb_path)
   print(settings.jquants_refresh_token)  # 未設定だと ValueError
   ```

2. DuckDB 接続を作り ETL を実行
   ```python
   import duckdb
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl

   # settings.duckdb_path を使うのが推奨
   conn = duckdb.connect(str(settings.duckdb_path))
   result = run_daily_etl(conn, target_date=date.today(), id_token=None)
   print(result.to_dict())
   ```

3. ニューススコアリング（OpenAI を使用）
   ```python
   import duckdb
   from datetime import date
   from kabusys.ai.news_nlp import score_news

   conn = duckdb.connect(str(settings.duckdb_path))
   n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None -> 環境変数 OPENAI_API_KEY を使用
   print(f"書き込み銘柄数: {n_written}")
   ```

4. 市場レジーム判定
   ```python
   from kabusys.ai.regime_detector import score_regime
   from datetime import date
   import duckdb

   conn = duckdb.connect(str(settings.duckdb_path))
   score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
   ```

5. 監査ログ DB 初期化
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # conn は初期化済みの DuckDB 接続
   ```

6. J-Quants の ID トークンを直接取得（必要に応じて）
   ```python
   from kabusys.data.jquants_client import get_id_token
   token = get_id_token()  # settings.jquants_refresh_token を用いて取得
   ```

注意点:
- OpenAI 呼び出しは料金とレート制限の対象です。API キーを適切に管理してください。
- ETL や AI 処理は外部 API に依存するため、ネットワーク・認証エラー時のフェイルセーフ設計が組み込まれていますが、ログを確認して適切な対処を行ってください。

---

## ディレクトリ構成

主要ファイル/モジュールの概観（src/kabusys 以下）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数・Settings
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュースの NLU / AI スコアリング（score_news）
    - regime_detector.py             — マクロ + MA200 による市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（fetch/保存/トークン）
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）、ETLResult
    - etl.py                         — ETL インターフェース再エクスポート
    - quality.py                     — データ品質チェック
    - stats.py                       — 統計ユーティリティ（zscore_normalize）
    - calendar_management.py         — 市場カレンダー管理（is_trading_day 等）
    - news_collector.py              — RSS 収集（SSRF 対策、前処理）
    - audit.py                       — 監査スキーマ定義・初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py             — ファクター計算（momentum, value, volatility）
    - feature_exploration.py         — 将来リターン / IC / 統計サマリー
  - monitoring/ (予想される監視系モジュール、現状 README のコードベースに含まれる参照あり)
  - execution/ (約定 / 発注ラッパー等、将来的なモジュール)

その他：
- .env / .env.local の自動読み込みロジックは config.py に実装されています。
- デフォルト DB パスや PID/KILL フラグなどの設定は Settings クラスで管理されています。

---

## 環境変数（主なキー）

主に以下の環境変数を利用します（Settings 参照）:

- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- KABU_API_PASSWORD: kabu API パスワード（発注等）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB DB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）のパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: .env 自動ロードを無効化（テスト用）

設定が不足している場合、Settings が ValueError を投げることがあります（必須項目参照時）。

---

## 注意事項 / 運用上のヒント

- DuckDB の executemany に関するバージョン依存の振る舞い（空リスト不可等）を考慮した実装になっています。DuckDB のバージョンに注意してください。
- OpenAI の JSON mode を利用して厳密な JSON レスポンスを要求していますが、LLM の応答が想定外の場合はパース回避やスキップのロジックがあります。結果はログで確認してください。
- news_collector は RSS の SSRF 対策（リダイレクト検査、プライベートアドレスブロック、受信サイズ制限）を実装していますが、運用時は取得ソースの信頼性を監視してください。
- 本ライブラリはバックテストループ内部での直接 API 呼び出しを想定していません（Look-ahead の観点）。研究用途の場合は過去時点でのデータを用意してから利用してください。

---

必要に応じて README にサンプル .env.example、追加の CLI やユニットテスト手順を追記できます。ほかに補足したいセクション（例: CI 設定、詳細なスキーマ定義、運用手順など）があれば教えてください。