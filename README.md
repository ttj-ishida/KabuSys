# KabuSys

日本株向けの自動売買プラットフォーム（ライブラリ）。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル作成、ニュース収集、マーケットカレンダー管理、DuckDB スキーマ定義などを含むモジュール群を提供します。

注意：このリポジトリはライブラリ／バックエンド処理群の実装を含み、実際の注文送信や運用には別途ブローカー連携・運用管理が必要です。

---

## 主な機能

- J-Quants API クライアント
  - 日次株価（OHLCV）、財務データ、JPX マーケットカレンダーの取得（ページネーション対応）
  - レート制限とリトライ、トークン自動リフレッシュ対応
  - DuckDB へ冪等保存（ON CONFLICT / DO UPDATE）

- ETL パイプライン
  - 差分取得（最終取得日からの差分）+ バックフィルによる修正吸収
  - 市場カレンダー／株価／財務データの統合 ETL（run_daily_etl）

- Data スキーマ（DuckDB）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化（init_schema）
  - インデックス定義や制約を含む設計

- 特徴量計算（research）
  - Momentum / Volatility / Value 等のファクター計算
  - クロスセクション Z スコア正規化ユーティリティ

- 特徴量エンジニアリング（strategy.feature_engineering）
  - 生ファクターの合成・ユニバースフィルタ・Z スコアクリップ・features テーブルへの UPSERT（冪等化）

- シグナル生成（strategy.signal_generator）
  - features と AI スコアを統合して final_score を計算
  - Bear レジーム判定、BUY/SELL シグナルの生成と signals テーブルへの書き込み（冪等）

- ニュース収集（data.news_collector）
  - RSS 取得、前処理、記事の正規化・ID 生成、raw_news への保存、銘柄コード抽出と紐付け
  - SSRF 対策・受信サイズ上限・XML 脆弱性対策（defusedxml）

- マーケットカレンダー管理（data.calendar_management）
  - JPX カレンダーの差分取得・更新と営業日判定ユーティリティ

- 監査ログ（data.audit）
  - シグナル→オーダー→約定までのトレース可能な監査テーブル定義

---

## 必要条件

- Python 3.10 以上（typing の | や標準型注釈を利用）
- 必要パッケージ（最小）:
  - duckdb
  - defusedxml

推奨：仮想環境（venv / pyenv）内での実行。

例（pip）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install "duckdb" "defusedxml"
# またはパッケージ化されている場合は pip install -e .
```

（プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください）

---

## 環境変数

自動的にルートの `.env` → `.env.local`（`.env.local` が優先）を読み込みます（CWD ではなくソースファイル位置からプロジェクトルートを検出）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（README 用の抜粋）:

- J-Quants / API
  - JQUANTS_REFRESH_TOKEN (必須)
- kabuステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (省略時: http://localhost:18080/kabusapi)
- Slack（通知などで利用）
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- DB パス
  - DUCKDB_PATH（省略時: data/kabusys.duckdb）
  - SQLITE_PATH（省略時: data/monitoring.db）
- 実行モード / ログ
  - KABUSYS_ENV: development | paper_trading | live（省略時: development）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（省略時: INFO）

簡易 `.env.example`:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン / ソースを取得
2. Python 仮想環境の作成と有効化
3. 必要パッケージのインストール（duckdb, defusedxml など）
4. `.env` を作成して必須環境変数を設定
5. DuckDB スキーマ初期化

例コマンド:
```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml

# 環境変数を設定（.env を作成）
cp .env.example .env
#  .env を編集してトークン等を設定する

# Python でスキーマ初期化
python - <<'PY'
from kabusys.data.schema import init_schema
from kabusys.config import settings
init_schema(settings.duckdb_path)
print("DuckDB schema initialized at", settings.duckdb_path)
PY
```

注意: DuckDB ファイルの保存先ディレクトリに書き込み権限が必要です。

---

## 使い方（代表的な API/ジョブの例）

以下はライブラリの主要エントリポイントを直接呼ぶ Python スニペット例です。

- DB 初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
```

- 日次 ETL 実行
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

- 特徴量構築（features テーブル生成）
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2024, 1, 10))
print("features upserted:", count)
```

- シグナル生成
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
total = generate_signals(conn, target_date=date(2024, 1, 10))
print("signals written:", total)
```

- ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes を渡すと記事→銘柄の紐付け処理を行う
known_codes = {"7203","6758","9984"}  # 例
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

- カレンダー更新（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("calendar saved:", saved)
```

---

## よくある運用・トラブルシューティング

- 環境変数が読み込まれない
  - プロジェクトルートに `.env` / `.env.local` を配置しているか確認。自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定していると読み込まれません。
  - テスト実行時などで意図的に無効化しているケースに注意。

- DuckDB への接続エラー
  - 指定したパスの親ディレクトリに書き込み権限があるか確認。
  - `:memory:` を指定すればインメモリ DB を使用可能。

- J-Quants API 呼び出しで 401 が返る
  - `JQUANTS_REFRESH_TOKEN` が正しいか、期限切れでないか確認。ライブラリは自動的に ID トークンをリフレッシュしリトライします。

- RSS の取得が失敗する／空になる
  - RSS の URL が https/http のいずれかであるか、リダイレクト先がプライベート IP に解決されないかを確認（SSRF 対策で制限されています）。
  - 非標準構造のフィードでは記事検出に失敗することがあります（ログを確認してください）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py
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
    - (その他: quality.py など想定)
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
    - (監視関連モジュールを追加想定)

トップレベルの公開 API は pakage の __all__ などで data / strategy / execution / monitoring を想定しています。

---

## 開発上のメモ・設計方針

- ルックアヘッドバイアス回避：戦略系の計算は target_date 時点で利用可能なデータのみを使う設計。
- 冪等性重視：DB への書き込みは ON CONFLICT/UPSERT や日付単位の置換（DELETE→INSERT）で冪等化。
- 安全性：RSS の SSRF 対策、defusedxml による XML パース保護、受信サイズ制限などを実装。
- テスタビリティ：API トークン注入、ネットワーク呼び出し（_urlopen など）のモックが可能な設計。

---

## ライセンス・貢献

リポジトリのルートに LICENSE / CONTRIBUTING を追加してください。外部 API トークンや秘密情報は公開リポジトリに含めないでください。

---

README は実装ファイルのコメント・仕様に基づいて作成しました。運用・デプロイ向けにはさらに運用手順（cron / scheduler、監視・アラート、バックアップ、権限管理）を追記することを推奨します。必要であれば README に含めるサンプル .env、systemd / cron ジョブ例、Dockerfile や GitHub Actions ワークフローのテンプレートも作成します。どれを追加しますか？