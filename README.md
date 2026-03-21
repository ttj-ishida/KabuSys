# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
本リポジトリはデータ収集（J-Quants API）、ETL、ファクター計算、特徴量エンジニアリング、シグナル生成、ニュース収集、マーケットカレンダー管理、監査（トレーサビリティ）など、研究〜実運用までを想定した機能を含みます。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 簡単な使い方（コード例）
- 環境変数と自動 .env 読み込み
- ディレクトリ構成

---

プロジェクト概要
- 目的: 日本株の定量運用に必要なデータプラットフォームと戦略層の基礎機能を提供する。
- 設計方針: ルックアヘッドバイアスに配慮した時点ベースの処理、DuckDB を用いたローカル DB、API レート制御・リトライ、冪等な DB 操作を重視。

---

機能一覧
- data
  - J-Quants API クライアント（fetch/save、ページネーション、リトライ・トークン自動更新、レートリミット）
  - DuckDB スキーマ定義と初期化（init_schema）
  - ETL パイプライン（差分取得、バックフィル、品質チェックのフック）
  - ニュース収集（RSS 取り込み、前処理、記事→銘柄紐付け、SSRF 対策）
  - マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
  - 統計ユーティリティ（Z スコア正規化等）
  - 監査ログ（シグナル→発注→約定のトレーサビリティ）
- research
  - ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - 特徴量探索（将来リターン計算、IC 計算、統計サマリ）
- strategy
  - 特徴量作成（research の raw factor を正規化・ユニバースフィルタして features テーブルへ保存）
  - シグナル生成（features + ai_scores を統合して BUY/SELL シグナルを作成、売買ロジック・エグジット判定を含む）
- execution / monitoring
  - （パッケージ構造に存在。発注・監視用モジュールの実装を想定）
- config
  - 環境変数管理、.env の自動読み込みロジック

主な設計特徴
- DuckDB をコア DB として使用し、SQL と Python を組み合わせて高速に処理
- 冪等な DB 保存（ON CONFLICT / DO UPDATE / DO NOTHING）
- API 呼び出しはレート制御と再試行を実装
- 外部依存を最小限にし、defusedxml（RSS パース安全化）など最低限の依存を利用

---

セットアップ手順

前提
- Python 3.9+（typing の構文等を利用）
- ネットワーク接続（J-Quants API へアクセスする場合）

1) 仮想環境作成（推奨）
```bash
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate     # Windows
```

2) 必要パッケージのインストール
（パッケージ管理設定がない場合は必要モジュールを直接インストール）
```bash
pip install duckdb defusedxml
# テストや追加機能があれば他のライブラリもインストール
```
将来的にパッケージ化されていれば `pip install -e .` などを使って開発インストールできます。

3) プロジェクトルートに .env を作成（下記参照）
- 環境変数は .env / .env.local / OS 環境変数より読み込まれます（詳細は「環境変数と自動 .env 読み込み」参照）。

4) DuckDB スキーマ初期化
Python REPL かスクリプトで次を実行してください：
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ファイルパス（ディレクトリは自動作成されます）
```

---

使い方（代表的な操作例）

※ 以下は最小限のサンプルです。実運用ではロギング設定や例外処理、設定（env）を適切に行ってください。

1) 日次 ETL の実行
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) 特徴量（features）作成
（research 側の raw factor を DuckDB にロード済みである前提）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import build_features

conn = init_schema("data/kabusys.duckdb")
count = build_features(conn, target_date=date.today())
print(f"built features: {count}")
```

3) シグナル生成
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import generate_signals

