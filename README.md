# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からの日次データ収集）、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（発注から約定までのトレーサビリティ）などを含みます。

---

## 主要機能（概要）

- データ収集 / ETL
  - J-Quants API から株価（日足）、財務情報、JPX カレンダーを差分で取得・保存
  - DuckDB へ冪等的に保存（ON CONFLICT DO UPDATE）
  - 品質チェック（欠損値、スパイク、重複、日付不整合）
  - 市場カレンダーの更新・営業日判定ユーティリティ

- ニュース収集・NLP
  - RSS フィードからニュースを収集・前処理して raw_news に保存（SSRF対策、トラッキング除去等）
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメントの銘柄別スコアリング（ai_scores）

- 市場レジーム判定
  - ETF(1321) の 200 日移動平均乖離とマクロニュースの LLM センチメントを合成して日次レジーム（bull / neutral / bear）判定

- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
  - 汎用統計ユーティリティ（Zスコア正規化）

- 監査ログ（Audit）
  - signal → order_request → executions まで追跡可能な監査テーブル定義と初期化ユーティリティ
  - DuckDB ベースの監査 DB 初期化関数（UTC タイムスタンプ固定）

- 環境・設定管理
  - .env / .env.local / OS 環境変数から設定を自動読む（自動ロードは無効化可）

---

## セットアップ

前提
- Python 3.10+（PEP 604 型注釈を使用）
- Git, インターネット接続（J-Quants / OpenAI を利用する場合）

1. リポジトリをクローンしてパッケージをインストール
   ```bash
   git clone <repo-url>
   cd <repo>
   pip install -e .
   ```

2. 依存パッケージ（例）
   - duckdb
   - openai
   - defusedxml
   もし pyproject / requirements が無ければ手動で：
   ```bash
   pip install duckdb openai defusedxml
   ```

3. 環境変数／.env の準備
   プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   必須（動かす機能に応じて）:
   - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD — kabuステーション API のパスワード（使用時）
   - SLACK_BOT_TOKEN — Slack 通知を使う場合
   - SLACK_CHANNEL_ID — Slack 通知先
   - OPENAI_API_KEY — OpenAI を使う場合（score_news / score_regime）
   
   任意:
   - KABUSYS_ENV — development / paper_trading / live （デフォルト: development）
   - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると自動 .env ロードを無効化
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
   
   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（主要ユーティリティ例）

以下はライブラリ関数の呼び出し例です。実際にはアプリケーション側のスクリプトやジョブから呼び出します。

- DuckDB 接続の準備（デフォルトパスを settings から取得）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（prices/financials/calendar の差分取得と品質チェック）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントスコアリング（OpenAI 必須）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {written} symbols")
  ```

- 市場レジームスコア算出
  ```python
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（監査専用 DB を作る）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")  # ディレクトリを自動作成
  ```

- 研究用ファクター計算
  ```python
  from kabusys.research.factor_research import calc_momentum

  recs = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

注意点:
- OpenAI 呼び出しは API キー（OPENAI_API_KEY）を必要とします。API 呼び出しはリトライ・フェイルセーフ処理を行いますが、リソースと料金に注意してください。
- ETL / API 呼び出しはネットワークと外部サービスに依存します。テスト時には各種 API 呼び出しをモックすることを推奨します。

---

## 環境変数の自動ロード動作

- 自動ロード順序: OS 環境変数 > .env.local > .env
- プロジェクトルート判定: カレントファイルから親ディレクトリに `.git` または `pyproject.toml` を探しそこをルートとみなします。
- 自動読み込みを無効にする:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## 便利なワンライナー（例）

- ETL を cron / CI から実行する簡単な例（bash）
  ```bash
  python -c "import duckdb, datetime; from kabusys.data.pipeline import run_daily_etl; from kabusys.config import settings; conn=duckdb.connect(str(settings.duckdb_path)); print(run_daily_etl(conn, target_date=None).to_dict())"
  ```

---

## ディレクトリ構成（概観）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定読み込みロジック
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py — 市場レジーム判定（MA200 + マクロニュース）
  - data/
    - __init__.py
    - calendar_management.py — 市場カレンダー、営業日ユーティリティ
    - etl.py — ETL の公開インターフェース（再エクスポート）
    - pipeline.py — ETL パイプライン（run_daily_etl など）
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - quality.py — データ品質チェック
    - audit.py — 監査ログスキーマ定義と初期化
    - jquants_client.py — J-Quants API クライアント（取得/保存ロジック）
    - news_collector.py — RSS 取得・前処理・保存ロジック（SSRF 対策等）
    - (その他 data 関連モジュール)
  - research/
    - __init__.py
    - factor_research.py — モメンタム/ボラ/バリュー計算
    - feature_exploration.py — 将来リターン/IC/統計サマリ等
  - ai/, data/, research/ のユーティリティは相互に依存しつつも、実行時に外部 API を直接叩かない設計の関数も多くあり、テスト容易性を考慮しています。

---

## テスト / 開発ヒント

- 自動 .env ロードを無効にしてユニットテストで環境を制御:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- OpenAI / J-Quants / ネットワーク呼び出しはテストでモックしてください。コードは各所で _call_openai_api や urllib を内部で呼んでおり、テスト用に patch できるよう設計されています。
- DuckDB はインメモリも使用可能（":memory:" をパスに指定）で単体テストが容易です。

---

必要であれば、README に「例: ETL スケジュール」「より詳しい .env.example」「運用時の注意（レート制限, コスト）」などの項目を追加できます。どの項目を追加しますか？