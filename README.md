# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（モジュール群）。
データ取得（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、マーケットカレンダー管理、
DuckDB スキーマ、監査ログなどを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の量的戦略実行に必要なデータプラットフォームと戦略レイヤーを提供するライブラリです。
主な目的は以下です：

- J-Quants API からのデータ取得（株価・財務・カレンダー）
- DuckDB を用いたローカルデータベース（Raw / Processed / Feature / Execution 層）の管理
- ETL パイプライン（差分取得、品質チェック）
- 研究（research）用のファクター計算・探索ユーティリティ
- 戦略用の特徴量作成（feature engineering）とシグナル生成
- RSS ベースのニュース収集と銘柄抽出
- マーケットカレンダー管理と営業日の判定
- 発注・監査用のスキーマ（監査ログ / order_request / executions 等）

設計上、発注 API との直接結合は避け、各レイヤーは冪等性・トレース可能性を重視しています。

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（認証、レート制御、リトライ、ページネーション）
  - save_* 系で DuckDB への冪等保存
- data/schema.py
  - DuckDB のスキーマ定義および初期化（init_schema）
- data/pipeline.py
  - 日次 ETL（run_daily_etl）／個別 ETL ジョブ（prices/financials/calendar）
- data/news_collector.py
  - RSS フィード取得、前処理、raw_news への冪等保存、銘柄抽出
- data/calendar_management.py
  - market_calendar 更新、営業日判定、next/prev_trading_day
- data/audit.py
  - 監査ログ用テーブル定義（signal_events / order_requests / executions 等）
- data/stats.py
  - zscore_normalize（クロスセクション Z スコア）
- research/
  - factor_research.py：モメンタム／ボラティリティ／バリュー計算
  - feature_exploration.py：将来リターン、IC、統計サマリー
- strategy/
  - feature_engineering.py：research で算出した生ファクターを正規化し features テーブルに保存
  - signal_generator.py：features + ai_scores を統合して BUY/SELL シグナルを生成
- config.py
  - .env 自動ロード（.env / .env.local）と Settings（環境変数のラップ）
- news_collector の安全対策
  - SSRF / XML Bomb / レスポンスサイズ制限 等に対する防御実装

---

## セットアップ手順

前提: Python 3.9+（コード文法の型注釈を想定）

1. リポジトリをクローン / コピー

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 本リポジトリに requirements.txt がない場合、最低限以下をインストールしてください：
     - duckdb
     - defusedxml
   例:
   ```
   pip install duckdb defusedxml
   ```
   開発時は追加で linters やテストフレームワークを導入してください。

4. パッケージをインストール（開発モード）
   ```
   pip install -e .
   ```
   （setup.py / pyproject.toml がプロジェクトに用意されていることを想定）

5. 環境変数の設定
   - プロジェクトルートに `.env`（および任意で `.env.local`）を配置すると自動で読み込まれます。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

.env の例（.env.example 相当）
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_refresh_token_here

# kabuステーション API
KABU_API_PASSWORD=your_kabu_password
# KABU_API_BASE_URL を変更する必要があれば設定
# KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack（通知用）
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789

# DB パス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境
KABUSYS_ENV=development   # development | paper_trading | live
LOG_LEVEL=INFO
```

---

## 使い方（基本例）

以下は主要操作の簡単な利用例です。Python スクリプト内や REPL で実行できます。

1. DuckDB スキーマ初期化
```python
from kabusys.data import schema
from kabusys.config import settings

# settings.duckdb_path は Settings.duckdb_path 経由で取得可能
conn = schema.init_schema(settings.duckdb_path)
```

2. 日次 ETL 実行
```python
from kabusys.data import pipeline

# conn は schema.init_schema で得た接続、target_date は省略で today
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

3. 特徴量作成（strategy 層）
```python
from datetime import date
from kabusys.strategy import build_features

# target_date: datetime.date 型
n = build_features(conn, target_date=date(2025, 1, 31))
print(f"features upserted: {n}")
```

