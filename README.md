# KabuSys

KabuSys は日本株の自動売買／データプラットフォーム用のライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP スコアリング、ファクター計算、監査ログ、マーケットカレンダー管理、ならびにレジーム判定などを含む一連の機能を提供します。

---

## 主な特徴

- データ取得 (J-Quants)
  - 株価日足（OHLCV）、財務データ、上場銘柄情報、JPX カレンダーの差分取得・保存（ページネーション・レート制限・リトライ対応）
- ETL パイプライン
  - 差分更新／バックフィル、品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集 & NLP
  - RSS 収集（SSRF 対策・トラッキング除去）と OpenAI を使った銘柄ごとのニュースセンチメントスコア算出
- レジーム判定
  - ETF（1321）の 200 日 MA 乖離＋マクロニュースの LLM センチメントを合成した市場レジーム判定
- リサーチユーティリティ
  - モメンタム、ボラティリティ、バリュー等のファクター計算、将来リターン・IC・統計サマリー
- 監査ログ（トレーサビリティ）
  - シグナル → 発注 → 約定までの監査テーブル（DuckDB）を初期化・運用する機能
- マーケットカレンダー管理
  - JPX カレンダーの差分更新、営業日判定・前後営業日検索など

---

## 動作環境 / 前提

- Python 3.10 以上（型記法 Union 演算子 `|` を使用）
- DuckDB（Python パッケージ経由）
- OpenAI Python SDK を利用（ニュース/NLP/レジーム判定）
- defusedxml（RSS パーシング安全化）

推奨パッケージ（最低限）
- duckdb
- openai
- defusedxml

（プロジェクトに requirements.txt があればそちらを利用してください）

---

## セットアップ

1. リポジトリをクローン／チェックアウトし、パッケージをインストール
   - 開発環境で editable install:
     ```
     python -m pip install -e .
     ```
   - もしくは依存を直接インストール:
     ```
     python -m pip install duckdb openai defusedxml
     ```

2. 環境変数 / .env を準備
   - プロジェクトルートに `.env`（および開発用に `.env.local`）を置くと自動で読み込まれます（優先度: OS 環境変数 > .env.local > .env）。
   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須の環境変数（少なくとも以下を設定してください）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabu ステーション API のパスワード（必須）
     - OPENAI_API_KEY — OpenAI API キー（score_news / regime_detector 実行時に使用）
   - 任意 / デフォルトあり:
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用 DB、デフォルト: data/monitoring.db）
     - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
     - KABUSYS_ENV（development / paper_trading / live）  
     - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）

---

## 使い方（主な API / 実行例）

以下は代表的な利用フローと簡単なコード例です。実行前に必ず環境変数を設定してください。

- DuckDB 接続の作成（監査 DB 初期化等で利用）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（市場カレンダー → 株価 → 財務 → 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  # conn は上で作成した DuckDB 接続
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの NLP スコアリング（OpenAI API キーが必要）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  wrote = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None => 環境変数を使用
  print("書き込み銘柄数:", wrote)
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ DB 初期化（監査専用の DB ファイルを作る）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- 研究 / ファクター計算
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value
  from datetime import date

  momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
  value = calc_value(conn, target_date=date(2026, 3, 20))
  ```

- マーケットカレンダー更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job

  saved = calendar_update_job(conn)
  print("saved:", saved)
  ```

注意点:
- news_nlp / regime_detector は OpenAI の JSON mode（gpt-4o-mini）を使うため、OPENAI_API_KEY の設定が必要です。API 呼び出しは失敗に対してフォールバックやリトライ処理が入っていますが、呼び出し回数やコストに注意ください。
- ETL / データ保存は DuckDB に対して冪等（ON CONFLICT DO UPDATE）で行います。

---

## 主要モジュール（簡単説明）

- kabusys.config
  - 環境変数の読み込み・検証・設定オブジェクト（settings）
  - 自動 .env ロード（プロジェクトルート検出）

- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存関数）
  - pipeline / etl: ETL パイプライン、差分取得、run_daily_etl
  - news_collector: RSS 取得・整形・raw_news への保存（SSRF 対策）
  - calendar_management: 市場カレンダー管理と営業日判定
  - quality: データ品質チェック（欠損・スパイク・重複・日付整合性）
  - audit: 監査ログスキーマ作成 / 初期化
  - stats: zscore_normalize 等の統計ユーティリティ

- kabusys.ai
  - news_nlp: 銘柄ごとのニュースセンチメントスコア算出（OpenAI）
  - regime_detector: マクロセンチメント + ETF MA 乖離による市場レジーム判定

- kabusys.research
  - factor_research: Momentum / Volatility / Value のファクター計算
  - feature_exploration: 将来リターン計算、IC、統計サマリー、rank 等

---

## ディレクトリ構成（抜粋）

プロジェクトは `src/kabusys` 配下に実装されています。主要ファイルを抜粋すると:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/
      - __init__.py
      - jquants_client.py
      - pipeline.py
      - etl.py
      - news_collector.py
      - calendar_management.py
      - quality.py
      - audit.py
      - stats.py
      - other helper modules...
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/
    - monitoring/ (監視・実行関連モジュール想定)
    - strategy/ (戦略実装用プレースホルダ)
    - execution/ (約定関連)
    - ...（その他モジュール）

データベース（DuckDB）には以下のようなテーブル群を想定しています（一部）:
- raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, market_regime, signal_events, order_requests, executions, など

---

## 実運用上の注意

- 機密情報（API キー等）は .env や環境変数で安全に管理してください。リポジトリにコミットしないでください。
- OpenAI の呼び出しや J-Quants API 呼び出しはコスト／レート制限があります。バッチサイズや呼び出し頻度は設定に応じて調整してください。
- DuckDB のスキーマや既存データの扱いに注意してください（ETL は冪等性を考慮していますが、スキーマ変更時の互換性は保証されません）。
- 本ライブラリはバックテスト用のユーティリティと本番運用のための機能が混在しています。バックテストで使用する際は Look-ahead バイアス対策（target_date の扱い等）を遵守してください（コード内にも注記があります）。

---

必要であれば、README に次の内容を追加できます：
- 詳細な依存パッケージ一覧（requirements.txt）
- CI / テスト実行方法（pytest 等）
- 具体的な .env.example（テンプレート）
- 各テーブルのスキーマ定義ドキュメント

追加希望があれば教えてください。