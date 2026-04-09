# KabuSys

日本株向け自動売買・データプラットフォーム（KabuSys）のリポジトリ説明書。

概要、主要機能、セットアップ方法、基本的な使い方、ディレクトリ構成を日本語でまとめています。

---

## プロジェクト概要

KabuSys は日本株のデータ収集（J-Quants 等）、ETL、品質検査、ニュースのNLPスコアリング、LLMベースの市場レジーム判定、ファクター研究、監査ログ（トレーサビリティ）などを統合した自動売買／リサーチ基盤です。  
主に以下を目的とします。

- データ取得と永続化（DuckDB を用いた ETL）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- ニュースのセンチメント解析（OpenAI / gpt-4o-mini を利用）
- マーケットレジーム判定（価格指標 + マクロニュース）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ 等）
- 取引ワークフローの監査ログ（シグナル→発注→約定の追跡）

---

## 主要機能一覧

- data/jquants_client
  - J-Quants API からの株価・財務・カレンダー取得（ページネーション・リトライ・レート制御）
  - DuckDB への冪等保存（ON CONFLICT / 更新）
- data/pipeline
  - 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - ETL 結果を ETLResult で返却
- data/quality
  - 欠損、スパイク、重複、日付不整合チェック（QualityIssue）
- data/news_collector
  - RSS 取得・正規化・SSRF 対策・raw_news への保存
- ai/news_nlp
  - OpenAI を使ったニュース銘柄別センチメント解析（バッチ処理、JSON Mode、リトライロジック）
- ai/regime_detector
  - ETF（1321）200日移動平均乖離とマクロニュース（LLM）を合成して market_regime を日次判定
