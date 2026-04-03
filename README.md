# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースの NLP スコアリング、研究用ファクター計算、監査ログ（発注フロー追跡）、市場レジーム判定などを提供します。

主な設計方針は「ルックアヘッドバイアスを避ける」「DuckDB ベースの冪等な ETL」「外部 API に対する堅牢なリトライとレート制御」「監査可能なトレーサビリティ」です。

---

## 主な機能

- データ取得 / ETL
  - J-Quants API から株価（日足）、財務（四半期）／上場銘柄情報／JPX カレンダーを差分取得して DuckDB に保存（冪等保存）。
  - 日次 ETL パイプライン（run_daily_etl）：カレンダー→株価→財務→品質チェックの順で実行。
- データ品質チェック
  - 欠損（OHLC）、スパイク（前日比）、重複、日付整合性（未来日付・非営業日データ）を検出し QualityIssue を返す。
- ニュース収集 / 前処理
  - RSS フィードから記事を収集、URL 正規化、トラッキングパラメータ除去、SSRF 対策、raw_news への冪等登録。
- ニュース NLP（OpenAI）
  - ニュース記事を銘柄ごとに集約して LLM（gpt-4o-mini）でセンチメントスコアを算出し ai_scores に保存（score_news）。
- 市場レジーム判定（Regime Detector）
  - ETF 1321 の 200 日 MA 乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成し日次で 'bull' / 'neutral' / 'bear' を判定（score_regime）。
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算、将来リターン、IC 計算、Z スコア正規化など。
- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定までの監査テーブルを DuckDB に初期化・管理（init_audit_schema / init_audit_db）。
- 設定管理
  - .env / 環境変数から設定を読み込み（自動読み込みあり）。必須トークンの取得や環境／ログレベルの検証を行う。

---

## 必要な環境 / 依存

（プロジェクトに明示されたライブラリより抜粋）

- Python 3.10+
- duckdb
- openai
- defusedxml

その他は標準ライブラリで実装されています。実際のプロジェクトでは requirements.txt または pyproject.toml を用意してください。

---

## セットアップ手順（開発用）

1. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. インストール（ローカルパッケージとして）
   ```
   pip install -e .            # パッケージ化されている場合
   # または最低限の依存を入れる
   pip install duckdb openai defusedxml
   ```

3. 環境変数 / .env の準備  
   プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただしテスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。主な環境変数:

   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD (必須) — kabuステーション API パスワード
   - OPENAI_API_KEY (推奨) — OpenAI API キー（score_news / score_regime に未指定時に参照）
   - KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（任意）
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
   - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視・プロセス管理関連
   - KABUSYS_ENV — 環境 ("development", "paper_trading", "live")
   - LOG_LEVEL — ログレベル ("DEBUG","INFO",...)

   .env の自動読み込みはパッケージ内 `kabusys.config` がプロジェクトルート（.git または pyproject.toml）を探索して行います。

---

## 使い方（代表的な例）

以下はライブラリの主要機能を呼ぶサンプルです。実行前に必要な環境変数（JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY など）を設定してください。

- DuckDB 接続作成と日次 ETL 実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（OpenAI キーは環境変数 OPENAI_API_KEY に設定するか api_key を渡す）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書込み銘柄数: {written}")
  ```

- 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DB 初期化（専用 DB）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- 設定の参照（例: paths / tokens）
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.jquants_refresh_token)  # 設定されていなければ例外
  ```

注意:
- OpenAI 呼び出しは外部 API を利用するため課金が発生します。テスト時は API 呼び出し部分をモックすることを推奨します。コード中でも unittest.mock.patch で差し替えられる設計になっています（例: kabusys.ai.news_nlp._call_openai_api）。
- ETL やニュース収集は大量 API 呼び出しやネットワーク I/O を伴うため、運用時はレートやエラーハンドリングに注意してください。

---

## 実装上のポイント / 注意点

- ルックアヘッドバイアス回避:
  - 日付判定やデータ取得は target_date を明示的に受け取り、datetime.today() や date.today() を内部で直接参照しない関数設計が意識されています（テスト／バックテスト向け）。
- 冪等性:
  - DuckDB への保存は ON CONFLICT（更新）を用いて冪等に行います。
- API 呼び出し:
  - J-Quants クライアントはレートリミット（120 req/min）を守る RateLimiter、指数バックオフ、401 でのトークン自動リフレッシュを実装しています。
- ニュース収集:
  - URL 正規化、トラッキングパラメータ除去、SSRF 対策（リダイレクト検査、プライベートアドレス検出）、受信サイズ制限などセキュリティ対策あり。
- ロギング / 設定検証:
  - settings で KABUSYS_ENV / LOG_LEVEL の値チェックを行います。

---

## 主要なモジュール構成（ディレクトリ構成）

以下はパッケージ内の主要ファイル／モジュール一覧（src/kabusys 配下）です。実際のリポジトリでは他にもファイルがある可能性があります。

- kabusys/
  - __init__.py
  - config.py                      — 環境変数 / .env 読み込みと Settings
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースセンチメント（score_news）
    - regime_detector.py            — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント + 保存関数
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETL インターフェース（ETLResult re-export）
    - calendar_management.py        — 市場カレンダー管理・営業日ヘルパー
    - news_collector.py             — RSS ニュース収集
    - stats.py                      — zscore_normalize 等の統計ユーティリティ
    - quality.py                    — データ品質チェック
    - audit.py                      — 監査ログスキーマの初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py            — momentum/value/volatility の計算
    - feature_exploration.py        — forward returns, IC, factor summary, rank
  - monitoring/ (本サンプル内では参照のみ)
  - execution/ (本サンプル内では参照のみ)
  - strategy/ (本サンプル内では参照のみ)

---

## テスト / 開発時のヒント

- 環境変数の自動ロードを抑止したいテストでは:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- OpenAI や J-Quants の API 呼び出しはネットワークに依存するためユニットテストではそれらの呼び出しをモックしてください（モジュール内で差し替え可能な関数が用意されています）。
- DuckDB をインメモリで使うとテストが速くなります:
  ```
  conn = duckdb.connect(":memory:")
  ```

---

この README はコードベースの主要機能・使い方の概観をまとめたものです。実運用や拡張にあたっては、各モジュールの docstring とログ出力、設定値の確認を参照してください。必要であればサンプル設定ファイル（.env.example）や CLI ラッパー、ユニットテストのサンプルを追加できます。