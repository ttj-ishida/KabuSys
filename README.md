# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
DuckDB をデータレイクに用い、J-Quants API や RSS を取り込み、特徴量生成・シグナル生成・発注監査までを想定したモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の役割を持つ Python モジュール群です。

- J-Quants API から株価・財務・市場カレンダーを取得して DuckDB に保存する ETL（差分更新対応）
- RSS ベースのニュース収集と銘柄抽出
- Research 層で計算された生ファクターを正規化して features テーブルに格納する特徴量パイプライン
- features / ai_scores を統合して売買シグナル（BUY/SELL）を生成する戦略ロジック
- DuckDB のスキーマ初期化、監査ログテーブル定義、マーケットカレンダー管理 等

設計上の主な方針：
- ルックアヘッドバイアスを避ける（target_date 時点のデータのみを参照）
- DuckDB への保存は冪等（ON CONFLICT / INSERT ... DO UPDATE）を意識
- ネットワーク周りはリトライとレート制御を備える
- 外部に直接発注するレイヤーとは密結合しない（execution 層は分離）

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（認証・ページネーション・リトライ・レート制御）
  - pipeline: 日次 ETL（prices / financials / market_calendar）の差分更新と品質チェック
  - news_collector: RSS 収集、テキスト前処理、銘柄抽出、DB保存（冪等）
  - schema: DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - calendar_management: JPX カレンダー管理・営業日ロジック
  - stats: Z スコア正規化等の統計ユーティリティ
- research/
  - factor_research: momentum / volatility / value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）や統計サマリー
- strategy/
  - feature_engineering: research の生ファクターを統合・正規化して features に書き込む
  - signal_generator: features と ai_scores を統合して final_score を算出し signals を生成する
- config: .env 自動読み込み / 環境変数管理（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
- auditing / execution: 発注・約定・監査ログ用テーブル定義（監査用 DDL が含まれる）

---

## 要件 (推奨)

- Python 3.10+
- pip
- 必要な PyPI パッケージ（最低限）:
  - duckdb
  - defusedxml

推奨インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# (プロジェクト配布に requirements.txt / pyproject があればそれを使ってください)
```

---

## 環境変数 / .env

パッケージはプロジェクトルート（.git または pyproject.toml のある親ディレクトリ）を探索して自動で `.env` / `.env.local` を読み込みます。自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数:
- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須): kabu ステーション API パスワード
- KABU_API_BASE_URL (任意): kabu API のベース URL (デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須): Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須): Slack チャンネル ID
- DUCKDB_PATH (任意): DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意): SQLite (monitoring) ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意): "development" | "paper_trading" | "live"（デフォルト: development）
- LOG_LEVEL (任意): "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxx...
KABU_API_PASSWORD=your_kabu_pwd
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

config.Settings によりこれら値はプロパティ経由で取り出せます（例: from kabusys.config import settings; settings.jquants_refresh_token）。

---

## セットアップ手順

1. リポジトリをクローン
```bash
git clone <repo-url>
cd <repo>
```

2. 仮想環境作成・有効化
```bash
python -m venv .venv
source .venv/bin/activate
```

3. 依存パッケージをインストール
```bash
pip install duckdb defusedxml
# プロジェクトに requirements.txt/pyproject.toml があればそれを使ってください
```

4. .env の用意（プロジェクトルートに配置）
- .env.example を参考に必須キーを設定してください（上の「環境変数」参照）。

5. DuckDB スキーマ初期化
下記のようにして DuckDB ファイルを初期化します（デフォルトは data/kabusys.duckdb）。
```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.config import settings

db_path = settings.duckdb_path  # または直接 "data/kabusys.duckdb"
conn = init_schema(db_path)
# conn を使ってさらに操作できます
```

---

## 基本的な使い方（主要 API）

- 日次 ETL 実行（prices / financials / calendar の差分取得）
```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量構築（research の生ファクターを正規化して features に保存）
```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

- シグナル生成（features / ai_scores / positions を参照して signals を生成）
```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import generate_signals

conn = get_connection("data/kabusys.duckdb")
num = generate_signals(conn, target_date=date.today())
print(f"signals written: {num}")
```

- ニュース収集（RSS を DB に保存して銘柄紐付け）
```python
from kabusys.data.schema import get_connection
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コード集合
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

- J-Quants 生データ取得例（トークン自動リフレッシュ・ページネーション対応）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
records = fetch_daily_quotes(date_from=None, date_to=None)  # 引数を指定してください
saved = save_daily_quotes(conn, records)
```

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュール一覧（抜粋）です:

- kabusys/
  - __init__.py
  - config.py  — 環境変数 / .env 管理
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - pipeline.py
    - stats.py
    - features.py
    - calendar_management.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/  — 発注関連モジュール（空パッケージ、将来的な実装想定）
  - monitoring/ — 監視・メトリクス用（将来的な実装想定）

（各ファイル内に詳細な docstring と処理フローが記載されています）

---

## 運用上の注意 / トラブルシューティング

- 自動で .env を読み込む際、優先順位は OS 環境変数 > .env.local > .env です。テストで自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Python の型注釈に Python 3.10 の構文（X | Y）を使用しているため Python 3.10 以上を推奨します。
- J-Quants API にはレート制限があるため jquants_client は内部でレート制御とリトライを行います。大量取得時は待ちが発生します。
- DuckDB のスキーマ初期化は idempotent（既存テーブルはそのまま）です。開発環境でスキーマ変更を行う場合は注意してください。
- news_collector は RSS のリダイレクト先やコンテンツを検査して SSRF や XML Bomb 対策を実装していますが、外部フィードの仕様差により一部フィードが取得できない場合があります。

---

## 今後の拡張案（参考）

- execution 層のブローカー連携（kabu API を使った発注 / 約定受信）
- Slack / モニタリングへの通知モジュールの追加
- AI スコア生成パイプラインの実装（ai_scores テーブルへの書き込み）
- 単体テスト・統合テストスイートと CI 設定

---

README に記載の無い詳細（関数の引数仕様や内部のアルゴリズム設計）は各ソースの docstring を参照してください。  
さらに補足が必要でしたら（例: サンプルスクリプトの追加、requirements.txt の作成、より詳しい運用手順など）お知らせください。