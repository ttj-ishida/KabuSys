# KabuSys

日本株向けのデータプラットフォーム／自動売買基盤ライブラリ（パッケージ形式）
バージョン: 0.1.0

このリポジトリは、J-Quants / kabuステーション / OpenAI 等の外部サービスと連携して
データ収集（ETL）、品質チェック、特徴量計算、ニュースNLP、マーケットレジーム判定、
監査ログ（トレーサビリティ）など自動売買システムに必要な基盤処理を提供します。

---

## 主要機能一覧

- 環境設定管理
  - .env / 環境変数から安全に設定を読み込み（自動ロードは無効化可）
- Data（ETL / データ品質 / カレンダー / ニュース収集 / J-Quants クライアント）
  - J-Quants API から株価・財務・カレンダーを差分取得（レート制限・リトライ対応）
  - DuckDB への冪等保存（ON CONFLICT ベース）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - JPX マーケットカレンダー管理（営業日判定・next/prev 等）
  - ニュースRSS 収集（SSRF 対策・トラッキング除去・前処理）
  - 監査ログスキーマの初期化（signal → order_request → executions のトレース）
- Research（ファクター計算 / 特徴量探索）
  - Momentum / Volatility / Value 等のファクター算出
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI（ニュースNLP / マーケットレジーム判定）
  - OpenAI を使ったニュースセンチメント分析（gpt-4o-mini、JSON mode 想定）
  - ETF（1321）200日MA乖離とマクロニュースセンチメントを合成した市場レジーム判定
- ユーティリティ
  - Z スコア正規化などの統計ユーティリティ
  - ログレベル / 動作環境（development / paper_trading / live）管理

---

## 前提（推奨環境）

- Python 3.10+（type hints に Union | を使用しているため）
- DuckDB
- OpenAI Python SDK（openai）
- defusedxml（RSS パースの安全対策）
- ネットワーク接続（J-Quants / OpenAI 等）

推奨パッケージ（例）
pip install duckdb openai defusedxml

プロジェクトをセットアップする際は仮想環境を使用してください。

---

## セットアップ手順

1. リポジトリをクローンして、パッケージをインストール（編集可能モード）
   ```
   git clone <this-repo>
   cd <this-repo>
   pip install -e .
   ```

2. 必要な依存をインストール（例）
   ```
   pip install duckdb openai defusedxml
   ```

3. 環境変数の設定
   - プロジェクトルートの `.env` または `.env.local` に必要な環境変数を設定できます。
   - 自動で .env を読み込む仕組みがあります（プロジェクトルート判定は .git または pyproject.toml に基づく）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主な環境変数（必須/デフォルト付き）:
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
   - KABU_API_PASSWORD (必須) — kabuステーション API パスワード
   - KABU_API_BASE_URL (任意) — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
   - OPENAI_API_KEY (必須 for AI functions) — OpenAI API キー
   - DUCKDB_PATH (任意) — デフォルト DuckDB ファイルパス（data/kabusys.duckdb）
   - SQLITE_PATH (任意) — 監視用 SQLite パス（data/monitoring.db）
   - KABUSYS_ENV (任意) — 環境: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL (任意) — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

   例 `.env`（最低限の例）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-xxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

---

## 使い方（主要な API と実行例）

以下の例では、settings を使った DuckDB 接続と各種処理の呼び出し方法を示します。

- 共通: settings の参照
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)  # Path オブジェクト
  ```

- DuckDB 接続を作る
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する（run_daily_etl）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings
  import duckdb
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコアリング（score_news）
  ```python
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings
  import duckdb
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY が環境変数にある前提。api_key 引数で上書き可能。
  count = score_news(conn, target_date=date(2026, 3, 20))
  print("scored:", count)
  ```

- 市場レジーム判定（score_regime）
  ```python
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB の初期化（監査専用 DB）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # parent dir を自動作成
  ```

- 研究用ファクター計算
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  import duckdb
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  momentum = calc_momentum(conn, date(2026, 3, 20))
  ```

- データ品質チェックを走らせる
  ```python
  from kabusys.data.quality import run_all_checks
  import duckdb
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  issues = run_all_checks(conn, target_date=date(2026, 3, 20))
  for i in issues:
      print(i)
  ```

注意:
- AI 関連（score_news / score_regime）は OpenAI API キー（OPENAI_API_KEY）が必要です。api_key を関数引数で与えることもできます。
- ETL / J-Quants 連携は JQUANTS_REFRESH_TOKEN が必要です。
- 関数の多くは外部 API を呼ぶため、ネットワークや認証情報の準備が必要です。

---

## 実装上の設計方針（簡易メモ）

- ルックアヘッドバイアス防止:
  - 日付参照に datetime.today() / date.today() を多用せず、明示的な target_date を受け取る設計。
  - クエリでは target_date より未来のデータを排除する工夫あり。
- 冪等性:
  - データ保存（DuckDB）では ON CONFLICT / INSERT ... DO UPDATE を使うことで再実行可能な ETL を実現。
- フェイルセーフ:
  - 外部 API 呼び出し失敗時はスキップして継続する設計が多い（例: LLM の失敗時はゼロスコアやスキップ）。
- セキュリティ:
  - RSS の取得は SSRF 回避・Gzip サイズ制限・defusedxml を採用。
  - J-Quants リクエストはレートリミッタとリトライ（401 でのトークンリフレッシュ含む）。

---

## ディレクトリ構成（抜粋）

以下はコードベースの主要ファイルとモジュール構成です（src/kabusys 配下）。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境設定管理
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py      — 市場レジーム判定（MA + LLM）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得 + 保存）
    - pipeline.py             — ETL パイプライン（run_daily_etl 他）
    - etl.py                  — ETLResult の再エクスポート
    - quality.py              — データ品質チェック
    - calendar_management.py  — マーケットカレンダー管理
    - news_collector.py       — RSS ニュース収集
    - stats.py                — 統計ユーティリティ（zscore_normalize）
    - audit.py                — 監査ログ（スキーマ初期化）
  - research/
    - __init__.py
    - factor_research.py      — Momentum / Value / Volatility 等
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー
  - ai/、data/、research/ 各モジュールに関連ユーティリティが詰まっています。

---

## 開発・テストについて

- 環境変数読み込みは自動で行われますが、ユニットテストや CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動読み込みを抑制してください。
- OpenAI 呼び出しやネットワーク I/O 部分はモックしてテスト可能な設計になっています（モジュール内の _call_openai_api や _urlopen 等を patch して差し替え）。

---

## ライセンス / 注意事項

- 本 README はコード内に記載された実装に基づいたドキュメントです。実際に運用する場合は、API 利用規約・料金、注文実行のリスク、認証情報の管理に関して十分に注意してください。
- live 環境での実行は実資金の取引につながります。paper_trading 環境で十分に検証してから運用してください（KABUSYS_ENV=paper_trading / live を活用）。

---

必要であれば、以下を追加で作成できます:
- .env.example のテンプレート
- 実運用向けのデプロイ手順（systemd / cron / Airflow 連携例）
- API 使用例（kabuステーション発注フロー）や監査ログの運用手順

要望があれば上記ドキュメントやサンプルを追記します。