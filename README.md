# KabuSys

KabuSys は日本株向けの自動売買・データ基盤ライブラリです。  
J-Quants からのデータ取得・ETL、ニュース収集と LLM によるニュースセンチメント解析、ファクター／リサーチ用ユーティリティ、監査ログ（トレース可能な発注／約定履歴）などを提供します。

主な設計方針は「ルックアヘッドバイアス防止」「冪等性」「フェイルセーフ（部分失敗に強い）」「テスト容易性」です。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- 必要条件
- セットアップ手順
- 基本的な使い方（例）
- 環境変数（.env）例
- ディレクトリ構成

---

プロジェクト概要
- データ取得: J-Quants API から株価（OHLCV）、財務データ、JPX カレンダー等をページネーション対応で取得。
- ETL: 差分取得、バックフィル、品質チェック（欠損・スパイク・重複・日付不整合）。
- ニュース: RSS 取得・正規化、raw_news への冪等保存、銘柄紐付け。
- AI: OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄別）とマクロセンチメント（市場レジーム判定）。
- 監査ログ: signal → order_request → executions のトレース可能な監査テーブルと初期化ユーティリティ。
- 研究用ユーティリティ: ファクター計算（モメンタム・ボラティリティ・バリュー）、将来リターン、IC 計算、Z スコア正規化等。

---

機能一覧（抜粋）
- data.jquants_client
  - J-Quants API 呼び出し（レート制御・リトライ・トークン自動更新）
  - fetch / save 用関数: fetch_daily_quotes, save_daily_quotes, fetch_financial_statements, save_financial_statements, fetch_market_calendar, save_market_calendar, fetch_listed_info など
- data.pipeline
  - 日次 ETL の統合エントリ run_daily_etl と個別 ETL ジョブ run_prices_etl/run_financials_etl/run_calendar_etl
  - ETLResult による詳細な実行結果保持
- data.quality
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
- data.news_collector
  - RSS 取得・前処理・SSRF対策・受信サイズ制限・トラッキングパラメータ除去
- data.calendar_management
  - 営業日判定・next/prev_trading_day・calendar_update_job
- data.audit
  - 監査ログ用 DDL / インデックス、init_audit_schema / init_audit_db
- ai.news_nlp
  - calc_news_window, score_news：銘柄別ニュースを LLM で評価し ai_scores に書き込み
- ai.regime_detector
  - ETF 1321 の MA200 乖離とマクロニュース LLM センチメントを合成して market_regime に書き込み
- research
  - calc_momentum / calc_volatility / calc_value、calc_forward_returns、calc_ic、factor_summary、rank、zscore_normalize

---

必要条件
- Python 3.10+
- 主な依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ：urllib, json, datetime, logging 等

（パッケージは pyproject.toml / requirements.txt があればそれに従ってください。ここに示したのはコードから推定される主要依存です。）

---

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成（例）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 依存インストール（例）
   ```
   pip install duckdb openai defusedxml
   # またはプロジェクトに requirements があれば:
   # pip install -r requirements.txt
   ```

4. パッケージを編集可能モードでインストール（任意）
   ```
   pip install -e .
   ```

5. 環境変数 / .env を用意
   - プロジェクトルート（.git または pyproject.toml を基準）を探索して自動で .env を読み込みます。
   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必要な環境変数の一例は README 内「環境変数例」を参照してください。

6. DuckDB / 監査DB の初期化（例）
   ```python
   import duckdb
   from kabusys.config import settings
   from kabusys.data.audit import init_audit_db

   # settings.duckdb_path はデフォルト 'data/kabusys.duckdb'
   conn = init_audit_db(settings.duckdb_path)  # ファイルがなければ親ディレクトリを作成して初期化
   ```

---

基本的な使い方（例）

- 日次 ETL を実行する
  ```python
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn)  # target_date を渡すことも可能
  print(result.to_dict())
  ```

- ニューススコアリング（ai/news_nlp）
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY を環境変数に設定しておくか、api_key 引数にキーを渡す
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジームスコア計算（ai/regime_detector）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査スキーマの初期化（既存接続に対して）
  ```python
  import duckdb
  from kabusys.data.audit import init_audit_schema

  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

注意点
- OpenAI 呼び出しには OPENAI_API_KEY が必要です（score_news, score_regime の api_key 引数からも渡せます）。
- J-Quants の認証には JQUANTS_REFRESH_TOKEN が必要です（settings.jquants_refresh_token を通して参照）。
- DuckDB のスキーマ（テーブル定義）は別途 schema 初期化ユーティリティ等があると想定しています（このコードベース内でのスキーマ定義は audit 周りが含まれますが、raw_prices/raw_news などのテーブルは ETL 側で想定されています）。実際に運用する場合は初期スキーマの DDL を準備してください。

---

環境変数（.env）例
以下はプロジェクトで参照される主要な環境変数の例です（.env.example として保存してください）。

内容例 (.env)
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# Kabuステーション API
KABU_API_PASSWORD=your_kabu_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# OpenAI (score_news / regime_detector に使用)
OPENAI_API_KEY=sk-...

# LINE (通知などに利用する場合)
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=

# データベースパス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 監視 / 実行制御
PID_FILE_PATH=data/execution.pid
KILL_FLAG_PATH=data/kill.flag
KILL_FLAG_CLEAR_ON_START=0

# システム設定
KABUSYS_ENV=development       # development / paper_trading / live
LOG_LEVEL=INFO
```

自動 .env 読み込みについて
- パッケージ起動時にプロジェクトルート（.git または pyproject.toml を探索）を基準に .env → .env.local の順で自動読み込みします（.env.local は上書き）。OS 環境変数が優先されます。
- 自動読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください（テスト時などで便利です）。

---

ディレクトリ構成（抜粋）
（ルート: src/kabusys 以下）

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                      — ニュース NLP（score_news 等）
    - regime_detector.py               — マーケットレジーム判定
  - data/
    - __init__.py
    - jquants_client.py                — J-Quants API クライアント + 保存ロジック
    - pipeline.py                      — ETL パイプライン（run_daily_etl 等）
    - etl.py                           — ETLResult 再エクスポート
    - news_collector.py                — RSS ニュース収集
    - calendar_management.py           — 市場カレンダー管理
    - quality.py                       — データ品質チェック
    - stats.py                         — 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py                         — 監査ログスキーマ / 初期化
  - research/
    - __init__.py
    - factor_research.py               — モメンタム / バリュー / ボラティリティ等
    - feature_exploration.py           — 将来リターン / IC / summary / rank
  - ai/、data/、research/ の各モジュールはさらに多くの関数・ユーティリティを含みます。

---

開発メモ / 注意事項
- DuckDB の executemany にまつわる互換性に配慮したコード（空リスト回避など）があるため、DuckDB のバージョンと互換性に注意してください。
- OpenAI 呼び出しはリトライ・レスポンス検証・JSON mode を利用する想定です。テストでは API 呼び出し箇所をパッチして差し替えられるよう設計されています。
- コードはルックアヘッドバイアスを避けるため date.today()/datetime.today() の直接参照を最小化する設計です（関数に target_date を明示的に渡す）。

---

ライセンス / コントリビューション
- （ここにライセンス情報や貢献方法を追記してください）

---

お問い合わせ / サポート
- 問題や改善提案は Issue を作成してください。README の内容やセットアップで不明点があればご相談ください。

以上。