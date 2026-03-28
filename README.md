# KabuSys

日本株自動売買プラットフォームのライブラリ群です。データの ETL、ニュースの収集と AI によるセンチメント評価、ファクター計算、監査ログ管理、マーケットカレンダー管理など、自動売買システムで必要となるコア機能を提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を直接参照しない等）
- DuckDB を中心としたローカル分析・永続化
- J-Quants / OpenAI / kabuステーション など外部 API の堅牢な呼び出し（リトライ・レート制御等）
- 冪等性（ON CONFLICT や UUID を使った発注/監査ログ）と監査トレース

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェック（settings オブジェクト経由）
- データ ETL（J-Quants）
  - 株価日足、財務データ、JPX マーケットカレンダー取得（ページネーション・トークン管理・レート制御）
  - DuckDB への冪等保存（ON CONFLICT）
  - ETL の統合実行（run_daily_etl）
- データ品質チェック
  - 欠損データ、スパイク、重複、日付不整合の検出（QualityIssue）
- ニュース収集
  - RSS 取得・前処理・SSRF 対策・トラッキングパラメータ除去
  - raw_news / news_symbols への冪等保存
- AI（OpenAI）連携
  - ニュースを銘柄ごとにまとめて LLM へ送りセンチメント（score_news）
  - マクロニュース＋ETF MA乖離から市場レジーム判定（score_regime）
  - API 呼び出しはリトライやフォールバックを備える（失敗時は安全なデフォルト）
- リサーチ / ファクター
  - モメンタム、バリュー、ボラティリティ等のファクター計算（prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
  - Z スコア正規化ユーティリティ
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
  - 発注フローのトレーサビリティ（UUID 連鎖）
- 市場カレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - J-Quants からの差分更新ジョブ（calendar_update_job）

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントで | を使用）
- DuckDB（Python パッケージ）、openai（OpenAI Python SDK）、defusedxml 等が必要

1. リポジトリをクローン／チェックアウトしてパッケージをインストール
   - 推奨: 仮想環境を作成（venv / pyenv 等）
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate
     - pip install -e .  （プロジェクトが pip install 可能な設定である場合）
   - 必要パッケージ例:
     - pip install duckdb openai defusedxml

2. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env を作成すると、自動で読み込まれます（.env.local は .env 上書き）。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必要な（または推奨）環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabu API パスワード（必須）
     - KABU_API_BASE_URL: kabu API ベース URL（省略時 http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN: Slack ボットトークン（必須）
     - SLACK_CHANNEL_ID: 通知用チャンネル ID（必須）
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 呼び出し時に指定可能）
     - DUCKDB_PATH: データ用 DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
     - KABUSYS_ENV: 開発環境フラグ（development / paper_trading / live）
     - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
   - .env のフォーマットはコメント行、export KEY=val、シングル/ダブルクォート、インラインコメントなどに対応します。

3. データベース準備
   - DuckDB のファイルパス（例: data/kabusys.duckdb）に書き込み可能であることを確認してください。
   - 監査用 DB を初期化するには:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")

4. OpenAI 設定
   - score_news / score_regime を使う場合は OPENAI_API_KEY を環境変数に設定するか、関数呼び出しに api_key 引数を渡します。

---

## 使い方（基本例）

以下は最小限の利用例（Python REPL / スクリプト内）。

- settings（環境変数からの読み込み / 必須チェック）
  ```python
  from kabusys.config import settings
  token = settings.jquants_refresh_token  # 未設定なら ValueError が発生
  ```

- DuckDB 接続を作って ETL を実行（run_daily_etl）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- OpenAI を使ったニューススコアリング
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"{n_written} 銘柄のスコアを書き込みました")
  ```

- 市場レジーム判定（ETF 1321 + マクロニュース）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査 DB の初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- ファクター計算（研究用）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, date(2026, 3, 20))
  ```

注意点:
- LLM 呼び出しは API の料金とレート制限に影響します。大量実行には注意してください。
- ETL / データ取得は J-Quants のレート制限に準拠して実行されます（内部で調整済み）。

---

## 環境変数 / 設定（まとめ）

主要な設定は kabusys.config.settings から取得します。必須項目は未設定時に ValueError を出します。

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- 任意（デフォルトあり）:
  - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - KABUSYS_ENV (development | paper_trading | live)
  - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- 自動 .env 読み込み:
  - プロジェクトルート（.git/pyproject.toml）を基準に .env → .env.local の順で自動ロード
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主なモジュール一覧（抜粋）です。

- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- src/kabusys/data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py
  - calendar_management.py
  - news_collector.py
  - quality.py
  - stats.py
  - audit.py
  - (その他 ETL・ユーティリティ)
- src/kabusys/research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- src/kabusys/ai/__init__.py
- src/kabusys/research/__init__.py
- その他: strategy / execution / monitoring パッケージが __all__ に含まれます（実装が別途存在する想定）

（上記はコードベースから抽出した主要モジュールの一覧です）

---

## 開発上の注意と設計要点

- ルックアヘッドバイアス防止:
  - 多くのモジュールで現在日時を直接参照せず、外部から target_date を渡す設計です。バックテスト等では明示的に過去日を指定してください。
- 冪等性:
  - ETL / 保存処理は ON CONFLICT（または一意キー）で上書きすることで冪等化されています。
- 外部 API の堅牢性:
  - J-Quants クライアント・OpenAI 呼び出しはリトライ、レート制御、フェイルセーフ（失敗時のデフォルト値）を備えています。
- セキュリティ:
  - RSS の取得では SSRF 対策・受信サイズ上限・defusedxml を使用しています。
  - 秘密情報（トークン・パスワード）は .env などで適切に管理し、リポジトリに含めないでください。

---

## ライセンス / 貢献

（プロジェクトのライセンス・貢献ルールをここに記載してください。リポジトリに LICENSE があればその内容に従ってください。）

---

必要であれば README にサンプル .env.example、より詳細な API 使用例、CI / テスト実行方法、運用時の注意（コスト管理、レート監視、Slack 通知のサンプル）などを追記できます。どの情報を追加しますか？