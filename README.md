# KabuSys

KabuSys は日本株向けの自動売買・データ基盤ライブラリです。  
J-Quants からの市場データ取得（ETL）、ニュース収集・NLP（OpenAI を利用したセンチメント解析）、ファクター計算、監査ログ（約定トレース）など、自動売買システムのコア機能をモジュール化して提供します。

バージョン: 0.1.0

---

## 主な特徴

- データ取得（J-Quants）と ETL パイプライン（差分更新・バックフィル・品質チェック）
- DuckDB を用いたローカルデータベース保存（冪等操作）
- ニュース収集（RSS）と前処理、LLM による銘柄別・マクロセンチメントスコアリング
- 市場レジーム判定（ETF 1321 の MA とマクロセンチメントを合成）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ（signal → order_request → executions のトレースを保証）
- 環境変数／.env 自動読み込み機能（プロジェクトルートを検出）

---

## 機能一覧（抜粋）

- data/
  - ETL: run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - J-Quants クライアント: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - calendar_management: 営業日判定・翌営業日/前営業日取得・カレンダー更新ジョブ
  - news_collector: RSS 収集・前処理・raw_news 保存
  - quality: データ品質チェック（欠損・スパイク・重複・日付整合性）
  - audit: 監査ログ（テーブル作成・監査DB初期化）
  - stats: zscore_normalize などの統計ユーティリティ
- ai/
  - news_nlp.score_news(conn, target_date, api_key=None): ニュースから ai_scores を作成
  - regime_detector.score_regime(conn, target_date, api_key=None): 市場レジームを判定して market_regime へ保存
- research/
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- config
  - Settings クラス: 環境変数読み込み / .env 自動ロード / 必須変数チェック

---

## 必要条件

- Python 3.10+
- ライブラリ（代表）
  - duckdb
  - openai
  - defusedxml
  - そのほか標準ライブラリ（urllib 等）

（実際のパッケージ依存はプロジェクトの pyproject.toml / requirements.txt を参照してください）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動

   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成（任意）

   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .\.venv\Scripts\activate    # Windows
   ```

3. 依存パッケージをインストール

   例（pip）:
   ```
   pip install duckdb openai defusedxml
   ```

   ※ 実際は pyproject.toml / requirements.txt がある場合はそちらを使用してください。

4. 環境変数の設定

   プロジェクトルートに `.env` または `.env.local` を設置すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。必要な主要環境変数:

   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news/score_regime 実行時に必要）
   - KABUSYS_ENV: one of "development", "paper_trading", "live"（デフォルト: development）
   - LOG_LEVEL: "DEBUG","INFO"...（デフォルト: INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite のパス（デフォルト: data/monitoring.db）

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. DuckDB スキーマや監査DBの初期化（必要に応じて）

   Python から監査DBを初期化する例:

   ```python
   import duckdb
   from kabusys.data.audit import init_audit_db

   conn = init_audit_db("data/audit.duckdb")
   # conn は初期化済みの DuckDB 接続
   ```

---

## 使い方（基本例）

以下は主要なユースケースの簡単なサンプルです。すべて Python API を通じて実行します。

- DuckDB 接続準備

  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行（デフォルトで今日）:

  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())
  ```

- ニューススコアリング（前日 15:00 JST 〜 当日 08:30 JST のウィンドウ）:

  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026,3,20))
  print(f"written scores: {written}")
  ```

- 市場レジーム判定:

  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026,3,20))
  ```

- ファクター計算（研究用）:

  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  dm = calc_momentum(conn, date(2026,3,20))
  dv = calc_value(conn, date(2026,3,20))
  dvlt = calc_volatility(conn, date(2026,3,20))
  ```

- 監査スキーマの初期化（既存接続に対して）:

  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

注意点:
- OpenAI を呼ぶ関数（score_news / score_regime）は API キーが必要です。api_key 引数で渡すか、環境変数 OPENAI_API_KEY を設定してください。
- 各関数はルックアヘッドバイアスを避けるために内部で date を明示します（datetime.today() を参照しない設計）。
- ETL / API 呼び出しはリトライやフェイルセーフ（部分失敗の許容）を組み込んでいますが、設定やトークンが正しくないと失敗します。

---

## 環境変数（まとめ）

必須（使用箇所により必須になるもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants トークン（ETL）
- KABU_API_PASSWORD — kabuステーション API パスワード（注文周り）
- SLACK_BOT_TOKEN — Slack 通知に使用
- SLACK_CHANNEL_ID — Slack チャンネル ID
- OPENAI_API_KEY — OpenAI API（AI モジュール）

任意:
- KABUSYS_ENV — development / paper_trading / live
- LOG_LEVEL — DEBUG / INFO / ...
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視）パス（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する場合に 1 を設定

---

## ディレクトリ構成（主なファイルと説明）

src/kabusys/
- __init__.py
  - パッケージ初期化、公開 API 設定
- config.py
  - 環境変数 / .env 自動読み込み、Settings クラス
- ai/
  - __init__.py
  - news_nlp.py
    - ニュースの窓集約・OpenAI 呼び出し・ai_scores 書き込み
  - regime_detector.py
    - ETF 1321 の MA とマクロセンチメントを合成して market_regime を生成
- data/
  - __init__.py
  - calendar_management.py
    - 市場カレンダー管理 / 営業日判定
  - etl.py
    - ETL 結果型の公開（ETLResult）
  - pipeline.py
    - ETL パイプライン（run_daily_etl 等）
  - stats.py
    - zscore_normalize 等の統計ユーティリティ
  - quality.py
    - データ品質チェック
  - audit.py
    - 監査ログスキーマ作成 / init_audit_db
  - jquants_client.py
    - J-Quants API クライアント・保存ユーティリティ（fetch/save_*）
  - news_collector.py
    - RSS 収集・前処理・保存ロジック（SSRF 対策・サイズ制限等）
- research/
  - __init__.py
  - factor_research.py
    - momentum/value/volatility の計算
  - feature_exploration.py
    - 将来リターン・IC・統計サマリー等

---

## ログ / デバッグ

- LOG_LEVEL 環境変数でログレベルを設定（デフォルト INFO）
- AI / 外部 API 呼び出し部分はリトライおよびログ出力が組み込まれており、失敗時は警告を出して安全に継続する挙動が多く採用されています

---

## テスト／開発時のヒント

- 自動で .env を読み込む仕組みはプロジェクトルート（.git または pyproject.toml がある場所）を探索して行われます。テストで無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しや外部 HTTP をモックしやすいように、モジュール内部の呼び出し関数（例: _call_openai_api, _urlopen）を unittest.mock.patch で差し替えてテスト可能です。

---

## 免責 / 注意事項

- 本プロジェクトは自動売買インフラのコア機能を提供しますが、実際の売買（特に live 環境）に投入する前に十分なテスト・デューデリジェンスを行ってください。
- 取引は損失リスクを伴います。実運用ではリスク管理・レート制限・監査を慎重に設定してください。

---

必要があれば、README に以下を追加できます:
- 詳細なインストール手順（pyproject / poetry / pipenv 連携）
- 追加の設定項目や .env.example ファイル全文
- 各モジュールの API リファレンス（関数ごとの引数と戻り値の詳細）
- 運用ワークフロー例（ETL スケジュール、ジョブチェーン）

追加したい内容があれば教えてください。