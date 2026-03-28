# KabuSys

日本株向けの自動売買・データプラットフォームライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP、ファクター計算、研究ユーティリティ、監査ログ（発注・約定トレーサビリティ）、および取引レジーム判定などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム構築に必要なデータプラットフォームと分析コンポーネントを集約した Python パッケージです。主な目的は以下：

- J-Quants API からの差分 ETL（株価・財務・マーケットカレンダー）
- RSS からのニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント解析（銘柄別 ai_scores / マクロセンチメント）
- 市場レジーム判定（ETF + マクロニュースを合成）
- ファクター（モメンタム / バリュー / ボラティリティ等）計算と特徴量探索
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → executions）のための DuckDB スキーマ初期化

設計上、バックテストやフェアな評価のために Look-ahead bias を避ける実装思想（日時参照の制約、DB クエリの排他条件など）が組み込まれています。

---

## 主な機能一覧

- 環境設定読み込み（.env / .env.local 自動ロード、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
- J-Quants API クライアント（レートリミット・リトライ・トークン自動リフレッシュ）
- ETL パイプライン（run_daily_etl / 個別 run_prices_etl, run_financials_etl, run_calendar_etl）
- ニュース収集（RSS の正規化、前処理、raw_news への冪等保存）
- ニュース NLP（銘柄別センチメント: score_news）
- マクロセンチメント + ETF MA200 を用いた市場レジーム判定（score_regime）
- ファクター計算（calc_momentum, calc_value, calc_volatility）
- 研究ユーティリティ（forward returns, IC（Spearman）計算, factor_summary, zscore_normalize）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログスキーマ作成・初期化（init_audit_schema / init_audit_db）
- 各種ユーティリティ（統計、ニュースウィンドウ計算、カレンダー判定等）

---

## 必要条件 (概略)

- Python 3.10+
- 主要依存ライブラリ（抜粋）:
  - duckdb
  - openai
  - defusedxml
  - ※ネットワーク/SSL/標準ライブラリを使うため追加パッケージが必要な環境もあります

実際のインストール用の requirements.txt は本リポジトリに含まれている想定です。開発時は仮想環境を推奨します。

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# またはプロジェクトの requirements.txt を使う
# pip install -r requirements.txt
```

---

## 環境変数（重要）

以下の環境変数が多くの機能で必須です（例: .env に設定しておく）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- DUCKDB_PATH: デフォルトの DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視等に使う SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL: ログレベル ("DEBUG" | "INFO" | ...)

自動 .env ロード:
- パッケージはプロジェクトルート（.git または pyproject.toml を基準）にある `.env` / `.env.local` を自動で読み込みます。
- 自動ロードを無効にする場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

.env 例（.env.example を参考に作成してください）:
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C1234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易）

1. リポジトリをクローンして仮想環境を作成
   ```bash
   git clone <repo>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .
   # または必要パッケージを個別インストール
   pip install duckdb openai defusedxml
   ```

2. 環境変数を設定（.env を作成）
   - .env/.env.local に前節の必要なキーを設定

3. DuckDB データベース初期化（必要に応じて監査 DB を作成）
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # またはメモリ:
   conn = init_audit_db(":memory:")
   ```

4. ETL を初回実行（例）
   ```python
   import duckdb
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl

   conn = duckdb.connect("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

---

## 使い方（主要 API の例）

- DuckDB 接続の準備:
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL を実行:
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  ```

- ニュースセンチメント（銘柄別）をスコアリング:
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  n = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"scored {n} symbols")
  ```

- 市場レジーム判定:
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- ファクター計算（例: モメンタム）:
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum
  recs = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

- 監査スキーマ初期化（既存 DB に追加する場合）:
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

- データ品質チェック:
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026, 3, 20))
  ```

---

## 注意点 / 設計上の要点

- Look-ahead bias を避けるため、date 引数で対象日を明示して処理を行う実装がされています（内部で date.today() を不用意に参照しない）。
- OpenAI API を使う箇所は API キーを明示的に渡せます（関数引数 or 環境変数 OPENAI_API_KEY）。
- J-Quants API とのやり取りはレート制限・リトライ・トークン自動更新を組み込んでいます。
- ニュース収集は SSRF 対策や受信サイズ上限、XML の安全パース（defusedxml）を施しています。
- DuckDB による ETL/保存は冪等性（ON CONFLICT DO UPDATE / DO NOTHING）を考慮しています。
- テストのために一部内部関数（OpenAI 呼び出し等）をモックしやすい設計になっています（関数を差し替えて検証可能）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋: src/kabusys 以下）
- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理（.env 自動ロード等）
  - ai/
    - __init__.py
    - news_nlp.py                — ニュースセンチメント（銘柄別）
    - regime_detector.py         — 市場レジーム判定（ETF + マクロ）
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント & DuckDB 保存
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - etl.py                     — ETLResult の再エクスポート
    - news_collector.py          — RSS 収集・前処理
    - calendar_management.py     — 市場カレンダー管理・営業日ロジック
    - stats.py                   — 統計ユーティリティ（zscore_normalize 等）
    - quality.py                 — データ品質チェック
    - audit.py                   — 監査ログテーブル定義 & 初期化
  - research/
    - __init__.py
    - factor_research.py         — Momentum / Value / Volatility 等
    - feature_exploration.py     — forward returns, IC, summary, rank
  - research/（他モジュールは index 経由で公開）
- その他: .env.example（想定）、pyproject.toml 等（プロジェクトルート）

---

## 開発・テストのヒント

- 自動 .env ロードを無効化してユニットテストを実行する場合:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- OpenAI / ネットワーク呼び出しを含む箇所はモック化が想定されています（関数単位で差し替え可能）。
- DuckDB はファイルベースの軽量 DB で容易に CI に組み込めます。":memory:" を使えばインメモリでのテストが可能です。

---

## ライセンス・貢献

（ここにプロジェクトのライセンス、貢献方法、issues/PR の案内を書いてください。）

---

README は本コードベースの主要点をまとめたものです。各モジュールの詳しい仕様（引数、戻り値、例外動作など）はソース内の docstring を参照してください。必要であれば README に具体的な使用例や運用手順（デプロイ、スケジューリング、運用監視、Slack 通知フローなど）を追記できます。