4. シグナル生成
```python
from kabusys.strategy import generate_signals

count = generate_signals(conn, target_date=date(2025, 1, 31), threshold=0.6)
print(f"signals written: {count}")
```

5. ニュース収集ジョブの実行
```python
from kabusys.data.news_collector import run_news_collection

# known_codes は銘柄抽出に使う有効コード集合（省略可能）
res = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
print(res)  # {source_name: saved_count}
```

6. カレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

7. 環境設定確認
```python
from kabusys.config import settings
print(settings.env, settings.log_level, settings.duckdb_path)
```

注意:
- 各関数は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。init_schema で作成した接続か、get_connection を使って取得してください。
- ETL / データ取得関数は外部 API（J-Quants）を呼び出すため、環境変数に JQUANTS_REFRESH_TOKEN を正しく設定してください。
- features / signals の処理は "target_date 時点で知り得るデータのみ" を前提にした実装（ルックアヘッドバイアス対策）です。

---

## 主要モジュールとディレクトリ構成

（プロジェクトのルートを `src/kabusys` としたときの主なファイル/ディレクトリ）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数自動ロードと Settings
  - data/
    - __init__.py
    - jquants_client.py         # J-Quants API クライアント（fetch/save）
    - schema.py                 # DuckDB スキーマ定義 & init_schema / get_connection
    - pipeline.py               # ETL パイプライン（run_daily_etl 等）
    - news_collector.py         # RSS 収集・保存・銘柄抽出
    - calendar_management.py    # market_calendar 管理、営業日判定
    - stats.py                  # zscore_normalize 等統計ユーティリティ
    - features.py               # zscore_normalize の再エクスポート
    - audit.py                  # 監査ログスキーマ
    - execution/                # 発注関連の実装（空 __init__）
  - research/
    - __init__.py
    - factor_research.py        # ファクター計算（momentum/volatility/value）
    - feature_exploration.py    # 将来リターン/IC/統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py    # features テーブルに書き込む処理
    - signal_generator.py       # final_score 計算と signals への書き込み
  - execution/                  # 発注・ブローカー連携レイヤ（将来的な実装想定）

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 認証リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション等の API パスワード（発注連携用）
- KABU_API_BASE_URL (任意) — デフォルトは http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID (必須: Slack 通知を使う場合)
- DUCKDB_PATH / SQLITE_PATH (任意) — デフォルトは data/kabusys.duckdb / data/monitoring.db
- KABUSYS_ENV — development | paper_trading | live（デフォルト development）
- LOG_LEVEL — DEBUG | INFO | WARNING | ERROR | CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読込を無効化

---

## 運用上の注意

- DuckDB の初期化（init_schema）は一度実行すればよい（冪等）ですが、CI や初回セットアップでは必要です。
- J-Quants の API レート上限（120 req/min）を守るため、jquants_client では内部でレート制御を行っています。
- ETL は差分取得を前提としており、backfill_days の設定で直近数日の再取得を行い後出し修正を吸収します。
- news_collector では SSRF / XML Bomb / large response に対策が入っていますが、運用環境でも信頼できる RSS ソースの利用を推奨します。
- production（live）環境では KABUSYS_ENV を `live` に設定し、特に発注コードが追加された場合は慎重に検証してください。

---

## 貢献・拡張

- 発注ブリッジ（kabu API / 証券会社 SDK との連携）は execution レイヤに注入します。
- AI スコア生成や外部ニュース解析器（NLU）を ai_scores テーブルに書き込むことで戦略との統合が可能です。
- 品質チェックモジュール（data.quality）は pipeline.run_daily_etl で呼ばれる設計です。追加チェックは該当モジュールに実装してください。

---

不明点や README に追加したい内容（例: CLI コマンド、デプロイ手順、CI 設定のテンプレートなど）があれば教えてください。README を用途に合わせて拡張します。