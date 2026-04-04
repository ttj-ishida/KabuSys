# KabuSys

日本株向けのデータプラットフォーム兼自動売買補助ライブラリ。  
J-Quants / RSS / OpenAI などを利用してデータ収集・品質チェック・ファクター計算・ニュースNLP・市場レジーム判定・監査ログ初期化などを行うモジュール群を提供します。

この README はパッケージ内の主要機能、セットアップ手順、使い方例、ディレクトリ構成をまとめたものです。

## 概要
KabuSys は以下の領域を扱います。
- データ収集（J-Quants API 経由の株価・財務、JPX カレンダー、RSS ニュース）
- ETL パイプライン（差分取得・保存・品質チェック）
- ニュースの NLP（OpenAI を使った銘柄センチメント算出）
- 市場レジーム判定（ETF MA とマクロニュースの組合せ）
- 研究用ユーティリティ（ファクター計算・将来リターン・IC 等）
- 監査ログ／トレーサビリティ（signal → order_request → execution の監査テーブル）
- 各種ユーティリティ（カレンダー管理、統計関数、品質チェック 等）

設計上の特徴：
- Look-ahead bias を避けるため、内部で現在日時を安易に参照せず、明示的な target_date を受け取る関数が多い
- DuckDB を主要なオンディスク DB として利用
- OpenAI（gpt-4o-mini 等）への呼び出しはリトライ/バックオフを備えた実装
- .env 自動読み込み（プロジェクトルート検出）機能あり（無効化可）

## 機能一覧（抜粋）
- データ取得・保存
  - J-Quants: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - 保存関数: save_daily_quotes, save_financial_statements, save_market_calendar
- ETL
  - run_prices_etl, run_financials_etl, run_calendar_etl
  - run_daily_etl（統合 ETL 実行、品質チェック含む）
- ニュース処理
  - fetch_rss（RSS 収集・前処理）
  - score_news（銘柄ごとのニュースセンチメントを ai_scores に書き込む）
- レジーム判定
  - score_regime（1321 の MA とマクロニュースで 'bull'/'neutral'/'bear' を判定）
- 研究用
  - calc_momentum, calc_volatility, calc_value（ファクター計算）
  - calc_forward_returns, calc_ic, factor_summary, rank
  - zscore_normalize（正規化ユーティリティ）
- データ品質
  - check_missing_data, check_spike, check_duplicates, check_date_consistency
  - run_all_checks（すべての品質チェックを実行）
- カレンダー管理
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
  - calendar_update_job（J-Quants からカレンダー差分取得）
- 監査ログ
  - init_audit_schema / init_audit_db（監査テーブルの初期化）

## 前提（推奨）
- Python 3.10 以上（PEP 604 の型記法（|）を使用）
- DuckDB, OpenAI SDK, defusedxml などが必要

## 必要な環境変数
主に以下を設定してください（.env に記載して使用可）。パッケージはプロジェクトルート（.git または pyproject.toml がある場所）を探索して .env/.env.local を自動読み込みします（OS 環境変数が優先）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL 実行に必須）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector 実行に必須）

その他（省略時はデフォルトが使われるもの含む）:
- KABU_API_PASSWORD — kabu ステーション API パスワード（発注まわり）
- KABU_API_BASE_URL — kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 通知用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START — 監視関連
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視しきい値
- KABUSYS_ENV — development / paper_trading / live
- LOG_LEVEL — DEBUG/INFO/...

自動ロードを無効化する:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

.env の読み込み順序:
OS 環境 > .env.local（上書き）> .env（初期）  
（プロジェクトルートが見つからない場合は自動ロードをスキップ）

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン、プロジェクトルートへ移動
2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)
3. 必要パッケージをインストール（最低限の例）
   - pip install duckdb openai defusedxml
   - 追加に必要なパッケージがあれば適宜インストールしてください
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）
4. 環境変数を設定
   - プロジェクトルートに .env を作成するか、環境変数をエクスポート
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
5. データディレクトリ作成
   - mkdir -p data
6. DuckDB 接続を使った初期化（例: 監査 DB）
   - Python から init_audit_db() を呼び出して監査用 DB を作成可能

## 使い方（例）

基本的に関数は DuckDB 接続（duckdb.connect(...) が返す接続）と target_date を受け取ります。日付を明示的に渡すことでバックテスト等での再現性が保たれます。

- DuckDB 接続の作成例:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する:
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI API キーが環境変数にあること）:
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written {written} codes")
```

- 市場レジーム判定:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
# market_regime テーブルに結果を書き込む
```

- 監査 DB を初期化する:
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# これで監査テーブル(signal_events/order_requests/executions 等) が作成される
```

- カレンダー関連ユーティリティ:
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date

d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意点:
- OpenAI 呼び出しを行う関数（score_news や score_regime 等）は API キーが必須。api_key 引数でも指定可能（優先される）。
- 多くの関数は失敗安全（API エラー等で処理をスキップして継続）する設計ですが、ETL 全体のログや ETLResult の errors/quality_issues を確認してください。

## .env 例（最小）
参考として .env.example の内容を用意しておくと便利です（実コード内で .env.example の参照が示唆されています）。

```
JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
OPENAI_API_KEY=<your_openai_api_key>
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

## ディレクトリ構成（主要ファイル説明）
以下はパッケージ内部のおおまかな構成と各ファイルの役割（抜粋）です。

- src/kabusys/
  - __init__.py — パッケージのバージョン・公開API定義
  - config.py — 環境変数/.env の自動読み込み、Settings クラス
  - ai/
    - __init__.py — ai モジュールの公開関数
    - news_nlp.py — ニュースを銘柄ごとに集約して OpenAI でスコアリング、ai_scores への書込み
    - regime_detector.py — ETF(1321)のMA乖離とマクロニュースで日次市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py — JPX カレンダー管理（営業日判定・ジョブ）
    - pipeline.py — ETL パイプライン（差分取得・保存・品質チェック）
    - etl.py — ETLResult の再公開（インターフェース）
    - jquants_client.py — J-Quants API クライアント（取得・保存ロジック含む）
    - news_collector.py — RSS 取得・前処理・raw_news 保存
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py — 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py — 監査ログ（signal/order_request/execution）の DDL と初期化
  - research/
    - __init__.py — 研究用ユーティリティの公開
    - factor_research.py — Momentum/Value/Volatility 等ファクター計算
    - feature_exploration.py — 将来リターン/IC/統計サマリー等
  - research/*, ai/*, data/* — 各所に詳細な実装がある（上記参照）

## ログ・監視
- settings.log_level に従ってログを制御できます。
- 監視関連設定（PID/KILLフラグや CPU/Memory/Disk しきい値）は settings から読み取ります。

## テスト・モック
- OpenAI や外部 HTTP 呼び出しを行う関数はテスト用に内部の呼び出し _call_openai_api や _urlopen をモックできるように分離されています（unittest.mock.patch を利用）。

## サポート / 追加情報
- README は主要な使用方法・セットアップ・設計方針を抜粋してまとめています。各モジュール内に詳細なドキュメント文字列（docstring）があり、実装意図や処理フローが記載されています。実運用前には以下を確認してください:
  - J-Quants / OpenAI の API 利用制限・課金ポリシー
  - DuckDB のファイルパスとバックアップポリシー
  - 発注機能を使う場合は kabu API 周りの設定・テスト（paper_trading 環境の活用）

必要に応じて README に追記します。特定の機能の詳細や使用例（発注フロー、テストの書き方、CI 設定など）が必要であれば教えてください。