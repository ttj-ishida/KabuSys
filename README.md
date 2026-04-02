# KabuSys

日本株向けのデータプラットフォーム兼自動売買補助ライブラリ。  
ETL（J-Quants → DuckDB）、ニュース収集・NLP（OpenAI を利用したセンチメント解析）、市場レジーム判定、ファクター算出、データ品質チェック、監査ログ（注文/約定トレーサビリティ）など一連の機能を提供します。

---

## プロジェクト概要

KabuSys は以下を目的とするモジュール群を含むライブラリです。

- J-Quants API からの日次データ取得と DuckDB への保存（差分更新・ページネーション対応・リトライ・レート制御）
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング除去・冪等保存）
- OpenAI を用いたニュースセンチメント解析（銘柄単位のスコアリング）およびマクロセンチメントを組み合わせた市場レジーム判定
- ファクター計算（Momentum / Value / Volatility 等）と特徴量解析（将来リターン・IC・統計サマリー）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ初期化ユーティリティ
- 環境設定管理（.env 自動読み込み、必須環境変数チェック）

設計方針の共通点は「ルックアヘッドバイアス防止」「冪等性」「フェイルセーフ（API障害が発生しても中断しない）」「DuckDB を中心としたローカル分析容易性」です。

---

## 機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save 関数、認証・レート制御・リトライ）
  - カレンダー管理（営業日判定、next/prev_trading_day、calendar_update_job）
  - ニュース収集（RSS フィードの取得・前処理・保存、SSRF 対策）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore 正規化）
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントスコアを生成して ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF（1321）200日 MA とマクロニュースセンチメントを合成して market_regime を算出・保存
- research/
  - factor_research.calc_momentum / calc_value / calc_volatility: ファクター計算
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank: 将来リターン・IC・統計概要
- config.py
  - .env 自動読み込み（プロジェクトルートの .env / .env.local を優先）および settings オブジェクト
  - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN 等）
- audit / monitoring / execution / strategy（将来の拡張・発注統合向けにスケルトンが含まれる）

---

## 必要条件（依存ライブラリ）

主要なランタイム依存（抜粋）：

- Python 3.9+（型注釈の union | や型指定を利用）
- duckdb
- openai
- defusedxml

プロジェクトに requirements.txt / pyproject.toml があればそちらを参照してください。最低限のインストール例：

python -m pip install "duckdb" "openai" "defusedxml"

（実運用では他にも logging/requests 等のユーティリティを含めてセットアップしてください）

---

## セットアップ手順

1. リポジトリを取得し仮想環境を作成

   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

2. 依存パッケージをインストール

   pip install -r requirements.txt
   または個別に:
   pip install duckdb openai defusedxml

3. 環境変数を設定
   - プロジェクトルートに .env または .env.local を配置すると自動読み込みされます（config.py が .git あるいは pyproject.toml を基準にプロジェクトルートを探索して読み込み）。
   - 自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

推奨される .env の例:

```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabu ステーション API（注文連携がある場合）
KABU_API_PASSWORD=your_kabu_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# OpenAI
OPENAI_API_KEY=your_openai_api_key

# Slack 通知（任意）
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB パス（任意）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境 / ログ
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

必須環境変数（Settings で _require として扱われるもの）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

（OpenAI API キーは個別関数に api_key 引数で渡すこともできますが、環境変数 OPENAI_API_KEY を設定しておくと便利です）

---

## 使い方（簡易ガイド / サンプル）

以下はライブラリの主要ユースケースの例です。

- DuckDB 接続の作成（設定からパスを利用）

```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL の実行（run_daily_etl）

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースセンチメントのスコアリング（score_news）

```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# api_key を引数に渡すか、環境変数 OPENAI_API_KEY を設定しておく
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("written:", n_written)
```

- 市場レジーム判定（score_regime）

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ用 DB の初期化

```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

audit_conn = init_audit_db(settings.duckdb_path)
# init_audit_db は transactional=True でスキーマを作成します
```

- ファクター計算・研究ツール

```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, target_date=date(2026,3,20))
# zscore 正規化
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])
```

注意点:
- OpenAI 呼び出しはネットワーク/課金が発生します。テスト時は _call_openai_api をモックしてください（モジュール内に差し替え箇所を用意しています）。
- ETL 実行・AI 呼び出しはルックアヘッドバイアス対策が組み込まれており、target_date 引数を明示して実行することが推奨されます。
- ETL の結果は ETLResult オブジェクトで返り、品質チェックの問題は result.quality_issues に格納されます。

---

## 設定（settings）詳細

kabusys.config.Settings で以下プロパティを取得できます。主要なもの:

- jquants_refresh_token: J-Quants リフレッシュトークン（必須）
- kabu_api_password: kabu ステーション接続パスワード（必須）
- kabu_api_base_url: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- slack_bot_token / slack_channel_id: Slack 通知用（必須）
- duckdb_path: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- sqlite_path: 監視用 SQLite パス（デフォルト data/monitoring.db）
- pid_file_path / cpu_threshold_pct / memory_threshold_pct / disk_threshold_pct: 監視用設定
- env: KABUSYS_ENV（development / paper_trading / live）
- log_level: LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）にある `.env` / `.env.local` を自動で読み込みます。
- 読み込み順: OS 環境変数 > .env.local > .env（.env.local は上書き可能）
- 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## ディレクトリ構成

主要ファイル / モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - calendar_management.py
    - pipeline.py
    - etl.py (ETLResult re-export)
    - jquants_client.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/*（ファイル群）
  - monitoring/ (将来的な監視モジュール)
  - strategy/ (戦略定義・シグナル生成向けの骨組み)
  - execution/ (注文発行・ブローカー連携の骨組み)

各ファイルは README の冒頭にある通りの責務を持ち、DuckDB 接続を受け取る関数が中心です。

---

## 注意事項 / 運用上のヒント

- 本ライブラリには注文実行（ブローカー送信）の完全な実装は含まれず、実運用では十分なテストやリスク制御（ポジション管理・二重発注防止等）を実装してください。
- OpenAI / J-Quants 呼び出しには API キーや課金が必要です。テスト時は API コールをモックしてください。
- DuckDB の executemany に関する注意（空リストの扱いなど）がコード内に記載されています。バージョン差に留意してください。
- 監査ログは原則として削除しない運用を前提としています。初期化時に TimeZone を UTC に固定します。
- 本 README はコード内コメントを要約したものです。各モジュールの docstring（ソース内コメント）を参照すると詳細な挙動が理解できます。

---

もし README をさらにプロジェクト向けにカスタマイズしたい（例: CI 実行例、Dockerfile、cron ジョブ例、Slack 通知例、より詳細な .env.example、開発用コマンド等）があれば、目的に合わせて追記を作成します。