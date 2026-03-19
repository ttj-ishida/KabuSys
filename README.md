# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ群です。  
データ取得（J-Quants）→ ETL（DuckDB 保存）→ 特徴量計算 → シグナル生成 → 発注（execution 層）という一連のパイプラインを想定した実装を提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（target_date 時点のデータのみで処理）
- 冪等性（ON CONFLICT、トランザクション）を重視
- 外部 API 呼び出しは最小限（テストしやすく、発注層を分離）
- DuckDB を中心にオンプレ／ローカル実行可能な構成

---

## 機能一覧

- 環境設定管理
  - .env / 環境変数の自動ロード（パッケージ起点でプロジェクトルートを探索）
  - 必須変数チェック（settings オブジェクト）

- データ取得・保存（data）
  - J-Quants API クライアント（認証・リトライ・レートリミット・ページネーション対応）
  - 株価（daily quotes）、財務データ、マーケットカレンダーの取得・DuckDB 保存（冪等）
  - RSS ニュース収集（SSRF対策・gzip対応・トラッキング除去・記事IDハッシュ化）と銘柄紐付け
  - DuckDB スキーマ定義・初期化ユーティリティ
  - ETL パイプライン（差分更新・バックフィル・品質チェック連携）
  - マーケットカレンダー管理（営業日判定、前後営業日取得、カレンダー更新ジョブ）
  - 統計ユーティリティ（Zスコア正規化等）

- 研究（research）
  - ファクター計算（momentum / volatility / value）
  - 特徴量探索用ユーティリティ（将来リターン計算、IC 計算、統計サマリー）

- 戦略（strategy）
  - 特徴量作成（research の生ファクターを正規化・合成して features テーブルへ UPSERT）
  - シグナル生成（features と ai_scores を統合して final_score を計算、BUY/SELL シグナル生成）
  - 各ステップは target_date に基づく日付単位の置換で冪等化

- ニュース / 監査 / 実行管理
  - raw_news / news_symbols 等の保存と紐付け
  - 監査ログ（signal_events / order_requests / executions）スキーマ（トレーサビリティを重視）

---

## 前提 / 必要環境

- Python 3.9+
- duckdb
- defusedxml
- （標準ライブラリの urllib, datetime 等を使用）

インストール例（推奨：仮想環境内で実行）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# またはプロジェクトに requirements.txt / pyproject.toml があればそれに従う
# pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を有効化し、依存をインストールします。

2. 環境変数（または .env）を用意します。自動ロードはプロジェクトルート（.git または pyproject.toml のある親ディレクトリ）を基準に行われます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

推奨される .env の例（実際の値は各自で設定）:

```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabu ステーション API（発注を行う場合）
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack（通知等）
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789

# DB パス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境
KABUSYS_ENV=development  # development | paper_trading | live
LOG_LEVEL=INFO
```

3. DuckDB スキーマの初期化（ファイルパスは環境変数で上書き可）

例（Python REPL で）:

```python
from kabusys.data.schema import init_schema, get_connection
conn = init_schema("data/kabusys.duckdb")  # data ディレクトリが無ければ作成される
conn.close()
```

---

## 使い方（代表的なユースケース）

以下はライブラリを使って日次 ETL → 特徴量作成 → シグナル生成を実行するサンプルフローです。

- 日次 ETL（株価・財務・カレンダー取得、品質チェック）

```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
conn.close()
```

- 特徴量のビルド（features テーブルを構築）

```python
from datetime import date
from kabusys.data.schema import get_connection, init_schema
from kabusys.strategy import build_features

conn = init_schema("data/kabusys.duckdb")
n = build_features(conn, target_date=date.today())
print(f"features upserted: {n}")
conn.close()
```

- シグナル生成（features + ai_scores → signals）

```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import generate_signals

conn = init_schema("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals generated: {count}")
conn.close()
```

- ニュース収集ジョブ（RSS から raw_news と news_symbols へ保存）

```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 事前に有効なコードセットを作成
results = run_news_collection(conn, known_codes=known_codes)
print(results)
conn.close()
```

- マーケットカレンダー更新ジョブ

```python
from kabusys.data.schema import init_schema
from kabusys.data.calendar_management import calendar_update_job

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn, lookahead_days=90)
print(f"calendar saved: {saved}")
conn.close()
```

- 設定取得（環境変数からの読み取り）

```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
print(settings.env)
```

注意点：
- 各関数は DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を受け取ります。init_schema は接続を返す便利関数です。
- ETL / 保存関数は冪等性を考慮しているため、何度呼んでも重複は上書きまたはスキップされます（ON CONFLICT / DO UPDATE / DO NOTHING）。
- 自動でトークンをリフレッシュする処理やレート制御を J-Quants クライアントは持っています。API トークン等は settings から取得してください。

---

## ディレクトリ構成（主要ファイル）

リポジトリの重要なモジュール・ファイルを抜粋した構成イメージ:

- src/
  - kabusys/
    - __init__.py
    - config.py                              # 環境変数管理（settings）
    - data/
      - __init__.py
      - jquants_client.py                     # J-Quants API クライアント（取得 + 保存）
      - news_collector.py                     # RSS 収集・前処理・保存
      - schema.py                             # DuckDB スキーマ定義・init_schema
      - stats.py                              # 統計ユーティリティ（zscore_normalize）
      - pipeline.py                           # ETL パイプライン（run_daily_etl 等）
      - calendar_management.py                # カレンダー管理（営業日判定等）
      - audit.py                              # 監査ログスキーマ
      - features.py                           # data.stats の再エクスポート
    - research/
      - __init__.py
      - factor_research.py                    # momentum/volatility/value ファクター計算
      - feature_exploration.py                # 将来リターン / IC / 統計サマリー
    - strategy/
      - __init__.py
      - feature_engineering.py                # ファクター正規化・features テーブルへの保存
      - signal_generator.py                   # final_score 計算・BUY/SELL 生成
    - execution/                               # 発注/ブローカー連携のためのプレースホルダ（空 __init__ あり）
    - monitoring/                              # 監視・運用用モジュール（将来追加想定）

---

## 開発・運用上の注意

- 環境
  - 実運用（live）では `KABUSYS_ENV=live` を設定してください。paper_trading / development を切り替えて挙動を変えられます。
  - 自動 .env ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

- DB
  - DuckDB のファイルはデフォルトで `data/kabusys.duckdb`（settings.duckdb_path）です。バックアップや運用ポリシーを各自で検討してください。

- テスト
  - ETL / API 呼び出し部分は id_token を注入可能に作ってあります（テスト時はモック化しやすい）。
  - news_collector._urlopen などはテストで差し替え可能な設計です。

- セキュリティ
  - RSS の取得には SSRF 対策、XML パーサーには defusedxml を使用しています。
  - API トークン等は安全に管理してください（CI/Secrets 管理推奨）。

---

## 参考

- 設計ドキュメント（コード内コメントに参照される StrategyModel.md / DataPlatform.md / DataSchema.md 等）はリポジトリ外に想定されています。実装はそれらの仕様に沿って作られています。

---

この README はコードベースの主要な使い方をまとめたものです。具体的な運用手順・CI/CD 設定・発注ブローカー連携は運用ポリシーに合わせて実装・追加してください。質問やサンプルの拡張が必要であればお知らせください。