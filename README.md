# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリ群です。J-Quants や各種 RSS / ニュース、OpenAI（LLM）、および DuckDB を組み合わせて、データ収集（ETL） → 品質チェック → ファクター計算 → ニュース NLP / レジーム判定 → 監査ログ（発注/約定追跡）といったワークフローを提供します。

主な設計方針
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を不用意に参照しない）
- DuckDB を中心とした軽量かつ冪等（idempotent）な ETL / 保存処理
- 外部 API 呼出しはリトライ・レート制御・フェイルセーフを備える
- テスト容易性を考慮した依存注入やモックポイントを提供

---

## 機能一覧

- データ取得・ETL
  - J-Quants API クライアント（株価日足 / 財務 / 上場銘柄 / 市場カレンダー）
  - ETL パイプライン（差分取得、バックフィル、品質チェック）
  - ニュース収集（RSS → raw_news 保存、SSRF 対策、前処理）
  - 市場カレンダー管理（営業日判定 / next/prev / バッチ更新ジョブ）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）

- 研究（Research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、ランク化
  - Zスコア正規化ユーティリティ

- AI（ニュース NLP / レジーム判定）
  - ニュースを銘柄別に集約して OpenAI へ一括送信 → ai_scores へ保存
  - ETF（1321）200 日 MA とマクロニュースセンチメントを合成した市場レジーム判定

- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定 のトレーサビリティテーブル群（UUID ベース）
  - 監査用 DuckDB 初期化ユーティリティ

- 設定管理
  - .env/.env.local 自動ロード（プロジェクトルート判定）
  - settings オブジェクト経由で型安全にアクセス可能

---

## 要件

- Python 3.10 以上
- 推奨ライブラリ（最低限）
  - duckdb
  - openai
  - defusedxml

インストール例:
```bash
python -m pip install "duckdb" "openai" "defusedxml"
# 開発時はプロジェクトルートで
# pip install -e . が使えるセットアップがあればそれも併用
```

（プロジェクト独自の requirements.txt / setup がある場合はそちらを使用してください）

---

## セットアップ手順

1. リポジトリをクローン（もしくはソースを配置）
2. Python 仮想環境を作成・有効化
3. 依存ライブラリをインストール（上記参照）
4. 環境変数を設定
   - 推奨: プロジェクトルートに `.env` または `.env.local` を作成
   - 自動ロード: パッケージ import 時にプロジェクトルートの .env/.env.local を自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）

必須（基本的に必要になる）環境変数例:
```
JQUANTS_REFRESH_TOKEN=xxxxx        # J-Quants リフレッシュトークン（必須：ETL 用）
OPENAI_API_KEY=sk-xxxxx            # OpenAI API キー（ニュース NLP / レジーム判定で必須）
KABU_API_PASSWORD=xxxxx            # kabuステーション API 用パスワード（発注機能で必須）
```

任意 / デフォルト値あり:
```
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PID_FILE_PATH=data/execution.pid
KILL_FLAG_PATH=data/kill.flag
KILL_FLAG_CLEAR_ON_START=0
CPU_THRESHOLD_PCT=90.0
MEMORY_THRESHOLD_PCT=85.0
DISK_THRESHOLD_PCT=90.0
KABUSYS_ENV=development            # development | paper_trading | live
LOG_LEVEL=INFO                     # DEBUG | INFO | WARNING | ERROR | CRITICAL
LINE_CHANNEL_ACCESS_TOKEN=         # LINE 通知用（任意）
LINE_USER_ID=                      # LINE 通知用（任意）
```

注意:
- 環境変数の必須チェックは `kabusys.config.settings` が行います。必須変数が欠けているとプロパティアクセス時に ValueError が送出されます。
- .env のパースは基本的な shell 形式をサポートします。プロジェクトルートは .git または pyproject.toml を上位階層に探索して判定します。

---

## データベース初期化（監査ログ例）

監査ログ専用の DuckDB を初期化するには:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は duckdb.DuckDBPyConnection。以後監査テーブルが利用可能
```

既存の DuckDB 接続に監査スキーマを追加する場合は `init_audit_schema(conn, transactional=True)` を利用できます。

---

## 基本的な使い方（例）

- settings を参照する
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

- 日次 ETL 実行（J-Quants からの差分取得 → 保存 → 品質チェック）
```python
import duckdb
from kabusys.data.pipeline import run_daily_etl
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコア付け
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {written} codes")
# OpenAI API キーは OPENAI_API_KEY または score_news の api_key 引数で指定
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- マーケットカレンダーの利用
```python
from kabusys.data.calendar_management import (
    is_trading_day, next_trading_day, prev_trading_day, get_trading_days
)
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意:
- AI 関連関数は OpenAI API 呼び出しを行います。API キーと通信のレート制限に注意してください。
- J-Quants へのアクセスは `JQUANTS_REFRESH_TOKEN` を使って id_token を取得します。頻繁なリクエストはレート制限の対象になります。

---

## ディレクトリ構成

以下は主要なファイル・モジュール構成（省略あり）です:

- src/kabusys/
  - __init__.py  (パッケージ定義、__version__ = "0.1.0")
  - config.py    (環境変数 / settings 管理、.env 自動ロード)
  - ai/
    - __init__.py
    - news_nlp.py         (ニュースの LLM スコアリング、ai_scores への保存)
    - regime_detector.py  (ETF MA とマクロニュースから市場レジーム判定)
  - data/
    - __init__.py
    - jquants_client.py   (J-Quants API クライアント / 保存関数)
    - pipeline.py         (ETL パイプライン / run_daily_etl 等)
    - etl.py              (ETLResult の再エクスポート)
    - news_collector.py   (RSS 収集・前処理・raw_news 保存)
    - calendar_management.py (market_calendar 管理 / 営業日判定)
    - quality.py          (データ品質チェック)
    - stats.py            (Zスコア正規化等)
    - audit.py            (監査ログ DDL / 初期化ユーティリティ)
  - research/
    - __init__.py
    - factor_research.py  (モメンタム / ボラ / バリュー計算)
    - feature_exploration.py (forward returns / IC / summary / rank)
  - ai/、research/、data/ 以下に補助関数・ユーティリティが実装されています。

---

## 実運用上の注意点

- KABUSYS_ENV を `live` に設定すると実際の発注や外部連携機能を有効にする想定です。運用時は十分にテスト・確認してください。
- 発注・約定周りのテーブルは監査目的で削除しないことを前提に設計されています（FK は ON DELETE RESTRICT）。
- OpenAI や J-Quants などの外部 API キー／料金、及びそれらの利用規約に従って運用してください。
- .env やシークレットは適切に管理し、ソース管理に含めないでください。

---

## 開発者向けメモ

- 自動で .env を読み込む処理は `kabusys.config` 内にあり、プロジェクトルート（.git または pyproject.toml を基準）を探索します。テスト環境などで自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出し周り・RSS の URL オープン処理などいくつかの箇所はテスト時にモック差し替えられるように設計されています（ユニットテストでの差替えポイントが明示されています）。
- DuckDB のバージョン依存（executemany の挙動など）に留意して実装しています。

---

README に書かれている以外の詳細は各モジュールの docstring を参照してください。必要であれば README に追記・改善しますので、具体的に知りたい箇所を教えてください。