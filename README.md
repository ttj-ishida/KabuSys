# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- 前提条件 / 依存関係
- セットアップ手順
- 使い方（簡易例）
- 環境変数一覧
- ディレクトリ構成（主要ファイル説明）
- 開発上の留意点

---

## プロジェクト概要

KabuSys は、J-Quants 等から日本株データを取得して DuckDB に格納し、研究（research）で設計されたファクターを用いて特徴量（features）を構築、戦略ロジックでシグナルを生成するためのライブラリ群です。ニュース収集やマーケットカレンダー管理、ETL の差分更新ロジック、監査ログ（発注 → 約定のトレーサビリティ）など、実運用を想定した機能セットを備えています。

設計方針の一部:
- ルックアヘッドバイアス防止（target_date 時点のデータのみ使用）
- DuckDB ベースでローカルに永続化、冪等性（ON CONFLICT/UPSERT）
- 外部 API 呼び出しは data 層に集約
- 本番口座への直接発注部分（execution）は分離

---

## 機能一覧

主な機能:
- 環境変数 / .env 管理（自動読み込み機構）
- J-Quants API クライアント（レート制限・リトライ・トークン更新対応）
- DuckDB スキーマ定義・初期化（多層スキーマ: raw / processed / feature / execution）
- ETL パイプライン（差分更新、バックフィル、品質チェックフック）
- ニュース収集（RSS、SSRF対策、記事正規化、銘柄抽出）
- マーケットカレンダー管理（営業日判定・next/prev/trading days）
- 研究用ファクター計算（momentum / volatility / value 等）
- 特徴量作成（Zスコア正規化、ユニバースフィルタ、features テーブルへ UPSERT）
- シグナル生成（ファクターと AI スコア統合、BUY/SELL 生成、SELL 優先）
- 監査ログスキーマ（signal_events / order_requests / executions 等）
- ユーティリティ（統計関数 zscore_normalize 等）

---

## 前提条件 / 依存関係

- Python 3.10 以上（型注釈で | 演算子を使用）
- 必要ライブラリ（少なくとも下記を導入してください）:
  - duckdb
  - defusedxml

（最小限の依存は上記ですが、実行する機能に応じて標準ライブラリ以外が必要になる可能性があります。）

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

プロジェクトをパッケージとして扱う場合は、setup / pyproject を用意している想定で `pip install -e .` などが可能です。

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境作成・有効化
3. 依存ライブラリをインストール（例: duckdb, defusedxml）
4. 環境変数を設定（J-Quants トークン等、下記を参照）。プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
5. DuckDB スキーマを初期化:

Python REPL / スクリプトで:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # デフォルト path は data/kabusys.duckdb
conn.close()
```

---

## 使い方（簡易例）

- 日次 ETL を実行（市場カレンダー・株価・財務の差分取得・品質チェック）:
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
conn.close()
```

- 特徴量を生成（target_date の features を作成）:
```python
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features
from datetime import date

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2026, 3, 1))
print(f"upserted features: {n}")
```

- シグナル生成（features / ai_scores を参照して signals テーブルへ書き込む）:
```python
from kabusys.data.schema import get_connection
from kabusys.strategy import generate_signals
from datetime import date

conn = get_connection("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2026, 3, 1))
print(f"generated signals: {count}")
```

- ニュース収集ジョブ:
```python
from kabusys.data.schema import get_connection
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "8306"}  # 例: 有効銘柄コードセット
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

- カレンダー更新ジョブ:
```python
from kabusys.data.schema import get_connection
from kabusys.data.calendar_management import calendar_update_job

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

---

## 環境変数一覧

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD: kabu ステーション API（発注等）用パスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

任意 / デフォルトあり:
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite パス（monitoring 用。デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境（development / paper_trading / live、デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: "1" をセットすると .env 自動読み込みを無効化

注意:
- プロジェクトルートにある `.env` と `.env.local` は自動的に読み込まれます（OS 環境変数を優先）。`.env.local` は `.env` を上書きします。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主要モジュールと機能の概略です（パスは src/kabusys/...）。

- __init__.py
  - パッケージメタ情報（__version__）とサブパッケージ公開

- config.py
  - 環境変数ロード、Settings クラス（各種設定プロパティ）

- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント（レート制御・リトライ・save_* -> DuckDB 保存）
  - schema.py
    - DuckDB スキーマ定義・init_schema / get_connection
  - pipeline.py
    - ETL パイプライン（run_daily_etl / run_prices_etl 等）
  - news_collector.py
    - RSS 収集・前処理・DB 保存・銘柄抽出
  - calendar_management.py
    - market_calendar 管理、営業日判定、calendar_update_job
  - features.py
    - zscore_normalize の再エクスポート
  - stats.py
    - zscore_normalize 実装
  - audit.py
    - 監査ログ用 DDL（signal_events / order_requests / executions 等）
  - その他：quality モジュール想定（品質チェック。今回コードベースでは参照あり）

- research/
  - __init__.py
  - factor_research.py
    - momentum / volatility / value 等のファクター計算（prices_daily / raw_financials を参照）
  - feature_exploration.py
    - 将来リターン計算、IC（Spearman）計算、統計サマリ等

- strategy/
  - __init__.py
  - feature_engineering.py
    - research の raw ファクターを統合して features テーブルへ保存（Z スコア正規化・ユニバースフィルタ）
  - signal_generator.py
    - features と ai_scores を統合して final_score を計算、BUY/SELL を signals テーブルへ保存

- execution/
  - __init__.py
  - （発注ロジックはこの層に実装。今回のコードでは空の初期化ファイルのみ）

---

## 開発上の留意点 / 追加情報

- ルックアヘッドバイアス対策のため、全ての計算は target_date 時点のデータのみを使用する設計になっています。データの取得タイミング（fetched_at）や DB 保存タイミングを意識して運用してください。
- DuckDB の SQL を多用しパフォーマンスを考慮しています。大量データを扱う際はインデックスやクエリコストに注意してください。
- news_collector は SSRF 防止、XML 脆弱性対策（defusedxml）、レスポンスサイズ制限など堅牢性に配慮しています。
- J-Quants API はレート制限（120 req/min）に合わせた RateLimiter を内蔵しています。並列で大量リクエストを投げないように設計されています。
- production（live）環境では KABUSYS_ENV を `live` に設定し、発注・監査ログの取り扱いに注意してください。
- .env 自動ロード処理はプロジェクトルート（.git または pyproject.toml が存在する階層）を探索して行います。テスト環境などで自動ロードを抑制したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

README は以上です。必要であれば、インストール用の pyproject.toml / requirements.txt やデプロイ手順、より詳細な API リファレンス用ドキュメント（関数引数/戻り値の詳細、品質チェック一覧など）も作成できます。どの追加情報が必要か教えてください。