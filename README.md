# KabuSys

日本株向けの自動売買 / データパイプライン基盤ライブラリです。  
データ収集（J-Quants）、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、ETL・品質チェック、監査ログ等の機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株のアルゴリズム取引やリサーチ用途を想定した内部ライブラリ群です。主な目的は以下です。

- J-Quants API を用いた株価・財務・カレンダー等の差分ETL
- RSS ニュース収集と OpenAI を使った銘柄別センチメントの自動スコアリング
- マーケットレジーム判定（ETF とマクロニュースの組合せ）
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と統計ユーティリティ
- データ品質チェックと監査ログ（発注→約定のトレーサビリティ）
- DuckDB を中心としたローカルデータ管理

設計方針として「ルックアヘッドバイアスを防ぐ」「冪等性」「フォールトトレランス（API障害に対するフェイルセーフ）」を重視しています。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save 関数、トークン自動更新、レート制御）
  - NewsCollector（RSS 取得、前処理、SSRF対策、raw_news 保存）
  - calendar_management（営業日判定 / next/prev_trading_day / calendar_update_job）
  - quality（欠損、重複、スパイク、将来日付などの品質チェック）
  - audit（監査ログテーブルの初期化 / init_audit_db）
  - stats（zscore_normalize 等の統計ユーティリティ）
- ai
  - news_nlp.score_news（記事を銘柄別に集約し OpenAI でセンチメントを算出し ai_scores に書き込む）
  - regime_detector.score_regime（ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成し market_regime を更新）
- research
  - factor_research（calc_momentum / calc_value / calc_volatility）
  - feature_exploration（calc_forward_returns / calc_ic / factor_summary / rank）

---

## 要件

- Python 3.10+
- 依存ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリほか）

requirements.txt はこのリポジトリに含めていない場合があります。上記ライブラリをプロジェクトに合わせてインストールしてください。

---

## 環境変数（主なもの）

KabuSys は .env / .env.local を自動読み込みします（プロジェクトルートは .git または pyproject.toml を基準に探索）。自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須 / 使用される主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン（ETL 等で使用）
- OPENAI_API_KEY (API 呼び出し時に使用。関数呼び出し時に引数で上書き可能)
- KABU_API_PASSWORD（kabuステーション関連）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（通知用）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（モニタリング用デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH（監視用）
- KILL_FLAG_CLEAR_ON_START（"1"で起動時に kill flag をクリア）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT（監視閾値）
- KABUSYS_ENV（development / paper_trading / live、デフォルト development）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）

設定はソース内の `kabusys.config.settings` から取得可能です。

---

## セットアップ手順（例）

1. リポジトリをクローン

   git clone <repo_url>
   cd <repo>

2. 仮想環境を作成・有効化（任意）

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール（例）

   pip install duckdb openai defusedxml

   補足: 実運用では requirements.txt を整備し `pip install -r requirements.txt` を推奨します。

4. 環境変数を作成

   プロジェクトルートに `.env`（または `.env.local`）を作成し、必要なキーを設定します。例:

   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   LOG_LEVEL=INFO
   KABUSYS_ENV=development
   ```

   ※ .env.local は .env を上書きする形で優先読み込みされます。OS 環境変数はさらに優先されます。

5. データベース用ディレクトリ作成（デフォルトのパスを使う場合）

   mkdir -p data

---

## 使い方（主な例）

以下はライブラリ内の関数を直接呼んで利用する例です。詳細は各モジュールの docstring を参照してください。

- DuckDB 接続を作成して日次 ETL を実行する

  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（OpenAI）で銘柄スコアを算出して書き込む

  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY を環境変数で設定するか、第3引数で api_key を渡す
  written = score_news(conn, target_date=date(2026, 3, 20))
  print("written:", written)
  ```

- 市場レジーム（regime）を算出して保存する

  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査 DB の初期化（監査専用 DB を作る）

  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn を使って監査テーブルにアクセスできます
  ```

- ファクター計算や研究機能の呼び出し

  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  t = date(2026, 3, 20)
  mom = calc_momentum(conn, t)
  val = calc_value(conn, t)
  vol = calc_volatility(conn, t)
  fwd = calc_forward_returns(conn, t, horizons=[1,5,21])
  ```

- カレンダー更新バッチジョブ

  ```python
  from kabusys.data.calendar_management import calendar_update_job
  conn = duckdb.connect("data/kabusys.duckdb")
  calendar_update_job(conn)
  ```

注意:
- OpenAI 呼び出しは API キーが必要です。関数に `api_key` を渡すか環境変数 `OPENAI_API_KEY` を設定してください。
- DuckDB スキーマ（raw_prices, raw_financials, raw_news, ai_scores, market_regime, market_calendar など）が必要です。スキーマ初期化はプロジェクト全体の初期化スクリプト等で行ってください（この README はスキーマ生成の具体的 SQL を含みませんが、各モジュールの save_* / init_audit_schema 等が想定するスキーマに従ってください）。

---

## 自動環境変数読み込みの挙動

- パッケージはパッケージファイルの位置からプロジェクトルートを探索し、`.env` → `.env.local` を順に読み込みます（OS 環境変数が優先されます）。
- 読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利です）。

---

## ディレクトリ構成（要約）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数管理（Settings）
  - ai/
    - __init__.py
    - news_nlp.py           — ニュースの OpenAI ベースセンチメント評価、ai_scores 書き込み
    - regime_detector.py    — ETF + マクロニュースを組み合わせた市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（fetch / save / get_id_token 等）
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - etl.py                — ETLResult の公開
    - calendar_management.py— 市場カレンダー管理・営業日判定・calendar_update_job
    - news_collector.py     — RSS 取得・前処理・保存
    - quality.py            — データ品質チェック
    - stats.py              — zscore_normalize 等の統計ユーティリティ
    - audit.py              — 監査ログテーブル初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py    — モメンタム / バリュー / ボラティリティの計算
    - feature_exploration.py— 将来リターン / IC / 統計サマリー等
  - (その他: strategy / execution / monitoring パッケージを __all__ に含める設計あり)

各モジュールは docstring に詳細な設計・実装方針、入力/出力、フェイルセーフ挙動が記載されています。実装を拡張・利用する際はまず該当モジュールの docstring を参照してください。

---

## 運用上の注意

- OpenAI / J-Quants の API 利用にはそれぞれの利用規約に従ってください。API レート制限や課金に注意してください。
- DuckDB はファイルベースのデータベースです。並行書き込みやトランザクションの扱いに注意してください。
- ニュース収集では RSS のサイズ/外部アクセスに関するセキュリティ対策（SSRF ブロック、受信サイズ制限等）を実装していますが、実運用では追加の監視・ログ・制限を検討してください。
- 本ライブラリは設計方針として「外部への実際の注文発行を直接行わない」モジュールと「発注・監査を扱うモジュール」を分離することを意図しています。実際にブローカーと接続して発注する場合は安全・冪等制御・リスク管理を厳格に実装してください。

---

## サポート / 貢献

バグ修正や機能追加はプルリクエストを歓迎します。貢献前に issue を立てて実装方針を相談していただけるとスムーズです。

---

README はここまでです。さらに具体的な使い方（例: スキーマ初期化 SQL、デプロイ手順、CI 設定など）が必要であれば教えてください。