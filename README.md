# KabuSys

日本株向けの自動売買・データ基盤ライブラリ / ツール群です。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集と LLM を用いたニュースセンチメント評価、マーケットレジーム判定、研究用のファクター計算、監査ログ（発注/約定）スキーマなどを含みます。

主な設計方針として、バックテストでのルックアヘッドバイアス回避、API 呼び出しの堅牢なリトライ・レート制御、DuckDB を用いた冪等保存・高速クエリ、外部 API の失敗に対するフェイルセーフ（完全停止しない）を採用しています。

---

## 機能一覧

- 設定管理
  - .env / 環境変数の自動読み込み（プロジェクトルート検出）とバリデーション
- データプラットフォーム（data）
  - J-Quants からの差分 ETL（株価日足 / 財務 / JPX カレンダー）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - ニュース収集（RSS → raw_news、SSRF 対策・トラッキング削除）
  - 監査ログスキーマ（signal / order_request / executions）と初期化ユーティリティ
  - DuckDB への冪等保存ユーティリティ
- AI（ai）
  - ニュースの LLM ベースセンチメントスコアリング（gpt-4o-mini、JSON mode）
  - マクロ × ETF（1321）の MA200 乖離を合成した市場レジーム判定（bull/neutral/bear）
  - LLM 呼び出しはリトライ・バックオフ・パース検証あり
- 研究（research）
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 将来リターン計算、IC（スピアマン）、統計サマリー、Zスコア正規化ユーティリティ
- ユーティリティ
  - 汎用統計（zscore 正規化）
  - カレンダー操作ユーティリティ（営業日判定 / next/prev / 範囲取得）
- 外部連携
  - J-Quants API クライアント（レートリミット管理、401 自動リフレッシュ、ページネーション対応）
  - OpenAI（LLM）経由でのスコアリング（API キーを利用）

---

## セットアップ手順

前提:
- Python 3.10+ 推奨
- OS により curl/git 等

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows (PowerShell/CMD)
   ```

3. 依存パッケージをインストール
   - 必須（代表例）: duckdb, openai, defusedxml
   ```
   pip install -e .            # 開発インストール（setup があれば）
   pip install duckdb openai defusedxml
   ```
   実運用では requirements.txt や pyproject.toml の内容に合わせてインストールしてください。

4. 環境変数 / .env の準備
   - プロジェクトルートに `.env` / `.env.local` を置くと自動的に読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須の環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（get_id_token に使用）
     - KABU_API_PASSWORD — kabuステーション API パスワード
     - SLACK_BOT_TOKEN — Slack 通知用 Bot Token
     - SLACK_CHANNEL_ID — Slack チャネル ID
     - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
   - その他設定:
     - KABUSYS_ENV (development/paper_trading/live), LOG_LEVEL, DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH など
   - .env 例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-xxxx
     SLACK_BOT_TOKEN=xoxb-xxxx
     SLACK_CHANNEL_ID=C0123456789
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

5. DuckDB 初期化（監査ログ等を作る場合）
   - 例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```

---

## 使い方（代表的な例）

以下は Python REPL / スクリプトからの簡単な利用例です。

- 設定参照
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  ```

- DuckDB 接続を作って日次 ETL を実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの LLM スコア付け（score_news）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY が必要
  print(f"wrote scores for {written} codes")
  ```

- 市場レジーム判定（score_regime）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY が必要
  ```

- 監査テーブル初期化（既存 DB に追加）
  ```python
  import duckdb
  from kabusys.data.audit import init_audit_schema

  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

- 研究用ファクター計算例
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect(str(settings.duckdb_path))
  momentum = calc_momentum(conn, date(2026, 3, 20))
  ```

注意:
- AI 機能（news_nlp/regime_detector）は OpenAI の API キー（OPENAI_API_KEY）を環境変数または api_key 引数で渡す必要があります。
- J-Quants API 呼び出しは JQUANTS_REFRESH_TOKEN によるトークン発行を行います。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須 for data ETL）
- KABU_API_PASSWORD — kabu API パスワード（発注系）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（AI 機能に必要）
- SLACK_BOT_TOKEN — Slack Bot token（通知）
- SLACK_CHANNEL_ID — Slack チャネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（default: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視/運用用設定
- KABUSYS_ENV — environment: development / paper_trading / live
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動読み込みを無効化

---

## 実運用上の注意点

- Look-ahead バイアス回避:
  - 多くの関数は内部で date.today() を直接参照せず、target_date 引数を受け取る設計です。バックテストではこの点を遵守して使用してください。
- API レート制限とリトライ:
  - J-Quants クライアントは固定間隔スロットリング（120 req/min）を実装しています。大量バッチ処理の際はこれを考慮してください。
- LLM 呼び出し:
  - OpenAI の呼び出しは JSON Mode を利用して厳密な JSON を期待しますが、万が一のパース失敗時はフェイルセーフとして 0.0 スコアなどにフォールバックします。
- DuckDB の互換性:
  - 一部の実装は DuckDB のバージョンに依存する振る舞い（executemany の空リスト）を考慮しています。使用する DuckDB バージョンでテストしてください。

---

## ディレクトリ構成（主要ファイル）
（src/kabusys 以下の主要ファイル一覧）

- src/kabusys/
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
    - stats.py
    - audit.py
    - pipeline.py (ETLResult 再エクスポート)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (パッケージ名が __all__ にあるが詳細実装はここに配置可能)
  - strategy/ (戦略層のモジュールを格納する想定)
  - execution/ (注文実行周りのモジュールを格納する想定)

（上記は現時点での主要ファイル群です。実プロジェクトではさらにサブモジュール・ユーティリティが存在します。）

---

必要に応じて README に追記（例: CI / テスト実行方法、デプロイ/サービス起動手順、具体的な ETL スケジュール例）します。どの項目を詳しく書きたいか教えてください。