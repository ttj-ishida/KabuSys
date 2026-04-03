# KabuSys

日本株向け自動売買・データプラットフォームライブラリ

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買および研究用データプラットフォーム向けのライブラリ群です。  
J-Quants API を用いたデータ ETL、ニュース収集と LLM（OpenAI）によるニュース/NLP スコアリング、マーケットレジーム判定、
ファクター計算・探索、監査ログ（発注から約定までのトレーサビリティ）、および各種データ品質チェックを提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で日付の自動参照を行わない）
- DuckDB を中心としたローカルデータストアに冪等に保存
- 外部 API 呼び出しにはリトライ・バックオフ・レート制御を導入
- LLM 呼び出しは JSON Mode で厳密にパースしフェイルセーフ化

---

## 機能一覧

- 環境変数・設定管理（kabusys.config）
  - .env, .env.local の自動読み込み（プロジェクトルート検出）
  - 必須値チェック・型変換ユーティリティ

- データ ETL（kabusys.data.pipeline / jquants_client）
  - J-Quants API から株価日足・財務・マーケットカレンダーを差分取得・保存
  - 差分取得、バックフィル、品質チェック（欠損・スパイク・重複・日付整合性）

- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、URL 正規化、SSRF 制御、前処理、raw_news への冪等保存

- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメントスコア化（ai_scores へ保存）
  - バッチ処理、チャンク化、リトライ、レスポンス検証

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF(1321) の MA200 乖離とマクロニュース LLM センチメントを合成して日次で bull/neutral/bear を判定・保存

- 研究用ファクター計算（kabusys.research）
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー、Z-score 正規化ユーティリティ

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブルを生成する初期化ユーティリティ
  - 監査用 DuckDB データベース初期化関数

- 汎用統計ユーティリティ（kabusys.data.stats）
  - Zスコア正規化等

---

## セットアップ手順

想定環境:
- Python 3.10 以上（型注釈の `X | Y` 構文を利用）
- DuckDB, OpenAI Python SDK, defusedxml 等の依存

推奨手順（ローカル開発）:

1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   例（最低限）:
   - pip install duckdb openai defusedxml

   実際のプロジェクトでは requirements.txt / pyproject.toml に依存管理を置くことを推奨します。

3. 環境変数 (.env) を用意
   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を置くと自動読み込みされます。
   自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   推奨 .env の例:
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # OpenAI（score_news / regime_detector 実行時に参照）
   OPENAI_API_KEY=sk-...

   # kabuステーション関連（発注等を行う場合）
   KABU_API_PASSWORD=your_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # LINE 通知（任意）
   LINE_CHANNEL_ACCESS_TOKEN=
   LINE_USER_ID=

   # データベースパス
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

4. DuckDB の初期スキーマ作成（使用するモジュールに応じて）
   - 監査ログ専用 DB を初期化する例:
     ```
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```

---

## 使い方（主要な利用例）

以下はライブラリの代表的な使い方例です。実行前に `.env` 等で API キーや DB パスを準備してください。

- DuckDB 接続を作成して日次 ETL を実行する
  ```
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（銘柄別スコア）を実行する
  ```
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY は環境変数か api_key 引数で渡す
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print("書き込み銘柄数:", n_written)
  ```

- 市場レジーム判定を実行する
  ```
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB の初期化（別 DB）
  ```
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- 設定値の参照
  ```
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live, settings.log_level)
  ```

注意点:
- OpenAI 呼び出し時は API レスポンスのバリデーションやリトライが組み込まれていますが、API キー・利用上限に注意してください。
- ETL / API 呼び出し系はネットワークアクセスを行うため、実行環境のネットワーク設定（プロキシ等）に注意してください。
- DuckDB のバージョンや SQL 方言に依存する箇所があるため、動作確認時は DuckDB の互換性に注意してください。

---

## 主要ディレクトリ構成

ここではリポジトリ内の主要ファイル/モジュールを示します（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（銘柄別スコア化）
    - regime_detector.py     — 市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py — マーケットカレンダー管理（営業日判定等）
    - etl.py                 — ETL インターフェース再エクスポート
    - pipeline.py            — 日次 ETL パイプライン（run_daily_etl 等）
    - stats.py               — 統計ユーティリティ（Z-score 等）
    - quality.py             — データ品質チェック
    - audit.py               — 監査ログ（テーブル作成 / 初期化）
    - jquants_client.py      — J-Quants API クライアント（取得 & DuckDB 保存）
    - news_collector.py      — RSS ニュース収集・前処理
  - research/
    - __init__.py
    - factor_research.py     — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー 等
  - monitoring/ (存在が __all__ にあるが実装ファイルはここに含まれている可能性があります)

各モジュールはドキュメント文字列（docstring）で設計要件や注意点が詳述されています。実装関数群はDuckDBコネクションを受け取る設計で、外部副作用（発注等）を限定的に行うよう配慮されています。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- OPENAI_API_KEY — OpenAI API キー（score_news / regime_detector で利用）
- KABU_API_PASSWORD — kabu API パスワード（発注連携がある場合）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知（任意）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（モニタリング用）パス
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START — 実行/監視用

必須の値が未設定の場合、kabusys.config.Settings のプロパティ呼び出しで ValueError が発生します。

---

## 開発・テストに関する補足

- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml がある場所）から行われます。テスト中に自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出し関数はユニットテストで差し替え（mock）しやすいように内部呼び出しを分離しています（例: news_nlp._call_openai_api をパッチ可能）。
- DuckDB の executemany に空リストを渡せない制約を考慮した実装箇所があります（互換性に注意）。

---

README に記載のない内部 API や追加設定は、該当モジュールの docstring を参照してください。何か特定の使い方（例: 発注フローの実装、監視スクリプト、Docker 化等）について詳細が必要であれば知らせてください。