# KabuSys

日本株向けの自動売買 / データ基盤ライブラリセットです。  
データ収集（J-Quants / RSS）、ETL、データ品質チェック、ファクター計算、LLM を使ったニュースセンチメント、マーケットレジーム判定、監査ログ（発注→約定トレーサビリティ）など、トレーディング・パイプラインの主要機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は次のような機能をモジュール別に提供します。

- data: J-Quants API クライアント、ETL パイプライン、マーケットカレンダー、ニュース収集、データ品質チェック、監査ログの初期化など
- research: ファクター（モメンタム、バリュー、ボラティリティ）計算、将来リターン / IC / 統計サマリー
- ai: OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄毎）および市場レジーム判定
- config: 環境変数/.env からの設定読み込みと settings オブジェクト
- その他: 実行／監視／発注周りのインタフェース（パッケージ化のための __all__ 定義等）

設計上の注意点（主要な方針）:
- Look-ahead bias を避けるために内部で date.today() などを無闇に参照しない。
- DuckDB を用いたローカルデータベース中心の設計。
- API 呼び出しにはリトライ・バックオフ・レート制御を実装。
- ETL/品質チェックはフェイルセーフ（ステップ単位でエラーを集約・報告）。

---

## 主な機能一覧

- J-Quants API クライアント（fetch / save の実装、ページネーション、401 自動リフレッシュ、レートリミット）
- ETL（差分取得・バックフィル・品質チェックの自動化）
- 市場カレンダー管理（JPX カレンダーの保存と営業日判定ユーティリティ）
- ニュース収集（RSS → raw_news、SSRF 対策・トラッキング除去・整形）
- ニュース NLP（gpt-4o-mini を使った銘柄別センチメント集計）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM スコアを合成）
- 研究用ユーティリティ（ファクター計算、forward returns、IC、Z スコア正規化）
- 監査ログスキーマ（signal_events / order_requests / executions）と初期化ユーティリティ
- データ品質チェック（欠損、スパイク、重複、日付不整合）

---

## セットアップ手順

1. 前提
   - Python 3.10 以上（typing の「|」表記や型ヒントを使用）
   - DuckDB（Python パッケージ duckdb）
   - OpenAI Python SDK（OpenAI を使う機能を利用する場合）
   - defusedxml（ニュース RSS パースの安全化）
   - ネットワークアクセス（J-Quants / RSS / OpenAI へアクセスするため）

2. インストール（例）
   - 仮想環境の作成と有効化
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
   - 依存パッケージのインストール（requirements.txt がある想定）
     - pip install -r requirements.txt
     - 依存リストがない場合の最低例:
       - pip install duckdb openai defusedxml

   - パッケージを開発モードでインストール（作業用）
     - pip install -e .

3. 環境変数 / .env
   - プロジェクトルートに `.env` または `.env.local` を置くと、自動で読み込まれます（OS 環境変数は優先）。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 必須の環境変数（少なくとも以下は設定が必要）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション等の API パスワード
     - SLACK_BOT_TOKEN — Slack 通知に使用する Bot トークン
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
     - OPENAI_API_KEY — OpenAI を使う機能で必要（score_news, score_regime）
   - オプション／デフォルト:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG/INFO/...) — デフォルト: INFO
     - DUCKDB_PATH (例: data/kabusys.duckdb) — デフォルト
     - SQLITE_PATH (例: data/monitoring.db)
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

   - 簡易 .env 例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     OPENAI_API_KEY=sk-xxxxx
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-xxxxx
     SLACK_CHANNEL_ID=C0123456789
     DUCKDB_PATH=data/kabusys.duckdb
     ```

---

## 使い方（コード例）

以下は典型的な利用シーンの例です。実行前に必ず環境変数 / .env を設定してください。

- DuckDB 接続の作成:
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL の実行:
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントスコアを作成（AI 必須: OPENAI_API_KEY）:
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み件数: {n_written}")
  ```

- 市場レジーム判定:
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB を初期化する:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions テーブルが作成されます
  ```

- 設定値を取得する:
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

- RSS を直接取得して確認（ニュースコレクタの低レベル関数）:
  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  ```

注意点:
- OpenAI 呼び出しは API キーが必須です。api_key を関数引数で渡すことも可能（テスト時の差し替え等）。
- LLM 関連の関数は、API エラー時にフォールバック/スキップする実装になっています（例: スコアを 0 にする等）。

---

## ディレクトリ構成

主要なファイル / モジュール構成（src/kabusys 以下を抜粋）:

- kabusys/
  - __init__.py
  - config.py                     — 環境変数/.env 読み込みと settings
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュースセンチメント（銘柄別）
    - regime_detector.py           — 市場レジーム判定（MA200 + マクロLLM）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント + save_*
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - etl.py                       — ETLResult 再エクスポート
    - calendar_management.py       — マーケットカレンダー管理・営業日ユーティリティ
    - news_collector.py            — RSS 収集（SSRF 対策・正規化）
    - quality.py                   — データ品質チェック（欠損・スパイク・重複など）
    - stats.py                     — zscore_normalize 等の統計ユーティリティ
    - audit.py                     — 監査ログスキーマ初期化（signal / orders / executions）
  - research/
    - __init__.py
    - factor_research.py           — momentum / value / volatility 計算
    - feature_exploration.py       — forward returns / IC / factor summary / rank

README に載せきれない細部:
- 各関数の docstring に処理フロー・設計方針・フェイルセーフの挙動を詳述しています。実装を参照してください。

---

## 実運用上の注意事項

- 本リポジトリは「取引ロジック（実際の発注）」と「データ取得・計算」を分離しており、発注・監視部分は別モジュール（execution / monitoring 等）で扱います。実際にリアルマネーで運用する際は sandbox/paper_trading 環境で十分に検証してください。
- 環境変数の leakage に注意してください（API トークンなど）。
- OpenAI や J-Quants の API 使用には料金が発生する場合があるため、レート・コスト管理を行ってください。
- ETL は部分失敗に強い設計ですが、品質チェックで致命的な問題が検出された場合は手動での確認・復旧が必要です。

---

もし README に追加したい具体的な使用例、CI 設定、requirements.txt、サンプル .env.example などがあれば、その内容を教えてください。必要に応じて README を拡張します。