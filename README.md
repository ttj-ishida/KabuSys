# KabuSys

日本株向けの自動売買フレームワーク（部分実装）。データ取得・ETL、特徴量生成、シグナル生成、ニュース収集、監査ログ・スキーマ管理などを提供します。

> 本リポジトリはモジュール群（src/kabusys/…）の抜粋をもとに README を作成しています。実行前に各依存ライブラリや環境変数を適切に設定してください。

## プロジェクト概要

KabuSys は次のレイヤーで構成されたトレーディング基盤を目指します。

- Raw Layer: 外部 API（主に J-Quants）から取得した生データを保存
- Processed Layer: 日足・財務・カレンダーなど整形済みデータ
- Feature Layer: 戦略／AI 用の特徴量（features / ai_scores）
- Execution Layer: シグナル・発注・約定・ポジション管理・監査ログ

主な設計方針は、冪等性（DB の ON CONFLICT を利用）、ルックアヘッドバイアス回避、外部 API のレート制御・リトライ、DB トランザクションによる原子性の確保です。

## 主な機能一覧

- J-Quants API クライアント（レートリミット、リトライ、トークン自動リフレッシュ）
  - 株価日足 / 財務データ / マーケットカレンダー取得 + DuckDB 保存
- ETL パイプライン（差分取得、バックフィル、品質チェックフック）
- DuckDB スキーマ定義と初期化（init_schema）
- 研究向けファクター計算（momentum, volatility, value）
- 特徴量エンジニアリング（Z-score 正規化、ユニバースフィルタ、features テーブル保存）
- シグナル生成（ファクター + AI スコアの統合 → BUY / SELL の決定）
- ニュース収集（RSS からのフェッチ、前処理、raw_news 保存、銘柄抽出）
- マーケットカレンダー管理（営業日判定・前後営業日検索）
- 監査ログ（signal_events / order_requests / executions など）

## 要件

- Python 3.10 以上（型記法や pathlib などに依存）
- 必要パッケージ（例）
  - duckdb
  - defusedxml
- 実運用で使う場合は J-Quants API アクセスに必要なネットワーク構成とトークン、kabuステーション API、Slack トークン等が必要

インストール例（ローカル開発）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# パッケージをeditableインストールする場合（pyproject.toml/setup があれば）
# pip install -e .
```

## 環境変数（.env）

パッケージ起動時にプロジェクトルートの `.env` および `.env.local` を自動で読み込みします（CWD には依存せず、__file__ を起点にプロジェクトルートを探索）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabuステーション API ベース URL（省略可、デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（モニタリング用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

例 (.env.example):
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

## セットアップ手順（簡易）

1. Python 仮想環境を作成・有効化
2. 必要パッケージをインストール（duckdb, defusedxml など）
3. プロジェクトルートに `.env`（上記キーを設定）を作成
4. DuckDB スキーマ初期化（スクリプトまたは REPL で実行）

サンプル: DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
conn.close()
```

## 使い方（主要 API の例）

以下は Python REPL / スクリプトでの利用例です。

- ETL（1日分の差分 ETL を実行）
```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

# DB 初期化（ファイルなければ作成）
conn = init_schema("data/kabusys.duckdb")

# 日次 ETL（target_date を省略すると今日）
result = run_daily_etl(conn, target_date=date(2024, 1, 10))
print(result.to_dict())

conn.close()
```

- 特徴量ビルド
```python
from datetime import date
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, date(2024, 1, 10))
print("features upserted:", count)
conn.close()
```

- シグナル生成
```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
total = generate_signals(conn, date(2024, 1, 10))
print("signals written:", total)
conn.close()
```

- ニュース収集（RSS）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)
conn.close()
```

- J-Quants から日足を直接取得して保存（テスト用）
```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import get_connection, init_schema

conn = init_schema(":memory:")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,10))
jq.save_daily_quotes(conn, records)
```

## 主要モジュール（責務の概要）

- kabusys.config
  - .env 自動読込、環境変数取得ユーティリティ（Settings）
- kabusys.data
  - jquants_client: J-Quants API 呼び出し・保存（rate limit / retry / token refresh）
  - schema: DuckDB スキーマ定義と init_schema / get_connection
  - pipeline: ETL の統合処理（run_daily_etl, run_prices_etl, …）
  - news_collector: RSS フェッチ、前処理、raw_news 保存、銘柄抽出
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - stats: zscore_normalize（共通統計ユーティリティ）
- kabusys.research
  - factor_research: momentum/volatility/value を計算
  - feature_exploration: 将来リターン計算、IC、統計サマリ等
- kabusys.strategy
  - feature_engineering.build_features: features テーブル作成
  - signal_generator.generate_signals: final_score 計算と signals への書き込み
- kabusys.execution / kabusys.monitoring
  - （execution, monitoring 用の名前空間／実装の拡張ポイント）

## ディレクトリ構成

（抜粋。実際のリポジトリにはさらにファイルやドキュメントが存在する可能性があります）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - stats.py
      - pipeline.py
      - calendar_management.py
      - features.py
      - audit.py
      - (その他: quality.py 等)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
      - feature_engineering.py
      - signal_generator.py
    - execution/
      - __init__.py
    - monitoring/
      - (監視関連モジュール)
- pyproject.toml / setup.cfg / requirements.txt（プロジェクトに応じて）

## 運用上の注意・ベストプラクティス

- 環境変数（特にトークン・パスワード）は `.env` に保存する場合、リポジトリにコミットしないこと。`.gitignore` に追加してください。
- DuckDB ファイルは定期的にバックアップしてください。インメモリでは永続化されません。
- J-Quants API のレート制限やトークン管理に注意。モジュールは 120 req/min を守る実装ですが、運用側でも監視を。
- Slack / kabu API など外部サービスと連携する際はリトライ・エラーハンドリングと冪等性を考慮してください。
- テスト時は自動 .env ロードを無効化できます: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

## 開発・拡張ポイント

- execution 層: 実際の注文発行・ブローカーラッパー（kabu API）を実装
- risk management: シグナルをフィルタするリスクエンジン
- AI スコアの生成と統合（ai_scores のパイプライン）
- quality モジュールの実装（データ品質判定ルール）
- CI/CD: スキーマ変更時のマイグレーション手順

---

必要であれば、README に含める具体的な CLI スクリプト例、docker-compose 構成、より詳細な .env.example、テストの書き方（ユニットテスト/モック）なども追加できます。どの情報を補足しましょうか？