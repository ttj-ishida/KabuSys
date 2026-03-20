# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ（プロトタイプ）です。  
DuckDB を内部データストアとして用い、J-Quants API や RSS ニュースを取り込み、ファクター計算→特徴量正規化→シグナル生成までのワークフローを提供します。

## 主な特徴
- J-Quants API クライアント（ページネーション・レート制御・トークン自動リフレッシュ・リトライ）
- DuckDB ベースのスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- ニュース収集（RSS → 前処理 → DB 保存、SSRF/サイズ/XML攻撃対策）
- ファクター計算（Momentum / Volatility / Value 等、研究用関数）
- 特徴量エンジニアリング（Z スコア正規化、ユニバースフィルタ）
- シグナル生成（ファクター＋AIスコア統合、BUY/SELL ルール・エグジット判定）
- 監査ログ（order/signal/execution のトレースを意識したスキーマ設計）
- テスト容易性のための設計（ID トークン注入、.env 自動読み込み制御 等）

---

## 必要条件
- Python 3.10 以上（型注釈や union 型 `|` を使用）
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml

必要なパッケージはプロジェクトの requirements.txt / pyproject.toml があればそれを使用してください。最小限の手動インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

---

## 環境変数 / 設定
このパッケージは .env ファイルもしくは OS 環境変数から設定を読み込みます（プロジェクトルートに `.git` または `pyproject.toml` がある場合に自動ロード）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主に使用される環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
- KABU_API_BASE_URL (任意) — kabu API のベースURL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — 通知先 Slack チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — SQLite（監視用途など、デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — `development` / `paper_trading` / `live`（デフォルト: development）
- LOG_LEVEL (任意) — `DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`（デフォルト: INFO）

例 `.env`（プロジェクトルート）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C1234567890
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## セットアップ手順（概要）
1. リポジトリをクローン / 展開
2. Python 仮想環境を作成して有効化
3. 依存パッケージをインストール（duckdb / defusedxml 等）
4. 環境変数を `.env` またはシステム環境変数に設定
5. DuckDB スキーマを初期化

DuckDB スキーマ初期化の例:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

---

## 使い方（主要なワークフロー例）

1) データベース初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL の実行（J-Quants から差分取得し保存）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定することも可能
print(result.to_dict())
```

3) 特徴量の構築（research の計算結果を正規化して features テーブルへ UPSERT）
```python
from kabusys.strategy import build_features
from datetime import date
count = build_features(conn, date(2025, 1, 31))
print(f"features updated: {count}")
```

4) シグナル生成（features と ai_scores を統合して signals テーブルへ書き込む）
```python
from kabusys.strategy import generate_signals
from datetime import date
total = generate_signals(conn, date(2025, 1, 31))
print(f"signals written: {total}")
```

5) ニュース収集ジョブ（RSS 取得 → raw_news に保存 → 銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)
```

6) J-Quants データ取得 / 保存（個別利用）
```python
from kabusys.data import jquants_client as jq
rows = jq.fetch_daily_quotes(date_from=date(2025,1,1), date_to=date(2025,1,31))
saved = jq.save_daily_quotes(conn, rows)
```

---

## 推奨ワークフロー（一例）
- 毎夜 cron や CI で: run_daily_etl → feature 構築 → ai スコア取込 → generate_signals → signal_queue / execution 層へ流す
- News collector は頻度を別にして実行（RSS の数や API 負荷に応じて）
- 本番時は KABUSYS_ENV=live を設定、paper_trading モードでの検証を推奨

---

## 注意点 / 設計上の留意事項
- ルックアヘッドバイアスを避ける設計（target_date 時点のデータのみ参照する等）
- J-Quants API 呼び出しはレート制限とリトライ、401 の自動リフレッシュを実装
- DuckDB への保存は可能な限り冪等（ON CONFLICT）を用いている
- News collector は SSRF / XML 攻撃 / 大容量レスポンス対策を施している
- 一部仕様は DataPlatform.md / StrategyModel.md 等の設計ドキュメントに依存（実装済みコメントがコード内に存在）

---

## ディレクトリ構成（抜粋）
以下は主要モジュールとその目的の一覧です（ファイルは src/kabusys 以下）。

- kabusys/
  - __init__.py (パッケージ初期化、バージョン)
  - config.py (環境変数・設定管理)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント, 保存ユーティリティ)
    - news_collector.py (RSS -> raw_news, 銘柄抽出)
    - schema.py (DuckDB スキーマ定義・init_schema)
    - pipeline.py (ETL パイプライン: run_daily_etl 等)
    - stats.py (zscore_normalize 等統計ユーティリティ)
    - features.py (zscore_normalize の再エクスポート)
    - calendar_management.py (market_calendar 管理・営業日判定)
    - audit.py (監査ログ用スキーマ)
    - quality.py (品質チェックモジュール ※コードベースに存在する想定)
  - research/
    - __init__.py
    - factor_research.py (Momentum/Volatility/Value の計算)
    - feature_exploration.py (forward returns, IC, factor summary 等)
  - strategy/
    - __init__.py (build_features, generate_signals を公開)
    - feature_engineering.py (ファクター正規化・features への保存)
    - signal_generator.py (final_score 計算・BUY/SELL 生成)
  - execution/
    - __init__.py (発注・execution 層のエントリ)
  - monitoring/ (監視用モジュール群 - 概要のみ)

（上記は現行コードベースの主要ファイルを抜粋したものです。詳細はリポジトリ内の各ファイルの docstring を参照してください。）

---

## 開発・デバッグ時のヒント
- .env 自動読み込みは config.py のロジックで行われます。テストなどで無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。
- DuckDB は ":memory:" を指定して一時 DB を用いたテストが可能です:
  ```python
  conn = init_schema(":memory:")
  ```
- jquants_client の HTTP レイヤーは urllib を直接使っています。テスト時は関数をモックして外部通信を防いでください（例: fetch_daily_quotes の内部 _request をモック等）。
- news_collector では _urlopen を差し替えてテスト可能（モック用フックが想定されています）。

---

## ライセンス・貢献
この README はコードベースの抜粋に基づく概要説明です。実運用前に十分な検証（バックテスト・ペーパートレード・セキュリティ評価）を行ってください。貢献やバグ報告、設計ドキュメントの追加は歓迎します。

---

何か特定の使い方（例: ETL の cron 定義、signal の execution 層統合、テスト用データセット作成など）を README に追記したい場合は、用途を教えてください。必要に応じてサンプルスクリプトや CI ワークフロー例も作成します。