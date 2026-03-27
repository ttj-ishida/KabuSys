# KabuSys

日本株向けの自動売買・データ基盤ライブラリ群です。  
ETL（J-Quants）→ データ品質チェック → ファクター計算 → ニュースNLP → レジーム判定 → 監査ログ までをカバーするモジュール群を含みます。

---

## 主な概要

- データ収集（J-Quants API 経由の株価・財務・カレンダー）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース収集（RSS）と LLM を使った銘柄センチメント評価
- 市場レジーム判定（ETF の MA とマクロ記事センチメントの合成）
- リサーチ用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- 監査ログ（signal → order_request → execution のトレーサビリティ用スキーマ）
- データ品質チェック（欠損・重複・スパイク・日付不整合）

設計上の特徴：
- ルックアヘッドバイアスに配慮（内部で date.today() を不用意に参照しない）
- DuckDB を用いたローカルデータベース（軽量かつ SQL ベース）
- OpenAI（gpt-4o-mini）を用いた JSON Mode での LLM 呼び出し
- 冪等性（INSERT ... ON CONFLICT / DELETE→INSERT のパターン）を重視

---

## 機能一覧（モジュール別）

- kabusys.config
  - 環境変数 / .env の自動読み込み・取得ユーティリティ
- kabusys.data
  - jquants_client: J-Quants API クライアントと DuckDB 保存関数
  - pipeline: ETL メイン処理（run_daily_etl 等）、ETLResult
  - quality: データ品質チェック（欠損・スパイク・重複・日付整合性）
  - news_collector: RSS 収集と前処理（SSRF/サイズ制限対策あり）
  - calendar_management: マーケットカレンダーの管理・営業日判定
  - audit: 監査ログ（signal / order_requests / executions）テーブル定義と初期化
  - stats: 汎用統計ユーティリティ（zscore_normalize 等）
- kabusys.ai
  - news_nlp.score_news: ニュースを銘柄別に集約し LLM でセンチメントを算出して ai_scores に保存
  - regime_detector.score_regime: ETF MA とマクロ記事センチメントから市場レジームを判定し market_regime に保存
- kabusys.research
  - factor_research: calc_momentum, calc_volatility, calc_value
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

---

## 動作要件

- Python 3.10 以上（「|」型ヒントを使用）
- 必要パッケージ（代表的なもの）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ: urllib, email.utils, datetime, json 等

（実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください）

---

## 環境変数 (.env)

パッケージ起動時にプロジェクトルートの `.env` / `.env.local` を自動読み込みします（CWD ではなくソースファイル位置からプロジェクトルートを探索）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数：
- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuAPI ベースURL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネルID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxx
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  # macOS / Linux
   - .venv\Scripts\activate     # Windows

3. 依存関係インストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt/pyproject.toml があれば pip install -r requirements.txt）

4. .env を作成（.env.example を参考に）
   - プロジェクトルートに .env を配置

5. DuckDB データベースの作成（任意）
   - Python REPL やスクリプトから監査DBを初期化:
     ```
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     conn.close()
     ```
   - または既存の DuckDB に対してスキーマを追加:
     ```
     import duckdb
     from kabusys.data.audit import init_audit_schema
     conn = duckdb.connect("data/kabusys.duckdb")
     init_audit_schema(conn, transactional=True)
     ```

---

## 使い方（コード例）

- ETL（デイリー）を実行する例:
  ```
  import duckdb, datetime
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=datetime.date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（特定日）:
  ```
  import duckdb, datetime
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, datetime.date(2026, 3, 20))
  print("written:", n_written)
  ```

- レジーム判定（特定日）:
  ```
  import duckdb, datetime
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, datetime.date(2026, 3, 20))
  ```

- 研究用ファクター計算:
  ```
  import duckdb, datetime
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, datetime.date(2026, 3, 20))
  ```

注意事項:
- score_news / score_regime では OpenAI API キーが必要です（引数 api_key または環境変数 OPENAI_API_KEY）。
- ETL や保存処理は DuckDB のスキーマ（raw_prices, raw_financials, market_calendar, raw_news 等）を前提とします。スキーマ初期化は別途用意してください（本リポジトリに schema 初期化スクリプトがある想定）。

---

## ディレクトリ構成（主要ファイル抜粋）

- src/kabusys/
  - __init__.py
  - config.py  -- 環境変数／.env 管理
  - ai/
    - __init__.py
    - news_nlp.py       -- ニュース NLP（score_news）
    - regime_detector.py-- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py -- J-Quants API クライアント & DuckDB 保存
    - pipeline.py       -- ETL パイプライン（run_daily_etl 等）
    - quality.py        -- データ品質チェック
    - news_collector.py -- RSS 収集／前処理
    - calendar_management.py -- マーケットカレンダー管理
    - audit.py          -- 監査ログテーブル定義・初期化
    - stats.py          -- 汎用統計ユーティリティ
    - etl.py            -- ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py

（上記以外に strategy / execution / monitoring などのパッケージが想定されていますが、ここでは主要な data / ai / research 周りを羅列しています）

---

## 開発・運用上のメモ

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に行います。テストで自動読み込みを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI の呼び出し部分はテストで差し替えやすいように内部呼び出し関数（_call_openai_api）を用意しています。ユニットテストではモックを当ててください。
- J-Quants クライアントは API レート制限（120 req/min）や 401 自動リフレッシュ、リトライ（408/429/5xx）に対応しています。
- ニュース収集は SSRF 対策・受信サイズ制限・gzip 解凍後の再チェック等の防御を組み込んでいます。
- DuckDB への書き込みは基本的に冪等性を考慮した実装（ON CONFLICT や DELETE→INSERT）になっています。

---

## テスト・モックに関して

- OpenAI など外部 API 呼び出しはモック（unittest.mock.patch）で差し替え可能です（例: kabusys.ai.news_nlp._call_openai_api のモック）。
- news_collector._urlopen をモックして RSS のネットワーク依存を切ることができます。
- ETL の個別ユニット（run_prices_etl など）は jquants_client の fetch / save 関数をモックして振る舞いを検証できます。

---

この README はコードベースの主要設計と利用方法の概要を示したものです。詳細な API 仕様・スキーマ定義・運用ルールについては各モジュール内の docstring（関数・クラスの説明）を参照してください。