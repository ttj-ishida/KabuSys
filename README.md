# KabuSys

日本株向けの自動売買システム基盤ライブラリ（ライブラリ形式）
（機能: データ取得・ETL、ファクター計算・特徴量作成、シグナル生成、ニュース収集、DuckDB スキーマ管理 等）

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計されたモジュール群です。  
主に以下のレイヤーを提供します。

- Data layer（J-Quants API からのデータ取得、DuckDB 保存、ETL パイプライン）
- Research layer（ファクター計算・探索・統計ユーティリティ）
- Strategy layer（特徴量構築、シグナル生成）
- Execution / Audit（スキーマ定義・発注ログ・約定ログの設計）
- News collector（RSS から記事収集・銘柄紐付け）

設計上の特徴:
- DuckDB を主要な時系列 DB として使用（オンディスク / :memory: 両対応）
- J-Quants API に対するレート制御・リトライ・トークン自動更新対応
- ETL / DB 操作は冪等（ON CONFLICT / トランザクション）に配慮
- ルックアヘッドバイアスを避ける設計（target_date 時点のデータのみ使用）
- 外部依存を最小限にし、テスト可能性を意識した実装

---

## 機能一覧

- DuckDB スキーマ定義と初期化（kabusys.data.schema.init_schema）
- J-Quants API クライアント（差分取得・ページネーション・保存）
  - 株価日足、財務データ、マーケットカレンダー取得
  - save_* 系で raw_* テーブルへ冪等保存
- ETL パイプライン（差分取得・backfill・品質チェック）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- ファクター計算（research/factor_research）
  - momentum / volatility / value など
- 特徴量構築（strategy/feature_engineering.build_features）
  - 正規化（Zスコア）、ユニバースフィルタ、features テーブルへの UPSERT
- シグナル生成（strategy/signal_generator.generate_signals）
  - ファクター + AI スコア統合、BUY/SELL 生成、SELL 優先ポリシー
- ニュース収集（data/news_collector）
  - RSS フィード取得、前処理、raw_news / news_symbols への保存
  - SSRF 対策・受信サイズ制限・トラッキングパラメータ除去
- カレンダー管理（data/calendar_management）
  - 営業日判定、next/prev_trading_day、calendar_update_job
- 汎用統計ユーティリティ（data/stats.zscore_normalize、research の rank/ic 等）
- 設定管理（kabusys.config）: 環境変数 / .env 自動ロード（オプトアウト可）

---

## 必要条件 / 依存関係

最低限必要そうな依存パッケージ（コードから推定）：

- Python 3.9+
- duckdb
- defusedxml

その他: 標準ライブラリ（urllib, hashlib, datetime 等）を使用します。  
環境に合わせて必要に応じて追加ライブラリをインストールしてください。

例:
pip install duckdb defusedxml

（プロジェクトに requirements.txt / pyproject.toml があればそちらを参照してください）

---

## セットアップ手順

1. リポジトリをクローン / ワークディレクトリへ移動

2. 仮想環境を作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate（Unix系）または .venv\Scripts\activate（Windows）

3. 依存パッケージをインストール
   - pip install duckdb defusedxml

4. 環境変数の設定
   - プロジェクトルート（.git や pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます（kabusys.config）。
   - 自動ロードを無効化したい場合:
     - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定する

5. 必須環境変数（例）
   以下の変数はコード内で必須とされているものです（.env に設定してください）:

   - JQUANTS_REFRESH_TOKEN: J-Quants の refresh token
   - KABU_API_PASSWORD: kabuステーション API のパスワード
   - SLACK_BOT_TOKEN: Slack 通知用トークン
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

   オプション / デフォルト:
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）

   例の .env ファイル（簡易）:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

6. DuckDB スキーマの初期化
   Python REPL またはスクリプトから:
   ```py
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)  # Path オブジェクトを渡せます
   ```

---

## 使い方（主要な API 例）

以下は最小限のコード例です。日付は datetime.date を使用します。

- 初期化（DB）
```py
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)
```

