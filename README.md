# KabuSys

日本株向け自動売買・データプラットフォームの Python コードベース。  
データ取得（J-Quants）、DuckDB ベースのデータレイク、特徴量作成、シグナル生成、ニュース収集、ETL パイプラインなどをコンポーネント化しています。

## 概要
KabuSys は以下のレイヤーを備えた小規模なアルゴリズム取引基盤のコンポーネント群です。

- Data（J-Quants からの取得、DuckDB スキーマ定義、ETL、ニュース収集）
- Research（ファクター計算、将来リターン・IC 計算、統計サマリー）
- Strategy（特徴量正規化、シグナル生成）
- Execution（発注・監視のためのスケルトン）
- 設定管理（.env の自動読み込み、環境変数）

設計方針としては「ルックアヘッドバイアスの回避」「冪等性」「ネットワーク/セキュリティ対策（SSRF 等）」「DuckDB を使ったオンディスク DB」を重視しています。

---

## 機能一覧（主要機能）
- 環境変数 / .env 自動読み込み（.env, .env.local、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
- J-Quants API クライアント（ページネーション対応、レート制御、トークン自動リフレッシュ、リトライ）
  - 株価日足、財務データ、マーケットカレンダー取得
- DuckDB 用スキーマ定義と初期化（init_schema）
- ETL パイプライン（差分取得・保存・品質チェック）
  - 日次 ETL 実行（run_daily_etl）
- ニュース収集（RSS 取得、XML 安全パーサ、SSRF 防御、記事正規化、銘柄抽出）
- Research: ファクター計算（モメンタム／ボラティリティ／バリュー等）、IC・統計サマリー
- Strategy:
  - 特徴量作成（build_features）：research の raw factor を統合、Z スコア正規化、features テーブルへ保存
  - シグナル生成（generate_signals）：features と ai_scores を統合して BUY/SELL を生成、signals テーブルへ保存
- データ／統計ユーティリティ（zscore 正規化など）

---

## 必要条件（推奨）
- Python 3.10+
  - コード中で型ヒントに `X | Y` を使用しているため Python 3.10 以上を推奨します。
- pip、virtualenv（任意）
- 主な Python パッケージ（例）
  - duckdb
  - defusedxml

インストール例（仮想環境推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# パッケージ化されている場合:
pip install -e .
```
（プロジェクトに pyproject.toml/setup.cfg がある想定で pip install -e . が有効です）

---

## 環境変数（主な必須・任意設定）
自動で .env / .env.local をプロジェクトルートから読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。

必須（実行する機能に依存）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu API のパスワード（execution 層で使用）
- SLACK_BOT_TOKEN — Slack 通知用（オプション機能で使用）
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意 / デフォルトあり:
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/...（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — モニタリング用 SQLite（デフォルト: data/monitoring.db）
- KABU_API_BASE_URL — kabu API base URL（デフォルト: http://localhost:18080/kabusapi）

簡易 .env 例:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（最小手順）
1. リポジトリをクローンして仮想環境を用意
```
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
```

2. 依存パッケージのインストール
```
pip install duckdb defusedxml
# またはプロジェクトがパッケージ化されていれば
pip install -e .
```

3. .env を作成して必要な環境変数を設定（上記参照）

4. DuckDB スキーマ初期化
Python REPL やスクリプトで:
```
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```
これで必要なテーブルがすべて作成されます。

---

## 使い方（簡易例）
以下は主要ユースケースの簡単な使用例です。実行はプロジェクトルートで仮想環境を有効にした状態を想定します。

- データベース初期化（再掲）
```
python - <<'PY'
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
print("initialized:", conn)
PY
```

- 日次 ETL 実行（J-Quants トークンが設定されている前提）
```
python - <<'PY'
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
PY
```

- 研究用ファクター計算（例: モメンタム）
```
python - <<'PY'
from kabusys.data.schema import init_schema
from kabusys.research import calc_momentum
from datetime import date

