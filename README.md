# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
J-Quants からのデータ ETL、ニュース収集・NLP スコアリング、LLM を使った市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（トレーサビリティ）などの機能を提供します。

本 README はソースツリー（src/kabusys）に基づく概要、セットアップ、使い方、ディレクトリ構成をまとめたものです。

---

## 特長（機能一覧）

- ETL（データパイプライン）
  - J-Quants からの株価（日足）・財務・カレンダー差分取得（ページネーション対応）
  - 差分更新、バックフィル、品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース処理
  - RSS 収集（トラッキングパラメータ削除、SSRF 対策、XML 脆弱性対策）
  - raw_news / news_symbols による銘柄紐付け
- AI（LLM）利用
  - ニュースセンチメント（銘柄ごと）を OpenAI（gpt-4o-mini）で評価し ai_scores へ書込み
  - 市場レジーム（bull/neutral/bear）判定（ETF 1321 の MA200 とマクロニュースを合成）
  - 再試行・フォールバック・レスポンスバリデーション機構を実装
- データ管理・ユーティリティ
  - DuckDB を想定した保存／スキーマ初期化（監査ログ用 init）
  - 統計ユーティリティ（Zスコア正規化など）
  - マーケットカレンダー管理（JPX ベース）と営業日判定
- 発注監査（Audit）
  - signal → order_request → execution まで UUID 連鎖でトレーサビリティ確保
- 設定管理
  - .env / 環境変数から設定自動読み込み（プロジェクトルート検出、.env.local 優先上書き）
  - settings オブジェクト経由で各種設定にアクセス可能

---

## 要件

- Python 3.10+
- 主な外部パッケージ
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリの urllib 等を使用（requests は不要）

（実行環境に応じて sqlite3/duckdb CLI などが必要です）

pip での簡易インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# またはプロジェクトの依存ファイルがあれば: pip install -r requirements.txt
```

---

## 環境変数 / 設定

KabuSys は .env / .env.local / OS 環境変数から設定を読み込みます（プロジェクトルートに .git または pyproject.toml がある場合）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数（抜粋）:

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン。get_id_token / データ取得に使用されます。

- KABU_API_PASSWORD (必須)  
  kabuステーション API のパスワード（発注系を実装する場合に使用）。

- OPENAI_API_KEY (AI 機能利用時に必要)  
  OpenAI API キー。score_news / score_regime で使用できます（引数で直接渡すことも可）。

- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (任意)  
  LINE 通知を使う場合に設定。

- DUCKDB_PATH (任意)  
  デフォルト: data/kabusys.duckdb

- SQLITE_PATH (任意)  
  デフォルト: data/monitoring.db

- PAPER_FILL_MODE (paper_trading 用)  
  instant | partial | never | reject（デフォルト: instant）

- KABUSYS_ENV (development | paper_trading | live)  
  実行環境の種別（デフォルト: development）

簡単な .env の例:
```
JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"
OPENAI_API_KEY="sk-..."
KABU_API_PASSWORD="your_kabu_password"
DUCKDB_PATH="data/kabusys.duckdb"
KABUSYS_ENV="development"
LOG_LEVEL="INFO"
```

---

## セットアップ手順（ローカル）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・依存インストール
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb openai defusedxml
   ```

3. 環境変数を設定（プロジェクトルートに .env を作成）
   - 上記の .env 例を参考に作成してください。
   - テスト等で自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

4. データベース用ディレクトリ作成
   ```
   mkdir -p data
   ```

5. 監査ログ用 DB を初期化（任意）
   Python REPL やスクリプトで:
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # conn は duckdb 接続（監査テーブルが作成されています）
   ```

---

## 使い方（代表的な利用例）

以下は最小限の利用例です。すべて DuckDB の接続（または ":memory:"）を渡して実行します。

- 日次 ETL の実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントをスコアリング（OpenAI API キーが必要）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書込銘柄数: {written}")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査スキーマ初期化（既存接続に対して）
  ```python
  from kabusys.data.audit import init_audit_schema
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

- 設定の参照
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)  # Path オブジェクト
  print(settings.paper_fill_mode)
  ```

- 研究用関数（ファクター計算など）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  date0 = date(2026, 3, 20)
  mom = calc_momentum(conn, date0)
  val = calc_value(conn, date0)
  vol = calc_volatility(conn, date0)
  ```

注意:
- AI 関連の関数は OpenAI の API キー（または引数で渡す api_key）を必要とします。API コストとレート制限に注意してください。
- ETL 実行前に DuckDB のスキーマ（raw_prices, raw_financials, raw_news, market_calendar, ai_scores, news_symbols 等）を用意する必要があります（初期化スクリプトは別途用意されている想定です）。

---

## よく使うモジュール一覧（短い説明）

- kabusys.config  
  環境変数 / .env 自動読み込み、settings オブジェクトを提供。

- kabusys.data.jquants_client  
  J-Quants API クライアント（取得・保存関数、認証・レート制御・リトライ実装）。

- kabusys.data.pipeline  
  日次 ETL のメイン実装（run_daily_etl 等）、ETLResult 定義。

- kabusys.data.news_collector  
  RSS 収集と raw_news 保存ロジック（SSRF/XML 対策あり）。

- kabusys.data.quality  
  データ品質チェック（欠損、重複、スパイク、日付不整合）。

- kabusys.data.calendar_management  
  market_calendar の運用と営業日判定ユーティリティ。

- kabusys.data.audit  
  発注・約定の監査テーブル定義と初期化関数。

- kabusys.ai.news_nlp  
  銘柄ごとのニュースを LLM でスコア化して ai_scores に書込む。

- kabusys.ai.regime_detector  
  ETF 1321 の MA200 とマクロニュースセンチメントを合成して市場レジーム判定。

- kabusys.research  
  ファクター計算（momentum, value, volatility）と特徴量探索ユーティリティ。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下）

- __init__.py — パッケージ初期化、バージョン
- config.py — 環境変数 / .env 読み込みと settings
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメントのスコア化ロジック
  - regime_detector.py — 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得/保存）
  - pipeline.py — ETL パイプラインと ETLResult
  - calendar_management.py — マーケットカレンダー管理
  - news_collector.py — RSS 取得・正規化・保存
  - quality.py — データ品質チェック
  - audit.py — 監査ログ（テーブル定義と初期化）
  - etl.py — ETL の公開インターフェース再エクスポート
  - stats.py — 汎用統計ユーティリティ
- research/
  - __init__.py
  - factor_research.py — ファクター計算（momentum, value, volatility）
  - feature_exploration.py — 将来リターン・IC・統計サマリー等
- ai/regime_detector.py, ai/news_nlp.py — LLM 呼び出し実装（リトライ・検証含む）

---

## 開発・テスト上の注意

- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト時に自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出し部分は内部で分離されており、ユニットテストでは該当関数をモックして短時間で実行できるよう設計されています（例: patch で _call_openai_api を差し替え）。
- DuckDB に対する executemany の仕様差異（空リスト不可など）に注意して実装されています。CI 環境での DuckDB バージョン差はテストに影響します。

---

## ライセンス・貢献

- 本リポジトリに LICENSE ファイルがあればそちらを参照してください。  
- バグ報告・機能提案・プルリクエストは Issue/PR で受け付けます。

---

以上が README の要約です。必要に応じて「初期スキーマ定義」「テストの実行方法」「デプロイ手順」「CI 設定例」などを追記できます。どの情報を優先して追加しますか？