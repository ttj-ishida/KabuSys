# KabuSys

日本株向け自動売買／データプラットフォーム用ライブラリ。  
データ取得（J-Quants）・ETL・データ品質チェック・ニュースNLP（OpenAI）・市場レジーム判定・監査ログなどを備えたモジュール群を提供します。

---

## 概要

KabuSys は日本株のデータ基盤とリサーチ／自動売買のための共通ライブラリです。  
主に次を目的としています。

- J-Quants API からの株価・財務・カレンダー取得（ETL）
- DuckDB によるデータ保存・集計
- ニュース記事収集と OpenAI による NLP スコアリング
- 市場レジーム（bull/neutral/bear）判定
- 監査ログ（signal → order → execution の追跡）用スキーマ初期化
- データ品質チェック・ファクター計算・リサーチユーティリティ

設計上の特徴：
- ルックアヘッドバイアス（未来情報参照）を防ぐ実装方針
- 冪等性（INSERT ... ON CONFLICT / DELETE→INSERT パターン）
- 外部 API 呼び出しに対する堅牢なリトライ・レート制御
- DuckDB を中心にした軽量かつ高速な処理

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（fetch_* / save_*）
  - カレンダー管理（is_trading_day, next_trading_day, get_trading_days, calendar_update_job）
  - ニュース収集（RSS 取得・正規化・raw_news 保存ロジック）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - ニュース NLP スコアリング（score_news）
  - レジーム判定（score_regime）
- research/
  - ファクター計算（momentum, value, volatility）
  - 特徴量探索（forward returns, IC, summary）
- 設定管理（kabusys.config.Settings）
  - .env 自動読み込み（プロジェクトルート検出）
  - 環境変数の必須チェックおよび型変換ユーティリティ

---

## 前提（依存関係）

少なくとも以下が必要です（バージョンは適宜決めてください）:

- Python 3.10+
- duckdb
- openai (OpenAI の Python SDK)
- defusedxml

インストール例（仮）:
```bash
python -m pip install duckdb openai defusedxml
# 開発・パッケージ化する場合
pip install -e .
```

※ 実際の requirements.txt / pyproject.toml はプロジェクトに合わせて用意してください。

---

## 環境変数 / .env

KabuSys は環境変数または .env / .env.local から設定を読み込みます（プロジェクトルートに .git または pyproject.toml がある場合に自動読込）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な必須環境変数（例）:

- JQUANTS_REFRESH_TOKEN - J-Quants のリフレッシュトークン（ETL 用）
- OPENAI_API_KEY - OpenAI API キー（news_nlp / regime_detector 用）
- KABU_API_PASSWORD - kabuステーション API パスワード（execution 関連）
- SLACK_BOT_TOKEN - Slack 通知トークン（監視・通知）
- SLACK_CHANNEL_ID - Slack チャンネル ID

任意・デフォルト設定:

- KABUSYS_ENV (development | paper_trading | live) - デフォルト: development
- LOG_LEVEL (DEBUG|INFO|...) - デフォルト: INFO
- DUCKDB_PATH - デフォルト: data/kabusys.duckdb
- SQLITE_PATH - デフォルト: data/monitoring.db
- PID_FILE_PATH - デフォルト: data/execution.pid
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT - 監視しきい値

例 .env:
```
JQUANTS_REFRESH_TOKEN=xxxx...
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン / 作業ディレクトリに移動
2. 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```
3. 必要パッケージをインストール
   ```bash
   pip install duckdb openai defusedxml
   # 開発モードでパッケージをインストールする場合
   pip install -e .
   ```
4. .env を作成（上記を参照）
5. DuckDB ファイルの親ディレクトリなどを作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

---

## 使い方（主な API / サンプル）

以下サンプルは概念的な使用例です。適切な例外処理やログ設定を追加してください。

- DuckDB 接続の作成と ETL 実行（日次 ETL）
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path は Path オブジェクト
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str("data/kabusys.duckdb"))
written = score_news(conn, target_date=date(2026, 3, 20))  # 戻り値: 書き込んだ銘柄数
print("書き込み銘柄数:", written)
```

- 市場レジーム判定
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化（別 DB を利用する場合）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit_kabusys.duckdb")
# conn は duckdb.DuckDBPyConnection
```

- カレンダー関連ユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026,3,20)
print("is_trading_day:", is_trading_day(conn, d))
print("next_trading_day:", next_trading_day(conn, d))
```

- RSS フェッチ（ニュース収集の一部；ネットワークエラーに注意）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

---

## 実運用上の注意点

- OpenAI や J-Quants の API キーは厳重に管理してください。ローカルの .env はリポジトリに含めないでください。
- ETL の実行はジョブとしてスケジュールし、ログ・監視を有効にしてください。
- Live 口座接続や発注ロジックを統合する際は、KABUSYS_ENV を `paper_trading` / `live` に正しく設定してください。
- DuckDB のファイルは定期的にバックアップしてください。監査ログは削除しない前提です。
- ニュース NLP や OpenAI 呼び出しはコストとレート制限に留意してください。エラー時はフェイルセーフ（スコア 0.0）で動作する設計です。

---

## ディレクトリ構成

リポジトリ（src/kabusys） の主なファイル・ディレクトリ:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py         — ニュース NLP スコアリング（score_news）
    - regime_detector.py  — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py         — ETL メインロジック（run_daily_etl 他）
    - jquants_client.py   — J-Quants API クライアント（fetch_/save_）
    - calendar_management.py — 市場カレンダー管理
    - news_collector.py   — RSS 収集・前処理
    - quality.py          — データ品質チェック（QualityIssue 等）
    - stats.py            — zscore_normalize 等の統計ユーティリティ
    - audit.py            — 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
    - pipeline.py         — ETLResult dataclass の定義（再エクスポート via etl.py）
  - research/
    - __init__.py
    - factor_research.py  — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — forward returns, IC, summary, rank
  - monitoring/ (存在が示唆されるが実装ファイルはここにない場合あり)
  - execution/ (発注実装用の名前空間)
  - strategy/ (戦略ロジック用の名前空間)

---

## 貢献・拡張

- 新しい ETL 経路・データソースを追加する際は jquants_client の設計（レート制御・リトライ・トークンリフレッシュ）に倣ってください。
- テストでは外部 API 呼び出し部分（OpenAI, urllib）をモックするユーティリティが用意されています（モジュール内でテストフックを使えるように実装済み）。
- セキュリティ: news_collector は SSRF・XML Bomb 対策を組み込んでいますが、外部フィードを追加する場合はソースの信頼性を確認してください。

---

README の内容はソースコードの実装状況に応じて更新してください。追加の具体的な使用例や運用手順（CI/CD、ジョブスケジューラ、監視設定）が必要であれば、その要件に合わせたドキュメントを作成します。