conn = init_schema(":memory:")  # テスト用にメモリ DB
# prices_daily にテストデータを入れてから
res = calc_momentum(conn, date(2024, 1, 31))
print(len(res))
PY
```

- 特徴量ビルド & シグナル生成
```
python - <<'PY'
from kabusys.data.schema import init_schema
from kabusys.strategy import build_features, generate_signals
from datetime import date

conn = init_schema("data/kabusys.duckdb")
d = date(2024, 1, 31)
n_feat = build_features(conn, d)
n_signals = generate_signals(conn, d)
print("features:", n_feat, "signals:", n_signals)
PY
```

- ニュース収集ジョブ（既知銘柄セットを渡して紐付け）
```
python - <<'PY'
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758"}  # 例: トヨタ、ソニーなど
res = run_news_collection(conn, known_codes=known_codes)
print(res)
PY
```

- J-Quants からの取得（個別呼び出し例）
```
python - <<'PY'
from kabusys.data import jquants_client as jq
from datetime import date

# 必要に応じて jq.get_id_token() を使ってトークンを強制再取得できます
quotes = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
print(len(quotes))
PY
```

注意:
- 実際の運用ではエラーハンドリングやバックオフ、ログ確認を行ってください。
- execution（発注）関連は本 README の時点では発注モジュールのスケルトンや監査テーブルが用意されていますが、ブローカー接続や実際の送信処理は別途実装が必要です。

---

## ディレクトリ構成（抜粋）
以下は主要なファイル／モジュールの一覧（src/kabusys 配下）。実際のリポジトリには他の設定ファイル等があると想定されます。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / .env ロードと Settings クラス
  - data/
    - __init__.py
    - jquants_client.py           — J-Quants API クライアント（取得・保存ユーティリティ）
    - schema.py                   — DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py                 — ETL パイプライン（run_daily_etl 等）
    - news_collector.py           — RSS 収集・前処理・保存・銘柄抽出
    - stats.py                    — zscore_normalize 等統計ユーティリティ
    - features.py                 — data.stats の再エクスポート
    - calendar_management.py      — market_calendar の管理・営業日判定
    - audit.py                    — 監査ログテーブル定義
    - quality.py?                 — （品質チェックモジュール、pipeline から参照）
    - pipeline.py                 — ETL の主ロジック（既出）
  - research/
    - __init__.py
    - factor_research.py          — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py      — 将来リターン・IC・統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py     — build_features（正規化・フィルタ等）
    - signal_generator.py        — generate_signals（final_score 計算、BUY/SELL 生成）
  - execution/
    - __init__.py                — （発注層のためのプレースホルダ）
  - monitoring/                  — （監視用 DB / スクリプトなどを想定）
  - ...（その他ユーティリティ）

---

## 実装上のポイント（短め）
- DuckDB を中心に Raw / Processed / Feature / Execution のレイヤーでデータを管理します。
- J-Quants クライアントはレート制御（120 req/min）とリトライ、401 時の自動トークンリフレッシュを備えます。
- ニュース収集は SSRF 対策、XML パースの安全化、受信サイズ制限、トラッキングパラメータ除去を行います。
- 戦略側はルックアヘッドバイアス防止のため、target_date 時点のデータのみを参照する設計です。
- 多くの DB 書き込みは冪等に実装（ON CONFLICT / INSERT ... DO UPDATE / DO NOTHING）されています。

---

## よくある質問
Q. どの Python バージョンで動きますか？  
A. Python 3.10 以上を推奨します（型ヒントに `X | Y` を使用）。

Q. 依存パッケージは何がありますか？  
A. 最低限 duckdb と defusedxml が必要です。プロジェクトをパッケージ化している場合は pyproject / requirements を参照してください。

Q. 本番で使うには？  
A. 実運用では下記が必要です：
- 運用用の設定（KABUSYS_ENV=live 等）
- 発注層の broker 接続実装（現在は監査テーブル・スキーマあり）
- 適切な監視・ロギング・バックテスト・リスク管理（ストップロス・ポジション制御）
- セキュリティ（秘密情報は Vault 等で管理）

---

もし README に追記したい内容（例: CI、テストの実行方法、具体的な .env.example ファイル、依存一覧、デプロイ手順）があれば教えてください。必要に応じてREADMEの拡張版を作成します。