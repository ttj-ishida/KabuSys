# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースNLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（発注/約定トレーサビリティ）など、トレーディングシステムに必要な共通機能を提供します。

主な設計方針
- DuckDB を中心としたローカルデータレイヤ（Look-ahead バイアス対策を重視）
- J-Quants / OpenAI 呼び出しは再試行・レート制御・フェイルセーフ実装
- DB 書き込みは冪等（ON CONFLICT / DELETE→INSERT 等）
- テスト容易性のため外部キー・APIキー注入・モック差し替えを想定

---

## 機能一覧

- 環境設定管理
  - .env 自動読み込み（プロジェクトルート検出）および必須変数チェック
- データ取得 / ETL（kabusys.data）
  - J-Quants API クライアント（株価 / 財務 / マーケットカレンダー）
  - ETL パイプライン（差分取得・バックフィル・品質チェック）
  - ニュース収集（RSS → raw_news、SSRF対策・トラッキング除去）
  - カレンダー管理（営業日判定 / next/prev / SQ判定）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ（signal_events / order_requests / executions）初期化ユーティリティ
- AI / NLP（kabusys.ai）
  - ニュースに基づく銘柄センチメント（score_news）
  - マクロニュース + ETF MA200 を合成した市場レジーム判定（score_regime）
  - OpenAI 呼び出しは JSON Mode + 再試行・パース保護
- 研究用モジュール（kabusys.research）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
  - z-score 正規化ユーティリティ
- ユーティリティ
  - 統計関数、ETL 結果クラス、ID トークンキャッシュ、RateLimiter など

---

## セットアップ手順

前提
- Python 3.10+（型注釈に union などを使用）
- DuckDB、OpenAI Python SDK、defusedxml などが必要

1. リポジトリをクローン / コピー
   - 通常の Python パッケージとして開発環境にインストールします。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. 依存関係をインストール
   - (プロジェクトに requirements.txt がある場合)
     - pip install -r requirements.txt
   - ない場合は最低限:
     - pip install duckdb openai defusedxml

   （プロジェクトを editable インストールする場合）
   - pip install -e .

4. 環境変数の準備
   - プロジェクトルートに .env（または .env.local）を置くと自動読み込みされます。
   - 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

   必須変数（使用する機能により必要なものは変わります）:
   - JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
   - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime で使用）
   - KABU_API_PASSWORD — kabuステーション API パスワード（発注機能を使う場合）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知を使う場合
   - KABUSYS_ENV — environment (`development`, `paper_trading`, `live`)（任意、デフォルト development）
   - LOG_LEVEL — ログレベル（DEBUG/INFO/...）（任意）
   - DUCKDB_PATH — DuckDB 保存パス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C1234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. データベース初期化（監査ログ等）
   - 監査ログ用 DB を作る:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - 既存の DuckDB 接続に監査スキーマを追加する場合:
     ```python
     from kabusys.data.audit import init_audit_schema
     import duckdb
     conn = duckdb.connect("data/kabusys.duckdb")
     init_audit_schema(conn, transactional=True)
     ```

---

## 使い方（代表的な例）

以下は基本的な利用例です。実行前に必要な環境変数を設定してください。

- DuckDB 接続を取得して日次 ETL を実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントをスコアして ai_scores に書き込む
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY は環境変数か引数で渡す
  print(f"scored {count} codes")
  ```

- 市場レジーム判定（ETF 1321 の MA とマクロニュースの合成）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))
  ```

- 研究用ファクター計算（モメンタム等）
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, target_date=date(2026,3,20))
  vol = calc_volatility(conn, target_date=date(2026,3,20))
  val = calc_value(conn, target_date=date(2026,3,20))
  ```

- データ品質チェックの実行
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i)
  ```

注意事項 / 実運用上のポイント
- score_news / score_regime は OpenAI API を呼び出します。APIキーの取り扱い・課金に注意してください。
- ETL の差分ロジックや calendar の調整は「ルックアヘッドバイアス」を避けるよう設計されています。テストやバックテストで日付の扱いに注意してください。
- J-Quants API のレート制限（120 req/min）に合わせて RateLimiter や再試行ロジックがありますが、長時間の大量取得は注意してください。

---

## 主要モジュール・ディレクトリ構成

（ローカルのソース配下: src/kabusys）

- kabusys/
  - __init__.py (パッケージ定義)
  - config.py
    - .env 自動読み込み、Settings（環境変数アクセス）
  - ai/
    - __init__.py (score_news を公開)
    - news_nlp.py (ニュースセンチメント → ai_scores 書き込み)
    - regime_detector.py (ETF MA200 + マクロセンチメント → market_regime)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント、保存関数)
    - pipeline.py (ETL パイプライン: run_daily_etl 他)
    - etl.py (ETLResult 再エクスポート)
    - stats.py (z-score 正規化 等)
    - quality.py (データ品質チェック)
    - calendar_management.py (市場カレンダー管理 / 営業日判定)
    - news_collector.py (RSS 収集・前処理・raw_news 保存)
    - audit.py (監査ログスキーマ初期化・init_audit_db)
  - research/
    - __init__.py (研究用 API 再エクスポート)
    - factor_research.py (momentum/volatility/value 等)
    - feature_exploration.py (forward returns / IC / rank / summary)
  - ai/ など（上記）

---

## 実装上の注記（開発者向け）

- look-ahead バイアス対策:
  - 日付計算は内部で datetime.today()/date.today() を直接参照しない関数設計（target_date を明示的に渡す）。
  - DB クエリは target_date 未満 / 以前など明確に排他条件を設ける。
- 冪等性:
  - J-Quants の保存関数は ON CONFLICT DO UPDATE を使い冪等化。
  - ETL はバックフィルを取り込みつつ既存データ保護を行う。
- OpenAI 呼び出し:
  - JSON Mode を使用し、レスポンスの厳密なパースを行う。API 失敗やパース失敗時はフォールバック（0.0）で継続。
  - テストでは内部の _call_openai_api をモックすることを想定。
- エラーハンドリング:
  - 各段階は例外をキャッチして ETL レポートに記録する（Fail-Fast ではなく全件収集）。

---

もし README に追記したい実行スクリプト例（cron や Airflow 用のラッパー）、SQL スキーマ定義、あるいは .env.example の雛形が必要であれば教えてください。README をプロジェクトの慣例（Contributing/License/CI）のスタイルに合わせて拡張することもできます。