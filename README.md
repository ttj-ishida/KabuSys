# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
ETL、ニュースNLP、ファクター計算、監査ログ、J-Quants クライアント、マーケットカレンダー等を含むモジュール群で構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ用に設計された内部ライブラリ群です。主な目的は次のとおりです。

- J-Quants API からのデータ取得（株価・財務・カレンダー）
- ETL パイプライン（差分取得・保存・品質チェック）
- ニュース収集および OpenAI を用いたニュースセンチメント評価（銘柄別 / マクロ）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）
- 監査ログ（シグナル→発注→約定のトレース可能性）を DuckDB に保存
- マーケットカレンダー管理・営業日ロジック

設計方針として、ルックアヘッドバイアス回避、冪等性、フェイルセーフ（APIエラー時の堅牢性）に注力しています。

---

## 機能一覧

- data
  - J-Quants API クライアント（認証、ページネーション、保存用ユーティリティ）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - ニュース収集（RSS、安全対策付き）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore 正規化）
- ai
  - ニュースセンチメント解析（score_news：銘柄別）
  - 市場レジーム判定（score_regime：ETF 1321 MA200 とマクロセンチメント合成）
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索・IC 計算（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - 環境変数/設定管理（.env 自動ロード、必須チェック、KABUSYS_ENV 判定）

主な設計上の特徴：
- DuckDB を中心に設計（軽量かつローカル分析に適合）
- OpenAI API（gpt-4o-mini）を JSON Mode で使用するラッパー実装（リトライ・バリデーション付き）
- J-Quants のレート制御・リトライ・トークン自動リフレッシュ対応

---

## セットアップ手順

前提:
- Python 3.10 以上を推奨（PEP 604 の union types (A | B) を使用）
- DuckDB、OpenAI SDK、defusedxml 等の依存ライブラリが必要

1. 仮想環境作成（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. 依存パッケージをインストール（例）
   ```
   pip install duckdb openai defusedxml
   ```
   ※ プロジェクトではさらにロギング設定やテストフレームワーク（pytest 等）を使う場合があります。

3. 環境変数 / .env の準備  
   プロジェクトルート（pyproject.toml や .git がある親ディレクトリ）に `.env` および任意で `.env.local` を配置できます。自動ロード順序は OS 環境 > .env.local > .env です。
   自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   例: `.env`（機密情報は実際の値を設定）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB / DB 初期化（監査DBなど）
   - 監査ログ専用 DB を作る:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - ETL 等で使用する DuckDB ファイルは `settings.duckdb_path` を参照するか、明示的に開きます。

---

## 使い方（主要な関数例）

以下はライブラリの主要なエントリーポイントの簡単な利用例です（実運用ではログ設定や例外処理を追加してください）。

- 設定読み込み
  ```python
  from kabusys.config import settings
  # 必須変数は settings.jquants_refresh_token 等で取得（未設定なら例外）
  ```

- ETL（日次）実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別）をスコア化（OpenAI API キーは環境変数か引数で指定）
  ```python
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026, 3, 20))  # returns 書込銘柄数
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- ファクター計算（研究用）
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  conn = duckdb.connect(str(settings.duckdb_path))
  mom = calc_momentum(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  ```

- 監査スキーマ初期化（既存接続に対して）
  ```python
  from kabusys.data.audit import init_audit_schema
  conn = duckdb.connect(str(settings.duckdb_path))
  init_audit_schema(conn, transactional=True)
  ```

注意点:
- OpenAI 呼び出しを含む関数（score_news, score_regime）は環境変数 `OPENAI_API_KEY` を参照します。引数で API キーを渡すことも可能です。
- DuckDB 接続は呼び出し側で管理してください。関数は接続オブジェクトを受け取ります。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 等で使用）
- KABU_API_PASSWORD: kabuステーション API パスワード
- KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack チャンネル ID
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化する場合に 1 を設定

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要ソースツリー（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
    - pipeline.py
    - etl.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (監視系や発注関連は別モジュールに含める想定)
  - strategy/ (戦略層は別モジュールや上位レイヤで実装)
  - execution/ (注文実行ロジックは別モジュールで整備)

（上の一覧は実際のファイルを抜粋したもので、細かいファイルはソースツリーを参照してください。）

ツリー例（簡略）
```
src/
└─ kabusys/
   ├─ __init__.py
   ├─ config.py
   ├─ ai/
   │  ├─ news_nlp.py
   │  └─ regime_detector.py
   ├─ data/
   │  ├─ jquants_client.py
   │  ├─ pipeline.py
   │  ├─ quality.py
   │  ├─ news_collector.py
   │  └─ audit.py
   └─ research/
      ├─ factor_research.py
      └─ feature_exploration.py
```

---

## 実運用上の注意点

- ルックアヘッドバイアス防止: 多くの処理は明示的な target_date を引数で受け取り、内部で date.today() を参照しない設計です。バックテストや再現性を高めるために target_date を明示することを推奨します。
- 冪等性: jquants_client の保存関数や ETL では ON CONFLICT/DELETE→INSERT で冪等動作を想定していますが、運用時には DB バージョン依存（DuckDB のバージョン）に注意してください。
- OpenAI 呼び出し: レスポンスのバリデーションやリトライを実装していますが、プロンプト設計やコスト管理（トークン消費）には注意してください。
- セキュリティ: news_collector は SSRF 対策（リダイレクト検証・プライベートIP除外）や XML 防御を組み込んでいます。外部入力を扱う際は追加の監査を検討してください。

---

## 貢献・拡張

- 追加したい機能
  - 取引所別の深堀りカレンダー処理、より緻密なポジション管理、kabu API 実行ラッパーの実装など
- テスト
  - 各モジュールは外部 API 呼び出しを抽象化しているため、モック／スタブによる単体テストが容易です。
- ドキュメント
  - Strategy や Execution 層の仕様（シグナル→発注→約定ワークフロー）を別ドキュメントで整備してください。

---

必要であれば、この README を元に具体的な .env.example、データベーススキーマの初期化サンプル、デプロイ手順、CI 設定テンプレートなども作成します。どの部分を優先して追加しますか？