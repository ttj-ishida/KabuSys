# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）・データ品質チェック・ニュース NLP（OpenAI）・市場レジーム判定・リサーチ用ファクター計算・監査ログ（オーダー・約定トレーサビリティ）などを含みます。

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API からの差分 ETL（株価・財務・市場カレンダー）の取得と DuckDB への冪等保存
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- RSS ベースのニュース収集と OpenAI による銘柄センチメントの付与
- マクロ + テクニカルを組み合わせた市場レジーム判定（bull / neutral / bear）
- ファクター計算・特徴量探索（モメンタム、ボラティリティ、バリュー等）
- 監査ログ用スキーマ（signal / order_request / executions）と初期化ユーティリティ
- 実行環境向けの設定・環境変数読み込みユーティリティ

設計上のポイント:
- ルックアヘッドバイアスを避ける（内部で datetime.today()/date.today() を直接参照しない等）
- DuckDB を中心とした SQL + Python 実装
- API 呼び出しはリトライ・バックオフ・レート制御を実装
- ETL / 保存は冪等（ON CONFLICT / UPDATE）で運用可能

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（fetch_* / save_*）
  - 市場カレンダー管理（is_trading_day / next_trading_day / calendar_update_job）
  - ニュース収集（RSS -> raw_news）
  - データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（score_news）: OpenAI を用いた銘柄ごとのセンチメント付与
  - 市場レジーム判定（score_regime）: ETF 1321 の MA200 乖離 + マクロニュースを合成
- research
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - .env（自動読み込み）と環境変数管理（settings オブジェクト）

---

## 必要条件 / 推奨環境

- Python 3.10 以上（型注釈 Path | None 等を使用）
- 必要パッケージ（一例）
  - duckdb
  - openai (openai Python SDK)
  - defusedxml
  - （標準ライブラリ：urllib, json, logging 等）

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# 開発インストール（パッケージ化されている場合）
# pip install -e .
```

（プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用してください）

---

## 環境変数 / 設定

KabuSys は .env / .env.local または OS 環境変数を読み込んで設定を提供します。自動ロードはプロジェクトルート（.git または pyproject.toml を探索）を基準に行われます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数（settings で参照されるもの）

- 認証・API
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
  - KABU_API_PASSWORD (必須) — kabu ステーション API パスワード
  - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 実行時に必要）
- Slack
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- データベース / パス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PID_FILE_PATH (デフォルト: data/execution.pid)
- 監視閾値（任意）
  - CPU_THRESHOLD_PCT (デフォルト: 90.0)
  - MEMORY_THRESHOLD_PCT (デフォルト: 85.0)
  - DISK_THRESHOLD_PCT (デフォルト: 90.0)
- システム
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト "development"
  - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト "INFO"

例 (.env.example):
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-xxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

3. 依存パッケージをインストール
   ```
   pip install duckdb openai defusedxml
   ```

   （プロジェクトで requirements.txt / pyproject.toml があればそちらを使用）

4. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を作成するか、OS 環境変数を設定します。
   - 必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY）を設定してください。

5. DuckDB データベースの用意
   - デフォルトは `data/kabusys.duckdb`（settings.duckdb_path）。フォルダがなければ自動作成されます（関数により）。

---

## 使い方（例）

以下は主要ユースケースのサンプルコードです。実行は Python スクリプトまたは REPL で行います。

- 日次 ETL を実行（J-Quants から株価/財務/カレンダーを取得して DuckDB に保存）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコア生成（OpenAI を使って銘柄ごとの ai_scores を生成）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None -> 環境変数 OPENAI_API_KEY を使用
print(f"scored {count} symbols")
```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースで判定）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB 初期化
```python
from kabusys.config import settings
from kabusys.data.audit import init_audit_db

# 監査専用 DB を初期化して接続を取得
conn = init_audit_db(settings.duckdb_path)
# -> signal_events / order_requests / executions テーブルが作成されます
```

- 研究用途（ファクター計算）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, target_date=date(2026,3,20))
val = calc_value(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
```

---

## 注意点 / 運用上のヒント

- OpenAI の呼び出しはレートやコストが発生します。実行時にはキーとコスト管理を行ってください。
- J-Quants API のレート制限（120 req/min）に対応するためクライアントにレート制御が組み込まれていますが、多数の並列処理は避けてください。
- ETL は冪等設計（ON CONFLICT DO UPDATE）です。部分的な失敗が発生しても既存データを保護するように配慮されています。
- テストや CI で自動的に .env を読み込ませたくない場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- KABUSYS_ENV は "development", "paper_trading", "live" のいずれかを指定してください（settings が検証します）。

---

## ディレクトリ構成

主要ファイル / モジュールを抜粋しています（src/kabusys 以下）。

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
    - etl.py
    - stats.py
    - quality.py
    - audit.py
    - jquants_client.py
    - news_collector.py
    - (その他 jquants client / helpers)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (※コードベースに存在する場合の監視関連モジュール)
  - strategy/ (戦略関連は将来的にここに格納)
  - execution/ (注文実行関連はここに格納)

（実際のリポジトリではさらにテスト、スクリプト、docs 等が存在する可能性があります）

---

## 貢献 / 開発

- コードは DuckDB と SQL ウェイトを多用するため、実行前に小さなローカルデータベースで動作確認を行ってください。
- OpenAI 呼び出し部分はモックしやすく設計されています（ユニットテストで _call_openai_api を差し替え可能）。
- ETL / jquants_client 周りは API の変更に敏感なので、API 契約が変わった場合は fetch/save のペイロードを確認してください。

---

必要であれば README にサンプル .env.example を追加したり、より詳しい運用手順（バックテストとの連携、監視 / ロギング設定、データスキーマ仕様）を追記します。どの部分を詳しく書きたいか教えてください。