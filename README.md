# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。DuckDB をデータストアとして利用し、J-Quants からのデータ取得（ETL）、ニュース収集・NLP、ファクター計算、監査ログ、マーケットカレンダー管理、及び戦略・約定周りの補助機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とするモジュール群を含むパッケージです。

- J-Quants API を用いた株価・財務・マーケットカレンダーの差分 ETL（data.pipeline）
- ニュース RSS 収集と前処理（data.news_collector）
- ニュースの LLM（OpenAI）によるセンチメントスコアリング（ai.news_nlp）
- マクロニュースと ETF の移動平均乖離を組み合わせた市場レジーム判定（ai.regime_detector）
- 研究用ファクター計算・特徴量探索（research）
- データ品質チェック、カレンダー管理、監査ログスキーマ等の運用ユーティリティ
- 設定・環境変数管理（config）

設計上の方針として、バックテスト等で Look-ahead バイアスを生まないように日付取り扱いに注意し、外部 API はリトライやレート制御を持たせるなど実運用を想定した堅牢性を重視しています。

---

## 主な機能一覧

- ETL（data.pipeline）
  - 日次 ETL 実行（株価 / 財務 / カレンダー取得、品質チェック）
  - 差分更新とバックフィル対応
- J-Quants クライアント（data.jquants_client）
  - 株価日足、財務データ、上場情報、マーケットカレンダー取得
  - レートリミット、認証トークン自動リフレッシュ、再試行ロジック
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- ニュース収集（data.news_collector）
  - RSS フィード取得、前処理、ID 正規化（SSRF 対策・トラッキング除去）
- ニュース NLP（ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメント算出（JSON Mode、バッチ処理、リトライ）
- 市場レジーム判定（ai.regime_detector）
  - ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して daily レジーム判定を行う
- 研究用ツール（research）
  - Momentum / Value / Volatility などファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- データ品質チェック（data.quality）
  - 欠損・重複・スパイク・日付不整合チェック
- カレンダー管理（data.calendar_management）
  - 営業日判定、next/prev 営業日、期間内営業日取得、JPX カレンダーの夜間更新ジョブ
- 監査ログ（data.audit）
  - signal → order_request → execution までトレース可能な監査スキーマ定義・初期化

---

## 必要条件（概略）

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - その他：標準ライブラリを中心に実装されていますが、requirements.txt を用意している場合はそちらに従ってください。

（プロジェクト環境や CI 用に pyproject.toml / requirements.txt があることを想定します）

---

## セットアップ手順

1. Python 仮想環境を作成・有効化
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージのインストール
   - プロジェクトルートで（pip のインストール方針に合わせて）
     - pip install -e .                 # ソースを編集しながら使う場合
     - または pip install -r requirements.txt

   - 必要な主要ライブラリ（例）
     - pip install duckdb openai defusedxml

3. 環境変数の設定
   - ルートに .env を置くと自動的に読み込まれます（ただしテスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD      — kabuステーション API パスワード（発注連携がある場合）
     - SLACK_BOT_TOKEN        — Slack 通知用トークン（任意の通知機能と連携する場合）
     - SLACK_CHANNEL_ID       — Slack チャンネル ID
     - OPENAI_API_KEY         — OpenAI を使う機能を有効化する場合（ai.news_nlp / ai.regime_detector）
   - 任意（デフォルトあり）:
     - KABUSYS_ENV            — development / paper_trading / live（デフォルト development）
     - LOG_LEVEL              — DEBUG/INFO/...（デフォルト INFO）
     - KABU_API_BASE_URL      — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH            — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH            — SQLite（監視用）パス（デフォルト data/monitoring.db）

   - .env の例（簡易）
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567

4. データベース初期化（監査ログ等）
   - 監査用 DB を初期化する例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")  # 必要なら親ディレクトリを作成する
     ```
   - 全体のスキーマ初期化はプロジェクトで別途用意されるスキーマ初期化関数を使ってください（例: data.schema.init_schema() のような関数がある想定）。

---

## 使い方（代表的な例）

以下は簡単な Python スニペットで、DuckDB 接続を作り ETL や NLP を実行する例です。

- DuckDB 接続の作成（設定からパス取得）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行（run_daily_etl）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントスコア取得（OpenAI API キーが必要）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026, 3, 20), api_key="your_openai_key")
  print(f"wrote scores for {written} codes")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20), api_key="your_openai_key")
  ```

- カレンダー操作のユーティリティ
  ```python
  from datetime import date
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

- RSS を取得（ニュース収集・前処理）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```
  - fetch_rss はネットワークエラーを上位に投げます。取得後、DB 保存処理（raw_news, news_symbols への紐付け等）はプロジェクト内で用意された保存処理を利用してください。

- 監査 DB 初期化（独立 DB）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  ```

---

## 知っておくべき実装上の注意点

- Look-ahead バイアス回避
  - 多くのモジュール（news_nlp, regime_detector, pipeline 等）は内部で date.today()/datetime.today() を直接参照せず、target_date を明示的に渡す設計です。バックテストや再現性のために target_date を明示的に指定してください。
- 環境変数の自動読み込み
  - パッケージはプロジェクトルート（.git または pyproject.toml が見つかる場所）から .env/.env.local を自動ロードします。テストや特殊ケースで無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し
  - ai.news_nlp と ai.regime_detector は OpenAI の Chat Completions JSON モードを使います。API 呼び出しは retry ロジックを持ちますが、API キーは安全な方法で提供してください。
- J-Quants API
  - jquants_client はレート制御・トークン自動リフレッシュを備えています。JQUANTS_REFRESH_TOKEN の設定が必須です。
- DuckDB の executemany の仕様
  - DuckDB 0.10 系では executemany に空リストを渡せないケースがあるため、実装上空リストチェックが入っています。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                — ニュースの LLM スコアリング（銘柄別）
    - regime_detector.py        — 市場レジーム判定（ETF MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント（取得・保存）
    - pipeline.py               — ETL パイプライン（run_daily_etl 等）
    - etl.py                    — ETL の結果クラス ETLResult の再エクスポート
    - news_collector.py         — RSS 取得・前処理
    - calendar_management.py    — マーケットカレンダー管理・営業日判定
    - quality.py                — データ品質チェック
    - stats.py                  — 汎用統計ユーティリティ（zscore 等）
    - audit.py                  — 監査ログスキーマ初期化・DB 作成
  - research/
    - __init__.py
    - factor_research.py        — Momentum/Value/Volatility 等ファクター計算
    - feature_exploration.py    — 将来リターン計算、IC、統計サマリー

各モジュールは docstring に設計方針・処理フローを詳細に記載しているため、実装参照時に重要な注意点や動作を把握できます。

---

## 開発・テストについて

- テストや CI では自動 env 読み込みを無効にするために KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使ってください。
- OpenAI 呼び出しやネットワーク依存部分はモック化しやすいように実装されています（例: ai.news_nlp._call_openai_api を patch 可能）。
- DuckDB はインメモリ ":memory:" をサポートしているため、単体テストはファイル I/O を避けて高速に実行可能です。

---

## ライセンス / 連絡先

（ここにプロジェクトのライセンスや連絡先を記載してください。README のテンプレートに合わせて追記してください。）

---

この README はコードの主要機能と利用方法の概要を記したものです。詳細な API 仕様や追加のユーティリティは各モジュールの docstring を参照してください。必要であればサンプルスクリプトやデプロイ手順（systemd / cron / Airflow 連携等）の追記も可能です。