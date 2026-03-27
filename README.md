# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
J-Quants（株価・財務・カレンダー）からのデータ取得・ETL、ニュース収集とLLMによるニュースセンチメント、マーケットレジーム判定、リサーチ（ファクター計算）や監査ログ（トレース可能な発注/約定履歴）などを提供します。

--- 

目次
- プロジェクト概要
- 主な機能
- 必要な環境変数
- セットアップ手順
- 基本的な使い方（例）
- ディレクトリ構成（主要ファイル）
- 補足（自動 .env ロード等）

---

## プロジェクト概要

KabuSys は日本株の自動売買基盤およびデータプラットフォーム向けユーティリティ群です。  
主に以下を目的としています。

- J-Quants API からの差分取得・保存（DuckDB へ冪等保存）
- ニュースの収集・前処理・LLMによる銘柄別センチメントスコア付与
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- 研究用途のファクター計算、将来リターンやIC計算
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- 監査ログ（signal → order_request → execution）のスキーマと初期化ユーティリティ

コードはモジュール化され、ETL・データ処理は DuckDB 接続を受け取って動作するため、テスト・バッチ実行・研究ノート等で簡単に組み込めます。

---

## 主な機能（抜粋）

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（認証、取得、DuckDB への保存）
  - カレンダー管理（営業日判定、next/prev_trading_day）
  - ニュース収集（RSS 取得、前処理、SSRF 対策）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ初期化（init_audit_db / init_audit_schema）
  - 汎用統計ユーティリティ（zscore 正規化）
- ai/
  - ニュース NLP（score_news：銘柄ごとに LLM でセンチメントを算出して ai_scores に書き込み）
  - 市場レジーム判定（score_regime：ETF 1321 の MA 乖離とマクロニュースを合成）
- research/
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 特徴量解析（将来リターン計算 / IC / 統計サマリー）
- 設定管理
  - settings（.env 自動読込機能を備え、必要な env をラップ）

---

## 必要な環境変数

実行に最低限必要な主要変数（例）:

- JQUANTS_REFRESH_TOKEN - J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD - kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN - Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID - Slack チャンネル ID（必須）
- OPENAI_API_KEY - OpenAI 呼び出しに使用（score_news, score_regime などで使用）
- DUCKDB_PATH - デフォルトの DuckDB ファイルパス（省略時: data/kabusys.duckdb）
- SQLITE_PATH - 監視用 SQLite パス（省略時: data/monitoring.db）
- KABUSYS_ENV - 環境 (development | paper_trading | live)（省略時: development）
- LOG_LEVEL - ログレベル（DEBUG/INFO/...、省略時 INFO）

ヒント:
- プロジェクトルートに `.env` / `.env.local` を置くと、自動でロードされます（ただしテスト時などに無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

---

## セットアップ手順

前提:
- Python 3.10 以上（PEP 604 の | 型注釈や組み込みジェネリック表記を使用）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

1. 仮想環境作成・アクティベート（例）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 依存パッケージをインストール
   - 本リポジトリに requirements.txt がない場合は必要な主要パッケージを手動インストールします:
     ```
     pip install duckdb openai defusedxml
     ```
   - 他に urllib系は標準ライブラリで賄われます。

3. リポジトリをインストール（開発モード）
   ```
   pip install -e .
   ```
   ※ setup 配置が無い場合は、プロジェクト直下で Python の import パスが正しく通るようにしてください（PYTHONPATH を通すか、パッケージ化）。

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、OS 環境変数として設定します。
   - 例 (.env):
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

5. DuckDB 初期スキーマ（監査スキーマなど）の初期化
   - 監査ログ専用 DB を作る例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     # 必要なら conn.execute(...) で他スキーマやテーブルを作成
     conn.close()
     ```
   - ETL 用の共通 DuckDB に対しては、アプリ側でスキーマ作成用ユーティリティを呼んでください（本リポジトリのスキーマ初期化関数等を利用）。

---

## 使い方（簡単な例）

以下はライブラリ関数の呼び出し例です。実行前に環境変数や DuckDB の接続準備をしてください。

- 日次 ETL を実行（DuckDB 接続を渡す）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  conn.close()
  ```

- ニュースのセンチメントスコアを生成（OpenAI API key が必要）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None で環境変数を使用
  print(f"ai_scores に書き込んだ銘柄数: {written}")
  conn.close()
  ```

- 市場レジーム判定を実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  conn.close()
  ```

- 監査 DB の初期化（監査専用 DB を作る）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # テーブルが作成され、UTC タイムゾーン設定が適用されます
  conn.close()
  ```

- J-Quants API を直接呼んでデータを取得する
  ```python
  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
  token = get_id_token()  # settings.jquants_refresh_token を参照
  recs = fetch_daily_quotes(id_token=token, date_from=date(2026,1,1), date_to=date(2026,3,1))
  ```

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を想定）

- __init__.py
  - パッケージ名と __version__
- config.py
  - .env 自動ロード・settings ラッパー（必須 env の検証）
- ai/
  - __init__.py
  - news_nlp.py — ニュースの LLM スコアリング（score_news）
  - regime_detector.py — ETF MA とマクロニュースを合成した市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存・認証・レート制御）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）、ETLResult
  - etl.py — ETL の公開インターフェース（ETLResult 再エクスポート）
  - news_collector.py — RSS 収集 / 前処理 / SSRF 対策
  - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付整合性）
  - stats.py — zscore_normalize など共通統計ユーティリティ
  - audit.py — 監査ログ（signal, order_requests, executions）スキーマ初期化
- research/
  - __init__.py
  - factor_research.py — Momentum / Value / Volatility 等のファクター計算
  - feature_exploration.py — 将来リターン・IC・統計サマリー等
- その他（将来的に strategy / execution / monitoring モジュールを含む可能性あり）

---

## 補足情報

- .env の自動読込はプロジェクトルート（.git または pyproject.toml のある階層）を基準に行われます。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- LLM（OpenAI）呼び出しはリトライやフェイルセーフを備えていますが、APIキーの設定や課金設定はユーザ側で行ってください。API 失敗時はフォールバック（0.0 のスコア等）を行い、処理を継続します。
- DuckDB の executemany に関する注意点（バージョン互換性）や、ETL の冪等性（ON CONFLICT DO UPDATE）など、実運用に便利な設計方針が各モジュールに組み込まれています。
- テスト時には env 自動読み込みを無効化し、OpenAI 呼び出しやネットワーク I/O をモックする想定で実装されています（内部の _call_openai_api 等は差し替え可能）。

---

必要であれば、この README をプロジェクトの pyproject.toml / requirements.txt に合わせて調整したり、典型的な .env.example を追加したり、よく使うコマンド（ETL cron 起動例、監視ジョブ、Slack 通知のセットアップ手順）を追記します。どの部分を詳しくしたいか教えてください。