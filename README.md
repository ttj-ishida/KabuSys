# KabuSys

日本株向けの自動売買（データプラットフォーム＋戦略）ライブラリです。  
本リポジトリはデータ取得（J-Quants）、DuckDB ベースのデータ設計、ファクター計算・特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、ETL パイプラインなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 特徴（概要）

- J-Quants API クライアント（レートリミット、リトライ、トークン自動リフレッシュ対応）
- DuckDB に基づく 3 層データスキーマ（Raw / Processed / Feature / Execution）
- ETL パイプライン（差分取得、バックフィル、品質チェックフック）
- ファクター計算（モメンタム・ボラティリティ・バリュー等）と Z スコア正規化
- 戦略シグナル生成（コンポーネントスコアの重み付き統合、BUY/SELL 判定、Bear レジーム抑制）
- ニュース収集（RSS フィード、SSRF 対策、トラッキングパラメータ除去、記事–銘柄紐付け）
- マーケットカレンダー管理（営業日判定、next/prev/trading_days 等ユーティリティ）
- 監査（audit）・発注履歴テーブル定義（監査トレーサビリティ設計）

---

## 主な機能一覧

- data/
  - jquants_client.py: J-Quants API 呼び出し・保存ユーティリティ（fetch/save）
  - pipeline.py: 日次 ETL（run_daily_etl, run_prices_etl, ...）
  - schema.py: DuckDB スキーマ定義・初期化（init_schema）
  - news_collector.py: RSS 収集・整形・保存（fetch_rss, save_raw_news, run_news_collection）
  - calendar_management.py: 市場カレンダーの管理（is_trading_day, next_trading_day, calendar_update_job）
  - stats.py: zscore_normalize 等の統計ユーティリティ
  - audit.py: 監査テーブル DDL（signal_events, order_requests, executions）
- research/
  - factor_research.py: モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py: 将来リターン計算・IC（Spearman）・統計サマリー
- strategy/
  - feature_engineering.py: ファクターの正規化・features テーブルへの保存（build_features）
  - signal_generator.py: features と ai_scores からシグナル生成（generate_signals）
- config.py: 環境変数 / .env の自動読み込み、設定ラッパー（settings オブジェクト）

---

## 動作要件

- Python 3.10 以上（型ヒントで `X | None` を使用）
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml
- （任意）J-Quants API 利用には有効な J-Quants の refresh token が必要

パッケージのインストール例（仮）:
```bash
python -m pip install --upgrade pip
python -m pip install duckdb defusedxml
# プロジェクトを editable install する場合（setup が用意されていれば）
# python -m pip install -e .
```

---

## 環境変数（.env）

settings クラスは環境変数から設定を取得します。自動的にプロジェクトルート（.git または pyproject.toml がある場所）を探索し、`.env` と `.env.local` を読み込みます。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須（最低限設定が必要なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants の refresh token
- KABU_API_PASSWORD: kabu API パスワード（kabu 接続を使う場合）
- SLACK_BOT_TOKEN: Slack 通知を使う場合
- SLACK_CHANNEL_ID: Slack 通知チャンネルID

任意（デフォルト有り）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL、デフォルト: INFO）

例（.env）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. Python 3.10+ を用意する
2. 必要パッケージをインストールする（例）
   ```bash
   pip install duckdb defusedxml
   ```
3. プロジェクトルートに `.env` を作成し、上記の必須環境変数を設定する
4. データベース初期化（DuckDB スキーマ作成）
   - Python REPL またはスクリプトで次を実行:
     ```python
     from kabusys.data.schema import init_schema
     from kabusys.config import settings

     conn = init_schema(settings.duckdb_path)
     ```
   - これにより必要な全テーブルとインデックスが作成されます。

---

## 使い方（主要な呼び出し例）

Python スクリプトや REPL からライブラリを呼び出して利用します。以下は代表的な操作例です。

- DuckDB 接続の初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
```

- 日次 ETL（市場カレンダー・株価・財務の差分取得）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ファクターの計算・特徴量の構築（features テーブルへ書き込み）
```python
from kabusys.strategy import build_features
from datetime import date

n = build_features(conn, target_date=date(2024, 1, 1))
print(f"features upserted: {n}")
```

- シグナル生成（signals テーブルへ書き込み）
```python
from kabusys.strategy import generate_signals
from datetime import date

count = generate_signals(conn, target_date=date.today())
print(f"signals generated: {count}")
```

- ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection

# known_codes はニュースから抽出する銘柄コードの集合（オプション）
results = run_news_collection(conn, known_codes={"7203", "6758"})
print(results)  # {source_name: saved_count, ...}
```

- カレンダー更新ジョブ（夜間バッチとして）
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

- 設定値参照
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

---

## 注意事項 / 設計上のポイント

- ルックアヘッドバイアス回避: 戦略・特徴量計算は target_date 時点で利用可能なデータのみを用いるよう設計されています。
- 冪等性: データ保存関数は基本的に ON CONFLICT / DO UPDATE / DO NOTHING を使って冪等性を確保しています。
- レート制限: J-Quants API 呼び出しは固定間隔スロットリングで 120 req/min を順守します（内部 RateLimiter）。
- ニュース収集: SSRF や XML Bomb などを考慮して堅牢に実装されています（defusedxml、ホスト検査、サイズ上限など）。
- 環境読み込み: プロジェクトルートを .git / pyproject.toml から自動検出して `.env` を読み込みます。自動読み込みを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- KABUSYS_ENV は `development` / `paper_trading` / `live` のいずれかでなければなりません。

---

## ディレクトリ構成

以下は主要なファイルとディレクトリの構成（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - pipeline.py
      - schema.py
      - stats.py
      - features.py
      - calendar_management.py
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
    - monitoring/  (モジュール出口として __all__ に含まれているが、実装は別途)
- pyproject.toml (プロジェクトルートにある想定)

---

## 開発・テストのヒント

- DuckDB のインメモリ DB を使えばテストが容易です:
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema(":memory:")
  ```
- 設定自動ロードを無効化して、テスト専用の環境をプログラム内で設定するには:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
  その上でテストコード内で os.environ を設定するか、settings をモックしてください。
- RSS フェッチや外部 API 呼び出しはネットワークに依存するためユニットテストではモック推奨です（モジュールは内包関数をモックしやすい設計になっています）。

---

## 参考 / 今後の拡張案

- execution モジュールの実装（kabu ステーション等への実際の発注処理）
- AI スコア生成パイプライン（ai_scores テーブルの生成）
- Slack 通知や監視（monitoring）統合
- CI 用のスキーママイグレーションやデータ品質ダッシュボード

---

必要であれば、この README に対する英語版、あるいは具体的な運用手順（cron/airflow 用のジョブ例、Dockerfile、systemd unit など）も作成します。どの形式が必要か教えてください。