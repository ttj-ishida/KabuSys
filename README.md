# KabuSys

日本株のデータプラットフォームと自動売買支援ライブラリ（KabuSys）の README。  
このリポジトリはデータ取得（J-Quants）、ニュース収集・NLP（OpenAI）、研究用ファクター計算、ETL、監査ログ等の実装を含みます。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム構築を目的とした Python モジュール群です。主な役割は次の通りです。

- J-Quants API から株価・財務・市場カレンダーを差分取得して DuckDB に保存する ETL パイプライン
- RSS ベースのニュース収集と前処理（raw_news テーブル）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別 ai_score, マクロセンチメント）
- 市場レジーム判定（MA200 とマクロセンチメントを統合）
- 研究用のファクター計算・特徴量解析（モメンタム、バリュー、ボラティリティ、将来リターン、IC 等）
- データ品質チェック、マーケットカレンダー管理、監査ログ（トレーサビリティ）用スキーマ
- 環境変数 / .env 管理ユーティリティ

設計上、バックテストでのルックアヘッドバイアスを避けるために日時参照や DB クエリは慎重に実装されています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API 取得（差分取得・ページネーション・保存）
  - pipeline: 日次 ETL（prices, financials, calendar）と ETL 結果管理
  - news_collector: RSS 収集、前処理、raw_news 保存
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - calendar_management: JPX カレンダー管理、営業日判定ユーティリティ
  - audit: 監査ログスキーマ生成・初期化（signal / order_request / executions など）
  - stats: 汎用統計ユーティリティ（Zスコア正規化等）
- ai/
  - news_nlp: 銘柄ごとのニュースセンチメントを OpenAI に問い合わせて ai_scores を生成
  - regime_detector: ETF（1321）200日 MA とマクロニュースセンチメントを組み合わせて市場レジーム判定
- research/
  - factor_research: Momentum, Value, Volatility 等のファクター計算
  - feature_exploration: 将来リターン計算、IC 計算、統計サマリー
- config.py: .env / 環境変数の自動読み込み・設定アクセス
- その他: 実用的なユーティリティ群

---

## セットアップ手順

前提: Python 3.9+（コードは型注釈に Python >=3.9 構文を使用）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境の作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール  
   （プロジェクトに requirements.txt / pyproject.toml がある前提でインストール。なければ最低限の必須パッケージを入れてください）
   - pip install duckdb openai defusedxml

   ※ 実際のプロジェクトでは pyproject.toml / requirements.txt を参照してください。

4. 環境変数 / .env の用意  
   プロジェクトルートに `.env` または `.env.local` を置くと自動的に読み込まれます（CWD ではなくパッケージ位置からプロジェクトルートを探索）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   重要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN=...        # 必須（J-Quants 認証用リフレッシュトークン）
   - OPENAI_API_KEY=...               # OpenAI API キー（news_nlp, regime_detector）
   - KABU_API_PASSWORD=...            # kabuステーション API のパスワード（必要に応じて）
   - KABUSYS_ENV=development|paper_trading|live
   - LOG_LEVEL=INFO
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. データディレクトリの作成（必要に応じて）
   - mkdir -p data

---

## 基本的な使い方

下記は Python REPL やスクリプトから利用する例です。DuckDB 接続はファイルパス（例: data/kabusys.duckdb）を指定して確立します。

- ETL（日次パイプライン）の実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別 ai_score）を生成
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env OPENAI_API_KEY を使用
  print("scored:", n_written)
  ```

- 市場レジーム判定（ma200 + マクロニュース）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ用 DuckDB 初期化
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # 必要なテーブルとインデックスが作成されます
  ```

- 設定アクセス（環境変数）
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  ```

- 研究用関数（例: モメンタム）
  ```python
  from kabusys.research.factor_research import calc_momentum
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, date(2026, 3, 20))
  ```

注意点:
- OpenAI 呼び出しには API キーが必要です（api_key 引数で明示的に与えるか、環境変数 OPENAI_API_KEY を設定してください）。API コールはリトライやフェイルセーフ（失敗時は 0.0 等で継続）を備えています。
- J-Quants API は認証トークン（リフレッシュトークン）を使用します。settings.jquants_refresh_token を設定してください。
- DuckDB に対する executemany の空リストは一部バージョンでエラーになるため、内部実装で注意されています。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants の refresh token
- OPENAI_API_KEY — OpenAI API キー
- KABU_API_PASSWORD — kabuステーション API のパスワード
- KABUSYS_ENV — 環境 "development" / "paper_trading" / "live"（デフォルト development）
- LOG_LEVEL — "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH 等の監視用パス

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml を基準）配下の `.env` → `.env.local` が順に読み込まれます。
- 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数/.env 管理
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースセンチメント解析 & ai_scores 書込
    - regime_detector.py            — 市場レジーム判定（1321 MA200 + マクロ）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（fetch/save）
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - news_collector.py             — RSS 収集・前処理
    - quality.py                    — データ品質チェック
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - calendar_management.py        — 市場カレンダー管理・営業日判定
    - audit.py                      — 監査ログスキーマ初期化
    - etl.py                        — ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py            — Momentum/Value/Volatility 等
    - feature_exploration.py        — 将来リターン, IC, summary, rank

（上記ファイル単位で関数・クラスの目的が README の各章に記載されています）

---

## 開発・テストのヒント

- API キーや外部コールを伴う関数は、テスト時にモック（unittest.mock.patch）を使用する想定で実装されています（例: news_nlp._call_openai_api を差し替え可能）。
- DuckDB はインメモリ(":memory:") もサポートしているため、単体テストでファイルを残さずに実行できます。
- ETL は部分的に失敗しても他処理に影響を与えないように例外処理が組まれています。ログで詳細を確認してください。

---

## ライセンス / 貢献

この README はコードベースの概要説明です。実際の配布リポジトリでは LICENSE / CONTRIBUTING.md を参照してください。

---

問題があれば使い方の具体的な例（実行コマンドやスクリプト）や .env.example のテンプレートを追加で生成します。どの操作を優先して説明しますか？