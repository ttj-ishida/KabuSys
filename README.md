# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
ETL（J-Quants からの株価 / 財務 / カレンダー取得）、ニュース収集・NLP スコアリング（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（発注／約定トレーサビリティ）などの機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は、日本株を対象にしたリサーチ／運用プラットフォーム向けの小〜中規模なコンポーネント群を集めた Python パッケージです。主に以下を目的としています。

- J-Quants API を使った時系列データ（株価・財務・カレンダー）の差分 ETL
- RSS からのニュース収集と前処理、OpenAI を使ったニュースセンチメント（銘柄別）算出
- 日次の市場レジーム判定（ETF の MA とマクロニュースを合成）
- ファクター計算・IC 計測などの研究ユーティリティ
- データ品質チェック
- 監査ログ（signal → order_request → execution）の DB スキーマ提供

設計方針の一部:
- ルックアヘッドバイアス回避（datetime.today() の直接参照を避ける）
- DuckDB を主なローカル DB ストレージに使用
- 冪等性（ETL 保存は ON CONFLICT / DO UPDATE で実装）
- 外部 API 呼び出しはリトライ・バックオフ・フェイルセーフを組み込み

---

## 主な機能一覧

- data.jquants_client: J-Quants API との通信、取得・保存（raw_prices / raw_financials / market_calendar 等）
- data.pipeline: 日次 ETL パイプライン（差分取得・保存・品質チェック）と ETLResult
- data.news_collector: RSS 取得、前処理、raw_news 保存（SSRF / XML 脆弱性対策あり）
- ai.news_nlp: ニュースを銘柄別に集約して OpenAI でスコア化し ai_scores に保存
- ai.regime_detector: ETF（1321）200日 MA 乖離 + マクロニュース（LLM）で市場レジーム判定を実行
- data.quality: 欠損・スパイク・重複・日付不整合のチェック
- data.audit: 監査ログ（signal_events / order_requests / executions）スキーマ作成・初期化ユーティリティ
- research.*: ファクター計算（momentum/value/volatility）と特徴量解析ユーティリティ
- data.stats: zscore_normalize 等の共通統計ユーティリティ

---

## 必要要件（推奨）

- Python >= 3.10（型ヒントで | 演算子を使用）
- 必須ライブラリ（代表例）:
  - duckdb
  - openai
  - defusedxml
- （その他）標準ライブラリの urllib / datetime 等を使用

プロジェクトの実行に必要な具体的なバージョンは requirements.txt / pyproject.toml を参照してください（本リポジトリに存在しない場合は上記主要パッケージをインストールしてください）。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ...（リポジトリ URL）

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml

   （パッケージをまとめた requirements.txt があれば `pip install -r requirements.txt`）

4. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（ただし、テスト等で無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください）。

   - 必須環境変数（Settings クラス参照）:
     - JQUANTS_REFRESH_TOKEN （J-Quants リフレッシュトークン）
     - KABU_API_PASSWORD     （kabuステーション API のパスワード）
     - SLACK_BOT_TOKEN       （Slack 通知用 Bot トークン）
     - SLACK_CHANNEL_ID      （Slack 通知チャンネル ID）

   - 任意（デフォルトあり）:
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PID_FILE_PATH（デフォルト: data/execution.pid）
     - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
     - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）
     - OPENAI_API_KEY（OpenAI 呼び出しに使用）

   例 .env（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C0123456789
   ```

5. データディレクトリ作成
   - （必要なら）data/ 等のディレクトリを作成して DB ファイルを格納してください。多くの関数は自動で親ディレクトリを作成することがありますが明示しておくと安全です。

---

## 使い方（簡単な例）

以下は Python REPL / スクリプトからの利用例です。実行前に必要な環境変数を設定してください。

- DuckDB 接続を作って ETL を実行する例
  ```py
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリングを日次で実行
  ```py
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written={written}")
  ```

- 市場レジーム判定を実行
  ```py
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB を初期化
  ```py
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions テーブルが作成されます
  ```

- 関数群（研究用）の使用例（モメンタム計算）
  ```py
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
  print(len(momentum))
  ```

注意:
- OpenAI を使う処理（news_nlp, regime_detector）は `OPENAI_API_KEY` または api_key 引数が必要です。
- J-Quants API を使う ETL は `JQUANTS_REFRESH_TOKEN` を設定してください。

---

## 自動 .env 読み込みについて

- 起動時に `.env` と `.env.local`（プロジェクトルート）を自動で読み込みます。
- 読み込み順序: OS 環境変数 > .env.local > .env
- 自動読み込みを無効にするには、環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（ユニットテスト等で便利です）。

---

## ディレクトリ構成（主要ファイル）

（パッケージルートは src/kabusys 以下を想定）

- src/kabusys/
  - __init__.py  — パッケージ定義
  - config.py    — 環境変数 / 設定管理（Settings）
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースを銘柄別に集約して OpenAI でスコア化
    - regime_detector.py  — ETF MA とマクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（取得・保存）
    - pipeline.py         — ETL パイプライン / run_daily_etl / run_*_etl
    - etl.py              — ETLResult 再エクスポート
    - news_collector.py   — RSS 収集・サニタイズ・保存
    - calendar_management.py — 市場カレンダー管理と営業日ユーティリティ
    - quality.py          — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py            — 監査ログスキーマ初期化（signal/order/execution）
    - stats.py            — zscore_normalize 等
  - research/
    - __init__.py
    - factor_research.py  — momentum/volatility/value 等のファクター計算
    - feature_exploration.py — forward returns / IC / factor summary 等
  - ai/、research/、data/ 以外に strategy/ execution/ monitoring パッケージ名が __all__ に挙がっていますが、実装はこのリポジトリの該当ファイル群に依存します（将来的な拡張領域）。

---

## 開発・テスト時のメモ

- 設計上、ルックアヘッドバイアスを避けるために多くの関数は明示的な `target_date` を受け取ります。バックテスト等で使用する際は呼び出し側で日付管理を徹底してください。
- OpenAI や J-Quants への外部呼び出しはリトライやフェイルセーフを備えていますが、テスト時は該当モジュールの内部 API 呼び出し関数をモックしてください（module 内の _call_openai_api 等を patch する設計になっています）。
- news_collector は SSRF 対策・XML パースに defusedxml を使っています。RSS フィードの取得では外部接続の挙動に注意してください。

---

## ライセンス・貢献

本ドキュメントはリポジトリに含まれるソースコードに基づく README 例です。実際のライセンスやコントリビューション手順はリポジトリの LICENSE / CONTRIBUTING.md を参照してください（なければリポジトリ管理者に問い合わせてください）。

---

ご要望があれば、README にセットアップ用の Dockerfile / docker-compose の例、より詳細な .env.example、CI 用のテスト実行手順、あるいは各モジュールの API リファレンス追記を作成します。どれを優先しますか？