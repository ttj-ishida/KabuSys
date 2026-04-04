# KabuSys

日本株向け自動売買・データ基盤ライブラリ。J-Quants / Kabuステーション 等の外部サービスと連携し、データ収集（ETL）、品質チェック、ファクター計算、ニュース/NLP によるスコアリング、監査ログ管理、及び市場レジーム判定などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は、バックテスト / 研究環境および実運用を念頭に設計されたモジュール群を持つ Python パッケージです。主な目的は以下:

- J-Quants API からの株価・財務・カレンダー等の差分取得（ETL）
- DuckDB を用いたデータ格納と品質チェック
- ニュース収集（RSS）と OpenAI を用いたニュースセンチメント分析（銘柄別 ai_score）
- ETF とマクロニュースを組み合わせた市場レジーム判定（bull/neutral/bear）
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と特徴量探索
- 発注／約定の監査ログテーブル初期化・管理（監査トレーサビリティ）

設計方針として、ルックアヘッドバイアスの回避、冪等性、フェイルセーフ（API障害時は影響を最小化）を重視しています。

---

## 主な機能一覧

- data（データ基盤）
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（fetch/save 各種データ）
  - market calendar 管理・営業日判定（is_trading_day / next_trading_day / get_trading_days 等）
  - RSS ニュース収集（fetch_rss）と前処理
  - データ品質チェック（欠損、重複、スパイク、日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）

- ai（ニュース NLP / レジーム判定）
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI に投げて ai_scores に書き込み
  - regime_detector.score_regime: ETF（1321）の MA200乖離 と マクロニュースセンチメント を合成して market_regime に書き込み

- research（リサーチ用ユーティリティ）
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）

- 設定管理（kabusys.config）
  - .env ファイルや OS 環境変数から設定値を自動読込（プロジェクトルート検出）
  - settings オブジェクト経由で各種パラメータ取得

---

## セットアップ手順

以下は開発用の一般的な手順です。実際のプロジェクト運用では依存バージョンの固定や Secrets 管理を適切に行ってください。

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. Python 仮想環境作成（例）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

3. 依存パッケージをインストール  
   パッケージ管理ファイル（requirements.txt / pyproject.toml）がある想定です。開発時の主要依存例:
   - duckdb
   - openai
   - defusedxml
   - requests（必要時）
   インストール例:
   ```
   pip install -e .
   # または
   pip install duckdb openai defusedxml
   ```

4. 環境変数 / .env を用意
   - プロジェクトルート（.git か pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと、自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可）。
   - 主な環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視等で使用する SQLite パス（デフォルト data/monitoring.db）
     - KABUSYS_ENV: 環境 ("development" | "paper_trading" | "live"), デフォルト "development"
     - LOG_LEVEL: ログレベル ("DEBUG"|"INFO"|...)（デフォルト "INFO"）
   - .env の書式は shell の export/KEY=val 形式、引用符・コメント等に対応しています。

5. データディレクトリを作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（基本例）

多くの機能は Python API として提供されます。以下は代表的な使用例です。

- DuckDB 接続と日次 ETL の実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  # target_date を指定しなければ今日が対象（内部で営業日に調整される）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- OpenAI を用いたニューススコアリング（銘柄別 ai_scores に書き込む）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY を環境変数に設定するか、api_key 引数で渡す
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"written: {written} codes")
  ```

- 市場レジーム判定の実行
  ```python
  from kabusys.ai.regime_detector import score_regime
  written = score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ DB の初期化（監査スキーマを作成）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- J-Quants トークン取得（直接呼び出す場合）
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # env の JQUANTS_REFRESH_TOKEN を利用
  ```

注意:
- OpenAI 呼び出しは gpt-4o-mini（設定ファイル内）を使用する設計です。API 呼び出し回数に注意してください（リトライ・フェイルセーフ実装あり）。
- ETL / API 呼び出しはネットワーク接続と有効な認証情報が必要です。
- 大量のデータを書き込む処理は DuckDB のスキーマを事前に作成しておく必要があります（ETL の前提となるテーブル定義を用意してください）。

---

## 主要モジュールの説明（簡易）

- kabusys.config
  - settings: 環境変数経由で各種設定を取得。自動 .env ロード機能あり。

- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token: リフレッシュトークンから id_token を取得

- kabusys.data.pipeline
  - run_daily_etl: カレンダー→株価→財務→品質チェック を順に実行

- kabusys.data.news_collector
  - fetch_rss: RSS フィードを安全に取得し正規化して返す

- kabusys.data.quality
  - run_all_checks: 欠損・重複・スパイク・日付不整合を検出

- kabusys.ai.news_nlp
  - score_news: ニュースを集約して OpenAI に渡し銘柄別スコアを ai_scores に保存

- kabusys.ai.regime_detector
  - score_regime: ETF MA200 乖離とマクロニュースを合成して market_regime に保存

- kabusys.research.*
  - ファクター計算・特徴量解析ユーティリティ

---

## 環境変数の主な一覧

- JQUANTS_REFRESH_TOKEN (必須 for J-Quants)
- KABU_API_PASSWORD (必須 for kabuステーション API)
- OPENAI_API_KEY (news_nlp / regime_detector 用)
- KABU_API_BASE_URL (kabu API ベース URL; デフォルト http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (デフォルト data/monitoring.db)
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG|INFO|...)

.env の自動ロードはプロジェクトルート（.git または pyproject.toml がある位置）を基準に行われます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成

（抜粋・代表例）

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
    - etl.py
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
    - schema / 他の補助モジュール（想定）
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research 等のサブモジュール群

実際のリポジトリはさらに細分化されたファイル群・テスト・ドキュメント等を含む想定です。

---

## 運用上の注意 / ベストプラクティス

- 機密情報（API トークン等）はソース管理しないこと。環境変数やシークレットマネージャを利用してください。
- OpenAI や J-Quants の呼び出しはレート制限や費用に注意してください。実稼働では呼び出し頻度を制御すること。
- ETL は冪等であることを前提としていますが、テーブルスキーマや権限を事前に確認してください。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使い、環境を明示的にセットしてください。
- DuckDB ファイルを共有する場合は排他制御、バックアップを設けてください。

---

## 開発・貢献

バグ報告や改善提案は Issue を通してお願いします。プルリクエストは小さく分け、ユニットテストを添えてください。

---

以上が本プロジェクトの README です。追加で CLI の使い方、テーブルスキーマ、例となる .env.example、あるいは具体的な ETL 実行のワークフローを README に追加したい場合は、要望を教えてください。