# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
ETL、ニュース収集・NLP（OpenAI 経由）、ファクター計算、監査ログ、マーケットカレンダーなどを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的とした Python コンポーネント群です。

- J-Quants API から株価・財務・市場カレンダーを差分取得して DuckDB に格納する ETL
- RSS ベースのニュース収集と前処理 / 銘柄紐付け
- OpenAI（gpt-4o-mini 等）を使ったニュースのセンチメント分析（銘柄単位）およびマクロセンチメントを用いた市場レジーム判定
- ファクター計算（モメンタム / バリュー / ボラティリティ等）およびリサーチ用ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 約定まで追跡可能な監査ログ（監査テーブルの初期化・管理）
- kabuステーション / LINE 等の設定を環境変数で管理できる設定ユーティリティ

設計上の特徴：
- Look-ahead bias を避けるため、内部処理で date.today()/datetime.today() を不用意に参照しない設計
- DuckDB を中心としたローカル分析・保存
- OpenAI / J-Quants など外部 API 呼び出しに対するリトライ・バックオフ・フェイルセーフ処理を実装

---

## 主な機能一覧

- データ取得／ETL
  - 日次 ETL（market calendar / prices / financials）: kabusys.data.pipeline.run_daily_etl
  - J-Quants クライアント（ページネーション・レート制御・トークンリフレッシュ）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- ニュース関連（NLP）
  - RSS 取得・前処理・記事ID正規化（SSRF対策・トラッキング除去）
  - 銘柄ごとのニュース統合スコアリング: kabusys.ai.news_nlp.score_news
  - 市場レジーム判定（ETF1321のMA200乖離 + マクロセンチメント）: kabusys.ai.regime_detector.score_regime

- 研究 / ファクター
  - モメンタム / バリュー / ボラティリティの計算: kabusys.research.factor_research
  - 将来リターン計算・IC（スピアマン）計算・統計サマリー: kabusys.research.feature_exploration
  - Zスコア正規化ユーティリティ: kabusys.data.stats.zscore_normalize

- データ品質とカレンダー管理
  - 品質チェック（欠損 / スパイク / 重複 / 日付不整合）
  - JPX カレンダーの取得・判定ユーティリティ（is_trading_day 等）

- 監査ログ（audit）
  - signal_events, order_requests, executions 等のテーブル定義／初期化
  - init_audit_db で監査専用 DuckDB を初期化可能

- 設定管理
  - .env / .env.local をプロジェクトルートから自動読み込み（プロジェクトルートは .git または pyproject.toml を基準）
  - 環境変数に基づく Settings クラス (kabusys.config.settings)

---

## セットアップ手順

前提: Python 3.9+（一部 typing 機能に依存）を想定（実行環境に合わせて調整してください）。

1. リポジトリをクローンして開発インストール
   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -e ".[dev]"    # requirements を setup.cfg/pyproject に合わせて用意している想定
   ```
   必須パッケージ（例）:
   - duckdb
   - openai
   - defusedxml
   - （標準ライブラリ以外は requirements.txt / pyproject.toml を参照してください）

2. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` を置くと自動読み込みされます。
   - 読み込み順序: OS 環境変数 > .env.local > .env
   - 自動読み込みを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須の環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ETL 実行に必要）
     - KABU_API_PASSWORD : kabuステーション API のパスワード（実運用で必要）
   - OpenAI 利用時:
     - OPENAI_API_KEY : LLM 呼び出しに必要（news_nlp, regime_detector）
   - 省略可能 / デフォルト値あり:
     - KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL : INFO 等（デフォルト: INFO）
     - DUCKDB_PATH / SQLITE_PATH / PID_FILE_PATH など（デフォルトは src 内 Settings を参照）

   Settings クラスのプロパティは kabusys.config.settings 経由で参照できます。

3. データベースディレクトリ作成（必要なら）
   - デフォルトの DuckDB パスは `data/kabusys.duckdb`。親ディレクトリを作っておくと便利です。

---

## 使い方（簡単なコード例）

