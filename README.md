# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォーム向けライブラリです。  
DuckDB をデータ格納に用い、J-Quants API などから市場データ・財務データ・ニュースを取得・保存し、特徴量計算や品質チェック、ETL パイプライン、監査ログなど一連の機能を提供します。

バージョン: 0.1.0

---

## 主要な特徴（機能一覧）

- 環境変数ベースの設定管理（自動 .env ロード、必須値チェック）
- J-Quants API クライアント
  - 日次株価（OHLCV）・財務データ・マーケットカレンダー取得
  - レート制限・リトライ・トークン自動リフレッシュ対応
  - DuckDB への冪等保存ユーティリティ
- DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン
  - 差分取得（バックフィル対応）
  - カレンダー先読み、品質チェック組込みの日次 ETL
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）
  - URL 正規化 / トラッキングパラメータ除去 / SSRF 対策 / gzip 制限
  - raw_news 保存および銘柄紐付け
- マーケットカレンダー管理（営業日判定、次/前営業日取得、更新ジョブ）
- 研究用モジュール
  - ファクター計算（Momentum, Volatility, Value 等）
  - 将来リターン計算 / IC（スピアマン）計算 / 統計サマリー
  - Z スコア正規化ユーティリティ
- 監査ログ（signal → order → execution のトレース用テーブル群）

---

## セットアップ手順

前提:
- Python 3.10 以上（タイプ注釈に PEP 604 などを使用しているため）
- Git などの一般的な開発ツール

1. リポジトリをクローン（任意）:
   git clone <repository-url>

2. 仮想環境を作成して有効化（推奨）:
   python -m venv .venv
   source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要なパッケージをインストール:
   pip install duckdb defusedxml

   （他に requests 等を追加する可能性はあるが、現状のコードは標準ライブラリ＋上記で動作します）

4. パッケージを開発モードでインストール（プロジェクトルートに setup/pyproject がある場合）:
   pip install -e .

5. 環境変数を設定:
   - プロジェクトルートに `.env` / `.env.local` を配置すると自動ロードされます（自動ロードは既定で有効）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須環境変数（例）
- JQUANTS_REFRESH_TOKEN=xxxxx
- KABU_API_PASSWORD=xxxxx
- SLACK_BOT_TOKEN=xxxxx
- SLACK_CHANNEL_ID=xxxxx

オプション
- KABUSYS_ENV=development|paper_trading|live  （デフォルト: development）
- LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL （デフォルト: INFO）
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db

例（.env）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（簡単な導入例）

以下は Python REPL / スクリプトから主要機能を使う簡単な例です。

1) 設定取得
```
from kabusys.config import settings
token = settings.jquants_refresh_token
print(settings.duckdb_path)
```

2) DuckDB スキーマ初期化
```
from kabusys.data.schema import init_schema
conn = init_schema(settings.duckdb_path)  # ":memory:" も可
```

3) 日次 ETL の実行
```
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)
print(result.to_dict())
```

4) ニュース収集ジョブ（RSS）を走らせる
```
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
# known_codes: 有効な銘柄コードのセット（抽出に使用）
known_codes = {"7203", "6758", ...}
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)
```

5) 研究用ファクター計算（例: momentum）
```
from datetime import date
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic, zscore_normalize

d = date(2024, 1, 31)
mom = calc_momentum(conn, d)
fwd = calc_forward_returns(conn, d, horizons=[1,5,21])
# IC 計算例（カラム名を適宜合わせる）
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
# z-score 正規化
normalized = zscore_normalize(mom, ["mom_1m", "ma200_dev"])
```

6) マーケットカレンダーの利用
```
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date

d = date(2024, 1, 1)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

---

## よく使う API（抜粋）

- 設定
  - kabusys.config.settings
    - jquants_refresh_token, kabu_api_password, kabu_api_base_url, slack_bot_token, slack_channel_id, duckdb_path, sqlite_path, env, log_level, is_live, is_paper, is_dev

- データ取得 / 保存
  - kabusys.data.jquants_client.get_id_token(...)
  - kabusys.data.jquants_client.fetch_daily_quotes(...)
  - kabusys.data.jquants_client.save_daily_quotes(conn, records)
  - kabusys.data.jquants_client.fetch_financial_statements(...)
  - kabusys.data.jquants_client.save_financial_statements(conn, records)
  - kabusys.data.jquants_client.fetch_market_calendar(...)

- スキーマ / DB
  - kabusys.data.schema.init_schema(db_path)
  - kabusys.data.schema.get_connection(db_path)
  - kabusys.data.audit.init_audit_schema(conn)

- ETL / パイプライン
  - kabusys.data.pipeline.run_daily_etl(conn, target_date=None, ...)

- ニュース収集
  - kabusys.data.news_collector.fetch_rss(url, source)
  - kabusys.data.news_collector.save_raw_news(conn, articles)
  - kabusys.data.news_collector.run_news_collection(conn, sources=None, known_codes=None)

- 品質チェック
  - kabusys.data.quality.run_all_checks(conn, target_date=None, reference_date=None)

- 研究 / ファクター
  - kabusys.research.calc_momentum(conn, target_date)
  - kabusys.research.calc_volatility(conn, target_date)
  - kabusys.research.calc_value(conn, target_date)
  - kabusys.research.calc_forward_returns(...)
  - kabusys.research.calc_ic(...)
  - kabusys.data.stats.zscore_normalize(...)

---

## ディレクトリ構成

以下はソースツリーの主要ファイル（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/         (発注・実行関連の実装領域、現状空 __init__)
    - strategy/          (戦略実装領域、現状空 __init__)
    - monitoring/        (監視用モジュール群、現状 __init__ 空)
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - stats.py
      - pipeline.py
      - features.py
      - calendar_management.py
      - audit.py
      - etl.py
      - quality.py
    - research/
      - __init__.py
      - feature_exploration.py
      - factor_research.py

（README はリポジトリのルートに配置してください。プロジェクトルートは .git または pyproject.toml を基準に自動で検出され、.env/.env.local を自動ロードします）

---

## 運用上の注意 / 補足

- 自動ロード:
  - パッケージは起動時にプロジェクトルートから `.env` / `.env.local` を自動読み込みします（OS 環境変数が優先されます）。テスト等で無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- J-Quants API:
  - レート制限（120 req/min）を守る実装になっています。ID トークンは自動でリフレッシュされ、401 時は一度だけ再試行します。

- DuckDB スキーマ:
  - init_schema は冪等でテーブルを作成します。監査用のスキーマは init_audit_schema / init_audit_db を利用してください。

- セキュリティ:
  - news_collector は SSRF 対策・XML 外部実行対策（defusedxml）・レスポンスサイズ制限などを実装していますが、運用環境ではさらにネットワークポリシーやプロキシ制御を行ってください。

- ライセンス / コントリビューション:
  - 本リポジトリに付随する LICENSE や CONTRIBUTING を参照してください（無い場合はプロジェクト管理者に確認してください）。

---

必要であれば、README に実行例の追加（CI/CD、Dockerfile、systemd ジョブ、Slack 通知の設定例など）や、requirements.txt / pyproject.toml の推奨セットアップを追記します。どの情報を追加したいか教えてください。