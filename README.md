# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）・データ品質チェック・ニュース収集・AI ベースのニュース評価・市場レジーム判定・リサーチ向けファクター計算・監査ログ（注文フロー追跡）などの機能を提供します。

バージョン: 0.1.0

---

## 主要な概要（Project overview）

KabuSys は次の役割を持つモジュール群で構成されています。

- data: J-Quants API クライアント、ETL パイプライン、ニュース収集、カレンダー管理、品質チェック、統計ユーティリティ、監査テーブル初期化等
- ai: ニュースの NLP（センチメント）評価、マクロニュースとテクニカル指標を組み合わせた市場レジーム判定
- research: ファクター計算（モメンタム、ボラティリティ、バリュー等）と特徴量探索ユーティリティ
- config: 環境変数・設定管理（.env 自動読み込みを含む）

設計上の考慮点（抜粋）:
- ルックアヘッドバイアスを避けるため、内部で date.today()/datetime.today() に依存しない実装が基本
- DuckDB をローカル DB として利用
- 外部 API 呼び出しにはリトライ・レート制限・フォールバックを組み込み
- 冪等性を考慮した DB 書き込み（INSERT … ON CONFLICT DO UPDATE 等）

---

## 機能一覧（Features）

- J-Quants API クライアント
  - 株価日足（OHLCV）取得、財務データ取得、上場銘柄情報、マーケットカレンダー取得
  - トークン管理（refresh token → id token）、レートリミット、リトライ
- ETL パイプライン
  - 日次 ETL（calendar / prices / financials）と品質チェック（欠損・重複・スパイク・日付整合性）
  - 差分更新・バックフィル対応、ETL 結果の ETLResult 出力
- ニュース収集（RSS）
  - RSS フィード取得、URL 正規化、SSRF 対策、記事保存（raw_news / news_symbols）
- AI ニュース NLP
  - OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントスコアを算出し ai_scores に保存
  - バッチ・リトライ・レスポンス検証ロジック
- 市場レジーム判定
  - ETF 1321（Nikkei 225 連動）200日移動平均乖離とマクロニュース LLM 評価を組合せて daily regime を判定
- リサーチ / ファクター計算
  - momentum / volatility / value 等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、ファクター統計サマリ、Zスコア正規化
- 監査ログ（audit）
  - signal_events / order_requests / executions 等の監査テーブル定義・初期化ユーティリティ
- 設定管理
  - .env 自動読み込み（プロジェクトルート検出）、必須環境変数チェック、実行環境（development / paper_trading / live）判定

---

## セットアップ手順（Setup）

前提
- Python 3.10 以上（型注釈 "X | Y" を利用）
- DuckDB, OpenAI SDK, defusedxml 等の依存

例（仮想環境作成と必要パッケージのインストール）:

1. 仮想環境を作る:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）:
   - pip install duckdb openai defusedxml

   プロジェクトを editable インストールする場合:
   - pip install -e .

3. 環境変数を設定:
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env`／`.env.local` を置くと自動で読み込まれます。
   - 自動読み込みを無効にする場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

推奨パッケージ（最低限）
- duckdb
- openai
- defusedxml

（実際の requirements.txt があればそちらを利用してください）

---

## 環境変数（主なキー）

このライブラリは環境変数から設定を読み取ります。主要な変数:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack 投稿先チャンネル ID（必須）
- DUCKDB_PATH: DuckDB の DB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルトは development
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY: OpenAI API キー（score_news や regime_detector 実行時に必要）

config 例（.env）:
- JQUANTS_REFRESH_TOKEN=xxxx
- OPENAI_API_KEY=sk-...
- DUCKDB_PATH=~/kabusys/data/kabusys.duckdb
- KABUSYS_ENV=development

設定は kabusys.config.settings からアクセス可能です（例: from kabusys.config import settings; settings.jquants_refresh_token）。

---

## 使い方（Usage）

以下は代表的な利用例です。実行環境に合わせて適宜パス / キーを設定してください。

- DuckDB 接続を作る（settings で DUCKDB_PATH を参照）:
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する:
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（銘柄別センチメント）を実行する:
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored: {n_written}")
  ```

- 市場レジーム判定:
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 研究用ファクター計算:
  ```python
  from datetime import date
  from kabusys.research import calc_momentum, calc_value, calc_volatility

  mom = calc_momentum(conn, target_date=date(2026, 3, 20))
  val = calc_value(conn, target_date=date(2026, 3, 20))
  vol = calc_volatility(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DB 初期化（監査専用の DuckDB ファイルを作成）:
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # テーブルが作成される
  ```

注意点:
- score_news / score_regime は OpenAI API を使用するため OPENAI_API_KEY が必要です（引数で api_key を渡すことも可能）。
- テスト時は内部の API 呼び出し関数（例: kabusys.ai.news_nlp._call_openai_api）をモックして差し替えが可能です。
- ETL / 保存処理は DuckDB のスキーマ（raw_prices, raw_financials, market_calendar 等）が事前に整備されていることを前提とします（スキーマ初期化機能はプロジェクトに応じて提供してください）。

---

## ディレクトリ構成（Directory structure）

主要ファイル・モジュール一覧（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数 / 設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py                     — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py              — 市場レジーム判定（MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント（取得 + 保存）
    - pipeline.py                     — ETL パイプライン（run_daily_etl 等）
    - etl.py                          — ETL 型エクスポート（ETLResult）
    - news_collector.py               — RSS 取得・前処理・保存
    - calendar_management.py          — マーケットカレンダー管理（営業日判定等）
    - quality.py                      — データ品質チェック（欠損・重複・スパイク等）
    - stats.py                        — 統計ユーティリティ（zscore_normalize）
    - audit.py                        — 監査テーブル定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py              — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py          — 将来リターン・IC・統計サマリ等

（上記以外に strategy / execution / monitoring 等のパッケージが想定されていますが、今回のコードリストでは data / ai / research / config が中心です）

---

## 開発・テストに関するメモ

- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テストで自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し部分は内部でリトライ・例外処理を行います。ユニットテストでは _call_openai_api を patch/mocking して外部呼び出しを防いでください。
- DuckDB を利用する関数は接続オブジェクトを引数にとる設計のため、インメモリの DuckDB（":memory:"）を使ったテストが容易です。
- ニュース収集部分は defusedxml で XML パースを保護し、SSRF 対策（ホスト検査、リダイレクト検査）を実装しています。

---

## ライセンス / 貢献

（プロジェクト固有のライセンス情報・貢献ガイドラインをここに記載してください）

---

ご不明点や README に追加したい具体的な使用例（CI/CD、運用スケジュール、Docker 化など）があればお知らせください。README をそれに合わせて拡張します。