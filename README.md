# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースの NLP スコアリング、マーケットレジーム判定、監査ログ（取引トレーサビリティ）などを提供します。

バージョン: 0.1.0

## 概要
KabuSys は日本株向けのデータパイプラインおよびリサーチ / 信号生成のためのコンポーネント群を提供する Python ライブラリです。主な目的は以下の通りです。

- J-Quants API を用いた株価・財務・マーケットカレンダーの差分取得と DuckDB への保存（ETL）
- データ品質チェック（欠損、重複、スパイク、日付整合性）
- RSS ベースのニュース収集と前処理（SSRF / サイズ上限対策、正規化）
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメントスコアリング（銘柄ごと）
- ETF とマクロニュースを組み合わせた市場レジーム判定（bull / neutral / bear）
- 監査ログ（シグナル → 発注 → 約定）用のスキーマ初期化ユーティリティ
- 研究用のファクター計算・特徴量解析ユーティリティ（モメンタム、バリュー、ボラティリティ、IC 等）

設計方針として、ルックアヘッドバイアスの排除、冪等性（idempotency）を重視し、DuckDB をストアとして利用します。

---

## 機能一覧
- 環境/設定管理（自動 .env 読込、必須キーの検証）
- J-Quants クライアント
  - 株価日足（OHLCV）取得・保存
  - 財務データ取得・保存
  - マーケットカレンダー取得・保存
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- データ品質チェック（missing / duplicates / spike / date_consistency）
- ニュース収集（RSS）と前処理（トラッキングパラメータ除去、SSRF 対策）
- ニュース NLP（OpenAI）による銘柄ごとのセンチメントスコア生成
- 市場レジーム判定（ETF MA とマクロニュースの LLM 評価の組合せ）
- 監査ログスキーマの初期化（signal_events / order_requests / executions）
- 研究用モジュール（ファクター計算、前方リターン、IC、統計要約）
- 汎用統計ユーティリティ（Z-score 正規化 など）

---

## 動作環境・依存
- Python 3.10+
- 必須（主要外部ライブラリ）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- 標準ライブラリ：urllib, logging, datetime, json, hashlib 等

（実際の setup.py / pyproject.toml があればそれに従ってください）

---

## セットアップ手順（開発環境向け例）
1. リポジトリをクローンし、プロジェクトルートへ移動
2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （パッケージ配布がある場合）pip install -e .
4. 環境変数設定
   - プロジェクトルートに `.env`（および必要に応じて `.env.local`）を作成します。自動読み込みはデフォルトで有効です（無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必須例（.env に記載する想定のキー）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - OPENAI_API_KEY=your_openai_api_key
     - KABU_API_PASSWORD=your_kabu_api_password
     - SLACK_BOT_TOKEN=your_slack_bot_token
     - SLACK_CHANNEL_ID=your_slack_channel_id
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development  # 許容値: development, paper_trading, live
     - LOG_LEVEL=INFO          # 許容値: DEBUG, INFO, WARNING, ERROR, CRITICAL

注意:
- settings（kabusys.config.Settings）により必須キーは実行時に検査され、未設定時は ValueError が発生します。
- `.env` の読み込み順: OS 環境 > .env.local > .env（.env.local は上書き）。

---

## 使い方（主要ユースケースの例）

以下はライブラリをインポートして主要機能を呼び出す例です。実行コードは Python スクリプトや cron / ワーカーから呼び出して運用します。

- DuckDB 接続の作成（デフォルトパスは settings.duckdb_path）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL（run_daily_etl）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

# ETL を実行（引数省略で今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのスコアリング（OpenAI を使用）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で指定
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {n_written} symbols")
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB の初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events, order_requests, executions テーブルが作成されます
```

- RSS フィード取得（ニュース収集）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

- 研究用ファクター計算
```python
from kabusys.research import calc_momentum, calc_value

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# 統計正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])
```

---

## 設定（環境変数のポイント）
主要な環境変数・設定は kabusys.config.Settings で公開されています。主なもの:

- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / regime_detector が利用）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: メイン DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用途の SQLite パス（data/monitoring.db）
- KABUSYS_ENV: 環境。development / paper_trading / live
- LOG_LEVEL: ログレベル

設定ファイルの自動読み込みはプロジェクトルート（.git or pyproject.toml）を起点に .env / .env.local を読み込みます。自動読み込みを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成
（この README は提供コードベースに基づいて作成しています）

- src/
  - kabusys/
    - __init__.py
    - config.py                   # 環境変数・設定管理
    - ai/
      - __init__.py
      - news_nlp.py               # ニュースセンチメント（銘柄ごと）スコアリング
      - regime_detector.py        # 市場レジーム判定（ETF MA + マクロニュース）
    - data/
      - __init__.py
      - jquants_client.py         # J-Quants API クライアント（取得 + 保存）
      - pipeline.py               # ETL パイプライン（run_daily_etl 等）
      - etl.py                    # ETL の公開インターフェース（ETLResult）
      - news_collector.py         # RSS フィード取得・前処理
      - calendar_management.py    # マーケットカレンダー管理（is_trading_day 等）
      - quality.py                # データ品質チェック
      - stats.py                  # 統計ユーティリティ（zscore_normalize）
      - audit.py                  # 監査ログスキーマ初期化
    - research/
      - __init__.py
      - factor_research.py        # ファクター算出（momentum, value, volatility）
      - feature_exploration.py    # forward returns, IC, summary, rank

---

## 運用上の注意 / ベストプラクティス
- ルックアヘッドバイアス対策として、モジュールの多くは `date` や `target_date` を外部から受け取るよう実装されています。内部で `date.today()` / `datetime.today()` を安易に使わないでください。
- OpenAI 呼び出しや HTTP リクエストにはリトライとバックオフのロジックが入っていますが、API コスト・レート制限に注意してください。
- ETL 実行時は DuckDB の適切なバックアップやスナップショット戦略を検討してください（監査ログは削除しない前提）。
- 本番（live）環境に切り替える際は KABUSYS_ENV を `live` に設定し、発注系の設定（kabu API 等）を正しく行ってください。paper_trading 環境を活用して検証してください。

---

## 貢献・開発
- コードスタイルはドキュメントにあわせて一貫したログ出力・例外ハンドリング・型注釈を心がけています。
- テストを追加する際は、外部 API 呼び出しをモック（OpenAI / J-Quants / HTTP）してユニットテストを作成してください。
- .env の自動読み込みはテストで邪魔になることがあるため、テスト実行時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定するとよいです。

---

質問や README に追加してほしい項目があれば教えてください。具体的な実行スクリプト例（systemd / cron / Airflow / Docker-compose など）や `.env.example` のサンプルも用意できます。