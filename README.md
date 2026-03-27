# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
DuckDB をデータストアに採用し、J-Quants API からのデータ取得（ETL）、ニュースの収集・AI ベースのセンチメント解析、ファクター計算、監査ログ（トレーサビリティ）等を提供します。

---

## 目次
- プロジェクト概要
- 主な機能一覧
- 前提条件
- セットアップ手順
- 簡単な使い方（コード例）
- 環境変数（.env）例
- ディレクトリ構成（主要ファイル説明）
- 補足・設計上のポイント

---

## プロジェクト概要
KabuSys は日本株のアルゴリズム取引/リサーチ向けに設計されたパッケージ群です。  
主に次の目的を持ちます。

- J-Quants API を用いた市場データ（株価・財務・カレンダー等）の差分取得（ETL）
- RSS 等からのニュース収集と前処理
- OpenAI（gpt-4o-mini 等）を用いたニュースのセンチメント解析（銘柄別 / マクロ）
- ファクター算出（モメンタム、バリュー、ボラティリティ等）と統計ユーティリティ
- 監査ログ（signal → order_request → execution）を格納する監査スキーマの初期化
- データ品質チェック（欠損、スパイク、重複、日付不整合など）

設計上、バックテストやルックアヘッドバイアスを避ける工夫（例：target_date ベースの窓、API 呼び出しのフェイルセーフ）を各所で行っています。

---

## 主な機能一覧
- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（取得・保存・トークンリフレッシュ・レート制御）
  - ニュース収集（RSS）/ 前処理 / DB 保存
  - マーケットカレンダー管理（営業日判定、next/prev など）
  - データ品質チェック（missing, spike, duplicates, date consistency）
  - 監査ログスキーマ（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - ニュースセンチメント（score_news）
  - 市場レジーム判定（score_regime：ETF 1321 の MA200 とマクロ記事の LLM センチメントを合成）
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（forward returns, IC, ranking, summary）
- config
  - 環境変数ロード（.env 自動読み込み / 保護 / override 処理）
  - settings オブジェクト経由で設定参照

---

## 前提条件
- Python 3.10+ （typing | union syntax を使用）
- 主要依存ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS フィード / OpenAI API）

（実際の requirements.txt はプロジェクトに合わせて調整してください）

---

## セットアップ手順（開発向けの一例）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージインストール（例）
   - pip install -U pip
   - pip install duckdb openai defusedxml

   開発中はプロジェクトルートで:
   - pip install -e .

3. 環境変数設定
   - プロジェクトルートに `.env` を置く（下の「環境変数（.env）例」を参照）
   - 自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

4. データベース初期化（監査ログ用など）
   - 監査ログ専用 DB を初期化する例:
     ```python
     import duckdb
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     # conn は初期化済みの duckdb 接続
     ```

5. DuckDB メイン DB を使う場合は `settings.duckdb_path` を参照して接続してください:
   ```python
   from kabusys.config import settings
   import duckdb
   conn = duckdb.connect(str(settings.duckdb_path))
   ```

---

## 使い方（主要な関数の例）

- 設定参照
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)  # 必須変数は未設定だと ValueError
  ```

- 日次 ETL 実行（市場カレンダー・株価・財務・品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())
  ```

- ニュースセンチメントを計算して ai_scores テーブルへ書き込む
  ```python
  from kabusys.ai.news_nlp import score_news
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026,3,20), api_key="YOUR_OPENAI_KEY")
  print("written", n_written)
  ```

- 市場レジーム判定（ETF 1321 MA200 とマクロ記事の LLM センチメントの合成）
  ```python
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20), api_key="YOUR_OPENAI_KEY")
  ```

- 監査スキーマの初期化（既存接続へ）
  ```python
  from kabusys.data.audit import init_audit_schema
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

- ファクター計算・IC 等（Research）
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026,3,20))
  forwards = calc_forward_returns(conn, date(2026,3,20))
  rho = calc_ic(momentum, forwards, "mom_1m", "fwd_1d")
  ```

---

## 環境変数（.env）例
config.Settings が期待する主要変数例（最低限設定が必要なものを含む）:

- JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>  # 必須
- KABU_API_PASSWORD=<kabu_api_password>               # 必須（kabu API 用）
- KABU_API_BASE_URL=http://localhost:18080/kabusapi    # 任意（デフォルト）
- SLACK_BOT_TOKEN=<slack_bot_token>                   # 必須（通知等）
- SLACK_CHANNEL_ID=<slack_channel_id>                 # 必須
- OPENAI_API_KEY=<openai_api_key>                     # OpenAI を利用する機能で必須
- DUCKDB_PATH=data/kabusys.duckdb                      # DuckDB ファイルパス
- SQLITE_PATH=data/monitoring.db                       # 監視 DB 等
- KABUSYS_ENV=development|paper_trading|live           # 動作環境（検証・実運用判定）
- LOG_LEVEL=INFO|DEBUG|WARNING|ERROR|CRITICAL

.env の自動読み込みについて:
- パッケージはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探し、.env → .env.local の順で自動ロードします。
- OS 環境変数は保護され、.env.local の override は許可されます。
- 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で便利）。

---

## ディレクトリ構成（主要ファイルと説明）
（src/kabusys 以下）

- __init__.py
  - パッケージのバージョン等
- config.py
  - 環境変数のロード・settings オブジェクト
- ai/
  - news_nlp.py : ニュースを銘柄別に集約して OpenAI でスコアリングし ai_scores に書き込む
  - regime_detector.py : ETF 1321 の MA200 とマクロ記事 LLM を合成して market_regime に書き込む
- data/
  - jquants_client.py : J-Quants API クライアント（fetch/save 等）
  - pipeline.py : ETL パイプライン (run_daily_etl など) と ETLResult
  - news_collector.py : RSS フィード取得・前処理・raw_news 保存
  - calendar_management.py : 市場カレンダー管理・営業日判定
  - quality.py : データ品質チェック
  - stats.py : zscore_normalize 等の統計ユーティリティ
  - audit.py : 監査ログ用 DDL / init_audit_schema / init_audit_db
  - etl.py : ETLResult の再エクスポート
- research/
  - factor_research.py : momentum / value / volatility のファクター計算
  - feature_exploration.py : forward returns / IC / summary / rank 等
- monitoring/, strategy/, execution/, など（パッケージ公開名として __all__ に含められている可能性あり）

各モジュールは README 内で説明した通りに責務が分離されています。実運用時は DuckDB スキーマ（テーブル作成）や権限、定期ジョブ（cron / Airflow 等）での ETL スケジューリングを検討してください。

---

## 補足・設計上のポイント
- ルックアヘッドバイアス対策:
  - 多くの関数は `target_date` を明示的に受け取り、内部で datetime.today() を直接参照しない設計です。
  - DB クエリは「date < target_date」「date <= target_date 以前の最新」などで未来データを参照しないように留意しています。
- フェイルセーフ:
  - OpenAI/API 呼び出しなどの失敗時にはゼロスコアにフォールバックしたり、部分失敗として処理を続行する設計が多く採用されています。
- 冪等性:
  - J-Quants の保存関数は ON CONFLICT DO UPDATE を使用しており、再実行しても重複を書き込まない設計です。
- セキュリティ:
  - news_collector では SSRF や XML bomb を防ぐための対策（ホスト検査、defusedxml、レスポンスサイズ制限等）を実装しています。

---

必要であれば、README に含めるサンプル SQL スキーマ、詳しい DB 初期化手順、CI / デプロイ手順、あるいは具体的な cron / systemd のジョブ定義例なども作成できます。どの情報がさらに必要か教えてください。