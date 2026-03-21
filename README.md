# KabuSys

日本株向けの自動売買／データ基盤ライブラリ（KabuSys）。  
データ取得（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、監査ログ／スキーマ管理までを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株の定量投資ワークフローをサポートするライブラリです。主な役割は次の通りです。

- J-Quants API からのデータ取得（株価・財務・マーケットカレンダー）
- DuckDB を用いたデータ格納・スキーマ管理（Raw / Processed / Feature / Execution 層）
- ETL（差分更新、バックフィル、品質チェック）
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー 等）
- 特徴量の正規化・合成（features テーブル作成）
- シグナル生成（final_score 計算、BUY/SELL 判定）と signals テーブル保存
- RSS からのニュース収集と銘柄紐付け（raw_news / news_symbols）
- 発注・約定・監査ログ基盤（監査テーブル群）

設計上の特徴：
- ルックアヘッドバイアスを防ぐため日付時点のみを利用する処理設計
- DuckDB に対する冪等保存（ON CONFLICT / トランザクション）
- API レート制御・リトライ・トークン自動リフレッシュ等の堅牢性対策
- 外部依存を最小化（主要ロジックは標準ライブラリ + DuckDB）

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（レートリミット対応・リトライ・保存関数）
  - schema: DuckDB スキーマ定義と初期化（Raw/Processed/Feature/Execution 層）
  - pipeline: 日次 ETL（差分取得・保存・品質チェック）
  - news_collector: RSS 収集、前処理、DB 保存、銘柄抽出
  - calendar_management: マーケットカレンダー管理、営業日判定ユーティリティ
  - stats: zscore_normalize 等の統計ユーティリティ
  - features: features API（再エクスポート）
  - audit: 発注〜約定の監査ログテーブル
- research/
  - factor_research: Momentum / Volatility / Value などのファクター計算
  - feature_exploration: 将来リターン計算、IC 計算、統計サマリー
- strategy/
  - feature_engineering: raw ファクターを統合し features テーブルを作成
  - signal_generator: features と ai_scores を統合して BUY/SELL シグナルを生成
- execution/: 発注・実行（将来的な拡張想定）
- monitoring/: 監視・アラート関連（将来的な拡張想定）
- config.py: 環境変数管理（.env 自動読み込み、必須キーチェック）

---

## 必要条件・依存関係

主な実行依存ライブラリ（抜粋）:
- Python 3.9+
- duckdb
- defusedxml

（その他は標準ライブラリ中心。実際の packaging/pyproject に依存関係を記載してください）

インストール例（開発環境）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# パッケージとして開発インストールしている場合:
pip install -e .
```

---

## 環境変数（必須・任意）

config.Settings で参照する主な環境変数：

必須:
- JQUANTS_REFRESH_TOKEN：J-Quants リフレッシュトークン
- KABU_API_PASSWORD：kabuステーション API パスワード（execution 層で使用）
- SLACK_BOT_TOKEN：Slack Bot Token（通知等で使用する場合）
- SLACK_CHANNEL_ID：Slack チャンネル ID（通知先）

任意（デフォルトあり）:
- KABUSYS_ENV：development / paper_trading / live（デフォルト: development）
- LOG_LEVEL：ロギングレベル（DEBUG/INFO/...、デフォルト: INFO）
- DUCKDB_PATH：DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH：モニタリング用 SQLite パス（デフォルト: data/monitoring.db）

自動 .env ロード:
- パッケージはプロジェクトルート（.git または pyproject.toml を基準）にある `.env` / `.env.local` を自動で読み込みます。
- テスト等で自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例（.env）:
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

1. リポジトリをクローンして仮想環境を作成
   ```bash
   git clone <repo_url>
   cd <repo_dir>
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb defusedxml
   pip install -e .
   ```

2. 環境変数を用意（.env をプロジェクトルートに作成）
   - 必須のトークン類を `.env` に記載する
   - 自動読み込みが有効なら起動時に読み込まれます

3. DuckDB スキーマを初期化
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # 親ディレクトリは自動作成
   conn.close()
   ```

---

## 基本的な使い方（例）

以下は簡単な対話式／スクリプト例です。

- DuckDB 初期化（上記と同様）
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL 実行
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を省略すると今日が対象
print(result.to_dict())
```

- 特徴量構築（features テーブル作成）
```python
from datetime import date
from kabusys.strategy import build_features
count = build_features(conn, date(2024, 1, 5))
print("features updated:", count)
```

- シグナル生成
```python
from datetime import date
from kabusys.strategy import generate_signals
n_signals = generate_signals(conn, date(2024, 1, 5))
print("signals written:", n_signals)
```

- ニュース収集ジョブ（RSS）
```python
from kabusys.data.news_collector import run_news_collection
# known_codes は銘柄抽出時に使う有効コード集合（例: set of "7203","6758",...）
results = run_news_collection(conn, sources=None, known_codes=None)
print(results)
```

- 研究用ファクター計算（単体利用）
```python
from kabusys.research import calc_momentum, calc_volatility, calc_value
from datetime import date
m = calc_momentum(conn, date.today())
v = calc_volatility(conn, date.today())
val = calc_value(conn, date.today())
```

注意:
- 多くの処理は target_date 時点のデータのみを参照します（ルックアヘッド防止）。
- 各種 ETL / 保存処理は冪等設計のため再実行可能です。

---

## ディレクトリ構成（主要ファイル）

プロジェクト内の主要なモジュール構成（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py  — 環境変数管理（.env 自動読み込み、Settings）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（fetch/save）
    - schema.py               — DuckDB スキーマ定義・初期化
    - pipeline.py             — ETL（差分更新・日次パイプライン）
    - news_collector.py       — RSS 収集・前処理・DB 保存
    - calendar_management.py  — マーケットカレンダー管理・営業日ユーティリティ
    - stats.py                — zscore_normalize 等統計ユーティリティ
    - features.py             — 再エクスポート（zscore_normalize）
    - audit.py                — 監査ログ用 DDL
    - (その他)
  - research/
    - __init__.py
    - factor_research.py      — モメンタム/ボラ/バリュー算出
    - feature_exploration.py  — 将来リターン/IC/統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py  — features テーブル作成
    - signal_generator.py     — final_score 計算・signals 書き込み
  - execution/                — 発注関連（拡張領域）
  - monitoring/               — 監視（拡張領域）

---

## 運用上の注意点 / 補足

- スキーマ（schema.init_schema）は冪等であり、既存データを壊さずにテーブルを作成します。
- jquants_client は API レート制御（120 req/min）・リトライ・401 時トークン自動リフレッシュに対応しています。J-Quants の利用規約・レート制約を遵守してください。
- news_collector は SSRF や XML 攻撃対策（defusedxml・スキーム検証・プライベートアドレス検出）を備えていますが、運用時は RSS ソースの信頼性を確認してください。
- 自動 .env 読み込みはプロジェクトルート（.git or pyproject.toml）から行われます。CI やテストで不要な場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 本リポジトリ内の設計ドキュメント（StrategyModel.md, DataPlatform.md, DataSchema.md 等）に沿って各アルゴリズムは実装されています。詳細は該当ドキュメント（存在する場合）を参照してください。

---

必要であれば、README にサンプル .env.example、より詳細な API 使用例（ETL スケジュール、cron/airflow への組み込み例）、監査テーブルの使い方、Slack 通知フローなどを追加できます。どの部分を詳しく記載したいか教えてください。