# KabuSys

日本株向けのデータプラットフォーム兼自動売買基盤のコアライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースの NLP スコアリング、マーケットレジーム判定、研究用ファクター計算、監査ログ（約定/発注トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- 前提・依存関係
- セットアップ手順
- 環境変数（.env）設定
- 使い方（クイックスタート）
- 主要モジュールの説明（利用例）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計されたライブラリ群です。  
主に次の領域をカバーします。

- データ収集（J-Quants API 経由の株価・財務・カレンダーなど）
- ETL パイプライン（差分取得、保存、品質チェック）
- ニュース収集・前処理・NLP スコアリング（OpenAI を利用したセンチメント）
- 市場レジーム判定（ETF + マクロニュースの合成）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- マーケットカレンダー管理（営業日判定等）

設計方針として「ルックアヘッドバイアス回避」「冪等操作」「フェイルセーフ（API障害時の軽いフォールバック）」を重視しています。

---

## 機能一覧

主な機能と提供モジュール（抜粋）:

- kabusys.config
  - .env 自動読み込み、環境変数管理
- kabusys.data.jquants_client
  - J-Quants API クライアント（認証・ページネーション・保存関数）
  - save_daily_quotes / save_financial_statements / save_market_calendar
- kabusys.data.pipeline
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - ETLResult 型
- kabusys.data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
- kabusys.data.news_collector
  - RSS 取得・前処理・SSRF 対策・記事正規化
- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None) — ニュースを銘柄ごとにスコア化して ai_scores テーブルに保存
- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None) — ETF 1321 の MA とマクロニュースを合成して市場レジーム判定
- kabusys.research
  - calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary / rank 等
- kabusys.data.audit
  - init_audit_schema / init_audit_db — 監査ログ用テーブルの初期化（冪等）

---

## 前提・依存関係

最低限の外部依存（実行には以下をインストールしてください）:

- Python 3.9+（typing 機能を使っています）
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- （標準ライブラリでほぼ完結していますが、ネットワーク利用・DB利用を前提とします）

例:
pip install duckdb openai defusedxml

※ 実運用では別途 Slack 連携や kabuステーション API 用のクライアント等が必要です（本コードにも参照箇所あり）。

---

## セットアップ手順

1. リポジトリをチェックアウト／クローンする

   git clone <repo-url>
   cd <repo-dir>

2. 仮想環境を作成して有効化（推奨）

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール

   pip install -U pip
   pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

4. .env を作成

   プロジェクトルート（pyproject.toml や .git のある場所）に .env を配置すると自動で読み込まれます。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。必要な環境変数の一覧は次節参照。

5. DuckDB ファイルや監査 DB を初期化

   - ETL で使用する DuckDB のパスは環境変数で指定できます（デフォルト: data/kabusys.duckdb）。
   - 監査専用 DB の初期化例は下記。

   Python 例:
   from pathlib import Path
   import duckdb
   from kabusys.data.audit import init_audit_db

   audit_conn = init_audit_db(Path("data/audit.duckdb"))

---

## 環境変数（.env で設定）

以下の環境変数が使用されます（必須は明示）:

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（get_id_token に使用）
- SLACK_BOT_TOKEN : Slack 通知用（必要に応じ）
- SLACK_CHANNEL_ID : Slack チャンネル ID

kabuステーション関連:
- KABU_API_PASSWORD : kabu API パスワード
- KABU_API_BASE_URL : kabu API の base URL（省略時: http://localhost:18080/kabusapi）

データベースパス（オプション、デフォルトあり）:
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite パス（デフォルト data/monitoring.db）

システム設定（オプション）:
- KABUSYS_ENV : development | paper_trading | live （デフォルト development）
- LOG_LEVEL : DEBUG | INFO | WARNING | ERROR | CRITICAL （デフォルト INFO）

OpenAI:
- OPENAI_API_KEY : OpenAI API キー（score_news / score_regime で参照される）

注意:
- .env は自動的にプロジェクトルートから読み込まれます（.env → .env.local の順）。OS 環境変数が優先されます。
- テスト時に自動読み込みを防ぎたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（クイックスタート例）

