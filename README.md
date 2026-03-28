# KabuSys

日本株向けのデータプラットフォーム & 自動売買補助ライブラリです。  
J-Quants / kabuステーション / OpenAI 等の外部サービスと連携して、データ取得（ETL）、品質チェック、ニュースNLP / 市場レジーム判定、ファクター計算、監査ログ管理などの機能を提供します。

---

## 主要な特徴

- データ収集（J-Quants）
  - 株価日足（OHLCV）、財務データ、上場銘柄情報、JPXカレンダーの差分取得（ページネーション対応）
  - レート制限・リトライ・トークン自動リフレッシュ対応
- ETLパイプライン
  - 差分フェッチ、冪等保存（DuckDBへのON CONFLICT処理）、品質チェック
  - 日次一括実行（calendar → prices → financials → quality）
- ニュース収集 / NLP
  - RSS から記事収集（SSRF対策・トラッキング除去・前処理）して raw_news に保存
  - OpenAI（gpt-4o-mini）を使った銘柄単位のセンチメントスコアリング（ai_scores への保存）
- 市場レジーム判定
  - ETF(1321) の 200 日 MA 乖離（70%）とマクロニュース LLM 評価（30%）を合成して日次で bull/neutral/bear を判定
- 研究用ユーティリティ
  - モメンタム / バリュー / ボラティリティ等のファクター計算、将来リターン、IC（Spearman）計算、Zスコア正規化
- 監査ログ（Audit）
  - signal → order_request → executions までトレース可能な監査テーブル群の初期化ユーティリティ
- データ品質チェック
  - 欠損、重複、スパイク、将来日付・非営業日データ検出

設計上の要点
- ルックアヘッドバイアス防止（多くの処理で date.today() を直接参照せず、明示的な target_date を受け取る）
- DuckDB を用いた高速なローカル分析・保存
- 外部呼び出しに対する堅牢なエラーハンドリングとフォールバック

---

## 必要条件（概略）

- Python 3.10+
- 主要依存ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / OpenAI / RSS 等）

※ 実際の依存バージョンはプロジェクトの packaging / requirements を参照してください。

---

## 環境変数

重要な環境変数（最低限）

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
- KABU_API_PASSWORD — kabuステーション API パスワード（必要に応じて）
- KABU_API_BASE_URL — kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用（必要に応じて）
- SLACK_CHANNEL_ID — Slack 送信先チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視DBなど）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development" / "paper_trading" / "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL")
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する場合は "1"

README 配布例として .env.example などを用意し、必要なキーを設定してください。

---

## セットアップ手順（例）

1. リポジトリをクローン
   - git clone ...

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - pip install -r requirements.txt
     （プロジェクトに requirements.txt が無い場合、少なくとも duckdb, openai, defusedxml 等をインストール）

4. 環境変数を設定
   - プロジェクトルートに .env を作成するか、OS環境変数として設定
   - 例 (.env):
     - JQUANTS_REFRESH_TOKEN=...
     - OPENAI_API_KEY=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - KABUSYS_ENV=development

5. データベース初期化（監査DBなど）
   - Python REPL やスクリプトで監査DB初期化:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")

---

## 使い方（簡単なコード例）

基本: DuckDB 接続を用意して関数を呼び出します。

- DuckDB に接続する例:
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する（run_daily_etl）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントスコアを生成する（score_news）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # APIキー未指定なら環境変数を使用
  print(f"scored {count} codes")
  ```

- 市場レジームを評価する（score_regime）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- ファクター計算（研究用途）
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  momentum = calc_momentum(conn, date(2026, 3, 20))
  volatility = calc_volatility(conn, date(2026, 3, 20))
  value = calc_value(conn, date(2026, 3, 20))
  ```

- 監査DBの初期化（独立DBを作る）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

注意点:
- OpenAI の呼び出しは api_key 引数で注入するか、環境変数 OPENAI_API_KEY を設定してください。
- 多くの関数は target_date を明示的に受け取り、ルックアヘッドバイアスを防ぐ設計になっています。

---

## ディレクトリ構成（抜粋）

概観（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定管理（.env 自動ロード機能あり）
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースの集約 + OpenAI による銘柄センチメント評価
    - regime_detector.py      — ETF MA とマクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得 + DuckDB 保存）
    - pipeline.py             — ETL（run_daily_etl 等）
    - etl.py                  — ETL 結果型のエクスポート（ETLResult）
    - quality.py              — データ品質チェック（欠損/重複/スパイク/日付不整合）
    - news_collector.py       — RSS 収集（SSRF 対策・前処理）
    - calendar_management.py  — 市場カレンダー / 営業日判定ユーティリティ
    - stats.py                — zscore_normalize 等の統計ユーティリティ
    - audit.py                — 監査テーブルDDLと初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py      — Momentum / Volatility / Value 計算
    - feature_exploration.py  — 将来リターン・IC・統計サマリーなど
  - ai/...、data/...、research/... が主要モジュール群

（実際のリポジトリにはさらに strategy、execution、monitoring 等のモジュールが含まれる想定）

---

## 開発・運用上の注意

- 自動 .env ロード:
  - パッケージはプロジェクトルート（.git または pyproject.toml を探索）から .env / .env.local を自動で読み込みます。
  - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で利用）。
- 安全設計:
  - news_collector は SSRF 対策、Gzip サイズチェック、XML 防御（defusedxml）などを実装しています。
  - J-Quants クライアントはレート制御・リトライ・トークンリフレッシュを備えます。
- エラー処理:
  - 多くの処理はフェイルセーフ（API失敗時はフォールバックやスキップ）となっており、ETL は段階ごとに個別エラーハンドリングを行います。
- テスト:
  - OpenAI 呼び出し等は内部でラップされており、ユニットテスト時にはモック差し替えが可能です（モジュール内の _call_openai_api などを patch）。

---

## よくある質問 / トラブルシューティング

- Q: OpenAI で 5xx やタイムアウトが発生したら？
  - A: モジュールはリトライ・バックオフを行い、最終的にエラー時は安全側（macro_sentiment=0.0 や該当チャンクスキップ）で処理を継続します。
- Q: DuckDB スキーマがない場合は？
  - A: ETL を初めて走らせる前に必要なテーブルスキーマを用意してください（初期化スクリプトや migration が別途ある想定）。監査用テーブルは init_audit_schema / init_audit_db で作成できます。
- Q: .env のパースがうまくいかない
  - A: config._parse_env_line は POSIX ライクな .env をかなり忠実にパースします。特殊なフォーマットがある場合はキー=値 形式に合わせてください。

---

必要であれば、README に実行スクリプト例（cron/airflow / systemd timer での ETL 実行例や Slack 通知連携、バックテスト時の注意点）を追加できます。どの用途向けの手順を優先して追記しますか？