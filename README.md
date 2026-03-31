# KabuSys

KabuSys は日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース NLP（LLM を用いたセンチメント評価）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（注文 → 約定トレース）などを含みます。

---

## 主な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API からの株価（日次 OHLCV）、財務データ、JPX カレンダー取得
  - 差分取得・バックフィル・保存（DuckDB への冪等保存）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集／前処理
  - RSS フィードから記事収集（SSRF 対策、トラッキングパラメータ除去）
- ニュース NLP（LLM）
  - gpt-4o-mini（OpenAI）による銘柄ごとのニュースセンチメント算出（ai_scores テーブル）
  - マクロ記事を用いた市場レジーム判定（ma200 とマクロセンチメントの合成）
- リサーチ向け解析
  - モメンタム / ボラティリティ / バリュー 等のファクター計算
  - 将来リターン計算・IC（Information Coefficient）算出・統計サマリー
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブルを用いた監査スキーマ初期化
  - order_request_id を冪等キーとして二重発注防止
- 設定管理
  - .env / 環境変数を自動ロード（プロジェクトルート検出）／無効化オプションあり

---

## 必要環境 / 依存ライブラリ

（実行には以下のライブラリが必要になります。プロジェクトのセットアップ方法は次節参照）
- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- そのほか標準ライブラリ

※ 実際のパッケージ名・バージョンはプロジェクトの packaging/requirements に合わせてください。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. Python 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate    # macOS / Linux
   .venv\Scripts\activate       # Windows (PowerShell/Cmd)
   ```

3. 必要パッケージをインストール（例: pip）
   - 開発中に editable インストールする場合:
     ```
     pip install -e .
     ```
   - または最低限の依存を入れる:
     ```
     pip install duckdb openai defusedxml
     ```

4. 環境変数設定
   - プロジェクトルートに `.env`（および `.env.local`）を置くと自動で読み込まれます（初期ロードは .git または pyproject.toml の位置を基準に判定）。
   - 自動ロードを無効化したいテスト等では環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例: `.env` の最低限のサンプル（実際のトークンは安全に管理してください）
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabuステーション
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# OpenAI
OPENAI_API_KEY=your_openai_api_key

# Slack (通知等)
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C...

# データベースパス（オプション）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 環境
KABUSYS_ENV=development   # development | paper_trading | live
LOG_LEVEL=INFO
```

---

## 設定管理（settings）

パッケージ内で以下のように利用できます:
```py
from kabusys.config import settings

token = settings.jquants_refresh_token
db_path = settings.duckdb_path  # pathlib.Path
is_live = settings.is_live      # bool
```

有効な KABUSYS_ENV の値: `development`, `paper_trading`, `live`  
LOG_LEVEL: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

---

## 使い方（主要なサンプル）

以下はライブラリの代表的な使い方サンプルです。実行前に必ず設定（.env / 環境変数）を用意してください。

- DuckDB へ接続して日次 ETL を実行する
```py
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(__import__('kabusys').config.settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（特定日）を実行する
```py
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None -> 環境変数 OPENAI_API_KEY を使用
print(f"scored {count} stocks")
```

- 市場レジーム判定（ma200 + マクロセンチメント）
```py
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB 初期化（監査専用 DB を作る）
```py
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # parent dir will be created if needed
# conn を使って以降の監査ログ読み書き処理を行う
```

- カレンダー関連ユーティリティ
```py
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意:
- score_news / score_regime など OpenAI を呼ぶ関数は `api_key` 引数にキーを渡すか、環境変数 `OPENAI_API_KEY` を設定してください。
- ETL / データ保存処理は DuckDB のスキーマ（raw_prices / raw_financials / market_calendar 等）を前提とします。初期スキーマ作成はプロジェクトのスキーマ初期化ユーティリティを使ってください（本 README のコードベースには schema 初期化の参照点が複数あります）。

---

## 主要モジュールとディレクトリ構成

以下は src/kabusys 以下のおおまかな構成と各モジュールの役割です。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数 / .env の自動ロードと settings（J-Quants トークン、kabu API、Slack、DB パス等）
  - ai/
    - __init__.py
    - news_nlp.py         : ニュースを LLM でスコアリングし ai_scores テーブルへ書き込む
    - regime_detector.py  : ma200 とマクロセンチメントを合成して market_regime を判定
  - data/
    - __init__.py
    - jquants_client.py   : J-Quants API クライアント（取得 + DuckDB への保存）
    - pipeline.py         : 日次 ETL パイプライン（run_daily_etl, run_prices_etl 等）
    - etl.py              : ETLResult の再エクスポート
    - stats.py            : z-score 正規化など汎用統計ユーティリティ
    - quality.py          : データ品質チェック群（欠損、スパイク、重複、日付不整合）
    - calendar_management.py : 市場カレンダー管理 / 営業日判定 / calendar_update_job
    - news_collector.py   : RSS 取得・前処理・raw_news 保存ロジック
    - audit.py            : 監査ログ（signal_events / order_requests / executions）スキーマ作成・初期化
  - research/
    - __init__.py
    - factor_research.py  : モメンタム / ボラティリティ / バリュー等のファクター計算
    - feature_exploration.py : 将来リターン計算 / IC / 統計サマリー 等
  - monitoring/ (※コードベースに含まれる場合あり)
  - execution/ (発注周りの実装（kabu 等）を想定）
  - strategy/ (シグナル生成ロジックを想定）

（上記はコードベースから抽出した主要ファイル一覧です。実際のリポジトリには README やスクリプト、テスト、setup/pyproject 等が含まれる可能性があります。）

---

## 安全性・設計上の注意事項

- Look-ahead bias（ルックアヘッド）対策が各所に組み込まれており、API 呼び出し / date 演算は適切に実装されていますが、実運用／バックテスト時は使用方法を十分に確認してください。
- OpenAI / J-Quants など外部 API の呼び出しが含まれるため、API キーの管理は慎重に行ってください。
- 実際の注文送信を行う機能（kabu ステーションなど）を運用する際は、paper_trading モードで十分に検証してから live モードへ移行してください。KABUSYS_ENV を適切に設定してください。

---

もし README の補足（例: .env.example の詳しいテンプレート、より具体的な初期スキーマ作成方法、CI / テストの手順、パッケージ公開手順など）が必要であれば、使用ケースに合わせて追記します。