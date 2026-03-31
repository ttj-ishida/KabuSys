# KabuSys

日本株向けのデータプラットフォーム & 自動売買補助ライブラリです。  
J-Quants からのデータ取得、DuckDB を用いた ETL、ニュースの NLP スコアリング、LLM による市場レジーム判定、リサーチ用ファクター計算、監査ログ用スキーマ等を提供します。

主な設計方針：
- ルックアヘッドバイアス回避（内部で date.today()/datetime.today() を直接参照しない設計）
- 冪等性を重視した DB 保存（ON CONFLICT / idempotent）
- 外部 API 呼び出しにはリトライ・バックオフやレートリミットを適用
- テスト容易性を考慮した依存注入箇所（例: API 呼び出しの差し替えが容易）

---

## 機能一覧

- 環境設定管理
  - .env/.env.local からの自動読み込み（プロジェクトルート検出）
  - 必須環境変数の取得ユーティリティ
- データ ETL（J-Quants）
  - 日次株価（OHLCV）・財務データ・市場カレンダーの差分取得・保存
  - 差分取得、バックフィル、品質チェックを含む日次パイプライン（run_daily_etl）
  - レートリミット、認証トークン自動リフレッシュ、リトライ処理
- ニュース収集 / 前処理
  - RSS 収集、URL 正規化、SSRF 対策、記事テキスト前処理、raw_news 保存用ユーティリティ
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュース統合センチメント（score_news）
  - LLM 呼び出しのリトライ / JSON バリデーション / スコアクリッピング
- レジーム判定（AI + 市況）
  - ETF (1321) の MA200 乖離とマクロニュースセンチメントを合成して日次レジーム判定（score_regime）
- リサーチ（ファクター計算・特徴量探索）
  - Momentum / Volatility / Value ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、統計サマリ（factor_summary）
  - z-score 正規化ユーティリティ
- データ品質チェック
  - 欠損、重複、将来日、スパイク等の検出（run_all_checks）
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査スキーマ定義・初期化（init_audit_schema / init_audit_db）

---

## 必要条件

- Python 3.10 以上（typing の | 演算子や __future__ annotations を使用）
- 必要なパッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API, RSS ソース, OpenAI）

実際のプロジェクトでは requirements.txt を用意して pip でインストールしてください。

---

## セットアップ手順（例）

1. 仮想環境作成・有効化
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS/Linux: source .venv/bin/activate

2. 必要パッケージのインストール（例）
   - pip install duckdb openai defusedxml

   （プロジェクト内で requirements.txt がある場合は pip install -r requirements.txt）

3. 環境変数 / .env を用意
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます。
   - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

4. DuckDB / SQLite 用ディレクトリを作成（必要に応じて）
   - デフォルトではデータは data/ 以下に保存されます（設定は環境変数で上書き可能）。

---

## 環境変数（主なもの）

必須：
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL）
- SLACK_BOT_TOKEN — Slack 通知に使用する場合
- SLACK_CHANNEL_ID — Slack チャネル ID
- KABU_API_PASSWORD — kabu API（別モジュールで使用）

オプション・デフォルトあり：
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — DEBUG/INFO/...
- KABU_API_BASE_URL — デフォルト http://localhost:18080/kabusapi
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — デフォルト data/monitoring.db
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- OPENAI_API_KEY — OpenAI を使う関数に必要（関数呼び出しの api_key 引数でも注入可能）

.env のパースはシェル風（export KEY=val や引用符、インラインコメント等に対応）です。

---

## 使い方（抜粋）

以下はライブラリの主要な利用例です。詳細は各モジュールの docstring を参照してください。

- ETL（日次パイプライン）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（AI）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print("書き込んだ銘柄数:", written)
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- ファクター計算（リサーチ）
  ```python
  from kabusys.research import calc_momentum, calc_value

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, target_date=date(2026, 3, 20))
  val = calc_value(conn, target_date=date(2026, 3, 20))
  ```

- 監査DBの初期化（監査専用 DB）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")  # 親ディレクトリは自動作成
  ```

- J-Quants クライアント（直接利用）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

  token = get_id_token()  # 環境変数 JQUANTS_REFRESH_TOKEN を参照
  records = fetch_daily_quotes(id_token=token, date_from=date(2026,1,1), date_to=date(2026,3,20))
  ```

注意点：
- OpenAI 関連関数（score_news, score_regime）は api_key 引数で明示的にキーを渡せます。未指定時は環境変数 OPENAI_API_KEY を参照します。
- ETL / API 呼び出しはネットワークや認証に依存するため、実行前に環境変数の設定とネットワーク接続を確認してください。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py — ニュース NLP スコアリング（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py — 市場カレンダー管理・判定ユーティリティ
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult の再エクスポート
    - jquants_client.py — J-Quants API クライアント（fetch / save）
    - news_collector.py — RSS ニュース収集・前処理
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - quality.py — データ品質チェック
    - audit.py — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py — Momentum/Volatility/Value 等のファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - research, ai, data の各種モジュールに多数の補助関数とドキュメント文字列あり

（上記は主要ファイルの一覧。実際のツリーはさらに細かいモジュールを含みます）

---

## 開発メモ / 運用上の注意

- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml がある階層）を基準に行われます。CI/テストで自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の executemany 周りの挙動（バージョン依存）に注意している箇所があります（空リストの executemany を避ける等）。
- OpenAI の呼び出しには JSON Mode（厳密な JSON 出力）を期待しており、応答のパースは堅牢化していますが、運用ではレスポンスの差異に注意してください。
- J-Quants API のレート制限（120 req/min）を尊重する実装になっています。

---

README はここまでです。各モジュールの docstring に詳細な設計・使用法が記載されています。必要であれば、使用例を拡張したサンプルスクリプトや requirements.txt、.env.example のテンプレートを作成しますのでお知らせください。