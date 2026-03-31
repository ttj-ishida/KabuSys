# KabuSys

日本株向けのデータプラットフォーム & 自動売買補助ライブラリです。  
ETL、ニュースNLP、マーケットレジーム判定、ファクター計算、監査ログ（トレーサビリティ）などを提供します。  
（パッケージは src/kabusys 配下に実装されています）

---

## プロジェクト概要

KabuSys は以下を主に目的とした Python モジュール群です。

- J-Quants API などからのデータ取得（株価日足、財務データ、JPX カレンダー）
- データの ETL（差分取得、冪等保存、品質チェック）
- ニュースの収集・NLP スコアリング（OpenAI を用いたセンチメント）
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- 研究用ファクター計算・特徴量探索（モメンタム・バリュー・ボラティリティ等）
- 発注・約定フローの監査ログ（監査テーブルの初期化支援）
- 汎用ユーティリティ（統計、カレンダー管理など）

設計にあたっては「ルックアヘッドバイアス防止」「冪等性」「フェイルセーフ（API失敗時に処理継続）」を重視しています。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（fetch_*, save_*）
  - マーケットカレンダー管理（is_trading_day / next_trading_day / calendar_update_job）
  - ニュース収集（RSS → raw_news 保存）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP スコアリング（score_news）
  - 市場レジーム判定（score_regime）
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）

---

## 前提 / 動作環境

- Python 3.10 以上（型アノテーションに PEP 604 の `X | Y` を使用）
- 必要パッケージ（主なもの）
  - duckdb
  - openai
  - defusedxml
  - そのほか標準ライブラリを多用（urllib、json 等）

requirements.txt が無い場合は上記をインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン（またはソースを取得）

   git clone <repository-url>
   cd <repository-root>

2. 仮想環境を作成して有効化

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール

   pip install --upgrade pip
   pip install duckdb openai defusedxml

   （プロジェクトをパッケージとして使う場合）
   pip install -e .

4. 環境変数設定（.env）

   プロジェクトルートの .env または .env.local を読み込みます（自動ロード）。  
   自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必要な環境変数（主なもの）:
   - JQUANTS_REFRESH_TOKEN  （必須） — J-Quants のリフレッシュトークン
   - OPENAI_API_KEY         （必須 for AI 機能） — OpenAI API キー
   - KABU_API_PASSWORD      （必須 if kabu API を使う場合）
   - KABU_API_BASE_URL      （任意, default: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN        （必須 if Slack 通知を使う場合）
   - SLACK_CHANNEL_ID       （必須 if Slack 通知を使う場合）
   - DUCKDB_PATH            （任意, default: data/kabusys.duckdb）
   - SQLITE_PATH            （任意, default: data/monitoring.db）
   - KABUSYS_ENV            （任意, development|paper_trading|live）
   - LOG_LEVEL              （任意, DEBUG|INFO|WARNING|ERROR|CRITICAL）

   例 (.env):

   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

---

## 使い方（主なユースケース）

以下は Python REPL やスクリプトから呼ぶ際の利用例です。各例では duckdb 接続に settings.duckdb_path を使用しています。

- ETL（日次パイプライン）を実行する

  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

  - run_daily_etl はカレンダー → 株価 → 財務 → 品質チェックを順に実行します。処理は各ステップで例外を捕捉し続行する設計です。戻り値は ETLResult オブジェクトです。

- ニュースのスコアリング（AI）

  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  n = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込んだ銘柄数: {n}")

  - OPENAI_API_KEY が環境変数に設定されているか、score_news の api_key 引数で渡してください。
  - news_nlp はタイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）に基づいて raw_news と news_symbols を参照します。

- 市場レジーム判定（AI + MA）

  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ DB の初期化

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn は DuckDB 接続。テーブルが作成されます。

- マーケットカレンダー関連のユーティリティ

  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  conn = duckdb.connect(str(settings.duckdb_path))
  print(is_trading_day(conn, date(2026, 3, 20)))
  print(next_trading_day(conn, date(2026, 3, 20)))

---

## 設計上の注意点 / 実運用上の注意

- ルックアヘッドバイアス対策
  - 多くの関数は内部で datetime.today() / date.today() を直接参照せず、target_date を明示的に受け取る設計です。バックテストでの誤用に注意してください。

- 冪等性
  - J-Quants からの保存処理は ON CONFLICT（Upsert）で冪等性を担保しています。ETL は差分取得 + バックフィルにより API 側の後出し修正を吸収します。

- フェイルセーフ
  - OpenAI API 呼び出しや外部 API エラーは基本的に例外で処理を中断させず、フェイルセーフ（スコア 0 と見なす、あるいは該当処理をスキップ）で継続します。ログを確認してください。

- 環境変数の自動ロード
  - パッケージの config モジュールはプロジェクトルート（.git または pyproject.toml を検出）から .env と .env.local を自動で読み込みます。テスト時に自動ロードを止めるには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

- OpenAI 利用
  - news_nlp / regime_detector は gpt-4o-mini を想定した JSON mode を使用しています。API のコスト・レート制限に注意してください。

---

## ディレクトリ構成

リポジトリ内で重要なファイル・モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュースセンチメントスコアリング（score_news）
    - regime_detector.py           — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（fetch_*, save_*）
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - etl.py                       — ETLResult 再エクスポート
    - news_collector.py            — RSS 収集・前処理
    - calendar_management.py       — マーケットカレンダー管理
    - quality.py                   — データ品質チェック
    - stats.py                     — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                     — 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py           — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py       — 将来リターン・IC・統計サマリー等
  - ai/ (上記)
  - research/ (上記)

ファイル構成を把握すると、データ取得 → 保存 → 品質チェック → 研究・戦略というフローが追いやすくなっています。

---

## 追加情報 / トラブルシューティング

- DuckDB の接続先パス（DUCKDB_PATH）は settings.duckdb_path で取得可能です。初回はファイルが無ければ自動作成されます。
- J-Quants API の id_token は jquants_client.get_id_token() が自動取得・キャッシュ・リフレッシュを行います。大量の API 呼び出しはレート制限に注意してください（120 req/min）。
- RSS フェッチでは SSRF 対策（リダイレクト先検査、プライベート IP ブロック、レスポンスサイズ制限）を行っています。外部フィードの追加時に接続失敗する場合はログを確認してください。
- OpenAI 呼び出し周りはリトライや 5xx 親切設計をしていますが、API 仕様変更に伴い SDK クラス名や例外型が変わると影響を受ける可能性があります。

---

もし README に加えるべき具体的な実行コマンド、.env.example の完全版、あるいは CI/デプロイ手順などが必要であれば教えてください。必要に応じて追記します。