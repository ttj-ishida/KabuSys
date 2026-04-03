# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
DuckDB をバックエンドにして J-Quants などからデータを取得・保存し、ニュースの NLP スコアリングや市場レジーム判定、ファクター計算・リサーチユーティリティ、監査ログ等の機能を提供します。

バージョン: 0.1.0

---

## 主要機能（概要）

- ETL（データ取得・保存・品質チェック）
  - J-Quants から株価（日足）、財務、マーケットカレンダーを差分取得して DuckDB に永続化
  - 品質チェック（欠損・スパイク・重複・日付不整合）を実行
- ニュース NLP（OpenAI）
  - RSS 収集→前処理→銘柄ごとにまとめて LLM（gpt-4o-mini）でセンチメント評価 → ai_scores に保存
- 市場レジーム判定（Regime Detector）
  - ETF（1321）200日移動平均乖離とマクロニュースの LLM センチメントを合成して日次でレジーム判定（bull/neutral/bear）
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions などの監査テーブル定義・初期化ユーティリティ
- 研究用ユーティリティ（Research）
  - ファクター計算（モメンタム・バリュー・ボラティリティ等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、正規化ユーティリティ
- マーケットカレンダー管理（JPX）
  - 営業日判定 / next_trading_day / prev_trading_day / get_trading_days 等
- セキュリティ考慮
  - RSS の SSRF 対策、defusedxml を使った XML パース、レスポンスサイズ上限など

---

## 必要条件

- Python 3.10 以上（typing の新構文を利用）
- 必要な主要パッケージ（例）
  - duckdb
  - openai（OpenAI Python SDK、新 SDK の OpenAI クライアントを利用）
  - defusedxml
- ネットワークアクセス（J-Quants API / OpenAI / RSS ソース 等）

（プロジェクトの packaging / requirements.txt がある場合はそちらを参照してください）

---

## 環境変数 / .env

パッケージはプロジェクトルートの `.env` / `.env.local`（優先度：OS環境 > .env.local > .env）を自動ロードします。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数：

- J-Quants
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- OpenAI
  - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime に使用）
- kabu ステーション API
  - KABU_API_PASSWORD (必須) — kabu API 用パスワード
  - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- LINE 通知（任意）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID
- データベース / パス
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — デフォルト: data/monitoring.db
- 監視関連
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- 実行環境
  - KABUSYS_ENV — 有効値: development / paper_trading / live （デフォルト development）
  - LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL

`.env.example` を参考に `.env` を作成してください（リポジトリに例ファイルがある想定）。

---

## セットアップ手順（例）

1. Python 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 必要パッケージのインストール（例）
   - pip install duckdb openai defusedxml

   （実際はプロジェクトの requirements.txt / pyproject.toml を使ってください）

3. 環境変数設定
   - プロジェクトルートに `.env` を作成し、必要なキーを設定する
     ```
     JQUANTS_REFRESH_TOKEN=...
     OPENAI_API_KEY=...
     KABU_API_PASSWORD=...
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. DuckDB（監査 DB 等）の初期化（任意）
   - 例: 監査テーブルを初期化する
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     conn.close()
     ```
   - メインデータベースは設定した `DUCKDB_PATH` に対して利用することが多いです。

---

## 基本的な使い方（サンプル）

以下はライブラリをプログラムから利用する簡単な例です。各関数は DuckDB 接続を受け取りますので、まず接続を作成してください。

- ETL（日次 ETL の実行）
  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  conn.close()
  ```

- ニュース NLP スコアリング（score_news）
  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  n = score_news(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは OPENAI_API_KEY を参照
  print("書き込み銘柄数:", n)
  conn.close()
  ```

- 市場レジーム判定（score_regime）
  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  conn.close()
  ```

- 監査スキーマ初期化（既述）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn をそのまま監査ログ用に使う
  ```

注意:
- score_news / score_regime は OpenAI API を呼びます。API キーは引数で渡すこともできます（api_key パラメータ）。
- 各モジュールはルックアヘッドバイアス防止のため、内部で date.today() を参照しない設計になっています（target_date を明示的に渡すことが推奨されます）。

---

## 開発上のポイント / 挙動

- 自動環境変数読み込み:
  - パッケージロード時にプロジェクトルート（.git または pyproject.toml がある親ディレクトリ）を探索し、`.env` と `.env.local` を読み込みます。テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
- DuckDB に対する書き込みは可能な限り冪等（ON CONFLICT / DELETE → INSERT など）を意識しています。
- OpenAI 呼び出しは JSON Mode を利用し、失敗時はフェイルセーフ（多くの場合 0.0 フォールバック）を採用しています。
- RSS 収集には SSRF 防止 / レスポンス上限 / XML 攻撃対策が実装されています。

---

## ディレクトリ構成（主要ファイル）

下記はリポジトリ内の主要モジュールの抜粋です（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                 — ニュース NLP（score_news）
    - regime_detector.py          — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py           — J-Quants API クライアント・保存ロジック
    - pipeline.py                 — ETL パイプライン（run_daily_etl 等）
    - etl.py                      — ETL 公開 API（ETLResult の再エクスポート）
    - news_collector.py           — RSS 収集・前処理
    - calendar_management.py      — マーケットカレンダー管理
    - quality.py                  — データ品質チェック
    - stats.py                    — 統計ユーティリティ（zscore_normalize）
    - audit.py                    — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py          — ファクター計算（momentum / value / volatility）
    - feature_exploration.py      — 将来リターン / IC / summary utilities
  - ai/ (上記)
  - その他: strategy / execution / monitoring 等（パッケージ公開対象として __all__ に含まれる）

（実際のリポジトリにはさらにユーティリティや補助モジュールが存在する可能性があります）

---

## 注意事項 / ベストプラクティス

- OpenAI / J-Quants API の利用はそれぞれの利用規約・コストに注意してください（API キー管理）。
- バックテストや研究ではルックアヘッドバイアスに注意してください：本ライブラリはその防止に配慮した実装を行っていますが、使用側でも target_date を明示的に固定する等の注意が必要です。
- 本 README はコードベースの主要点をまとめたものです。内部仕様や細かい挙動は各モジュールの docstring を参照してください。

---

必要であれば、インストール手順を pyproject.toml / requirements.txt ベースでの具体例や、ユニットテストの実行方法、よく使う CLI スクリプト（もしあれば）の記載も追加します。どの情報を優先して追記しますか？