# KabuSys — 日本株自動売買システム

KabuSys は日本株のデータ取得・ETL・特徴量生成・シグナル算出を行うライブラリ群です。  
J-Quants API からのデータ収集、DuckDB を用いたローカルデータ管理、研究用ファクター計算、戦略用特徴量生成、シグナル生成ロジックを含みます。

主な設計方針：
- ルックアヘッドバイアスの防止（target_date 時点の情報のみ使用）
- 冪等性（DB への保存は ON CONFLICT / トランザクションで安全に）
- 外部 API 呼び出し・発注層への直接依存を最小化（各層は明確に分離）
- 標準ライブラリ中心での実装（外部依存は最小限）

---

## 機能一覧

- データ取得 / ETL（kabusys.data）
  - J-Quants API クライアント（レート制限・リトライ・トークン自動リフレッシュ対応）
  - 株価（OHLCV）・財務データ・市場カレンダーの取得 / 保存
  - DuckDB スキーマ定義 & 初期化
  - ETL パイプライン（差分更新、バックフィル、品質チェックフック）
  - ニュース収集（RSS → raw_news、記事から銘柄抽出）
  - マーケットカレンダー管理（営業日判定等）
  - 監査ログ（発注・約定のトレーサビリティ）

- 研究用ツール（kabusys.research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算（forward returns）
  - IC（情報係数）や統計サマリー計算

- 戦略（kabusys.strategy）
  - 特徴量エンジニアリング（生ファクターの正規化・フィルタリング → features テーブル）
  - シグナル生成（features + ai_scores を統合して BUY / SELL を生成）

- 汎用ユーティリティ
  - Z スコア正規化等の統計関数
  - .env 自動ロード（プロジェクトルートの .env / .env.local。無効化可）

---

## セットアップ手順

要求
- Python 3.10 以上（PEP 604 の union 型 `X | Y` を使用）
- DuckDB（Python パッケージ）
- defusedxml（RSS パースの安全化）
- （オプション）その他ツール：urllib 等は標準ライブラリ

例（venv を使った開発環境の作成）:

```bash
# リポジトリをクローン
git clone <repo-url>
cd <repo>

# 仮想環境作成・有効化
python -m venv .venv
source .venv/bin/activate  # macOS / Linux
.venv\Scripts\activate     # Windows

# 必要パッケージをインストール
pip install duckdb defusedxml
# （プロジェクトで requirements.txt がある場合はそれを使ってください）
# pip install -r requirements.txt

# パッケージを編集可能インストール（任意）
pip install -e .
```

環境変数（必須／推奨）
- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
  - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（使用する場合）
  - SLACK_CHANNEL_ID: Slack チャンネル ID（使用する場合）
  - KABU_API_PASSWORD: kabu ステーション API パスワード（execution 層使用時）
- 任意（デフォルトあり）
  - KABUSYS_ENV: 実行環境 (development | paper_trading | live)。デフォルト: development
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...）。デフォルト: INFO
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化
  - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）

.env の自動読み込み
- パッケージはプロジェクトルート（.git または pyproject.toml を探す）から .env/.env.local を自動で読み込みます。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（基本的なワークフロー）

以下は最も基本的な例です。実環境ではログ設定・エラーハンドリング・スケジューリング等を追加してください。

1) DuckDB スキーマ初期化

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は環境変数 DUCKDB_PATH のデフォルトを参照
conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）

```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量ビルド（features テーブル作成）

```python
from kabusys.strategy import build_features
from datetime import date

n = build_features(conn, target_date=date.today())
print(f"features upserted: {n}")
```

4) シグナル生成（signals テーブル作成）

```python
from kabusys.strategy import generate_signals
from datetime import date

count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {count}")
```

5) ニュース収集ジョブ（RSS → raw_news, news_symbols）

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes は銘柄コードセット（例: 全上場4桁コードの set）
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set(["7203", "6758"]))
print(results)
```

6) カレンダー更新（夜間バッチ）

```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

---

## ディレクトリ構成（抜粋）

プロジェクトは src/kabusys 配下にパッケージ化されています。主要ファイルと説明：

- src/kabusys/
  - __init__.py
  - config.py                    : 環境変数・設定管理（.env 自動読み込み、Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py           : J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py          : RSS 取得・前処理・DB 保存、銘柄抽出
    - schema.py                  : DuckDB スキーマ定義 & init_schema()
    - pipeline.py                : ETL パイプライン（run_daily_etl 等）
    - stats.py                   : zscore_normalize 等統計ユーティリティ
    - calendar_management.py     : カレンダー更新 / 営業日判定ユーティリティ
    - audit.py                   : 発注・約定の監査ログテーブル定義
    - features.py                : data.stats の再エクスポート
  - research/
    - __init__.py
    - factor_research.py         : momentum / value / volatility の計算
    - feature_exploration.py     : forward returns / IC / summary 統計
  - strategy/
    - __init__.py
    - feature_engineering.py     : features テーブル用の正規化・フィルタ処理
    - signal_generator.py        : final_score 計算と BUY/SELL シグナル生成
  - execution/                   : 発注実装（空のパッケージ／拡張ポイント）
  - monitoring/                  : 監視・モニタリング関連（拡張ポイント）

上記は主要モジュールの抜粋です。詳細は各ファイルの docstring を参照してください。

---

## 実運用時の注意点

- API レート制限を必ず守る（J-Quants はデフォルト 120 req/min）。jquants_client は固定間隔の RateLimiter を実装していますが、上位での呼び出し頻度管理も必要です。
- 認証トークンの管理（リフレッシュトークン / ID トークン）の取り扱いは慎重に行ってください。JQUANTS_REFRESH_TOKEN は秘匿してください。
- DuckDB ファイルは単一ファイル DB です。バックアップ・運用時の排他制御（複数プロセス書き込み）に注意してください。
- シグナル→発注→約定の実行層（execution）は外部ブローカーや kabu ステーションへの接続実装が必要です。本ライブラリは発注 API 呼び出しのロジックには依存しない設計です（extension point を想定）。
- ニュース収集は RSS の多様な形式に対応しますが、RSS 側の変更によりパース失敗が起きる場合があります。defusedxml を用いて安全にパースします。

---

## 開発・拡張ポイント

- execution パッケージにブローカー固有のラッパーを実装して注文送信／約定処理を追加できます。
- AI スコア（ai_scores）を生成するモジュールを追加し、signal_generator の weights による統合を活用できます。
- 監視・アラート（Slack 通知など）は settings 内の Slack 設定を使って実装できます。

---

## 最後に

この README はコードベースの概要と基本的な利用法をまとめたものです。各モジュールには詳細な docstring が書かれているため、具体的な挙動や引数・戻り値の仕様はソース内コメントを参照してください。追加の利用例や運用手順が必要であればお知らせください。