- 日次 ETL 実行（株価・財務・カレンダーを差分取得）
```py
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量構築（features テーブル作成）
```py
from kabusys.strategy import build_features
from datetime import date

n = build_features(conn, target_date=date(2024, 1, 1))
print(f"features upserted: {n}")
```

- シグナル生成（signals テーブル作成）
```py
from kabusys.strategy import generate_signals
from datetime import date

total = generate_signals(conn, target_date=date(2024, 1, 1), threshold=0.6)
print(f"signals written: {total}")
```

- ニュース収集ジョブ
```py
from kabusys.data.news_collector import run_news_collection

# known_codes は既知の銘柄コードセット（抽出時に使用）
results = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
print(results)  # {source_name: saved_count}
```

- カレンダー更新（夜間バッチ）
```py
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

- 市場日判定ユーティリティ
```py
from kabusys.data.calendar_management import is_trading_day, next_trading_day

is_trade = is_trading_day(conn, date(2024, 1, 1))
next_td = next_trading_day(conn, date(2024, 1, 1))
```

注意:
- 各関数は DuckDB 接続を受け取り、データの読み書きを行います。
- run_daily_etl などは内部でエラーハンドリングし、ETLResult にエラーや品質問題を集約します。処理の成否は returned ETLResult を参照してください。

---

## 設定と環境変数の詳細

主な環境変数（コード上で参照されるもの）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB DB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境名 (development | paper_trading | live)、デフォルト development
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）、デフォルト INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" にするとプロジェクトルートの .env 自動読み込みを無効化

.env ファイルはプロジェクトルートから自動読み込みされます（.env → .env.local の順で上書き）。読み込みロジックは quotes, inline comments, export プレフィクス等に対応しています。

---

## ディレクトリ構成（主なファイル）

以下はソースの主要ファイルと簡単な説明です（src/kabusys/ を想定）。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込み・Settings クラス（settings オブジェクト）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch/save 関数）
    - news_collector.py — RSS 収集・前処理・DB 保存
    - schema.py — DuckDB スキーマ定義と init_schema
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — 市場カレンダー関連
    - audit.py — 監査ログ用テーブル DDL（発注→約定のトレーサビリティ）
    - features.py — data.stats の再エクスポート
  - research/
    - __init__.py
    - factor_research.py — momentum / volatility / value の計算
    - feature_exploration.py — forward returns / IC / summary / rank
  - strategy/
    - __init__.py
    - feature_engineering.py — features テーブル構築（正規化・ユニバースフィルタ等）
    - signal_generator.py — final_score 計算・BUY/SELL 生成・signals への書き込み
  - execution/
    - __init__.py
    - （将来的な発注ラッパーや broker integration 用）
  - monitoring/
    - （監視 / メトリクス関連の補助モジュールを想定）

各モジュールはドキュメンテーション文字列（docstring）で目的・設計方針・注意点を詳細に記載しています。まずは `kabusys.data.schema.init_schema()` で DB を作成し、`kabusys.data.pipeline.run_daily_etl()` を実行するワークフローが基本になります。

---

## 開発 / 実装上の注意点

- DuckDB へ保存する SQL は冪等（ON CONFLICT ...）を基本としていますが、初回はスキーマ初期化（init_schema）を必ず行ってください。
- J-Quants API のレート制限・リトライは jquants_client に入っています。大量取得時は適切にスロットリングされます。
- NewsCollector は SSRF 対策や受信サイズ制限を行っていますが、外部フィードの扱いは慎重に行ってください。
- 設定は環境変数ベースです。CI / 本番環境では機密情報の管理にご注意ください。

---

## 貢献・問い合わせ

この README はソースコードから主要機能を抜粋した概要です。実装の詳細や API の追加・改善はソース内 docstring を参照してください。問題報告や機能要望はリポジトリの Issue 等でお願いします。

---

以上。必要であれば README に追加したい具体的な実行例（cron ジョブ、systemd unit、Slack 通知例 等）を指定してください。