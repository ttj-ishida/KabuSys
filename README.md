# KabuSys

日本株向け自動売買・データプラットフォーム用ライブラリ。  
J-Quants API / RSS / OpenAI 等を用いたデータ収集（ETL）、ニュースのAIスコアリング、ファクター計算、監査ログ管理、マーケットカレンダー管理、ならびに戦略・約定用の基盤ユーティリティを提供します。

主な設計方針：
- ルックアヘッドバイアスを防ぐため、内部で date.today() / datetime.today() を直接参照しない設計（呼び出し側で基準日を渡す）。
- DuckDB をデータストアとして使用し、ETL は冪等（ON CONFLICT）で実行。
- 外部API呼び出し（J-Quants / OpenAI 等）はレート制限・リトライ・フェイルセーフを備える。

---

## 機能一覧

- 環境設定読み込み（.env / 環境変数、自動ロード機能）
- J-Quants API クライアント
  - 株価日足（OHLCV）取得 / 保存
  - 財務データ取得 / 保存
  - JPX マーケットカレンダー取得 / 保存
  - レート制限・トークン自動リフレッシュ・リトライ
- ETL パイプライン（run_daily_etl） — カレンダー / 株価 / 財務 / 品質チェック
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（RSS）と前処理（SSRF/サイズ制限/正規化等）
- ニュース NLP（OpenAI を利用した銘柄ごとのセンチメントスコア算出）
- 市場レジーム判定（ETF 1321 の MA200＋マクロニュースセンチメント合成）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、統計サマリ）
- 監査ログ（signal_events / order_requests / executions）スキーマ初期化・DB管理
- 汎用統計ユーティリティ（Zスコア正規化 等）

---

## 必要条件

- Python 3.10 以上
- 推奨パッケージ（主なもの）:
  - duckdb
  - openai
  - defusedxml

実際のプロジェクトでは pyproject.toml / requirements.txt を参照してください。

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境の作成（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 開発インストール / 依存インストール
   - ローカル開発用にパッケージ化されている場合:
     ```bash
     pip install -e .
     ```
   - 最低限の依存を直接インストールする場合:
     ```bash
     pip install duckdb openai defusedxml
     ```

4. 環境変数の設定
   - プロジェクトルートの `.env` または `.env.local` を用意することで自動ロードが可能（デフォルトで自動ロードされます）。
   - 主要な環境変数（例）:
     ```
     JQUANTS_REFRESH_TOKEN=...
     OPENAI_API_KEY=...
     KABU_API_PASSWORD=...
     KABU_API_BASE_URL=http://localhost:18080/kabusapi
     SLACK_BOT_TOKEN=...
     SLACK_CHANNEL_ID=...
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     PID_FILE_PATH=data/execution.pid
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - 自動環境変数ロードを無効化したい場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. DuckDB 初期化（監査DB 等）
   - 例：監査DBの初期化（Python REPL やスクリプトで）
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     # conn は duckdb.DuckDBPyConnection
     ```

---

## 使い方（主要な例）

以下は最小限の呼び出し例です。各関数は DuckDB 接続と target_date を明示的に受け取るため、テストやバッチ処理で日付を固定して利用できます。

- ETL（日次）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコア（OpenAI 使用）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print("scored", n_written)
  ```

- 市場レジーム判定（OpenAI 使用）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査スキーマ初期化（既存接続に適用）
  ```python
  import duckdb
  from kabusys.data.audit import init_audit_schema

  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

- 研究用ファクター計算（例：モメンタム）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

注意点：
- OpenAI / J-Quants API を使う関数は api_key / refresh token が必要です（引数経由または環境変数）。
- 多くの処理は冪等的に実行されるよう設計されています（ON CONFLICT DO UPDATE 等）。
- API 呼び出しはリトライやバックオフ、レート制御が組み込まれています。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
- KABU_API_PASSWORD: kabuステーション API のパスワード
- KABU_API_BASE_URL: kabuステーション API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視DBなど（デフォルト data/monitoring.db）
- KABUSYS_ENV: development | paper_trading | live
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化する場合は 1 をセット

---

## ディレクトリ構成（抜粋）

（実装に含まれる主なモジュール / ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースのAIスコアリング（score_news）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch/save）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult 再エクスポート
    - quality.py             — データ品質チェック
    - news_collector.py      — RSS ニュース収集
    - calendar_management.py — マーケットカレンダー管理
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログスキーマ & 初期化
  - research/
    - __init__.py
    - factor_research.py     — ファクター計算（momentum / value / volatility）
    - feature_exploration.py — 将来リターン / IC / サマリ 等
  - ai, research, data のほか strategy / execution / monitoring 等のパッケージが想定されます（__init__.py の __all__ を参照）。

---

## 設計上の注意・運用メモ

- Look-ahead バイアス防止：ほとんどの処理は対象日（target_date）を引数で受け取り、内部で現在時刻を参照しないようにしています。バックテストや再現性を重視する際は必ず target_date を固定してください。
- 冪等性：ETL / 保存関数は ON CONFLICT による上書きを行うため、同一処理を複数回実行しても整合性が保たれるように設計されています。
- レート制限：J-Quants API の呼び出しは内部的にレート制御しています（120 req/min）。OpenAI にはリトライ/バックオフ処理がありますが、利用側でもAPI制限に留意してください。
- セキュリティ：news_collector は SSRF 対策・受信サイズ制限・XML 脆弱性対策（defusedxml）を行っています。外部URLを扱う際はこれらの仕組みを尊重してください。

---

## 開発・寄稿

- コントリビュートや機能追加は Issue / PR ベースで受け付けてください。  
- テスト時は環境自動ロードを無効化するために `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると便利です。
- 外部API呼び出し部分はモックしやすいように内部呼び出しを分離しているため、ユニットテストで差し替えてください（例: news_nlp._call_openai_api を patch）。

---

何か追加したい項目や、README の例を実際のスクリプト/CI 向けに拡張したい場合は教えてください。