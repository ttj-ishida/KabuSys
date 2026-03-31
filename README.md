# KabuSys

日本株向け自動売買プラットフォームのライブラリ群です。  
データETL、ニュース収集・NLPスコアリング、リサーチ用ファクター計算、監査ログ（発注/約定トレーサビリティ）、および市場レジーム判定などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構成するコア機能群を提供する Python パッケージです。主な目的は以下の通りです。

- J-Quants API を使った株価・財務・カレンダーの差分ETL
- RSS ベースのニュース収集と OpenAI を用いた銘柄別センチメント（ai_score）算出
- マーケットレジーム（bull/neutral/bear）判定（ETF の MA とマクロニュースを組合せ）
- 研究（リサーチ）用途のファクター計算および統計ユーティリティ
- 監査（Audit）テーブルによるシグナル→発注→約定のトレーサビリティ
- データ品質チェック（欠損、スパイク、重複、日付不整合）

設計上の特徴として、Look-ahead バイアスを避ける実装、フェイルセーフ（API失敗時はスキップ/デフォルト値）、および DuckDB を用いたローカル DB 管理を重視しています。

---

## 主な機能（モジュール別）

- kabusys.config
  - .env / 環境変数の自動読み込み（.env, .env.local）と設定アクセス（settings オブジェクト）
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得 / 保存 / ページネーション / トークン自動リフレッシュ / レート制御）
  - pipeline: 日次 ETL 実行 run_daily_etl / 個別 ETL run_prices_etl 等
  - calendar_management: JPX カレンダー管理・営業日判定・calendar_update_job
  - news_collector: RSS 取得・前処理・raw_news への保存補助（SSRF対策、受信上限等）
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - audit: 監査ログテーブル定義と初期化（init_audit_schema / init_audit_db）
  - stats: 汎用統計ユーティリティ（zscore_normalize 等）
- kabusys.ai
  - news_nlp.score_news: 銘柄別ニュースセンチメントを OpenAI で取得し ai_scores に書き込む
  - regime_detector.score_regime: ETF(1321) MA とマクロニュースの LLM スコアを合成し market_regime に書き込む
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## セットアップ手順

前提:
- Python 3.10 以上（PEP 604 の | 型表記などを使用）
- DuckDB を利用（pip パッケージ duckdb）
- OpenAI API を使う機能は openai パッケージが必要
- RSS パースに defusedxml を利用

例: 仮想環境を使ったインストール例

1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必須パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt がある場合はそちらを使用してください）

3. 開発インストール（プロジェクトルートで）
   - pip install -e .

環境変数（主要なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須。jquants_client.get_id_token で使用）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector などで使用）
- KABU_API_PASSWORD: kabuステーション関連のパスワード（必要時）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知連携用
- DUCKDB_PATH: デフォルトの DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境 ("development" / "paper_trading" / "live")（デフォルト: development）
- LOG_LEVEL: ログレベル ("DEBUG" 等)

.env 自動読み込み
- パッケージ import 時にプロジェクトルート（.git または pyproject.toml を探索）から .env/.env.local を自動ロードします。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます（テスト時に便利）。

データベース初期化（監査DB 例）
- 監査ログ用 DB を初期化する簡単な例:

  ```
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

  これによりテーブルとインデックスが作成されます（UTC タイムゾーンを設定）。

---

## 使い方（代表的な API と例）

以下は簡単な使用例です。詳細は各モジュールの docstring を参照してください。

- DuckDB 接続を作って ETL を実行する例:

  ```
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())
  ```

- ニューススコアリング（OpenAI 必須）:

  ```
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
  print("written:", n_written)
  ```

- 市場レジーム判定:

  ```
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
  ```

- ファクター計算（リサーチ用）:

  ```
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026,3,20))
  volatility = calc_volatility(conn, date(2026,3,20))
  value = calc_value(conn, date(2026,3,20))
  ```

- カレンダー操作の例:

  ```
  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import is_trading_day, next_trading_day, calendar_update_job

  conn = duckdb.connect("data/kabusys.duckdb")
  # カレンダー更新ジョブ
  calendar_update_job(conn)
  print(is_trading_day(conn, date(2026,3,20)))
  print(next_trading_day(conn, date(2026,3,20)))
  ```

- RSS フェッチ（ニュース収集）:

  ```
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles[:5]:
      print(a["id"], a["datetime"], a["title"])
  ```

注意点:
- OpenAI 呼び出しはリトライやフェイルセーフを実装していますが、API キーや利用制限に注意してください。
- ETL / データ保存は DuckDB のテーブルスキーマに依存します。実運用前にスキーマ作成（DDL 実行）やマイグレーションを行ってください。
- news_nlp と regime_detector は外部 API に依存するため、テスト時は _call_openai_api をモックすることを推奨します（コード中にそのための記述があります）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                      - 環境変数 / settings
  - ai/
    - __init__.py
    - news_nlp.py                  - 銘柄別ニューススコアリング（score_news）
    - regime_detector.py           - 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py            - J-Quants API クライアント（fetch/save）
    - pipeline.py                  - ETL パイプライン（run_daily_etl 等）
    - calendar_management.py       - マーケットカレンダー管理
    - news_collector.py            - RSS ニュース収集
    - quality.py                   - データ品質チェック
    - stats.py                     - 統計ユーティリティ（zscore_normalize）
    - audit.py                     - 監査ログスキーマ / 初期化
    - etl.py                       - ETLResult のエクスポート
  - research/
    - __init__.py
    - factor_research.py           - ファクター計算（momentum/value/volatility）
    - feature_exploration.py       - 将来リターン / IC / 統計サマリー 等
  - (他: strategy, execution, monitoring パッケージ用のエクスポートプレースホルダ)

各ファイルには詳細な docstring（処理フロー・設計方針・注意点）が記載されています。実装を拡張する際は既存の設計方針ドキュメントを参照してください。

---

## 運用上の留意点

- 環境変数管理:
  - .env/.env.local の自動読み込みは便利ですが、本番では機密情報を安全に管理すること（Vault 等）を推奨します。
- テスト:
  - OpenAI / J-Quants 等外部 API 呼び出しはモックして単体テストを実施してください。各モジュールはテスト容易性を考慮した設計（差し替え可能な内部関数）になっています。
- ログと監査:
  - 監査テーブルは削除しない前提で設計されています。発注・約定の完全トレースを保証するため、テーブル初期化・バックアップ戦略を定めてください。
- バックテスト/研究:
  - Look-ahead バイアス回避のため、データ取得時刻（fetched_at）や ETL の対象日扱いに注意してください。jquants_client.fetch_listed_info 等は「いつそのデータが利用可能だったか」を意識して使用すること。

---

README はここまでです。さらに具体的な利用例、スキーマ定義、CI やデプロイ手順が必要であれば教えてください。追加でサンプル .env.example も作成できます。