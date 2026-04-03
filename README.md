# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、ファクター算出、監査ログ（約定トレーサビリティ）など、取引システムに必要な基盤機能を提供します。

バージョン: 0.1.0

---

## 目次

- プロジェクト概要
- 主な機能一覧
- 要求環境・依存関係
- セットアップ手順
- 環境変数（主要）
- 使い方（サンプル）
- ディレクトリ構成
- 設計上のポイント / 注意事項

---

## プロジェクト概要

KabuSys は以下の要素を含むモジュール群から構成されるライブラリです：

- データ取得・ETL（J-Quants API 経由で株価・財務・マーケットカレンダーを取得）
- ニュース収集（RSS）とニュース NLP（OpenAI によるセンチメント）
- 市場レジーム判定（ETF MA とマクロニュースの組合せ）
- 研究用ユーティリティ（ファクター計算・特徴量解析・統計）
- 監査ログスキーマ（シグナル → 発注 → 約定までのトレース用テーブル）
- データ品質チェック、カレンダー管理、監視用設定等

設計の基本方針として、ルックアヘッドバイアスを避けるため「関数は内部で現在日時を参照しない」「ETL は差分更新 + バックフィル」「DB への保存は冪等（ON CONFLICT）処理」等を採用しています。

---

## 主な機能一覧

- ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- J-Quants API クライアント（ページネーション・レートリミット・自動トークンリフレッシュ）
- ニュース収集（RSS の安全対策、SSRF 対策、トラッキングパラメータ除去）
- ニュース NLP（gpt-4o-mini を用いた銘柄別センチメント -> ai_scores への書き込み）
- 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメントの複合）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー 等）
- 監査ログ初期化（監査テーブル・インデックス作成、DuckDB 対応）
- データ品質チェック（欠損・スパイク・重複・日付不整合検出）
- 環境設定管理（.env 自動ロード、Settings オブジェクト）

---

## 要求環境・依存関係

- Python 3.10 以上（Union 型演算子 `|` を使用しているため）
- 必要なライブラリ（例）
  - duckdb
  - openai
  - defusedxml
  - その他: 標準ライブラリ（urllib, logging, datetime 等）

requirements.txt が無い場合は最低限次をインストールしてください：

pip install duckdb openai defusedxml

（プロジェクトに setup / pyproject があれば pip install -e . を推奨）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repository_url>

2. 仮想環境を作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux / macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存関係をインストール
   - pip install -r requirements.txt  （存在する場合）
   - または個別に:
     - pip install duckdb openai defusedxml

4. 環境変数の準備
   - プロジェクトルートに `.env`（および任意で `.env.local`）を置くと自動で読み込まれます。
   - 自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

5. DuckDB ファイルや監査 DB の作成ディレクトリを準備（ settings.duckdb_path 等に基づく）

---

## 主要な環境変数

必須（使用する機能に依存）:

- JQUANTS_REFRESH_TOKEN
  - J-Quants のリフレッシュトークン（ETL / jquants_client が必要）
- OPENAI_API_KEY
  - OpenAI を用いる機能（news_nlp.score_news / regime_detector.score_regime）で必要

その他（デフォルトがある／任意）:

- KABU_API_PASSWORD
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (development / paper_trading / live) — デフォルト development
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)

Note: 設定は `kabusys.config.settings` 経由でアクセスできます。

例:
from kabusys.config import settings
print(settings.jquants_refresh_token)

---

## 使い方（サンプル）

以下は主要 API の簡単な利用例です。実行前に必須の環境変数を設定してください。

1) DuckDB 接続を作成する（監査 DB の初期化・ETL 実行など）

python:
from datetime import date
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# 以降、conn を渡して各種関数を呼ぶ

2) 日次 ETL を実行する

python:
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

3) ニュースの NLP スコアを付与（OpenAI 必須）

python:
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY を使用
print(f"scored: {n_written}")

4) 市場レジーム判定

python:
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

5) 監査ログ DB 初期化（独立した監査用 DB を作る場合）

python:
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit に対して監査テーブルが作成される

6) 研究用ファクター計算

python:
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect(str(settings.duckdb_path))
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は list[dict]（date, code, mom_1m, mom_3m, ...）

---

## 注意点 / 設計上のポイント

- ルックアヘッドバイアスの抑制
  - 多くの関数は内部で現在日時を参照しない（target_date を引数に取る）ため、バックテストに適した設計になっています。
  - ETL と分析処理の境界を明確に分けることを想定しています。

- 冪等性
  - J-Quants データ保存や raw_news の保存などは ON CONFLICT やハッシュ ID による重複排除を行います。
  - order_request_id / broker_execution_id 等も冪等キー設計です。

- フェイルセーフ
  - AI API が失敗した場合、news_nlp/regime_detector はゼロや空のスコアで継続する実装になっています（例外を直ちに投げない）。

- セキュリティ
  - RSS 取得は SSRF 対策、受信サイズ制限、defusedxml による XML パースなどを行っています。
  - J-Quants API 呼び出しはレートリミットとリトライ処理を実装しています。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイル・モジュール群は以下の通りです（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP スコアリング
    - regime_detector.py           — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント + 保存関数
    - pipeline.py                  — ETL パイプライン（run_daily_etl など）
    - etl.py                       — ETL インターフェース再エクスポート
    - calendar_management.py       — 市場カレンダー管理
    - news_collector.py            — RSS ニュース収集
    - quality.py                   — データ品質チェック
    - stats.py                     — 統計ユーティリティ（zscore_normalize）
    - audit.py                     — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py           — ファクター計算（momentum, value, volatility）
    - feature_exploration.py       — 将来リターン・IC・統計サマリー
  - ai/, data/, research/ などの補助モジュール群

（上記は主要ファイルの抜粋です。実際のリポジトリではさらに細分化されています）

---

## 追加情報 / トラブルシュート

- 自動で .env を読み込む仕様です。テスト中や別の設定を使いたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- OpenAI の呼び出しは JSON Mode（response_format）を期待しているため、モデルやレスポンス形式が変わるとパースに失敗する可能性があります。
- DuckDB バージョンによっては executemany の空パラメータリストに制約があるため、該当箇所では空チェックが入っています。
- J-Quants API のレート制限は 120 req/min に対応したスロットリング実装が入っていますが、大量ページネーション時は十分な間隔で実行してください。

---

必要であれば、README に追加する実行スクリプト例（cron / systemd 用サービス定義）、.env.example のテンプレート、もしくは API ごとの詳細な使用例（SQL スキーマの説明やサンプルクエリ）も作成します。どの情報を優先して追加しますか？