# KabuSys — 日本株自動売買 / データ基盤ライブラリ

KabuSys は日本株のデータ収集・品質管理・特徴量計算・ニュース NLP・市場レジーム判定・監査ログ管理を行うためのライブラリ群です。ETL パイプライン、J-Quants クライアント、ニュース収集・NLP（OpenAI を利用）、リサーチ用ユーティリティ、監査テーブル初期化などを提供します。

---

## 主要機能

- データ取得 / ETL
  - J-Quants API から株価日足、財務データ、マーケットカレンダーの差分取得（ページネーション・レート制御・リトライ対応）
  - ETL パイプライン（run_daily_etl）でカレンダー → 株価 → 財務 → 品質チェックを一括実行

- データ品質管理
  - 欠損チェック、スパイク（異常値）検出、重複チェック、日付整合性チェック（market_calendar と照合）

- ニュース収集 & NLP
  - RSS から記事取得（SSRF 対策・トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント（score_news）
  - マクロニュースと ETF (1321) の MA200 乖離を合成した市場レジーム判定（score_regime）

- リサーチ / ファクター計算
  - モメンタム / ボラティリティ / バリュー等のファクター計算（duckdb を用いた SQL+Python 実装）
  - 将来リターン計算、IC（情報係数）計算、ファクターの統計サマリー、Z スコア正規化

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブルの DDL と初期化関数（init_audit_schema / init_audit_db）
  - 発注フローの冪等性とトレースを考慮した設計

---

## セットアップ手順

必要な Python バージョンはプロジェクトに依存しますが、3.10+ を推奨します。

1. 仮想環境作成（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 依存パッケージのインストール（例）
   - 本リポジトリに requirements.txt がない場合は最低限以下をインストールしてください:
     ```bash
     pip install duckdb openai defusedxml
     ```
   - パッケージとして使う場合:
     ```bash
     pip install -e .
     ```

3. 環境変数 / .env
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（優先順位: OS 環境変数 > .env.local > .env）。
   - 自動ロードを無効化する場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必要な主な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用（必須／機能を使う場合）
     - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 利用時）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/...
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）

4. データベース準備（例）
   - DuckDB ファイルを作成せずにコードから接続できます。監査 DB を初期化する例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```

---

## 使い方（代表的な関数・例）

以下は典型的な利用例です。各関数は duckdb.DuckDBPyConnection を受け取ります（例: duckdb.connect("path")）。

- DuckDB 接続作成:
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL 実行:
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコア付与（指定日分）:
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} codes")
  ```

- 市場レジーム判定:
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- ファクター計算例:
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  momentum = calc_momentum(conn, date(2026, 3, 20))
  value = calc_value(conn, date(2026, 3, 20))
  volatility = calc_volatility(conn, date(2026, 3, 20))
  ```

- 監査ログスキーマ初期化（既存接続に対して）:
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

注意点:
- OpenAI 呼び出しは API キーが必要です。テスト時は各モジュール内の _call_openai_api をモックしてください（docstring に記載の通り）。
- ETL / API 呼び出しはネットワーク依存・レート制御・リトライロジックを含みます。
- run_daily_etl は内部でカレンダーを取得し、取得後に target_date を営業日に調整します。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector の呼び出しで使用）
- SLACK_BOT_TOKEN — Slack Bot トークン（通知を行う場合）
- SLACK_CHANNEL_ID — Slack チャンネル ID（通知を行う場合）
- KABUSYS_ENV — 開発環境（development / paper_trading / live）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（値が設定されていると無効）

.env の書き方例:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
```

---

## テスト・モックに関するヒント

- OpenAI 呼び出しはモジュール内部の _call_openai_api を patch することで差し替えてテストできます（news_nlp、regime_detector 各モジュールに同名の内部関数があるため個別にモックしてください）。
- network 関連（J-Quants、RSS）は外部依存なので unittest.mock などで urllib / jquants_client._request をモックすると高速テストが可能です。
- 自動 .env 読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください（テストで環境隔離する際に便利です）。

---

## ディレクトリ構成（抜粋）

```
src/kabusys/
├── __init__.py
├── config.py                    # 環境変数管理・自動 .env ロード
├── ai/
│   ├── __init__.py
│   ├── news_nlp.py              # ニュースセンチメント（score_news）
│   └── regime_detector.py       # 市場レジーム判定（score_regime）
├── data/
│   ├── __init__.py
│   ├── jquants_client.py        # J-Quants API クライアント + DuckDB 保存
│   ├── pipeline.py              # ETL パイプライン run_daily_etl 等
│   ├── etl.py                   # ETLResult 再エクスポート
│   ├── quality.py               # データ品質チェック
│   ├── news_collector.py        # RSS 取得・正規化・保存補助
│   ├── calendar_management.py   # 市場カレンダー管理（営業日判定等）
│   ├── stats.py                 # 統計ユーティリティ（zscore_normalize）
│   └── audit.py                 # 監査ログ定義・初期化
├── research/
│   ├── __init__.py
│   ├── factor_research.py       # モメンタム/バリュー/ボラティリティ
│   └── feature_exploration.py   # 将来リターン/IC/統計サマリー
└── research/… (その他ユーティリティ)
```

各ファイルは docstring に設計方針・処理フロー・フェイルセーフ動作が詳述されています。実運用では各モジュールのロギングを有効にして監査ログ・ETLResult を監視してください。

---

もし README に追加したい運用例（cron / Airflow / systemd のジョブ定義、Slack 通知統合例、CI テスト手順など）があれば、用途に合わせて追記します。