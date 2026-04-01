# KabuSys

日本株向けのデータプラットフォーム兼自動売買基盤（KabuSys）のライブラリ群です。  
ETL / データ品質管理 / ニュースNLP（LLM）によるセンチメント / 市場レジーム判定 / 研究用ファクター計算 / 監査ログ等を含む、バックテスト〜運用までを想定したコンポーネント群を提供します。

---

目次
- プロジェクト概要
- 主な機能
- 動作要件・依存ライブラリ
- セットアップ手順
- 環境変数（.env）
- 使い方（簡易コード例）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は以下の要素から構成される Python パッケージです（src/kabusys）:

- データ取得・ETL（J-Quants API 経由）と DuckDB への保存
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- ニュース収集（RSS）とニュースの前処理
- ニュースを LLM（OpenAI）でセンチメント評価し銘柄別スコア化
- 市場レジーム判定（ETF MA + マクロニュース）
- 研究用途のファクター計算（モメンタム、バリュー、ボラティリティ等）
- 監査ログ（signal → order_request → executions のトレーサビリティ）
- 各種ユーティリティ（カレンダー管理、統計関数等）
- 環境設定読み込みユーティリティ（.env 自動読み込み）

設計方針としては「ルックアヘッドバイアスを避ける」「API呼び出しは冪等・リトライを備える」「DB への書き込みは冪等化（ON CONFLICT）する」「外部副作用を受けにくい設計（backtest と本番を分離）」などが取られています。

---

## 主な機能一覧

- ETL（data.pipeline）
  - run_daily_etl: 市場カレンダー / 株価 / 財務データの差分取得・保存・品質チェックを実行
  - 個別 ETL: run_prices_etl / run_financials_etl / run_calendar_etl

- データ取得クライアント（data.jquants_client）
  - J-Quants API 呼び出し、ページネーション、リトライ、トークン自動更新
  - save_* 関数で DuckDB へ冪等保存

- データ品質チェック（data.quality）
  - 欠損・スパイク・重複・日付不整合の検出

- ニュース収集・前処理（data.news_collector）
  - RSS 取得、URL 正規化、SSRF/サイズ対策、raw_news への保存想定

- ニュース NLP（ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメント集約・ai_scores 書き込みロジック
  - calc_news_window でニュースウィンドウの算出

- 市場レジーム判定（ai.regime_detector）
  - ETF(1321) の 200 日 MA 乖離 + マクロニュース LLM スコアを合成して market_regime テーブルへ書込

- 研究用ファクター計算（research.*）
  - calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（data.stats に実装）

- 監査ログ（data.audit）
  - 監査用スキーマの初期化（init_audit_schema / init_audit_db）
  - signal_events / order_requests / executions の DDL とインデックス

- 設定管理（config）
  - .env 自動読み込み（プロジェクトルート検出）
  - Settings クラス経由で設定値取得（必須設定は未設定時に ValueError）

---

## 動作要件・依存ライブラリ

主な Python 依存（実行には適宜インストールしてください）:

- Python 3.10+
- duckdb
- openai（OpenAI Python SDK）
- defusedxml
- 標準ライブラリ（urllib, json, datetime 等）

インストール例（プロジェクト配布形態により適宜調整）:

pip install duckdb openai defusedxml

※ 実行環境により追加のライブラリが必要になる場合があります（logging 等は標準）。

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要なパッケージをインストール
   - pip install -r requirements.txt  または pip install duckdb openai defusedxml
4. 環境変数を設定（.env を作成）
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env を作成すると、自動で読み込まれます（config モジュール）。
   - 自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

---

## 環境変数（主なキー）

以下はコード内で参照される主な環境変数です。

必須（未設定時は Settings が ValueError を送出）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL 用）
- KABU_API_PASSWORD — kabuステーション等と連携する場合のパスワード
- SLACK_BOT_TOKEN — Slack 通知用
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（ai.news_nlp / ai.regime_detector で使用）

任意 / デフォルトあり:
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

例 (.env):
JQUANTS_REFRESH_TOKEN=xxx
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your-password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG

---

## 使い方（簡易コード例）

以下は主要な関数の呼び出し例です。実際にはログ設定や例外処理、トークン注入等を整えて使ってください。

- DuckDB 接続を作成して ETL 実行:

from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- ニュースのセンチメント取得（ai.news_nlp.score_news）:

from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY が環境変数にあるか、api_key 引数で渡す
written_count = score_news(conn, target_date=date(2026, 3, 20))
print(f"wrote {written_count} ai_scores")

- 市場レジーム判定（ai.regime_detector.score_regime）:

from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))

- 研究用ファクター計算:

from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
moms = calc_momentum(conn, date(2026, 3, 20))
vals = calc_value(conn, date(2026, 3, 20))
vols = calc_volatility(conn, date(2026, 3, 20))

- 監査ログ DB 初期化:

from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成されます

---

## 運用上の注意

- OpenAI 呼び出しは API コストおよびレート制限に注意してください。リトライやフォールバックロジックが組まれているものの、API キーの利用状況は監視してください。
- J-Quants API のレート制限（120 req/min）に合わせて実装で待機制御が入っていますが、運用時は ID トークンや API エラーを監視してください。
- 本パッケージの一部は「外部サービスへ発注を行う」ような機能と連携可能な設計です。実際の売買・送信処理を組み合わせる場合は十分なテストとリスク管理が必要です（特に live 環境）。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テストで無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 主要なディレクトリ構成

（src/kabusys の主要ファイルのみ抜粋）

src/
  kabusys/
    __init__.py
    config.py                    -- 環境変数 / Settings
    ai/
      __init__.py
      news_nlp.py                -- ニュースセンチメント (score_news)
      regime_detector.py         -- 市場レジーム判定 (score_regime)
    data/
      __init__.py
      jquants_client.py          -- J-Quants API クライアント / 保存処理
      pipeline.py                -- ETL パイプライン（run_daily_etl 等）
      etl.py                     -- ETLResult 再エクスポート
      news_collector.py          -- RSS 収集・前処理
      calendar_management.py     -- 市場カレンダー判定・更新
      quality.py                 -- データ品質チェック
      stats.py                   -- 統計ユーティリティ（zscore_normalize）
      audit.py                   -- 監査ログ DDL / 初期化
    research/
      __init__.py
      factor_research.py         -- momentum/value/volatility 等
      feature_exploration.py     -- forward returns / IC / factor_summary / rank
    monitoring/                   -- （監視関連の実装想定）
    strategy/                     -- （戦略関連の実装想定）
    execution/                    -- （注文実行関連の実装想定）

---

もし README に追加してほしい内容（詳細な API 仕様、サンプルデータベース初期化 SQL、CI 設定、具体的な ETL スケジュール例、テスト方法など）があれば教えてください。必要に応じて追記します。