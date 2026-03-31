# KabuSys

日本株向けの自動売買／データ基盤ライブラリ（KabuSys）のリポジトリ向け README。

本プロジェクトは J-Quants / kabuステーション / OpenAI を組み合わせたデータ収集・品質管理・ニュースNLP・レジーム判定・リサーチ用ユーティリティ群を提供します。内部的には DuckDB を用いたローカルデータ基盤と、監査（audit）テーブルによるトレーサビリティを重視しています。

---

## 機能一覧

- 環境変数 / .env 管理（自動ロード、設定検証）
- J-Quants API クライアント
  - 日次株価（OHLCV）取得・保存（ページネーション対応、レート制御、トークン自動リフレッシュ）
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存
- ETL パイプライン（差分取得、バックフィル、品質チェック統合）
- データ品質チェック（欠損、スパイク、重複、日付整合性）
- ニュース収集（RSS -> raw_news 保存、SSRF 対策、正規化）
- ニュース NLP（OpenAI を使った銘柄別センチメントスコアリング）
- 市場レジーム判定（ETF 1321 の MA とニュースセンチメント合成）
- 監査ログ（signal / order_request / executions テーブルを初期化）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC 計算、Z-score 正規化 等）
- 汎用統計ユーティリティ

---

## 前提（推奨）

- Python 3.10+
- DuckDB（Python パッケージ）
- ネットワーク接続（J-Quants API、OpenAI、RSS ソース等）
- OpenAI API キー（ニュース NLP / レジーム判定で使用）

---

## セットアップ手順

1. リポジトリをクローンしてパッケージをインストール（開発モード）
   ```bash
   git clone <repo-url>
   cd <repo>
   pip install -e .
   ```
   または依存を直接インストールする場合:
   ```bash
   pip install duckdb openai defusedxml
   ```

2. 環境変数（または .env）を設定する  
   自動的にプロジェクトルートの `.env` → `.env.local` を読み込みます（CWD 依存せず __file__ ベースでルートを探索）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須環境変数（少なくとも以下を設定してください）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション連携用パスワード
   - SLACK_BOT_TOKEN: Slack 通知用トークン（必要に応じて）
   - SLACK_CHANNEL_ID: Slack チャンネル ID
   - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 用）

   推奨（オプション）:
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 sqlite パス（デフォルト: data/monitoring.db）

   例 `.env`（テンプレート）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

3. DuckDB スキーマの初期化（監査ログ等）  
   監査用 DB を新規作成してテーブルを初期化する例:
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # conn は duckdb.DuckDBPyConnection
   ```

---

## 使い方（簡単な例）

以下は主要な操作の呼び出し例（Python スクリプトから実行）。

- 日次 ETL を実行する
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 19))
  print(result.to_dict())
  ```

- ニュース NLP（銘柄別スコアリング）を実行する
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 19))
  print("書き込んだ銘柄数:", written)
  ```

- 市場レジーム判定を実行する
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 19))  # OpenAI API キーは環境変数で
  ```

- 監査スキーマを既存接続に追加する（トランザクション指定可能）
  ```python
  from kabusys.data.audit import init_audit_schema
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

- 研究用ユーティリティ（ファクター計算）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026, 3, 19))
  # momentum: list[dict]（date, code, mom_1m, mom_3m, mom_6m, ma200_dev）
  ```

注意点:
- すべての関数はルックアヘッドバイアスを避ける設計（内部で datetime.today() を参照しない）になっています。バックテストや再現性のために必ず target_date を明示してください。
- OpenAI 呼び出しはネットワークエラーや 5xx に対してリトライ・フェイルセーフを備えていますが、API キーが未設定だと ValueError になります。

---

## ディレクトリ構成（主要ファイルと概要）

（src/kabusys 以下）

- __init__.py
  - パッケージのエクスポート定義（data, strategy, execution, monitoring 等）
- config.py
  - 環境変数/.env 管理と Settings クラス（必須設定の検証）
- ai/
  - __init__.py
  - news_nlp.py: ニュースを OpenAI でスコアリングして ai_scores に保存する処理
  - regime_detector.py: ETF MA とニュースセンチメントを合成して市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py: J-Quants API クライアント（取得/保存ロジック）
  - pipeline.py: ETL の統合エントリポイント（run_daily_etl, run_prices_etl 等）
  - etl.py: ETLResult の公開再エクスポート
  - news_collector.py: RSS 取得と raw_news への保存（SSRF 対策・前処理）
  - calendar_management.py: JPX カレンダー管理・営業日判定・更新ジョブ
  - quality.py: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py: Z-score 正規化など汎用統計ユーティリティ
  - audit.py: 監査ログ（signal / order_requests / executions）の DDL と初期化処理
- research/
  - __init__.py
  - factor_research.py: Momentum / Value / Volatility 等のファクター計算
  - feature_exploration.py: 将来リターン・IC・統計サマリー等の研究ユーティリティ

（その他）
- data/ 以下のデータファイル（DuckDB ファイルや sqlite）はデフォルトで data/ に格納する想定（設定で変更可能）。

---

## 運用上の注意

- 環境変数や .env に秘密情報（API キー等）を含める場合は Git にコミットしないでください。
- J-Quants API のレート制限（120 req/min）を厳守するためモジュールでレート制御を行っていますが、外部から大量の並列呼び出しをしないでください。
- OpenAI の呼び出しはコストがかかります。バッチサイズやモデル（デフォルト gpt-4o-mini）を運用に合わせて調整してください。
- DuckDB の executemany に空リストが渡せないバージョンの互換性に合わせた実装パターンがあります（空チェックが行われます）。

---

必要であれば、README にサンプル .env.example を追加したり、CI / 実行スクリプト（cron、airflow、systemd ユニット等）の例を追記します。どの項目を詳細化したいか教えてください。