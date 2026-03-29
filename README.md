# KabuSys

日本株向けデータプラットフォーム兼自動売買基盤の軽量ライブラリ集です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集・NLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（発注→約定のトレーサビリティ）などを提供します。

## 主な特徴
- J-Quants API 経由の株価・財務・カレンダー取得（ページネーション・レート制御・再試行）
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース収集（RSS）と前処理、記事 → 銘柄紐付け
- OpenAI（gpt-4o-mini）を用いたニュースセンチメントスコアリング（ai_scores）および市場レジーム判定
- DuckDB を用いた高速な解析・保存
- 研究用モジュール（モメンタム・バリュー・ボラティリティ等のファクター、将来リターン、IC 計算、Zスコア正規化）
- 監査ログ（signal_events / order_requests / executions 等）の初期化ユーティリティ（冪等・UTC タイムスタンプ）
- 環境変数 / .env ベースの設定管理（自動ロード、優先度ルールあり）

---

## 機能一覧（抜粋）
- kabusys.config
  - 環境変数読み込み（.env, .env.local、自動ロードの ON/OFF）
  - settings オブジェクト経由で各種設定取得（J-Quants トークン、Kabu API パスワード、Slack トークン、DB パス等）
- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar 等
  - save_* 関数で DuckDB に冪等保存
- kabusys.data.pipeline
  - run_daily_etl（カレンダー → 株価 → 財務 → 品質チェック の一括実行）
- kabusys.data.news_collector
  - RSS 取得・前処理・raw_news 保存（SSRF や XML 脆弱性対策、サイズ制限等の安全対策を実装）
- kabusys.ai.news_nlp
  - score_news：銘柄ごとにニュースを集約し LLM でセンチメントを算出して ai_scores に保存
- kabusys.ai.regime_detector
  - score_regime：ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを合成して market_regime に保存
- kabusys.research
  - calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.data.quality
  - 欠損・重複・スパイク・日付不整合チェック（QualityIssue を返す）
- kabusys.data.audit
  - init_audit_schema / init_audit_db：監査ログ用テーブル・インデックスを初期化

---

## 必要条件（例）
- Python 3.10+
- パッケージ（主なもの）
  - duckdb
  - openai
  - defusedxml
  - （HTTP 用に標準ライブラリ urllib を使用）
- J-Quants / OpenAI / Slack など外部 API の利用には各種キーが必要

（プロジェクトルートに requirements.txt がある場合はそちらを参照してください）

---

## セットアップ手順（例）
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - pip install -r requirements.txt
   - または開発中であれば: pip install -e .

   必要な主要パッケージが無ければ以下をインストールしてください（例）:
   - pip install duckdb openai defusedxml

4. 環境変数の準備
   - プロジェクトルートに `.env`（や `.env.local`）を置くと自動で読み込まれます（優先順位：OS > .env.local > .env）。
   - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト等で利用）。
   - 主要な環境変数（必須）:
     - JQUANTS_REFRESH_TOKEN (J-Quants のリフレッシュトークン)
     - KABU_API_PASSWORD (kabuステーション API パスワード)
     - SLACK_BOT_TOKEN (Slack ボットトークン)
     - SLACK_CHANNEL_ID (通知先チャンネルID)
     - OPENAI_API_KEY (OpenAI 呼び出しに必要)
   - 任意／デフォルト:
     - KABUSYS_ENV (development / paper_trading / live) 既定: development
     - LOG_LEVEL (DEBUG / INFO / WARNING / ERROR / CRITICAL) 既定: INFO
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
   SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxx
   SLACK_CHANNEL_ID=C1234567890
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB データベースの初期化（監査ログ用など）
   - Python スクリプトで初期化できます:
     ```
     from kabusys.config import settings
     from kabusys.data.audit import init_audit_db
     init_audit_db(settings.duckdb_path)
     ```
   - 他にも schema 初期化ユーティリティがある想定（プロジェクトのスキーマ初期化手順に従ってください）。

---

## 使い方（簡単なコード例）
- ETL（日次）は run_daily_etl を呼ぶだけ
  ```
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュースセンチメント算定（指定日）
  ```
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("written:", n_written)
  ```

- 市場レジーム判定
  ```
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 研究モジュールの利用例（ファクター計算）
  ```
  from kabusys.research.factor_research import calc_momentum
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026, 3, 20))
  ```

注意:
- いずれの関数もルックアヘッドバイアス防止のため内部で datetime.today() を直接参照しない設計です（target_date を明示的に渡すことを推奨します）。
- OpenAI 呼び出しを行う関数は api_key 引数でキー注入可能（テスト容易性向上）。

---

## 設定と動作上の注意点
- .env 自動読み込み:
  - パッケージロード時にプロジェクトルート（.git または pyproject.toml を探索）を見つけると自動で `.env` → `.env.local` を読み込みます。
  - OS 環境変数は上書きされません（.env は未設定値のみセット、.env.local は override=True で上書き。ただし既存の OS 環境変数は保護されます）。
  - 自動ロード無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 環境モード:
  - KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれか。settings.is_live / is_paper / is_dev を参照可能。
  - 本番（live）での誤発注を防ぐため、発注実行ロジックは環境モードを参照するなどの安全ガード実装を推奨します。
- OpenAI 呼び出し:
  - gpt-4o-mini を前提にプロンプトや JSON モードを利用しています。API レスポンスのパースや再試行ロジックを内包しますが、呼び出し回数やコストに注意してください。

---

## ディレクトリ構成（主要ファイル）
プロジェクトの主要ソースは src/kabusys 以下に配置されています。抜粋:

- src/kabusys/
  - __init__.py
  - config.py                    # 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                # ニュース NLP（score_news）
    - regime_detector.py         # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py          # J-Quants API クライアント + 保存処理
    - pipeline.py                # ETL パイプライン（run_daily_etl 等）
    - etl.py                     # ETL 便宜公開（ETLResult 再エクスポート）
    - news_collector.py          # RSS ニュース収集
    - calendar_management.py     # 市場カレンダー管理
    - quality.py                 # データ品質チェック
    - stats.py                   # 統計ユーティリティ（zscore_normalize）
    - audit.py                   # 監査ログ（init_audit_schema/init_audit_db）
  - research/
    - __init__.py
    - factor_research.py         # momentum/value/volatility 等
    - feature_exploration.py     # forward returns / IC / summary / rank

（実際のファイル群はリポジトリの tree を参照してください）

---

## 開発／テストについて
- テストや CI を用意する場合、環境変数自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- OpenAI / J-Quants 呼び出し部分は関数単位で HTTP クライアントや API 呼び出しを差し替え可能に設計（テスト時はモックを注入してください）。

---

## 参考（便利なポイント）
- settings で必要なキーが未設定の場合は ValueError を発生させます（必須キー: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
- DuckDB のパスは settings.duckdb_path で取得できます（デフォルト data/kabusys.duckdb）。
- ETL の戻り値は ETLResult オブジェクトで、to_dict() により品質チェック情報やエラー一覧を簡単に取得できます。

---

ご不明点や追加したい機能（CLI、より詳細な初期スキーマ定義、サンプル .env.example など）があれば教えてください。README を用途に合わせて追補・調整します。