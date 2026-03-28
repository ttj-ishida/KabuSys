# KabuSys

KabuSys は日本株の自動売買プラットフォーム向けのライブラリ群です。データ収集（J-Quants / RSS）、ETL、データ品質チェック、マーケットカレンダー管理、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、ファクター計算、監査ログ（発注→約定トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 主要機能（抜粋）

- データ取得 / ETL
  - J-Quants API クライアント（株価日足、財務データ、JPX カレンダー）
  - 差分取得・ページネーション・自動トークンリフレッシュ・レートリミット対策
  - ETL パイプライン（run_daily_etl）と個別ジョブ（価格／財務／カレンダー）
- データ品質管理
  - 欠損値・重複・スパイク・日付不整合の検出（quality モジュール）
- 市場カレンダー管理
  - market_calendar テーブルの更新・営業日判定（is_trading_day / next_trading_day など）
- ニュース収集
  - RSS 取得・正規化・SSRF 対策・記事ID生成・raw_news への冪等保存（news_collector）
- NLP / AI
  - ニュースごとのセンチメントスコア算出（news_nlp.score_news）
  - マクロニュース＋ETF MA による市場レジーム判定（regime_detector.score_regime）
  - OpenAI（gpt-4o-mini）を JSON モードで利用。リトライ / フォールバック実装あり
- 研究用ユーティリティ
  - ファクター計算（momentum / value / volatility 等）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Zスコア正規化
- 監査ログ（Audit）
  - signal_events, order_requests, executions などの監査テーブル定義と初期化ユーティリティ
  - DuckDB 上で冪等に初期化可能（init_audit_schema / init_audit_db）

---

## 必要条件

- Python 3.10+
- 主要依存（例）
  - duckdb
  - openai
  - defusedxml

（実際の依存はプロジェクトの pyproject.toml / requirements.txt を参照してください）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <リポジトリURL>

2. Python 仮想環境を作成＆有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - またはプロジェクトに requirements.txt / pyproject.toml があればそれに従う:
     - pip install -r requirements.txt
     - または poetry / pipx などを使用

4. 環境変数（.env）を用意
   - プロジェクトルートに `.env`（または `.env.local`）を配置できます。KabuSys は起動時に自動でプロジェクトルートの .env を読み込みます（無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 最低限設定が必要な環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 実行時に使用）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必要に応じて）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
     - DUCKDB_PATH: デフォルト: data/kabusys.duckdb
     - SQLITE_PATH: デフォルト: data/monitoring.db
     - KABUSYS_ENV: development | paper_trading | live （デフォルト development）
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
   - `.env.example` をプロジェクトに用意している場合はそれを参考にしてください。

5. DuckDB データベース初期化（監査用）
   - 監査テーブルを含めて初期化する例:
     - python で:
       - from kabusys.data.audit import init_audit_db
       - conn = init_audit_db("data/audit.duckdb")
     - あるいは既存の conn に対して init_audit_schema(conn)

---

## 使い方（よく使う関数例）

以下は Python REPL / スクリプトでの利用例です。

- DuckDB 接続の作成（設定値を利用）
  - from kabusys.config import settings
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する
  - from kabusys.data.pipeline import run_daily_etl
  - from datetime import date
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- ニュース NLP スコアを生成する（OpenAI API キーが必要）
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - n = score_news(conn, target_date=date(2026,3,20))
  - print(f"書き込み銘柄数: {n}")

- 市場レジーム判定を実行する（OpenAI API キーが必要）
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - r = score_regime(conn, target_date=date(2026,3,20))
  - print("完了" if r == 1 else "失敗")

- ファクター計算（研究用）
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  - mom = calc_momentum(conn, target_date=date(2026,3,20))
  - vol = calc_volatility(conn, target_date=date(2026,3,20))
  - val = calc_value(conn, target_date=date(2026,3,20))

- 監査 DB 初期化（ファイルパス指定）
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/monitoring_audit.duckdb")

テスト時・CI では OpenAI 呼び出しをモックすることを推奨します。各モジュールでは内部の _call_openai_api を unittest.mock.patch で差し替えられるよう設計されています。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
- KABU_API_PASSWORD — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID — Slack 通知
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 開発環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（INFO 等）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると自動 .env ロードを無効化

注意: Settings クラスは未設定の必須変数に対して ValueError を送出します。

---

## テストとモックのヒント

- OpenAI への実際の呼び出しはテストでモックしてください（unittest.mock.patch）。
  - 例: patch("kabusys.ai.news_nlp._call_openai_api", mock_fn)
  - regime_detector も同様に内部で _call_openai_api を使っているためモック可能です。
- news_collector のネットワーク I/O は _urlopen をモックすると便利です。
- J-Quants API 呼び出しは jquants_client._request をモックしてレスポンスを返すことができます。

---

## ディレクトリ構成（主なファイル）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数／設定管理
    - ai/
      - __init__.py
      - news_nlp.py            — ニュースセンチメント（OpenAI）
      - regime_detector.py     — 市場レジーム判定（MA200 + マクロセンチメント）
    - data/
      - __init__.py
      - jquants_client.py      — J-Quants API クライアント & DuckDB 保存ロジック
      - pipeline.py            — ETL パイプラインと個別 ETL ジョブ
      - etl.py                 — ETL インターフェース再エクスポート
      - news_collector.py      — RSS ニュース取得・前処理
      - calendar_management.py — マーケットカレンダー管理
      - quality.py             — データ品質チェック
      - stats.py               — 共通統計ユーティリティ（zscore 等）
      - audit.py               — 監査ログスキーマ初期化
    - research/
      - __init__.py
      - factor_research.py     — ファクター計算（momentum/value/volatility）
      - feature_exploration.py — 将来リターン、IC、統計サマリー
    - (その他) data/etl.py 等

---

## 設計上の注意点・ポリシー

- ルックアヘッドバイアス対策:
  - 各モジュールは date/datetime の現在時刻取得に依存しない（外部から target_date を受け取る）。
  - データ取得・スコア計算は target_date 未満・以前のデータのみを参照するよう設計されています。
- 冪等性:
  - DuckDB への保存は ON CONFLICT DO UPDATE / INSERT ... ON CONFLICT を使って冪等に行います。
- フェイルセーフ:
  - OpenAI や API エラー時は例外を全体で投げず、フォールバック値（0.0 など）で継続する箇所があります。呼び出し元で結果を検査してください。
- セキュリティ:
  - news_collector は SSRF 対策・gzip（解凍）サイズチェック・XML の安全パーサ（defusedxml）を利用しています。
- ロギング:
  - 各モジュールは詳細なログを出力するため、運用時は LOG_LEVEL を適切に設定してください。

---

## 貢献 / 開発

- コードスタイル・テスト・CI のルールはプロジェクトルートの設定（pyproject.toml / .github）を参照してください。
- 新しい機能追加や API 変更は既存モジュールとの分離（モジュール結合を避ける）を心がけてください（例: ai モジュールが直接別モジュールの内部 private 関数に依存しない等）。

---

この README はコードベースの主要なモジュールと使い方をまとめたものです。より詳しい設計ドキュメント（DataPlatform.md / StrategyModel.md 等）がプロジェクトに含まれている場合はそちらも参照してください。質問や補足があれば教えてください。