以下は主要な操作を行うための簡単なコード例です。DuckDB の接続は duckdb.connect() を利用してください。

1) 日次 ETL 実行

Python:
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

- run_daily_etl は市場カレンダー ETL → 株価 ETL → 財務 ETL → 品質チェック の流れを実行します。
- ETL の個別関数（run_prices_etl / run_financials_etl / run_calendar_etl）も利用できます。

2) ニュースセンチメントのスコアリング（銘柄ごと）

Python:
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"wrote {n_written} scores")

- api_key が None の場合は環境変数 OPENAI_API_KEY を参照します。
- score_news は ai_scores テーブルに書き込みます（書き込み件数を返す）。

3) 市場レジーム判定

Python:
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))

- 内部で ETF 1321 の 200日 MA 乖離とマクロニュースの LLM スコアを合成して market_regime テーブルへ保存します。

4) 監査ログ（audit）初期化

Python:
from pathlib import Path
from kabusys.data.audit import init_audit_db

conn = init_audit_db(Path("data/audit.duckdb"))
# conn は初期化済みの DuckDB 接続

5) 研究用ファクター計算

Python:
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
date0 = date(2026, 3, 20)
mom = calc_momentum(conn, date0)
val = calc_value(conn, date0)
vol = calc_volatility(conn, date0)
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])

6) マーケットカレンダー関連

Python:
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
is_trading = is_trading_day(conn, d)
next_day = next_trading_day(conn, d)
days = get_trading_days(conn, d, d.replace(day=d.day+7))

---

## 主要モジュールの注意点／設計上のポイント

- ルックアヘッドバイアス防止:
  - 多くの関数は date.today()／datetime.now() を内部的に参照しないよう設計されています。target_date を明示的に渡すことでバックテストでも安全に利用できます。
- 冪等性:
  - J-Quants から取得したデータを保存する関数は ON CONFLICT DO UPDATE などを使い冪等性を担保しています。
- フェイルセーフ:
  - OpenAI や外部 API 呼び出しでの一時的な失敗は、スコアを 0 にする・処理をスキップする等のフォールバックを組み込んでいます。
- テスト性:
  - OpenAI 呼び出し等は内部関数をパッチしやすい構造です（ユニットテストでのモックが可能）。

---

## ディレクトリ構成

リポジトリ内の主要ファイル・モジュールの階層（抜粋）:

src/kabusys/
- __init__.py
- config.py                        -- 環境変数・.env ロード
- ai/
  - __init__.py
  - news_nlp.py                     -- ニュース NLP スコアリング
  - regime_detector.py              -- 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py               -- J-Quants API クライアント & 保存処理
  - pipeline.py                     -- ETL パイプラインと ETLResult
  - etl.py                          -- ETL インターフェース（ETLResult 再エクスポート）
  - news_collector.py               -- RSS 収集・前処理
  - calendar_management.py          -- マーケットカレンダー管理
  - quality.py                      -- データ品質チェック
  - stats.py                        -- 汎用統計ユーティリティ（z-score など）
  - audit.py                        -- 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py              -- Momentum / Value / Volatility 等の算出
  - feature_exploration.py          -- 将来リターン / IC / 統計サマリー等
- ai/
  - news_nlp.py
  - regime_detector.py
- research/
  - factor_research.py
  - feature_exploration.py

（実際のリポジトリではさらにテストや CI 設定、ドキュメント等が追加される想定です）

---

## 開発・貢献

- バグ修正や機能追加の PR は歓迎します。  
- コードの設計方針（ルックアヘッドバイアス回避・冪等性・API障害のフォールバック）を維持してください。

---

## 補足

- 本 README はコードベースの提供モジュール群に基づく概要ドキュメントです。実運用に際しては各 API（J-Quants、OpenAI、kabuステーション、Slack など）の利用規約やレート制限、セキュリティ方針を遵守してください。
- 実行時のログや DB スキーマ（raw_prices, raw_financials, market_calendar, ai_scores, market_regime, signal_events, order_requests, executions 等）を事前に確認し、環境に合わせた初期化を行ってください。

---

必要であれば「テーブルスキーマ一覧」や「よく使う SQL クエリ例」「運用用の .env.example」も作成できます。どれを追加しましょうか？