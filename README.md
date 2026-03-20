# KabuSys

日本株向けの自動売買（アルゴリズム取引）基盤ライブラリです。  
データ取得・ETL・特徴量生成・シグナル生成・監査（オーディット）など、戦略実行に必要な主要コンポーネントを提供します。

> 注意: このリポジトリはライブラリ／フレームワークとして機能するモジュール群を含みます。実際の運用では本ライブラリを組み合わせたアプリケーション層（ジョブスケジューラ、発注ブリッジ、モニタリングなど）を別途実装してください。

## 主な特徴（機能一覧）

- 環境変数 / .env の自動読み込みと型チェック（kabusys.config）
  - プロジェクトルート（.git / pyproject.toml）基準で .env を自動読み込み
  - 必須キーの検査・便利プロパティを提供
- データ取得・保存（kabusys.data）
  - J-Quants API クライアント（ページネーション・リトライ・レートリミット・自動リフレッシュ）
  - RSS ベースのニュース収集（SSRF対策、トラッキングパラメータ除去、ID生成）
  - DuckDB スキーマ定義と初期化ユーティリティ（冪等的なDDL）
  - ETL パイプライン（差分取得、バックフィル、品質チェックのフック）
  - マーケットカレンダー管理（営業日判定、next/prev/trading days）
  - 統計ユーティリティ（Z スコア正規化など）
- 研究用 / 戦略用（kabusys.research, kabusys.strategy）
  - ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - 特徴量エンジニアリング（正規化・ユニバースフィルタ）
  - シグナル生成（複数コンポーネントの重み付け合成、Bear フィルタ、エグジット判定）
- 監査（kabusys.data.audit）
  - シグナル→発注→約定をトレースする監査テーブル設計（UUIDによる一意性・冪等性）
- セキュリティ & 品質設計
  - XMLパースの堅牢化（defusedxml）
  - RSS取得時のSSRF対策、レスポンスサイズ制限（DoS対策）
  - DB操作は冪等性を考慮（ON CONFLICT / トランザクション）

## 動作環境 / 前提

- Python 3.10 以上（PEP 604 表記などを利用）
- 必要な Python パッケージ（最低限）
  - duckdb
  - defusedxml
- ネットワーク経由の API 利用には J-Quants のリフレッシュトークン等が必要

例（インストール）:
```bash
python -m pip install "duckdb" "defusedxml"
# 開発中はソース直下で:
python -m pip install -e .
```

## セットアップ手順

1. リポジトリをクローン／ダウンロード
2. Python 仮想環境を作成して依存をインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb defusedxml
   pip install -e .
   ```
3. 環境変数（.env）を準備
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動読み込みされます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 必須キー（kabusys.config が参照）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意 / デフォルト:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG|INFO|...) — デフォルト: INFO
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db

   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマ初期化
   - 初回はスキーマを作成します。パスは settings.duckdb_path（デフォルト: data/kabusys.duckdb）
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

## 使い方（基本的なワークフロー例）

以下はライブラリ API を直接呼び出す簡単なコード例です。実運用ではジョブスケジューラ（cron / Airflow / Dagster 等）に組み込むことを想定しています。

- 日次 ETL 実行（市場カレンダー取得 → 株価差分取得 → 財務取得 → 品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

# DB 初期化（初回のみ）
conn = init_schema("data/kabusys.duckdb")

# 日次 ETL を実行
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量構築（feature engineering）
```python
from datetime import date
import duckdb
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

- シグナル生成
```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
n_signals = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {n_signals}")
```

- ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コード集合
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

- カレンダー更新バッチ（夜間ジョブ）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"market_calendar saved: {saved}")
```

## 実装上の注意点 / 設計ポリシー（抜粋）

- ルックアヘッドバイアス対策（戦略・研究モジュールは target_date 時点までの情報のみを使用）
- ETL / 保存処理は冪等性（ON CONFLICT / トランザクション）を重視
- ネットワーク処理に関する堅牢化（リトライ・バックオフ・レスポンスサイズ制限）
- RSS取得に関しては SSRF 対策やトラッキング除去等の前処理を実装
- DuckDB を単一の真実のデータソースとして扱い、テーブル群（Raw / Processed / Feature / Execution）を定義

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境設定の読み込み・検証（settings）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（fetch/save のユーティリティ）
    - news_collector.py
      - RSS 取得・前処理・DB 保存
    - schema.py
      - DuckDB スキーマ定義・初期化（init_schema / get_connection）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - pipeline.py
      - ETL パイプライン（run_daily_etl 等）
    - calendar_management.py
      - 市場カレンダー管理（営業日判定・更新ジョブ）
    - audit.py
      - 監査テーブル定義と初期化（signal_events / order_requests / executions）
    - features.py
      - data.stats の再エクスポート
  - research/
    - __init__.py
    - factor_research.py
      - モメンタム / ボラティリティ / バリュー等のファクター計算
    - feature_exploration.py
      - 将来リターン、IC、統計サマリ等の研究用ユーティリティ
  - strategy/
    - __init__.py
    - feature_engineering.py
      - ファクター統合・正規化・features への書き込み
    - signal_generator.py
      - final_score の計算と signals への書き込み
  - execution/
    - __init__.py
      - （発注・ブローカー連携層は今後実装想定）
  - monitoring/
    - （モニタリング用モジュールを想定）

（上記は主要モジュールの要約です。詳細は各モジュールの docstring を参照してください。）

## 開発 / テストについて

- 自動環境読み込みは .env をプロジェクトルート（.git / pyproject.toml の親）から読み込みます。テスト時には `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効にできます。
- DuckDB のインメモリ接続は db_path に `":memory:"` を渡すことで可能です（テストで便利）。
- ネットワーク呼び出しは urllib を使用しており、ユニットテストではネットワーク部分（_urlopen / _request など）をモックしてください。

## 参考 / 追加ドキュメント

- 各モジュールの docstring（ソース内に詳細な設計・仕様説明があります）
- DataPlatform.md, StrategyModel.md 等（リポジトリ内にあれば参照してください）

---

不明点や README の追加記載（CI 手順、運用時のバックテスト例、デプロイ手順など）が必要でしたら、目的に応じて追補します。