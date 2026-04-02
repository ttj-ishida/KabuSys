# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。ETL、ニュース収集、AI ベースのニュースセンチメント評価、市場レジーム判定、ファクター計算、監査ログなどの機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータ収集・品質チェック・研究・信号→発注の監査までをカバーするモジュール群です。主に以下の用途を想定しています。

- J-Quants API からのデータ ETL（株価／財務／カレンダー）
- RSS ベースのニュース収集と銘柄紐付け
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（AI）
- ETF（1321）とマクロニュースを組み合わせた市場レジーム判定
- ファクター計算・特徴量探索（研究用）
- 監査（signal → order_request → execution）のための監査テーブル作成・初期化
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上、ルックアヘッドバイアス回避（実行時刻や環境に依存しない計算）や冪等性（DB 書き込み）を重視しています。

---

## 機能一覧

主な機能（モジュール別）:

- kabusys.config
  - .env / 環境変数の自動読み込み（プロジェクトルート検出）
  - アプリ設定の取得（J-Quants トークン・kabu API 等）
- kabusys.data
  - ETL パイプライン（pipeline.run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（jquants_client）: データ取得・保存（raw_prices / raw_financials / market_calendar 等）
  - news_collector: RSS 取得・正規化・raw_news 保存（SSRF 対策など）
  - calendar_management: 営業日判定 / next/prev_trading_day / calendar_update_job
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査テーブル作成・初期化（signal_events, order_requests, executions）
  - stats: zscore_normalize などの統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを評価し ai_scores に書き込む
  - regime_detector.score_regime: ETF 1321 の MA200 等とマクロニュースを合成して market_regime に書き込む
  - OpenAI API 呼び出しはリトライ・フェイルセーフを備えています（API 失敗時は安全に継続）
- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

---

## 動作要件 / 推奨環境

- Python 3.10+
- 必要パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / OpenAI / RSS）

※ 実行環境に合わせてパッケージバージョンや追加依存を適宜管理してください。

---

## セットアップ手順

1. リポジトリをクローンしてパッケージをインストール（開発モード例）:

   - pip を使う例:
     pip install -e .

   （requirements.txt や pyproject.toml がある場合はそれに従ってください）

2. 必要な環境変数を設定:
   - .env をプロジェクトルートに置くと自動で読み込まれます（.env.local は上書き）
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

   主要な環境変数（必須）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 用）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（実行/発注系で使用）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

   AI 関連（OpenAI）
   - OPENAI_API_KEY: OpenAI API キー（ai.score_news / regime_detector を使う場合）

   その他（オプション）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/...
   - DUCKDB_PATH: デフォルト "data/kabusys.duckdb"
   - SQLITE_PATH: 監視用 SQLite（デフォルト "data/monitoring.db"）
   - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=yyy
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   ```

3. データディレクトリ作成（必要であれば）:
   mkdir -p data

---

## 使い方（基本例）

以下は Python スクリプトや REPL からの利用例です。

- DuckDB 接続を作成して日次 ETL を実行する:

  ```python
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=None)  # target_date=None で今日
  print(result.to_dict())
  ```

- ニュースのセンチメント評価（OpenAI API キーが必要）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY が使われる
  print("書き込み銘柄数:", written)
  ```

- 市場レジーム判定（1321 MA200 + マクロニュース）:
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 03, 20))  # OpenAI API キーは環境変数か引数で指定
  ```

- 研究用ファクター計算:
  ```python
  from kabusys.research.factor_research import calc_momentum
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB を初期化:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn を使って監査テーブルへアクセスできます
  ```

- RSS 収集（news_collector）を利用して raw_news に保存するワークフローは、fetch_rss を呼び出した後、保存ロジックを実装することで行います（fetch_rss は記事一覧を返します）。news_collector には安全対策（SSRF 防止、受信上限、URL 正規化等）が組み込まれています。

---

## 重要な設計注意点 / 運用上のヒント

- ルックアヘッドバイアス回避:
  - 多くの関数は内部で `date.today()` を直接参照しない設計です。バックテストや再現性を確保するため、`target_date` を明示的に渡してください。
- OpenAI 呼び出し:
  - API レスポンスのパース失敗や API エラーはフェイルセーフ（スコアを 0 にフォールバック）になっています。テスト時は各モジュールの `_call_openai_api` をモック可能です。
- .env の自動ロード:
  - プロジェクトルートは .git または pyproject.toml を基準に検出されます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 冪等性:
  - ETL の保存は ON CONFLICT DO UPDATE で冪等に動作します。
- セキュリティ:
  - news_collector は SSRF 対策や XML 脆弱性対策（defusedxml）を組み込んでいますが、実運用ではさらに監視・ホワイトリスト運用を推奨します。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                -- 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py            -- ニュースセンチメント評価 / ai_scores 書き込み
  - regime_detector.py     -- 市場レジーム判定（1321 MA200 + マクロニュース）
- data/
  - __init__.py
  - calendar_management.py -- マーケットカレンダー操作（営業日判定、calendar_update_job）
  - etl.py                 -- ETL の公開インターフェース（ETLResult の再エクスポート）
  - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
  - stats.py               -- zscore_normalize 等統計ユーティリティ
  - quality.py             -- データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py               -- 監査テーブルの DDL / 初期化
  - jquants_client.py      -- J-Quants API クライアント（fetch/save 系）
  - news_collector.py      -- RSS 収集 / 前処理 / 保存ユーティリティ
- research/
  - __init__.py
  - factor_research.py     -- calc_momentum / calc_value / calc_volatility
  - feature_exploration.py -- calc_forward_returns / calc_ic / factor_summary / rank
- monitoring/ (存在宣言あり __all__ に含めているが詳細は実装参照)

その他:
- data/ (デフォルトの DB 保存先など)
- .env.example（プロジェクトルートに用意することを推奨）

---

## よくある操作コマンド例

- ETL をスケジューラから呼ぶ（cron / Airflow 等）:
  - Python スクリプトで run_daily_etl を呼ぶ。J-Quants トークンは環境変数で管理。
- OpenAI を使う処理をローカルで試す:
  - OPENAI_API_KEY を設定し、score_news / score_regime を実行。
- 監査 DB 初期化:
  - from kabusys.data.audit import init_audit_db; init_audit_db("data/audit.duckdb")

---

## テスト / 開発時のヒント

- OpenAI 呼び出しや外部 API 呼び出しはモックしやすいように内部関数（_call_openai_api など）を分離しています。ユニットテストではこれらを patch してネットワークを切ってください。
- 環境変数の自動読み込みをオフにしてテスト用の `.env` を使い分けるには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定し、テスト側で明示的に環境変数設定を行うと安全です。

---

## ライセンス / 貢献

プロジェクト固有のライセンス・コントリビュート方法はリポジトリのルートにある LICENSE / CONTRIBUTING 等のファイルをご参照ください。

---

README に記載のない内部実装や追加のユーティリティについては、モジュール内の docstring を参照してください。開発・運用で不明点があれば、使用するモジュール名と関数名を指定して質問してください。