conn = init_schema("data/kabusys.duckdb")
num_signals = generate_signals(conn, target_date=date.today())
print(f"signals generated: {num_signals}")
```

4) ニュース収集（RSS）と銘柄紐付け
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes: 抽出対象とする銘柄コードの集合（例：全上場銘柄のコードセット）
known_codes = {"7203", "6758", "9984"}  # サンプル
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

5) カレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

---

環境変数と自動 .env 読み込み
- 必須環境変数（Settings により _require されるもの）
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD : kabuステーション API のパスワード
  - SLACK_BOT_TOKEN : Slack 通知用トークン
  - SLACK_CHANNEL_ID : Slack チャンネル ID
- オプション
  - KABUSYS_ENV : 実行環境。allowed: development, paper_trading, live（デフォルト development）
  - LOG_LEVEL : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
  - DUCKDB_PATH : データベースファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH : 監視用 SQLite（デフォルト data/monitoring.db）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定すると自動 .env 読み込みを無効化

自動 .env 読み込み
- 実行時にプロジェクトルート（.git または pyproject.toml を基準）を探索し、以下を順に読み込みます：
  1. OS 環境変数（既存値は保護）
  2. .env （未設定のキーのみセット）
  3. .env.local（存在する場合、既存の OS 環境変数を保護しつつ上書き）
- テスト等で自動読み込みを無効にするには：
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

例：.env（簡易）
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=yyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

ディレクトリ構成（主要部分）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数と設定読み込みロジック
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（fetch/save）
    - news_collector.py       — RSS 取得・前処理・DB 保存・銘柄抽出
    - schema.py               — DuckDB スキーマ定義と init_schema/get_connection
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py  — 市場カレンダー管理と更新ジョブ
    - audit.py                — 監査ログ（signal/order/execution の DDL）
    - stats.py                — zscore_normalize 等の統計ユーティリティ
    - features.py             — data.stats の再エクスポート
  - research/
    - __init__.py
    - factor_research.py      — モメンタム / ボラティリティ / バリュー等の計算
    - feature_exploration.py  — 将来リターン・IC・統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py  — features テーブル作成（正規化・ユニバースフィルタ等）
    - signal_generator.py     — final_score 計算・BUY/SELL シグナル生成
  - execution/                 — 発注/実行ロジック（雛形）
  - monitoring/                — 監視関連（雛形）
- pyproject.toml (想定)
- .env, .env.local (任意)

各モジュールはドキュメント文字列に設計方針や処理フロー、注意点（例: ルックアヘッド防止や冪等性）を詳細に記載しています。まずは schema.init_schema で DB を初期化し、data.pipeline.run_daily_etl → strategy.build_features → strategy.generate_signals の順に一連の処理を試すのが基本的なワークフローです。

---

開発メモ / 注意点
- DuckDB のバージョン差異による制約（ON DELETE の挙動等）に注意。schema モジュール内にコメントで代替設計が記載されています。
- news_collector は外部 RSS の脆弱性対策（defusedxml、SSRF チェック、受信サイズ制限）を備えていますが、運用時はソースの信頼性・量に応じた監視が必要です。
- generate_signals は AI スコア（ai_scores テーブル）と統合可能。AI スコアがない場合は中立値（0.5）で補完されます。
- 本リポジトリは研究用途（research）から実運用（paper_trading / live）までの移行を想定しているため、KABUSYS_ENV によるフラグで実行モードを切り替えられます。

---

貢献・拡張
- 新しいファクターの追加: research/factor_research.py に関数を追加し、strategy/feature_engineering.py 側で統合してください。
- 発注ブローカー統合: execution 層に具体的な証券会社 API のアダプタを実装し、audit/order_requests テーブルを使用してトレーサビリティを保ってください。
- テスト: 各モジュールは外部依存を注入可能な作り（例: id_token の注入、_urlopen のモック）になっています。ユニットテストの追加を推奨します。

---

ライセンス・その他
- ライセンスやコードスタイル、CI 設定などはプロジェクトルートのファイル（pyproject.toml 等）に従ってください。

---

質問や、README に追加してほしい具体的な使い方（例えばスケジューラとの連携例、Docker 化、Slack 通知の使い方など）があれば教えてください。必要に応じて README を拡張します。