# KabuSys

日本株向け自動売買・データ基盤ライブラリ (KabuSys)

短い概要:
KabuSys は J-Quants 等から取得した市場データを DuckDB に蓄積し、研究→特徴量作成→シグナル生成→発注監査までをサポートする日本株自動売買システムのライブラリ群です。ETL、ファクター計算、特徴量正規化、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログ等の機能をモジュール単位で提供します。

---

目次
- プロジェクト概要
- 主な機能
- 要件
- セットアップ手順
- 環境変数（設定）
- 使い方（簡易サンプル）
- ディレクトリ構成
- 補足（ログ・テスト用フック等）

---

## プロジェクト概要

KabuSys は次のような役割を想定したライブラリセットです。

- J-Quants API からのデータ取得（株価、財務、マーケットカレンダー）
- DuckDB による Raw / Processed / Feature / Execution 層のスキーマ管理
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- 研究用ファクター計算（momentum / volatility / value 等）
- 特徴量の正規化（Zスコア）と feature テーブルへの保存
- 特徴量・AIスコアを統合したシグナル生成（BUY / SELL）
- RSS ベースのニュース収集と銘柄抽出
- マーケットカレンダー管理（営業日判定 / next/prev_trading_day 等）
- 発注フローの監査ログ（トレーサビリティ）

設計方針の要点:
- ルックアヘッドバイアス回避（target_date 時点のデータのみを使用）
- 冪等性（DB 保存は ON CONFLICT 等で上書き可能）
- 外部ライブラリへの過度な依存を避け、標準ライブラリや DuckDB を活用
- エラーは局所で処理し、可能な限り処理を継続（フォールトトレラント）

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（レート制御・トークンリフレッシュ・リトライ）
  - schema: DuckDB スキーマ定義と init_schema()
  - pipeline: run_daily_etl(), run_prices_etl(), run_financials_etl(), run_calendar_etl()
  - news_collector: RSS 取得・前処理・raw_news 保存・銘柄抽出
  - calendar_management: is_trading_day / next_trading_day / get_trading_days / calendar_update_job
  - stats: zscore_normalize 等の統計ユーティリティ
- research/
  - factor_research: calc_momentum / calc_volatility / calc_value
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary
- strategy/
  - feature_engineering.build_features: raw ファクターを正規化し features テーブルへ保存
  - signal_generator.generate_signals: features と ai_scores を統合し signals を生成
- execution/（発注周りのインターフェースを配置するための名前空間）
- config: 環境変数・設定読み込み（.env 自動読込機能あり）
- audit: 発注〜約定までの監査ログ用スキーマ定義

---

## 要件

- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS 等）
- J-Quants のリフレッシュトークンや各種 API 情報（環境変数で設定）

（プロジェクト配布の setup.py / pyproject.toml に依存関係が記載されている想定です）

---

## セットアップ手順

1. リポジトリをクローン／開発環境に配置
   - 例: git clone ...

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate

3. 依存関係のインストール
   - pip install -r requirements.txt
   - または個別に: pip install duckdb defusedxml

4. パッケージを開発モードでインストール（任意）
   - pip install -e .

5. .env の用意
   - プロジェクトルートに .env を作成し、必要な環境変数を設定します（下記参照）。
   - 自動で .env / .env.local をロードします（ただし CWD ではなくパッケージファイル位置からプロジェクトルートを検出）。

6. DuckDB スキーマ初期化
   - Python REPL やスクリプトで init_schema() を実行して DB を初期化します（例は次節）。

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（execution 用）
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID — Slack チャンネルID

オプション / デフォルトあり:
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動読み込みを無効化

注意:
- kabusys.config.Settings のプロパティは未設定時に ValueError を投げます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を使うか環境変数を注入してください。

---

## 使い方（簡易サンプル）

以下は最小限の操作例です。各項目はスクリプトや CLI ジョブから呼び出して利用します。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")  # デフォルトパスと同等
```

2) 日次 ETL 実行（J-Quants からデータ取得→保存→品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を省略すると今日
print(result.to_dict())
```

3) 特徴量（features）構築
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2024, 1, 5))
print(f"upserted features: {n}")
```

4) シグナル生成
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2024, 1, 5))
print(f"signals written: {count}")
```

5) ニュース収集（RSS）と保存
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 既知銘柄セット（抽出に使用）
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

6) マーケットカレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

注意点:
- run_daily_etl 等は内部で settings（環境変数）を参照します。J-Quants トークンがないと get_id_token で例外になります。
- テストしやすいように ETL などは id_token を注入可能です（引数 id_token を渡す）。

---

## ディレクトリ構成（主要ファイル）

（パッケージルート: src/kabusys/ 以下の主要ファイル抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - schema.py
    - pipeline.py
    - news_collector.py
    - calendar_management.py
    - audit.py
    - features.py
    - stats.py
    - pipeline.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/ (名前空間用)
  - monitoring/ (監視・外部連携用に想定されたディレクトリ)

（README 用に省略された補助モジュールや設計ドキュメント参照ファイルが存在する可能性があります）

---

## 補足・運用上の注意

- 自動 .env 読み込み:
  - config.py はプロジェクトルート（.git または pyproject.toml を起点）から .env と .env.local を自動で読み込みます。
  - テスト等で自動読込を抑止したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- ロギング・実行環境:
  - settings.log_level でロギングレベルを制御できます。
  - settings.env は "development"/"paper_trading"/"live" を受け付けます。live 時は実運用用処理・チェックを強化する想定です。

- テスト用フック:
  - jquants_client._request のリトライ・トークンリフレッシュロジックは実ネットワークに依存します。ユニットテスト時は get_id_token や _request、news_collector._urlopen 等をモックすることで外部依存を切り離せます。
  - ETL の関数群は id_token 注入に対応しており、固定のトークンやモッククライアントで動作させられます。

- エラーと品質チェック:
  - run_daily_etl は品質チェック結果を ETLResult.quality_issues に格納します。品質エラーがあっても処理は継続します（運用者が判断して手動で対応する想定）。

---

この README はコードベースの主要機能と使い方を簡潔にまとめたものです。詳細な API 仕様、データスキーマ、StrategyModel.md / DataPlatform.md の設計書や運用手順は別途ドキュメントを参照してください。必要であれば README にサンプルスクリプトや CI / デプロイ手順、より詳しい環境変数一覧を追記します。