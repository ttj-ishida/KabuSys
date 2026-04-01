# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。J-Quants と連携して市場データを取得・整備し、ニュース NLP やファクター計算、監査ログなどを備えた研究／運用用モジュール群を提供します。

主な用途
- J-Quants API からの株価・財務・カレンダー ETL
- RSS ニュース収集と OpenAI を使ったニュースセンチメント（ai_score）付与
- 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメントの融合）
- ファクター計算（モメンタム／バリュー／ボラティリティ等）
- データ品質チェック、監査ログ（発注→約定のトレーサビリティ）
- DuckDB を中心としたローカルデータ管理

---

## 機能一覧（主要モジュール）
- kabusys.config
  - .env ファイル / 環境変数読み込み、自動ロード（.env.local が .env を上書き）
  - 必須値チェック、環境フラグ（env / log_level 等）
- kabusys.data
  - ETL（pipeline.run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（jquants_client）
    - fetch / save のページネーション & レート制御、トークン自動リフレッシュ
  - news_collector: RSS 取得・正規化・raw_news への保存（SSRF/サイズ対策あり）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats: z-score 正規化ユーティリティ
  - calendar_management: 営業日判定・next/prev_trading_day・calendar 更新ジョブ
  - audit: 監査ログスキーマ初期化 / init_audit_db
- kabusys.ai
  - news_nlp.score_news: 銘柄別ニュースセンチメント取得（OpenAI）
  - regime_detector.score_regime: ETF 1321 MA200 とマクロセンチメントの合成による市場レジーム判定
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## 要求環境 / 依存パッケージ（例）
- Python 3.10+
- 必要パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS / OpenAI）
- （任意）Slack 連携トークンを使う場合は slack SDK 等

※実行環境やパッケージ管理はプロジェクトの pyproject.toml / requirements.txt を参照してください。

---

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install -r requirements.txt
   - もしくは最低限: pip install duckdb openai defusedxml
4. 環境変数 / .env の準備
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能）。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - OPENAI_API_KEY (OpenAI を使う場合必須)
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PID_FILE_PATH / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
     - KABUSYS_ENV (development / paper_trading / live)
     - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
5. DuckDB 初期化（必要に応じて）
   - Python から監査 DB を初期化する例（下記参照）

---

## .env の例
（README 用の簡易例 — 実際は .env.example を参照して必要値を設定してください）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（簡単なコード例）

- DuckDB に接続して日次 ETL を実行する
  - ETL は calendar → prices → financials → 品質チェック の順で実行します。

例:
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- ニュースセンチメントを計算して ai_scores に書き込む
  - OpenAI API キーは引数で与えるか環境変数 OPENAI_API_KEY を用います。

from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数から取得
print(f"written {n} codes")

- 市場レジームスコアを計算して market_regime テーブルへ書く

from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 監査DB 初期化（監査ログ用の独立 DB を作る）

from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って order_events/requests/executions テーブルが作成されます

- ファクター計算 / 研究用 API の利用例
  - calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary などは duckdb 接続と target_date を渡して使用します。

---

## 自動 .env 読み込みについて
- 設定はプロジェクトルート（.git または pyproject.toml を探索）にある .env / .env.local から自動で読み込まれます。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - .env.local は .env を上書きします（ローカル機密値用）。
- 自動読み込みを無効化したい場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル）
src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - jquants_client.py         # J-Quants API クライアント（fetch / save / auth / rate limit）
  - pipeline.py               # ETL パイプライン（run_daily_etl 等）
  - etl.py                    # ETL 型再エクスポート（ETLResult）
  - news_collector.py         # RSS 取得・前処理
  - calendar_management.py    # JPX カレンダー管理（営業日判定／更新ジョブ）
  - quality.py                # データ品質チェック
  - stats.py                  # zscore_normalize 等
  - audit.py                  # 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py        # calc_momentum, calc_value, calc_volatility
  - feature_exploration.py    # calc_forward_returns, calc_ic, factor_summary, rank
- research/... (その他ユーティリティ)
（上記以外に strategy / execution / monitoring 等が __all__ に含まれるが、ここでは主要な data/ai/research を説明）

---

## 設計上の注意点 / 備考
- Look-ahead バイアス回避:
  - 各モジュールは date.today() を内部で参照せず、必ず target_date を明示して処理できます（バックテストでの安全設計）。
- フォールトトレランス:
  - OpenAI / J-Quants の呼び出しはリトライ・フォールバック（失敗時は中立スコアやスキップ）で安全に動作する設計です。
- 冪等性:
  - DuckDB への保存は ON CONFLICT（Upsert）を使い冪等に保存します。
- セキュリティ:
  - RSS 取得では SSRF 回避・コンテンツサイズ制限を実装しています。
- テスト容易性:
  - 外部 API 呼び出し箇所はテスト時にモック可能な設計（関数単位で置き換えやすい）です。

---

以上が本ライブラリの概要、セットアップ、簡単な使い方です。詳細な API 仕様や運用ルール（StrategyModel.md / DataPlatform.md 等参照）がプロジェクト内ドキュメントに含まれていればそちらも合わせて参照してください。質問や README に追記してほしい項目があれば知らせてください。