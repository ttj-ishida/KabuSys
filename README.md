# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
ETL（J-Quants）、データ品質チェック、ニュース収集・NLP（OpenAI）、リサーチ用ファクター計算、監査ログ（約定トレーサビリティ）などを含みます。

- パッケージ名: kabusys
- バージョン: 0.1.0（src/kabusys/__init__.py）

---

## プロジェクト概要

KabuSys は日本株を対象にしたデータ取得・前処理、品質チェック、特徴量計算、ニュースセンチメント解析、さらに監査ログや発注のトレーサビリティを意識したユーティリティを提供するライブラリ群です。  
設計方針として「ルックアヘッドバイアス回避」「冪等性」「フェイルセーフ」「外部API呼び出しの堅牢化（リトライ・レート制御）」を重視しています。

主な利用場面:
- 日次 ETL パイプライン（J-Quants からの差分取得・保存）
- ニュースの収集と LLM による銘柄センチメントスコア算出
- 市場レジーム判定（ETF + マクロニュースの組合せ）
- 研究用途のファクター計算・IC 解析
- 監査ログ（signal → order_request → executions のトレース）
- データ品質チェック（欠損・重複・スパイク・日付不整合）

---

## 機能一覧

- config
  - .env / 環境変数読み込み、自動ロード（プロジェクトルート判定）
  - 必須設定のラッパー（settings）
- data
  - jquants_client: J-Quants API クライアント（認証・レート制御・保存関数）
  - pipeline: 日次 ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - calendar_management: JPX カレンダー管理と営業日判定
  - news_collector: RSS 取得・前処理・raw_news への保存ユーティリティ（SSRF 対策等）
  - quality: データ品質チェック（欠損・重複・スパイク・日付整合性）
  - audit: 監査ログスキーマ初期化・監査 DB 操作（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等の統計ユーティリティ
- ai
  - news_nlp: ニュース記事を LLM でまとめて銘柄ごとにスコア化（score_news）
  - regime_detector: ETF 200 日 MA とマクロニュース LLM を組み合わせて市場レジーム判定（score_regime）
- research
  - factor_research: モメンタム・バリュー・ボラティリティ等のファクター計算（calc_momentum, calc_value, calc_volatility）
  - feature_exploration: 将来リターン計算・IC 計算・統計サマリー等

---

## 必要な環境 / 依存

- Python 3.10+
- 必要パッケージ（最低限）:
  - duckdb
  - openai
  - defusedxml
  - （その他標準ライブラリのみで動くように設計されていますが、実行環境に応じて追加が必要な場合があります）

インストール例（仮の requirements がないため個別インストール）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install "duckdb" "openai" "defusedxml"
# 開発中に editable install をする場合:
pip install -e .
```

---

## 環境変数（主なもの）

config.Settings からアクセスされます。README で触れている主なキー:

- JQUANTS_REFRESH_TOKEN (必須)
- OPENAI_API_KEY (LLM 呼び出しに必要)
- KABU_API_PASSWORD (kabuステーション API 用、必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PID_FILE_PATH (デフォルト: data/execution.pid)
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT (監視閾値)
- KABUSYS_ENV (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)

自動的にプロジェクトルートの .env と .env.local を読み込みます（OS 環境変数が優先）。自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

.env のパースはシェルライク（export KEY=val やクォート・コメント処理）に対応しています。

---

## セットアップ手順（例）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. Python 仮想環境を作成して依存をインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .
   pip install duckdb openai defusedxml
   ```

3. 環境変数を設定（.env をプロジェクトルートに置く例）
   - .env.example を参考に .env を作成（プロジェクトに example がない場合は上のキー一覧を参照）
   - 必須: JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID

4. DuckDB データベース等のディレクトリを作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

---

## 使い方（主な API と実行例）

以下は簡単な利用例です。すべて Python スクリプトや REPL 内で実行できます。

- DuckDB 接続を作成する
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL を実行する（J-Quants から差分取得 → 保存 → 品質チェック）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを算出して ai_scores に保存
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written {written} codes")
  ```

- 市場レジーム（ETF 1321 MA + マクロニュース）を算出
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB を初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # init_audit_schema(conn_audit) は内部で呼ばれます
  ```

- 研究用ファクター計算例
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  conn = duckdb.connect("data/kabusys.duckdb")
  date0 = date(2026, 3, 20)
  mom = calc_momentum(conn, date0)
  val = calc_value(conn, date0)
  vol = calc_volatility(conn, date0)
  ```

注意:
- LLM 呼び出し（score_news, score_regime）は OPENAI_API_KEY を環境変数で渡すか api_key 引数で渡してください。
- J-Quants 呼び出しは JQUANTS_REFRESH_TOKEN を必要とします（get_id_token を内部で使用）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュール一覧（抜粋）です:

- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py              -- ニュース NLP（score_news）
  - regime_detector.py      -- 市場レジーム判定（score_regime）
- src/kabusys/data/
  - __init__.py
  - jquants_client.py       -- J-Quants API クライアント（fetch_*/save_*）
  - pipeline.py             -- ETL パイプライン（run_daily_etl 等）
  - calendar_management.py  -- 市場カレンダー操作（is_trading_day 等）
  - news_collector.py       -- RSS 収集・前処理・保存
  - quality.py              -- データ品質チェック
  - stats.py                -- zscore_normalize 等
  - audit.py                -- 監査ログスキーマ初期化
  - etl.py                  -- ETLResult の re-export
- src/kabusys/research/
  - __init__.py
  - factor_research.py      -- ファクター計算（momentum/value/volatility）
  - feature_exploration.py  -- 将来リターン・IC・統計サマリー

（各モジュールは docstring に詳細な設計・処理フロー・フォールバック仕様が記載されています）

---

## 動作上の注意事項 / 設計上のポイント

- ルックアヘッドバイアスへの配慮:
  - 多くの関数は内部で date.today() や datetime.now() を直接参照しないよう設計されています。テスト・バックテスト用途では外部から target_date を注入してください。
- 冪等性:
  - J-Quants の保存関数は ON CONFLICT DO UPDATE を用いて冪等に保存します。
  - NewsCollector は記事 ID を正規化 URL のハッシュで生成し冪等挿入を目指しています。
- OpenAI 呼び出し:
  - gpt-4o-mini を想定した JSON Mode を用いる想定です。レスポンスやエラーに対するリトライ・フォールバックロジックがあります。
- セキュリティ・堅牢性:
  - RSS 取得では SSRF 対策（リダイレクト検査、プライベート IP 拒否）と受信サイズ制限を実装しています。
  - J-Quants API 呼び出しはレート制限・401 の自動リフレッシュ・指数バックオフを実装しています。

---

## さらに詳しく / 開発者向け

- 各モジュールの docstring に機能の処理フロー・設計方針・引数/戻り値/例外仕様が書かれています。まずはそちらを参照してください。
- テストやモックを行う際は、OpenAI / HTTP 呼び出し箇所（news_nlp._call_openai_api, regime_detector._call_openai_api, news_collector._urlopen など）を patch することを推奨します。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。CI やテストで自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

フィードバックや質問があればお知らせください。README の追加項目（例: CI 設定、デプロイ手順、詳細な .env.example）も必要であれば作成します。