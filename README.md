# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム（ライブラリ）です。データ取得（J‑Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログ（トレーサビリティ）までを一貫して扱えるよう設計されています。データ永続化には DuckDB を利用し、戦略ロジックはルックアヘッドバイアスに配慮して実装されています。

---

## 主要な特徴（概要）

- データ取得
  - J‑Quants API から株価（OHLCV）、財務情報、JPX カレンダーを取得（レート制限・リトライ・トークン自動リフレッシュ対応）
- ETL パイプライン
  - 差分取得（バックフィル対応）、品質チェック、DuckDB への冪等保存
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層を含むスキーマ定義と初期化機能
- 研究（Research）機能
  - ファクター計算（Momentum, Volatility, Value 等）、将来リターン・IC 計算、統計サマリー
- 特徴量エンジニアリング
  - ファクター統合、ユニバースフィルタ、Z スコア正規化、features テーブルへの UPSERT
- シグナル生成
  - 正規化済みファクター＋AI スコア統合による final_score 計算、BUY/SELL の生成と signals テーブルへの書き込み（冪等）
- ニュース収集
  - RSS 取得・前処理・記事保存、銘柄コード抽出（SSRF 対策・トラッキングパラメータ除去）
- マーケットカレンダー管理
  - 営業日判定・前後営業日取得・夜間バッチ更新ジョブ
- 監査ログ（Audit）
  - signal → order_request → execution のトレースを残すテーブル群
- 環境変数管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）。自動ロード無効化フラグあり。

---

## 機能一覧（モジュール別）

- kabusys.config
  - 環境変数管理、.env 自動読み込み、必須設定チェック
- kabusys.data
  - jquants_client：J‑Quants API クライアント（取得 / 保存ユーティリティ）
  - schema：DuckDB スキーマ定義・初期化
  - pipeline：ETL ジョブ（run_daily_etl 等）
  - news_collector：RSS 収集・前処理・保存・銘柄紐付け
  - calendar_management：JPX カレンダー操作・更新ジョブ
  - stats：Z スコア正規化など汎用統計ユーティリティ
- kabusys.research
  - factor_research：mom/vol/value 等のファクター計算
  - feature_exploration：将来リターン計算、IC、要約統計
- kabusys.strategy
  - feature_engineering.build_features：features テーブル作成
  - signal_generator.generate_signals：signals テーブルへのシグナル書き込み
- kabusys.execution / monitoring
  - （実行・モニタリング関連の拡張領域）

---

## セットアップ手順

前提:
- Python 3.9+（typing の union 表記や型注釈を利用）
- duckdb がインストール可能な環境
- J‑Quants API トークン等が取得済み

1. リポジトリをチェックアウト
   - （ここではパッケージが `src/` 配下にあることを想定）

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. インストール
   - pip install -e . 
   - （requirements.txt / pyproject.toml がある場合はそちらに従ってください）

4. 必要な環境変数を設定
   - JQUANTS_REFRESH_TOKEN: J‑Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用（必須または用途に応じて）
   - DUCKDB_PATH（任意、デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: DEBUG/INFO/...
   - 自動 .env 読み込みはプロジェクトルートの .env/.env.local を参照します。自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで次を実行:
     - from kabusys.data.schema import init_schema
       init_schema("data/kabusys.duckdb")
   - または、メモリ DB でテスト: init_schema(":memory:")

---

## 使い方（サンプル）

以下は主要な操作フローの例です。適宜ログ設定や例外処理を追加してください。

- DuckDB 接続とスキーマ初期化
```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.config import settings

# ファイル DB を初期化して接続を取得
conn = init_schema(settings.duckdb_path)
# 既に初期化済みで接続だけ欲しい場合:
# conn = get_connection(settings.duckdb_path)
```

- 日次 ETL の実行（J‑Quants から株価/財務/カレンダーを取得）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定すれば任意日
print(result.to_dict())
```

- 特徴量の構築（features テーブルの作成）
```python
from kabusys.strategy import build_features
from datetime import date

n = build_features(conn, target_date=date.today())
print(f"features upserted: {n}")
```

- シグナル生成（signals テーブルへ書き込む）
```python
from kabusys.strategy import generate_signals
from datetime import date

count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals generated: {count}")
```

- ニュース収集ジョブの実行
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes は銘柄コードの集合（例: prices_daily に存在する code）
# 省略すると銘柄抽出を行わない（raw_news のみ保存）
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=None)
print(res)
```

- マーケットカレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

注意点:
- 各関数は DuckDB 接続（duckdb.DuckDBPyConnection）を直接受け取り、トランザクションや冪等性を内部で考慮しています。
- J‑Quants API 呼び出しはレート制限・リトライ・401 リフレッシュを内蔵しています。必要に応じて id_token を引数で注入できます（主にテスト用途）。

---

## ディレクトリ構成（主要ファイル）

以下はソースツリー（src/kabusys）内の主要モジュールと役割の概観です。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定
  - data/
    - __init__.py
    - jquants_client.py       — J‑Quants API クライアント（取得・保存）
    - news_collector.py       — RSS / ニュース収集と保存
    - schema.py               — DuckDB スキーマ定義と init_schema
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - stats.py                — 統計ユーティリティ（zscore_normalize 等）
    - features.py             — features インターフェース（再エクスポート）
    - calendar_management.py  — カレンダー管理・ジョブ
    - audit.py                — 監査ログスキーマ定義
  - research/
    - __init__.py
    - factor_research.py      — ファクター計算（momentum/volatility/value）
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py  — features 作成（build_features）
    - signal_generator.py     — signals 作成（generate_signals）
  - execution/                — 発注・実行層（プレースホルダ）
  - monitoring/               — 監視用モジュール（プレースホルダ）

---

## 設定例 (.env)

プロジェクトルートに .env または .env.local を置くことで自動読み込みされます（優先度: OS 環境 > .env.local > .env）。例:

KABUSYS_ENV=development
LOG_LEVEL=INFO
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

自動読み込みを無効化する場合:
- export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 注意事項 / ベストプラクティス

- DuckDB ファイルはバックアップや運用ルールを設けてください（特に production/live 環境）。
- J‑Quants の API レート・リクエスト制限を守るため、jquants_client は内部でスロットリングしています。直接大量リクエストを投げないでください。
- 設計上、ルックアヘッドバイアスを避けるため「target_date 時点の情報のみ」を利用する実装ポリシーが採られています。外部データや将来情報の取り扱いに注意してください。
- tests 用に環境変数の自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。

---

必要であれば README に「実行スクリプト例」や「デバッグ・ロギング設定」「CI 用の最小テスト例」などの追記を行います。どの項目を詳しく書き足しますか？