以下は代表的なユースケースの簡単な使用例です。実運用ではエラーハンドリング・ログ設定・スケジューラを組み合わせてください。

- DuckDB 接続を作って日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（OpenAI API キーが必要）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY を環境変数に設定しておくか、api_key 引数で渡す
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込んだ銘柄数: {n_written}")
  ```

- 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査 DB の初期化
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/monitoring_audit.duckdb")
  # テーブルが作成され、UTC タイムゾーンが設定されます
  ```

- 設定参照
  ```python
  from kabusys.config import settings

  print(settings.duckdb_path)   # Path object
  print(settings.env)           # 'development' / 'paper_trading' / 'live'
  ```

---

## 主要な環境変数（まとめ）

最低限設定が必要なキー:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用
- KABU_API_PASSWORD (必須) — kabuステーション API 用

OpenAI 関連:
- OPENAI_API_KEY — AI スコアリングに必要（news_nlp, regime_detector）

オプション・よく使う設定:
- KABUSYS_ENV (development | paper_trading | live) — 動作モード（デフォルト: development）
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — ログレベル
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視用 sqlite のパス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — .env 自動ロードを無効化

監視しきい値（デフォルトは Settings 内の値を参照）:
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py  — 環境変数 / Settings の読み込み
    - ai/
      - __init__.py
      - news_nlp.py         — 銘柄ごとのニュース NLP スコア
      - regime_detector.py  — 市場レジーム判定（ETF1321 + マクロ）
    - data/
      - __init__.py
      - jquants_client.py   — J-Quants API クライアント（取得・保存）
      - pipeline.py         — ETL パイプライン（run_daily_etl 等）
      - etl.py              — ETLResult の再エクスポート
      - news_collector.py   — RSS 取得・前処理・保存
      - calendar_management.py — 市場カレンダー管理・営業日判定
      - quality.py          — データ品質チェック
      - stats.py            — 共通統計ユーティリティ（zscore_normalize 等）
      - audit.py            — 監査ログ（DDL/初期化）
    - research/
      - __init__.py
      - factor_research.py  — モメンタム・バリュー・ボラティリティ
      - feature_exploration.py — 将来リターン / IC / 統計サマリー
    - ai/ (上記)
    - research/ (上記)
    - ... その他モジュール（strategy / execution / monitoring を想定する __all__）

---

## 設計上の注意点 / 運用上のポイント

- Look-ahead bias 回避:
  - レコード取得やスコアリングは target_date を明示して実行し、内部で現在日時に依存しない実装になっています。バックテストで使用する場合は ETL がバックテスト開始時点までのデータを保持していることを確認してください。

- OpenAI / 外部 API:
  - API キーは環境変数または関数引数で与えます。呼び出しはリトライ・バックオフ付きで行われ、失敗時は「安全なフォールバック（例えばスコア 0.0）」を取る実装です。ただし過剰なコスト発生やレート制限に注意してください。

- DB 書き込みは冪等設計:
  - save_* 関数は ON CONFLICT で更新するため再実行可能ですが、部分失敗時の整合性を考慮した上でスケジューラ等で運用してください。

- セキュリティ:
  - news_collector は SSRF 対策、XML パースの安全化（defusedxml）を行っています。RSS ソースは信頼できるものを設定してください。

---

## 例: よくある操作コマンド（参考）

- 日次 ETL を cron / systemd タスクで回す際の最小イメージ:
  - 仮想環境を有効化して Python スクリプトを実行し、ログを保存する

- News / AI スコアを定期実行:
  - score_news を ETL の直後に呼ぶことで当日日付分のニュースをスコア化する

---

README はここまでです。実際に導入する際は pyproject.toml / requirements.txt / .env.example を整備し、CI／デプロイ手順や運用手順（監視・ローテーション・バックアップ等）を追加で作成することを推奨します。必要であれば README に含めるサンプル .env.example や具体的な systemd / cron 設定のテンプレートも作成します。どの追加情報が必要か教えてください。