- research/*
  - ファクター計算（モメンタム／ボラティリティ／バリュー）
  - 将来リターン計算、IC（情報係数）、統計サマリー
- data/audit
  - シグナル → 発注 → 約定の監査テーブル定義・初期化ユーティリティ
- config
  - .env 自動読み込み（プロジェクトルートの .env / .env.local）と Settings オブジェクト

---

## 要求環境（例）

- Python 3.10+
- 依存ライブラリ（代表例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリに依存する機能が多い）

インストールはプロジェクトの packaging/requirements に依存します。簡易手順は以下参照。

---

## 環境変数（主なもの）

必須（本番／ETL 実行に必要）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client で使用）
- KABU_API_PASSWORD: kabu ステーション API パスワード（発注連携用）
- OPENAI_API_KEY: OpenAI API キー（ニュース NLU / regime 判定）

任意 / デフォルトあり
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE: paper_trading の埋め合わせ挙動（instant|partial|never|reject）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用（任意）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動 .env 読み込みを無効化

自動読み込みの挙動:
- パッケージはプロジェクトルート（.git または pyproject.toml を探索）を基準に自動で .env → .env.local を読み込みます。
- 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例 .env（簡易）
- JQUANTS_REFRESH_TOKEN=xxxxxxxx
- OPENAI_API_KEY=sk-...
- KABU_API_PASSWORD=your_password
- KABUSYS_ENV=development

---

## セットアップ手順（ローカル開発向け、概略）

1. リポジトリをクローン
   - git clone <repo_url>

2. 仮想環境を用意
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存インストール（最小）
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそれを使ってください:
    pip install -r requirements.txt または pip install -e .)

4. .env をプロジェクトルートに作成
   - 必須の環境変数を設定（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY など）

5. データディレクトリを作成（必要に応じて）
   - mkdir -p data

6. DuckDB 初期化（監査 DB を作る例）
   - Python REPL やスクリプトで init_audit_db を実行（下記を参照）

---

## 基本的な使い方（コード例）

以降は Python から直接関数を呼び出す例です。DuckDB 接続は duckdb.connect(path) を利用します。

- DuckDB 接続を作る
  - import duckdb
  - from kabusys.config import settings
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する
  - from kabusys.data.pipeline import run_daily_etl
  - import datetime
  - res = run_daily_etl(conn, target_date=datetime.date(2026,3,20))
  - print(res.to_dict())

- ニュースのスコアリング（OpenAI 必須）
  - from kabusys.ai.news_nlp import score_news
  - score_count = score_news(conn, target_date=datetime.date(2026,3,20))
  - print(f"書き込み銘柄数: {score_count}")

- 市場レジーム判定（OpenAI 必須）
  - from kabusys.ai.regime_detector import score_regime
  - result = score_regime(conn, target_date=datetime.date(2026,3,20))
  - print("完了" if result == 1 else "失敗")

- 監査ログ DB 初期化（監査用別 DB）
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")
  - # audit_conn に対して監査テーブルが作成されます

- ファクター計算例
  - from kabusys.research.factor_research import calc_momentum
  - records = calc_momentum(conn, datetime.date(2026,3,20))
  - # records は dict のリスト

注意点:
- OpenAI 周りは API キー必須。テスト時はモック可能（各モジュールの _call_openai_api を patch）。
- ETL と研究機能は DuckDB のスキーマ（raw_prices, raw_financials, raw_news, news_symbols, ai_scores, market_regime 等）に依存します。初期スキーマは別途用意する想定です。

---

## よく使うユーティリティ / 初期化

- audit.init_audit_schema(conn, transactional=True)
  - 既存の DuckDB 接続に監査用テーブル群を追加します。

- data.jquants_client.get_id_token()
  - J-Quants の idToken を取得（settings.jquants_refresh_token を使います）

- data.news_collector.fetch_rss(url, source)
  - RSS をパースして記事リストを返します（SSRF 対策済）

---

## テスト/開発メモ

- OpenAI 呼び出しはモックしやすい設計:
  - kabusys.ai.news_nlp._call_openai_api を patch してレスポンスを差し替えられます
  - kabusys.ai.regime_detector._call_openai_api も同様
- news_collector のネットワーク呼び出しは _urlopen をモック可能
- 自動 .env 読込を無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセット

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py  — 環境変数と設定読み込み
- ai/
  - __init__.py
  - news_nlp.py        — ニュースの LLM センチメント解析
  - regime_detector.py — マーケットレジーム判定ロジック
- data/
  - __init__.py
  - jquants_client.py      — J-Quants API クライアント（取得・保存）
  - pipeline.py           — ETL パイプライン（run_daily_etl など）
  - quality.py            — データ品質チェック
  - news_collector.py     — RSS 収集・正規化
  - calendar_management.py— マーケットカレンダー管理
  - audit.py              — 監査ログテーブル定義・初期化
  - etl.py                — ETLResult の再エクスポート
  - stats.py              — zscore_normalize 等の統計ユーティリティ
- research/
  - __init__.py
  - factor_research.py    — モメンタム/バリュー/ボラティリティ計算
  - feature_exploration.py— 将来リターン/IC/統計サマリー等
- research/*, ai/*, data/* にそれぞれ関連実装がまとまっています。

---

## 運用上の注意・設計方針（抜粋）

- ルックアヘッドバイアス対策:
  - 各モジュールは内部で datetime.today() を直接参照しない、または明示的な target_date を受け取る設計
  - prices_daily 等のクエリは target_date 未満や <=/>= を適切に扱い、未来データを参照しない
- フェイルセーフ:
  - LLM/API 失敗時はスコアを 0 にフォールバックする等、処理を止めない設計が多い
- 冪等性:
  - DuckDB への保存は ON CONFLICT / UPDATE で上書きすることで再実行可能に
- セキュリティ:
  - RSS の SSRF 対策（ホスト検査・リダイレクト検査）
  - defusedxml を使用して XML パースの安全性を確保

---

## 貢献・開発

- 新しい機能追加やバグ修正は Pull Request をお願いします。  
- 変更を行う際は、可能ならユニットテストを追加し、OpenAI 呼び出しなど外部依存はモックすることを推奨します。

---

README の内容はコードベースの一部から抜粋して整理しています。運用や本番利用の前に、環境変数・API キーの設定、DuckDB スキーマの初期化、十分なテストを行ってください。必要であれば README に記載するサンプル .env.example や初期スキーマ作成手順を追加できます。希望があれば追記します。