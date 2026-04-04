# KabuSys

日本株向け自動売買・データプラットフォーム（KabuSys）のREADMEです。  
このリポジトリはデータ収集・ETL、品質チェック、ファクター計算、ニュースNLP（LLM）、市場レジーム判定、監査ログ等を含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム／研究プラットフォームです。主な目的は以下です：

- J-Quants API からの株価・財務・カレンダー等の差分取得と DuckDB への保存（ETL）
- ニュース収集（RSS）と LLM によるニュースセンチメント評価（銘柄単位）
- 市場レジーム判定（ETF + マクロニュースの合成）
- ファクター（モメンタム／バリュー／ボラティリティ等）計算と特徴量探索（研究用途）
- データ品質チェック
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- kabuステーション等の実行・監視用モジュール群（execution / monitoring / strategy はパッケージ公開対象）

設計方針として、バックテストでのルックアヘッドバイアス回避、冪等性（DB挿入時の ON CONFLICT 等）、外部API呼び出しのリトライ/フェイルセーフを重視しています。

---

## 機能一覧

主要モジュールと機能（抜粋）：

- kabusys.config
  - .env または環境変数から設定を読み込み、アプリ設定を提供
  - 自動 .env ロード（プロジェクトルート検出）／無効化フラグあり

- kabusys.data
  - jquants_client: J-Quants API クライアント、ページネーション／レート制御／自動トークンリフレッシュ／保存関数
  - pipeline / etl: 日次 ETL パイプライン（calendar / prices / financials の差分取得 → 保存 → 品質チェック）
  - news_collector: RSS 収集（SSRF 対策、URL 正規化、トラッキング除去）
  - quality: 欠損・スパイク・重複・日付不整合の品質チェック（QualityIssue を返す）
  - calendar_management: JPX カレンダー管理・営業日計算（next/prev/get/is_trading_day等）
  - audit: 監査ログテーブルの初期化・監査DBユーティリティ
  - stats: z-score 正規化ユーティリティ

- kabusys.ai
  - news_nlp.score_news: 銘柄単位のニュースセンチメントを OpenAI（gpt-4o-mini）へ投げて ai_scores に書き込む
  - regime_detector.score_regime: ETF(1321) の ma200乖離 と マクロニュース（LLM）を合成して market_regime に書き込む

- kabusys.research
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクターを計算
  - feature_exploration: 将来リターン計算、IC、統計サマリー、ランク関数等

- パッケージ公開インターフェース
  - src/kabusys/__init__.py では data, strategy, execution, monitoring を公開対象にしています（strategy 等は別途実装やラッパーを想定）。

---

## 要件

- Python >= 3.10
- 必要なパッケージ（一例）:
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ以外の依存は最小化していますが、実行環境に応じて追加が必要になる場合があります。

requirements.txt（例）
```
duckdb>=0.10
openai>=1.0
defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   ```
   pip install -r requirements.txt
   # 開発用に editable install
   pip install -e .
   ```

4. 環境変数 / .env の準備

   プロジェクトルートに `.env` または `.env.local` を置くと自動でロードされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。必須の環境変数例:

   - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>    # 必須（ETL 用）
   - OPENAI_API_KEY=<your_openai_api_key>                  # 必須（news_nlp / regime_detector）
   - KABU_API_PASSWORD=<kabu_station_password>             # kabu API を使う場合
   - KABUSYS_ENV=development|paper_trading|live
   - LOG_LEVEL=INFO

   そのほか（任意）:
   - KABU_API_BASE_URL (デフォルト http://localhost:18080/kabusapi)
   - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
   - SQLITE_PATH (監視用)
   - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
   - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT

   サンプル .env（.env.example を用意してください）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxxx
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   LOG_LEVEL=DEBUG
   ```

5. DuckDB（監査DBなど）初期化例

   Python スクリプトや REPL から監査DBを初期化できます。
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # conn は duckdb.DuckDBPyConnection
   ```

---

## 使い方（主要ユースケースの例）

以下は代表的な関数呼び出し例です。各関数は Look-ahead バイアス回避のため target_date を明示的に渡す設計になっています。

- 日次 ETL 実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（ai_scores への書き込み）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"scored {count} codes")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- ファクター計算（モメンタム / ボラティリティ / バリュー）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  ```

- データ品質チェック
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.quality import run_all_checks

  conn = duckdb.connect("data/kabusys.duckdb")
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for issue in issues:
      print(issue)
  ```

- RSS 収集（news_collector.fetch_rss は低レベルユーティリティ）
  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  ```

注意点:
- OpenAI を使う処理は API 呼び出しを行うため、APIキーと利用上のコスト管理に注意してください。
- DuckDB に対する executemany や ON CONFLICT の挙動はバージョン差異に留意してください（コード内で互換性確保の工夫あり）。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を基準）を検出して行います。CI やテストで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成

主要なファイル／ディレクトリ構成（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py  — 環境設定／.env ロード
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースNLP（銘柄別スコアリング）
    - regime_detector.py  — 市場レジーム判定（ETF + マクロ）
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（fetch/save）
    - pipeline.py         — ETL パイプライン（run_daily_etl 等）
    - etl.py              — ETLResult 再エクスポート
    - news_collector.py   — RSS 収集（SSRF対策、正規化）
    - calendar_management.py — 市場カレンダー管理（営業日判定等）
    - quality.py          — データ品質チェック
    - stats.py            — 統計ユーティリティ（zscore_normalize 等）
    - audit.py            — 監査ログスキーマ初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py  — ファクター計算（momentum/volatility/value）
    - feature_exploration.py — 将来リターン、IC、統計サマリー等
  - research/*, ai/* の公開 API はパッケージ __all__ を通して提供

（パッケージ外に strategy / execution / monitoring 用の実装が別途ある想定。__init__ で公開対象に含めています。）

---

## 運用上のメモ

- KABUSYS_ENV 値: "development" / "paper_trading" / "live"（設定ミスは ValueError）
- ログレベルは LOG_LEVEL 環境変数で制御（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- 自動化ジョブ（Cron / Airflow 等）で ETL を運用する場合:
  - run_daily_etl の target_date を固定して過去日の再処理を再現可能にする
  - id_token のキャッシュ/リフレッシュは jquants_client が管理
- LLM 呼び出しはリトライ・フォールバックを内包しており、API障害時には 0.0 で継続する設計（フェイルセーフ）。ただし精度・コスト・レイテンシの管理は利用者側で考慮してください。

---

## 貢献 / 開発

- コーディング規約やユニットテストは各自の開発フローに合わせて導入してください。
- テスト時に .env の自動ロードを無効化したい場合：
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- OpenAI 呼び出しやネットワーク関連は unittest.mock.patch で差し替え可能な設計になっています（内部呼び出し関数が分離されています）。

---

不明点や README に追加したい実行例・環境情報（Dockerfile、CI設定、詳しいスキーマ定義など）があれば教えてください。必要に応じて README を拡張します。