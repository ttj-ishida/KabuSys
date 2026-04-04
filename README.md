# KabuSys

日本株向けのデータプラットフォーム＆自動売買支援ライブラリ。  
J-Quants / RSS / OpenAI 等を組み合わせ、データ収集（ETL）・品質チェック・ニュースNLP・レジーム判定・リサーチ用ファクター計算・監査ログ等のユーティリティを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API を用いた株価・財務・カレンダー等の差分 ETL（DuckDB に保存）
- ニュース収集（RSS）と OpenAI を使った銘柄別センチメントスコア算出
- マーケットレジーム判定（ETF 1321 の MA200 乖離 + マクロニュースセンチメント）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- リサーチ用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- 監査ログ用スキーマ生成（signal → order_request → execution のトレーサビリティ）

設計上の特徴:
- DuckDB をストレージとして利用（ローカルファイル or :memory:）
- Look-ahead bias に配慮した時間窓処理（バックテスト安全設計）
- OpenAI 呼び出しは JSON モード利用、リトライやフォールバックを実装
- .env / 環境変数経由の設定読み込み（プロジェクトルート基準、自動ロード可）

---

## 機能一覧

- data/
  - jquants_client: J-Quants API 取得・DuckDB 保存、認証リフレッシュ、レート制御
  - pipeline, etl: 日次 ETL 実行(run_daily_etl など)
  - news_collector: RSS 収集（SSRF 対策、前処理、冪等保存）
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - calendar_management: 市場カレンダー管理・営業日判定
  - audit: 監査ログテーブル初期化（signal / order_requests / executions）
  - stats: z-score 正規化など統計ユーティリティ
- ai/
  - news_nlp.score_news: 銘柄単位のニュースセンチメント算出（OpenAI）
  - regime_detector.score_regime: マーケットレジーム判定（ETF 1321 + マクロニュース）
- research/
  - factor_research: Momentum / Volatility / Value の計算
  - feature_exploration: 将来リターン計算、IC、統計サマリ、ランク変換
- config: 環境変数管理（.env 自動読み込み、必須項目の検査）
- audit 初期化ユーティリティ（init_audit_schema / init_audit_db）

注: strategy / execution / monitoring といった実行・モニタリング層の公開名は存在しますが、ここに含まれるコードはユーティリティ／データ処理／リサーチに重点を置いています。

---

## セットアップ手順

1. Python バージョン
   - Python 3.10 以上（PEP 604 の型記法などを使用しているため）

2. インストール（仮想環境推奨）
   - 仮想環境作成例:
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     ```
   - 必要パッケージのインストール例:
     ```bash
     pip install duckdb openai defusedxml
     ```
     ※ 実プロジェクトでは requirements.txt / pyproject.toml を利用してください。

   - パッケージを開発モードでインストールする場合:
     ```bash
     pip install -e .
     ```

3. 環境変数 / .env
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を置くと自動的に読み込まれます。
   - 読み込み順: OS 環境変数 > .env.local > .env（.env.local は .env を上書き）
   - 自動ロードを無効にするには:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主な環境変数:
     - JQUANTS_REFRESH_TOKEN (必須): J-Quants リフレッシュトークン
     - KABU_API_PASSWORD: kabu API パスワード（発注などで利用）
     - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で利用）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知用（任意）
     - DUCKDB_PATH (例: data/kabusys.duckdb)
     - SQLITE_PATH (監視DB 用)
     - KABUSYS_ENV: development/paper_trading/live
     - LOG_LEVEL: DEBUG/INFO/...
   - .env の書き方（例）:
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token_here
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

---

## 使い方（簡単な例）

以下は代表的な利用例です。実行には必要な環境変数（上記）を設定してください。

- DuckDB 接続を作成して日次 ETL を実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（OpenAI API キー必須）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))  # ai_scores に書き込まれる銘柄数を返す
  print("written:", written)
  ```

- 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  # market_regime テーブルに書き込まれます
  ```

- 監査ログ用 DB を初期化
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/monitoring_audit.duckdb")
  # テーブル(signal_events, order_requests, executions) が作成されます
  ```

- calendar_management のユーティリティ
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

注意:
- OpenAI を使う API は api_key を引数で渡すこともできます（関数内で環境変数 OPENAI_API_KEY を参照）。テストではモックを推奨します。
- ETL / API 呼び出しはネットワーク・API レート制限の影響を受けます。ログやリトライ挙動を確認してください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
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
  - news_collector.py
  - calendar_management.py
  - quality.py
  - stats.py
  - audit.py
  - pipeline.py (ETLResult 再エクスポート)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research パッケージ用途: ファクター計算 / IC / 統計解析
- (その他)
  - monitoring, execution, strategy などはパッケージ公開名に含まれるが、実装は別途

上記は主要ファイルの抜粋です。詳細はソースコード内のドキュメント文字列（docstring）を参照してください。

---

## 設計上の注意点 / 運用メモ

- Look-ahead bias 回避:
  - 各モジュールは datetime.today() や date.today() を内部で直接参照しないよう設計されています（target_date を明示して処理する）。
- 環境変数自動読み込み:
  - プロジェクトルートを .git または pyproject.toml から探索し .env / .env.local を読み込みます。テスト時などに自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - .env のパースはシェル風のクォートや export プレフィックスを扱います（config._parse_env_line を参照）。
- OpenAI 呼び出し:
  - JSON モードを期待し、レスポンスのパース失敗や API エラー時はフォールバック（例: macro_sentiment=0.0、またはスキップ）します。
- J-Quants API:
  - rate limit（120 req/min）を守るため内部でスロットリングを行います。401 受信時は自動でリフレッシュを試みます。
- DuckDB:
  - 一部処理で executemany に空リストを渡せない制約（DuckDB 0.10 系）に配慮した実装があります。運用時は使用する DuckDB バージョンの挙動を確認してください。

---

## ライセンス / 貢献

このリポジトリのライセンス情報、貢献ガイドラインはプロジェクトのルートにある LICENSE / CONTRIBUTING を参照してください（存在する場合）。

---

README に記載されている利用例はサンプルです。実運用での自動売買（実際の注文発行）を行う場合は十分なテスト・リスク管理・法令遵守を行ってください。