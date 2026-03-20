# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群です。データ取り込み（J-Quants）、ETL、ファクター計算、特徴量構築、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなど、戦略開発から実運用の下流までをカバーするモジュール群を提供します。

バージョン: 0.1.0

---

## 主な特徴

- データ取得
  - J-Quants API クライアント（株価日足 / 財務 / 市場カレンダー）
  - RSS ベースのニュース収集（安全性・SSRF 対策、トラッキングパラメータ除去）
- データ基盤
  - DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution レイヤ）
  - ETL パイプライン（差分取得、バックフィル、品質チェック統合）
  - マーケットカレンダー管理（営業日判定・前後営業日探索）
- 研究用 / 戦略用
  - ファクター計算（モメンタム、ボラティリティ、バリュー 等）
  - 特徴量エンジニアリング（Z スコア正規化、ユニバースフィルタ）
  - シグナル生成（ファクター・AIスコア統合、BUY/SELL の判定ロジック）
  - 研究支援ユーティリティ（将来リターン、IC 計算、統計サマリー）
- 発注・監査
  - Execution / Audit 向けスキーマ（シグナル・注文・約定・監査ログ）
- 設定管理
  - .env / 環境変数の自動読み込み（プロジェクトルート検出、優先順制御）

---

## 前提・依存関係

- Python 3.10 以上（型注釈の union `X | None` を利用）
- 主要パッケージ（例）
  - duckdb
  - defusedxml

インストールはプロジェクトの packaging 情報や requirements に依存しますが、最低限以下を用意してください:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# 開発用にパッケージを editable インストールする場合
pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローンする

```bash
git clone <repo-url>
cd <repo-dir>
```

2. 仮想環境作成・依存インストール

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt   # あれば
# または個別に
pip install duckdb defusedxml
pip install -e .
```

3. 環境変数の準備
   - プロジェクトルートに `.env` を作成すると、自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能）。

例: `.env`（最低限必要な値）

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
# 任意
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABU_API_BASE_URL=http://localhost:18080/kabusapi
```

4. DuckDB スキーマ初期化

Python REPL やスクリプトから:

```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")  # :memory: でインメモリ可
```

---

## 使い方（代表的な例）

下記は最小限の使用例です。各関数は DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を受け取ります。

- 日次 ETL（市場カレンダー・株価・財務の差分取得と品質チェック）

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量構築（features テーブルへ UPSERT）

```python
from datetime import date
from kabusys.strategy import build_features
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2025, 1, 10))
print(f"features upserted: {count}")
```

- シグナル生成（signals テーブルへ日付単位の置換）

```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
total = generate_signals(conn, target_date=date(2025, 1, 10))
print(f"signals written: {total}")
```

- ニュース収集（RSS 取得 → raw_news 保存 → 銘柄紐付け）

```python
from kabusys.data import news_collector, schema

conn = schema.get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
results = news_collector.run_news_collection(conn, sources=None, known_codes=known_codes)
print(results)
```

- J-Quants のトークン取得 / 生データ取得

```python
from kabusys.data import jquants_client as jq

id_token = jq.get_id_token()  # settings.jquants_refresh_token を参照
quotes = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```

注意: 上記の API 呼び出しは通信・認証を伴います。環境変数に正しい J-Quants トークン等を設定してください。

---

## 環境変数（主なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD: kabu API（kabuステーション）接続パスワード
  - SLACK_BOT_TOKEN: Slack 通知用 Bot Token
  - SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID
- 任意 / デフォルト
  - KABUSYS_ENV: development / paper_trading / live（default: development）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（default: INFO）
  - DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite パス（default: data/monitoring.db）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env の自動読み込みを無効化
  - KABU_API_BASE_URL: kabu API のベース URL（default: http://localhost:18080/kabusapi）

設定は `.env` に書くか環境変数としてエクスポートしてください。

---

## 主要モジュール概要

- kabusys.config
  - .env / 環境変数読み込み、自動検出（.git / pyproject.toml を基準にプロジェクトルートを探す）
  - settings オブジェクト経由で設定取得
- kabusys.data
  - jquants_client: J-Quants API クライアント（レートリミット、リトライ、ページネーション）
  - schema: DuckDB のスキーマ定義と init_schema / get_connection
  - pipeline: ETL パイプライン（run_daily_etl 等）
  - news_collector: RSS 取得・前処理・DB 保存・銘柄抽出
  - calendar_management: 営業日判定・更新ジョブ
  - stats: 共通統計ユーティリティ（zscore_normalize）
  - features: zscore_normalize の再エクスポート
  - audit: 発注/約定の監査ログ用スキーマ定義
- kabusys.research
  - factor_research: モメンタム / ボラティリティ / バリュー 等のファクター計算
  - feature_exploration: 将来リターン計算、IC、統計サマリー など
- kabusys.strategy
  - feature_engineering.build_features: raw ファクターを正規化して features へ保存
  - signal_generator.generate_signals: features / ai_scores を統合して signals を作成
- kabusys.execution
  - （実装の起点 / 拡張ポイント。発注・ブローカ連携等を実装）

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - schema.py
  - news_collector.py
  - calendar_management.py
  - stats.py
  - features.py
  - audit.py
  - pipeline.py
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
- monitoring/ (パッケージ名は __all__ に含まれる想定。監視用モジュールが入る想定)

（上記はコードベース抜粋です。実際のリポジトリには README、pyproject.toml 等のファイルが存在する可能性があります。）

---

## 開発・拡張のポイント

- DuckDB をデータレイヤの主要永続化に採用しているため、SQL を直接実行してデータ確認・デバッグが行えます。
- jquants_client はレートリミットやトークンリフレッシュを内包しており、本実装ではページネーション・リトライ戦略が組み込まれています。
- feature_engineering / signal_generator はルックアヘッドバイアス対策（target_date 時点までのデータのみ使用）を前提に設計されています。
- ニュース周りは SSRF・XML 攻撃・Gzip bomb 等に配慮した実装になっています（defusedxml、受信サイズ制限、ホスト検証）。

---

## 注意事項

- 本リポジトリは実際の発注を行う機能（ブローカ接続や本番環境との統合）を含む可能性があるため、実運用前に十分なレビュー・テストを行ってください。
- 環境変数や API トークンは機密情報です。公開リポジトリに直書きしないでください。
- duckdb ファイルやデータはバックアップや管理を適切に行ってください。

---

もし README に追加したい具体的な例（cronジョブ例、CI 設定、Dockerfile、実行スクリプト等）があれば、その用途に合わせてサンプルを追加できます。どの内容を優先して追記しますか？