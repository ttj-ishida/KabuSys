# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ群です。  
データ取得（J-Quants）、ETL、ニュース収集・NLP、AI を用いたニュース/市場レジーム評価、ファクター計算、品質チェック、監査ログ等のユーティリティを提供します。

---

## プロジェクト概要

KabuSys は日本株アルゴリズム取引基盤の一部として以下を担います。

- J-Quants API からの株価・財務・マーケットカレンダー取得と DuckDB への保存（ETL）
- RSS ベースのニュース収集と前処理（SSRF/サイズ制限対策あり）
- OpenAI（gpt-4o-mini など）を用いたニュースのセンチメント評価（銘柄毎）およびマクロセンチメントを組み合わせた市場レジーム判定
- ファクター計算（モメンタム / ボラティリティ / バリューなど）とリサーチ向け統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ初期化ユーティリティ
- 設定管理（.env の自動ロード、環境変数）と実行環境判定（development / paper_trading / live）

ライブラリ設計は「ルックアヘッドバイアス排除」「冪等性」「フェイルセーフ（APIエラー時の安全なフォールバック）」を重視しています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（取得・保存・ページネーション・認証更新・レート制御）
  - pipeline: 日次 ETL 実行（calendar / prices / financials）と ETLResult
  - news_collector: RSS 取得、前処理、raw_news 保存
  - calendar_management: 営業日判定、next/prev_trading_day、calendar 更新ジョブ
  - quality: データ品質チェック（missing, duplicates, spike, date consistency）
  - audit: 監査ログスキーマ初期化（DuckDB）
  - stats: zscore_normalize 等の統計ユーティリティ
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメント取得・ai_scores への保存（OpenAI）
  - regime_detector.score_regime: ETF（1321）200日MA乖離とマクロニュースセンチメントの合成による市場レジーム判定
- research/
  - factor_research: calc_momentum, calc_volatility, calc_value
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- config.py: .env 自動ロード（プロジェクトルート検出）と Settings（環境変数のラッパー）

---

## セットアップ手順

前提:
- Python 3.10 以上（型ヒントに PEP 604 の記法を使用）
- DuckDB が Python 環境にインストールされていること
- OpenAI API キー、J-Quants リフレッシュトークン、Slack 等の外部サービス設定（必要に応じて）

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo>

2. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージのインストール（最低限）
   pip install duckdb openai defusedxml

   ※プロジェクトに requirements.txt があればそれを使ってください：
   pip install -r requirements.txt

4. パッケージを開発インストール（任意）
   pip install -e .

5. 環境変数 / .env を用意
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必要な主要キー（例）:

     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_kabu_station_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

   - .env のパースは shell 風の書式（export を含む行やクォート・コメント対応）に準拠します。

---

## 使い方（主なユースケース）

以下はライブラリの主要機能の呼び出し例です。実行は Python スクリプトやジョブとして行ってください。

- DuckDB 接続例:
  from pathlib import Path
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する:
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメント（銘柄別）を評価して ai_scores に保存:
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026, 3, 19), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
  print(f"scored {n_written} codes")

- 市場レジームを判定して market_regime に書き込む:
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 19), api_key=None)

- 監査ログ DB を初期化する:
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # これで監査用テーブル(signal_events, order_requests, executions) が作成されます

- ファクター計算／リサーチユーティリティ:
  from datetime import date
  from kabusys.research import calc_momentum, calc_value, calc_volatility
  conn = duckdb.connect(str(settings.duckdb_path))
  momentum = calc_momentum(conn, date(2026, 3, 19))
  volatility = calc_volatility(conn, date(2026, 3, 19))
  value = calc_value(conn, date(2026, 3, 19))

- データ品質チェックを実行:
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,19))
  for i in issues:
      print(i)

注意点:
- OpenAI 呼び出しは gpt-4o-mini を利用する想定です（news_nlp, regime_detector 内でモデル指定）。
- API 呼び出しはリトライ・バックオフの保護がありますが、API キーやレート制限に注意してください。
- ETL / AI処理は「ルックアヘッドバイアス」を避けるため、内部で today()/datetime.now() を不用意に使わない設計になっています。target_date を明示的に渡すことを推奨します。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注機能など）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（通知用）
- SLACK_CHANNEL_ID: Slack チャンネル ID（通知用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視データ用 SQLite（デフォルト data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト development）
- LOG_LEVEL: ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env の自動ロードを無効化（テスト用）

settings オブジェクトからはこれらをプロパティとして参照できます:
from kabusys.config import settings
settings.jquants_refresh_token, settings.is_live, settings.duckdb_path, ...

---

## ディレクトリ構成

簡易的なファイル一覧（主要ファイル）:

- src/kabusys/
  - __init__.py
  - config.py                       # 環境変数読み込みと Settings
  - ai/
    - __init__.py
    - news_nlp.py                   # 銘柄別ニュースセンチメント
    - regime_detector.py            # 市場レジーム判定（MA + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py             # J-Quants API クライアント（fetch/save）
    - pipeline.py                   # ETL パイプライン（run_daily_etl 他）
    - etl.py                        # ETLResult 再エクスポート
    - news_collector.py             # RSS 収集・前処理
    - calendar_management.py        # マーケットカレンダー管理
    - quality.py                    # データ品質チェック
    - audit.py                      # 監査ログスキーマ初期化
    - stats.py                      # zscore_normalize 等
  - research/
    - __init__.py
    - factor_research.py            # calc_momentum, calc_volatility, calc_value
    - feature_exploration.py        # calc_forward_returns, calc_ic, factor_summary, rank

---

## 設計上の注意・運用上のポイント

- 自動環境ロード:
  - パッケージ import 時にプロジェクトルート（.git または pyproject.toml を基準）を探索して .env / .env.local を自動ロードします。テストや CI で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 冪等性:
  - ETL の保存関数は ON CONFLICT で既存行を更新するため再実行に安全です。
- フェイルセーフ:
  - OpenAI や外部 API の失敗時は、安全なデフォルト（例えば macro_sentiment=0.0）で継続する設計です。ただし、必須の API キーがない場合は ValueError を出します。
- 監査ログ:
  - order_request_id を冪等キーとして扱い、二重発注を防止する運用を前提としています。
- テスト:
  - ai モジュールの OpenAI 呼び出し部分は内部で差し替え可能（ユニットテストでのモック推奨）。

---

## 参考（トラブルシューティング）

- .env が読み込まれない:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないか確認。プロジェクトルートが正しく検出できないと自動ロードをスキップします。
- OpenAI 呼び出しでエラーが出る:
  - OPENAI_API_KEY が設定されているか、API利用上限に達していないか、モデル名(gpt-4o-mini)の利用可否を確認してください。
- J-Quants 呼び出しで 401 が返る:
  - JQUANTS_REFRESH_TOKEN の値を確認。jquants_client は 401 でトークン再取得を試みます。

---

必要に応じて README にサンプルスクリプトや CI / デプロイ手順、各テーブルのスキーマ（DDL）・例示 SQL を追記できます。要望があれば具体的な運用手順やデプロイ例、Docker コンテナ化のテンプレートも作成します。