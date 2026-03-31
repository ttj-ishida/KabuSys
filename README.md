# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース NLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（約定トレーサビリティ）などを提供します。

---

## 主な特徴

- J-Quants API からの差分 ETL（株価日足、財務データ、JPX カレンダー）  
  - ページネーション対応、レート制御、トークン自動リフレッシュ、冪等保存
- ニュース収集 & ニュース NLP（OpenAI / gpt-4o-mini）による銘柄別センチメント
- 市場レジーム判定（ETF 1321 の MA + マクロニュースの LLM センチメント合成）
- リサーチ用ファクター計算（モメンタム・ボラティリティ・バリューなど）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ（signal / order_request / executions）と初期化ユーティリティ
- DuckDB をデータプラットフォーム基盤として使用

---

## 前提条件

- Python 3.10+
- ネットワークアクセス（J-Quants / OpenAI / RSS 等）
- 主な依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml

（実際の依存関係は pyproject.toml / requirements.txt を確認してください）

---

## インストール

ソースツリーは src/ 配下にパッケージ（kabusys）があります。開発環境での例:

```bash
# 仮想環境作成（任意）
python -m venv .venv
source .venv/bin/activate

# pip でインストール（プロジェクトルートで実行）
pip install -e ".[dev]"   # または pip install -e .
```

pyproject.toml / requirements がある場合はその指示に従ってください。

---

## 環境変数 / .env

kabusys は起動時に自動でプロジェクトルート（`.git` または `pyproject.toml` があるディレクトリ）を探索し、`.env` → `.env.local` を読み込みます（OS 環境変数を優先）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須となる主要な環境変数（Settings で参照）:

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API のパスワード（発注等で使用）
- SLACK_BOT_TOKEN — Slack 通知に使用
- SLACK_CHANNEL_ID — Slack 通知先チャンネル
- OPENAI_API_KEY — OpenAI 呼び出しに使用

任意／デフォルト値を持つ設定:

- KABUSYS_ENV — `development` / `paper_trading` / `live`（デフォルト `development`）
- LOG_LEVEL — `DEBUG|INFO|WARNING|ERROR|CRITICAL`（デフォルト `INFO`）
- DUCKDB_PATH — DuckDB のパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH — 監視用 SQLite（デフォルト `data/monitoring.db`）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など

プロジェクトには `.env.example` を用意しておき、必要な値をコピーして `.env` を作成してください。

---

## セットアップ手順（簡易）

1. リポジトリをクローン、依存インストール、仮想環境有効化
2. `.env` を作成して必須の環境変数を設定
3. DuckDB データベースファイルの親ディレクトリを作成（settings.duckdb_path の親）
4. 必要に応じて監査DBの初期化

例: 監査テーブル初期化

```python
from pathlib import Path
import duckdb
from kabusys.config import settings
from kabusys.data.audit import init_audit_db

db_path = settings.duckdb_path  # Path オブジェクト
conn = init_audit_db(db_path)   # DDL を作成して接続を返す
# または
# conn = duckdb.connect(str(db_path))
# from kabusys.data.audit import init_audit_schema
# init_audit_schema(conn, transactional=True)
```

---

## 使い方（代表的な API）

以下は最小限の利用例です。詳細は各モジュールの docstring を参照してください。

- DuckDB 接続を作成して ETL を実行（日次 ETL）

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース NLP（指定日分のスコアリング）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY は環境変数でセットしている前提
n = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {n} codes")
```

- 市場レジーム判定（1321 MA + マクロニュース）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査スキーマ初期化（既述。init_audit_db / init_audit_schema を使用）

---

## 主要モジュール一覧（簡易説明）

- kabusys.config
  - 環境変数管理、.env 自動読み込み、Settings クラス（J-Quants / kabu / Slack / DB path 等）
- kabusys.data
  - jquants_client.py: J-Quants API クライアント（取得・保存ユーティリティ）
  - pipeline.py: ETL パイプライン（run_daily_etl 等）
  - calendar_management.py: JPX カレンダーと営業日ロジック
  - news_collector.py: RSS 取得・記事整形・保存ロジック
  - quality.py: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py: zscore_normalize 等の統計ユーティリティ
  - audit.py: 監査ログ（signal/order_request/executions）DDL と初期化
- kabusys.ai
  - news_nlp.py: ニュースをまとめて OpenAI に送り銘柄別スコアを作成
  - regime_detector.py: 市場レジーム判定（MA200 + LLM）
- kabusys.research
  - factor_research.py: Momentum, Volatility, Value ファクター計算
  - feature_exploration.py: 将来リターン計算、IC、統計サマリー 等

ディレクトリ: ソースは `src/kabusys/` に格納されています。

---

## 動作上の注意 / 設計思想のポイント

- Look-ahead バイアス対策:
  - 各処理は明示的な target_date を取り、内部で date.today() に依存しない設計です。
  - データ取得・集計において「target_date 未満 / 以前」のフィルタを厳格に適用しています。
- 冪等性:
  - J-Quants から保存する関数は ON CONFLICT（または個別 DELETE → INSERT）で冪等に保存します。
- フォールバック:
  - market_calendar 未取得時は曜日ベースで営業日判定を行うなど、安全側のフォールバックが実装されています。
- API 呼び出しの堅牢性:
  - J-Quants / OpenAI 呼び出しはリトライ / バックオフ、レート制御、エラー分類を実装しています。

---

## よくあるトラブルシューティング

- 環境変数が足りない / ValueError が発生する  
  - `.env` を作成し、必須変数（JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY 等）を設定してください。KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動ロード挙動を確認できます。
- DuckDB への権限問題 / ディレクトリがない  
  - settings.duckdb_path の親ディレクトリが存在するか確認してください。init_audit_db は親ディレクトリを自動作成します。
- OpenAI 呼び出しで JSON パースエラー  
  - レスポンスの検証は行われていますが、モデル出力が仕様と異なる場合にはスコアをスキップしフォールバック（0.0 など）する設計です。APIキー/モデルやプロンプトを確認してください。

---

## 開発 / テスト

- 自動 .env 読み込みを無効化してテストを行うには:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定する
- OpenAI 呼び出し等はモック化可能（各モジュールは呼び出し部分を別関数化しており unittest.mock.patch が可能）

---

この README はコードベースの主要ポイントをまとめたもので、詳細は各モジュールの docstring および API ドキュメント（存在する場合）を参照してください。必要であればセットアップ手順や使用例を追加で展開します。