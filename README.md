# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買支援ライブラリ（部分実装）

本リポジトリは日本株のデータ取得（J-Quants）、ETL、データ品質チェック、ニュースの NLP スコアリング、
市場レジーム判定、ファクター計算、監査ログ用スキーマなどを提供する Python パッケージ群です。
（strategy / execution / monitoring 等は公開 API に含まれますが、本リードミーに含まれるコード一式は主に data / ai / research 周りの機能を中心としています）

---

## 主要な機能

- データ取得 / ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、JPX マーケットカレンダーを差分取得・保存
  - ETL 用の差分ロジック、バックフィル、品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集 / NLP
  - RSS からニュース収集（SSRF 対策、トラッキングパラメータ除去、前処理）
  - OpenAI（gpt-4o-mini）を使った銘柄別ニュースセンチメントスコアリング（ai_scores へ保存）
- 市場レジーム判定
  - ETF(1321) の 200 日移動平均乖離とマクロニュース LLM センチメントを合成してレジーム判定
- 研究 / ファクター計算
  - モメンタム、ボラティリティ（ATR 等）、バリュー（PER/ROE）などの定量ファクター算出
  - 将来リターン計算、IC（Spearman）算出、ファクター統計要約
- カレンダー管理
  - market_calendar を用いた営業日判定、次/前営業日の取得、バッチ更新ジョブ
- 監査ログ（audit）
  - signal → order_request → execution のトレーサビリティを取るための DuckDB スキーマ定義・初期化ユーティリティ
- 設定管理
  - .env（.env.local）や環境変数からアプリ設定を自動読み込み（自動ロードは無効化可能）

---

## 必要条件（想定）

- Python 3.9+
- DuckDB（python duckdb パッケージ）
- OpenAI Python SDK（openai）
- defusedxml（RSS パースの安全対策）
- その他標準ライブラリ（urllib, json, logging 等）

推奨インストールパッケージ（最低限）:
- duckdb
- openai
- defusedxml

（プロジェクトに pyproject.toml / requirements.txt がある想定で、そちらからインストールしてください）

---

## 環境変数

以下の環境変数を設定する必要があります（用途に応じて必須になるものがあります）。

必須（機能を使う場合）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ETL / jquants_client）
- OPENAI_API_KEY         : OpenAI API キー（news_nlp / regime_detector）
- KABU_API_PASSWORD      : kabuステーション API のパスワード（発注連携がある場合）
- SLACK_BOT_TOKEN        : Slack 通知に使用（通知機能を利用する場合）
- SLACK_CHANNEL_ID       : Slack チャネル ID

その他（省略可、デフォルトあり）:
- KABUSYS_ENV            : development / paper_trading / live（デフォルト: development）
- LOG_LEVEL              : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL      : kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH            : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            : 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH          : 実行プロセスの PID ファイルパス（デフォルト: data/execution.pid）
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT : 監視しきい値（％）

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）にある `.env` → `.env.local` の順で自動読み込みされます。
- 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

設定オブジェクト利用例:
```py
from kabusys.config import settings
print(settings.jquants_refresh_token)
```

---

## セットアップ手順（例）

1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらからインストールしてください）
   - pip install -e .

4. 環境変数 / .env を用意
   - プロジェクトルートに `.env`（および必要に応じて `.env.local`）を作成。
   - 最小例（.env.example）:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=your_openai_api_key
     SLACK_BOT_TOKEN=...
     SLACK_CHANNEL_ID=...
     DUCKDB_PATH=data/kabusys.duckdb

5. データディレクトリを作る（必要に応じて）
   - mkdir -p data

---

## 使い方（主な API / 操作例）

以下はライブラリの主要機能を呼び出すための最小例です。実運用ではロギング設定やエラー処理を追加してください。

- DuckDB 接続の作成:
```py
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 監査ログ DB の初期化:
```py
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可
```

- 日次 ETL 実行:
```py
from kabusys.data.pipeline import run_daily_etl
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアリング（ai_scores へ書き込み）:
```py
from kabusys.ai.news_nlp import score_news
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", n_written)
```
- 市場レジーム判定（regime_detector）:
```py
from kabusys.ai.regime_detector import score_regime
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究用ファクター計算:
```py
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, target_date=date(2026,3,20))
val = calc_value(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
```

- ファクターの正規化:
```py
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

- カレンダーの営業日判定・検索:
```py
from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
is_trading_day(conn, date(2026,3,20))
next_trading_day(conn, date(2026,3,20))
get_trading_days(conn, date(2026,3,1), date(2026,3,31))
```

- J-Quants クライアント直接使用例:
```py
from kabusys.data.jquants_client import fetch_daily_quotes
from datetime import date

records = fetch_daily_quotes(date_from=date(2026,3,1), date_to=date(2026,3,20))
```
（J-Quants API を呼ぶには JQUANTS_REFRESH_TOKEN が必要です）

---

## 自動 .env ロードについて

- パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml のある親ディレクトリ）を探索し、`.env` と `.env.local` を順に読み込みます。
- 優先順位: OS 環境変数 > .env.local > .env
- 無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で利用）。

---

## ディレクトリ構成（抜粋）

以下は主要ファイルの所在です（省略あり）。実際のリポジトリではさらにファイルやテストがあるかもしれません。

- src/
  - kabusys/
    - __init__.py
    - config.py                      -- 環境変数/設定管理
    - ai/
      - __init__.py
      - news_nlp.py                  -- ニュース NLP（score_news）
      - regime_detector.py           -- 市場レジーム判定（score_regime）
    - data/
      - __init__.py
      - jquants_client.py            -- J-Quants API クライアント + 保存ロジック
      - pipeline.py                  -- ETL パイプライン / run_daily_etl / run_*_etl
      - etl.py                       -- ETL の公開インターフェース
      - calendar_management.py       -- マーケットカレンダー管理
      - news_collector.py            -- RSS ニュース収集
      - quality.py                   -- 品質チェック
      - stats.py                     -- 統計ユーティリティ（zscore）
      - audit.py                     -- 監査ログスキーマ初期化
    - research/
      - __init__.py
      - factor_research.py           -- モメンタム/バリュー/ボラティリティ
      - feature_exploration.py       -- 将来リターン / IC / summary / rank
    - (その他想定モジュール)
      - strategy/
      - execution/
      - monitoring/

---

## 注意事項 / 設計上のポイント

- Look-ahead bias（ルックアヘッドバイアス）を避ける設計が各モジュールに反映されています：
  - target_date を明示的に渡す設計
  - API 呼び出し・DB クエリで date < target_date / date <= 等の排他条件を適切に使用
- OpenAI 呼び出しはリトライやフェイルセーフを備え、API が利用できない場合は論理的なデフォルト（0.0 等）で継続します。
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）を採用しています。
- RSS 取得は SSRF 対策（リダイレクト検査・プライベートアドレス拒否）と受信サイズ制限があります。

---

## サポート / 貢献

- バグ報告や機能要望は issue を立ててください。プルリク歓迎です。
- 大きな変更を加える場合は設計意図（Look-ahead 回避、冪等性、トレーサビリティ等）を尊重してください。

---

この README はコードベースの主要部分を基に作成しています。実際の使用時はプロジェクトに含まれる pyproject.toml / requirements.txt / ドキュメント（もしあれば）をあわせて参照してください。