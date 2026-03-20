# KabuSys

日本株向けの自動売買システム用ライブラリ（KabuSys）。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買基盤のコア機能群をモジュール化した Python パッケージです。主な目的は次のとおりです。

- J-Quants API からの株価・財務・カレンダー取得と DuckDB への安全な保存（冪等）
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- 研究用ファクター計算（momentum, volatility, value など）
- 特徴量正規化・合成と戦略用 features テーブル作成
- シグナル生成（BUY/SELL）ロジック（重み付け・レジーム判定・エグジット判定）
- RSS からのニュース収集と銘柄紐付け（raw_news / news_symbols）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- 監査ログ（シグナル→注文→約定のトレース）

設計方針としては「ルックアヘッドバイアス回避」「冪等性」「外部依存の最小化」「堅牢なエラーハンドリング」を重視しています。

---

## 機能一覧

- data/
  - jquants_client: J-Quants API クライアント（レート制御・リトライ・トークン自動更新・DuckDB保存）
  - pipeline: 日次差分 ETL 実装（prices, financials, calendar）
  - schema: DuckDB スキーマ定義・初期化
  - news_collector: RSS 取得・前処理・raw_news 保存・銘柄抽出
  - calendar_management: market_calendar 管理・営業日判定ユーティリティ
  - stats: z-score 正規化などの統計ユーティリティ
  - audit: 発注・約定の監査ログスキーマ
- research/
  - factor_research: momentum / volatility / value のファクター計算
  - feature_exploration: 将来リターン、IC、統計サマリー等の研究用ユーティリティ
- strategy/
  - feature_engineering: 生ファクターのマージ・フィルタ・正規化 → features へ UPSERT
  - signal_generator: features と ai_scores を統合して final_score を算出、BUY/SELL を signals へ書込
- config: 環境変数管理（.env 自動ロード、必須チェック、環境判定）
- execution: （発注層のための名前空間。現状は __init__ のみ）
- monitoring: （監視系のための名前空間（パッケージ公開対象））

---

## セットアップ手順

前提
- Python 3.9+（typing | 等の構文が使われているため少なくとも 3.9 以上を想定）
- DuckDB を利用するため、純粋 Python 実装であれば pip で導入可能

1. リポジトリを取得し、仮想環境を用意する
   ```
   git clone <repo-url>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存パッケージをインストールする（例）
   ```
   pip install duckdb defusedxml
   ```
   - 他に必要なパッケージがあればプロジェクトの requirements.txt / pyproject.toml を参照してください。

3. パッケージをインストール（開発モード）
   ```
   pip install -e .
   ```

4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（config モジュール参照）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

   必須環境変数（このプロジェクトで参照される主要な値）：
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API パスワード
   - SLACK_BOT_TOKEN: Slack 通知に使用する Bot トークン
   - SLACK_CHANNEL_ID: 通知対象のチャンネル ID

   任意（デフォルト値あり）：
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: 実行環境（development / paper_trading / live）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

   サンプル .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=yyyy
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマ初期化
   Python REPL またはスクリプトで schema.init_schema を実行して DB を作成します。

   例:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```

---

## 使い方（簡単な例）

以下は主要ワークフローの例です。各モジュールは DuckDB の接続（duckdb.DuckDBPyConnection）を受け取る設計です。

1) 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
conn.close()
```

2) 特徴量作成（strategy.feature_engineering）
```python
from datetime import date
import duckdb
from kabusys.strategy import build_features

conn = duckdb.connect("data/kabusys.duckdb")
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
conn.close()
```

3) シグナル生成（strategy.signal_generator）
```python
from datetime import date
import duckdb
from kabusys.strategy import generate_signals

conn = duckdb.connect("data/kabusys.duckdb")
signals_count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {signals_count}")
conn.close()
```

4) ニュース収集ジョブ（news_collector）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(results)
conn.close()
```

5) J-Quants から直接データ取得して保存（テスト等）
```python
import duckdb
from kabusys.data import jquants_client as jq

conn = duckdb.connect("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print(saved)
conn.close()
```

ログ出力や動作モード（development / paper_trading / live）は環境変数 `KABUSYS_ENV` / `LOG_LEVEL` により制御されます。

---

## ディレクトリ構成

主なファイル・ディレクトリ構成（src 以下）:

- src/kabusys/
  - __init__.py
  - config.py
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
  - monitoring/  (パッケージ公開対象だが実装は別途)
  - その他（ドキュメントや設定ファイル）

（上記は本リポジトリ内の主要モジュールを抜粋したものです）

---

## 注意事項 / 実運用に関するメモ

- J-Quants API のレート制限や認証仕様に従うように実装済みですが、運用時は API 利用規約を順守してください。
- DuckDB スキーマは ON CONFLICT / トランザクション等で冪等性を確保していますが、運用スクリプト側でもバックアップやバージョン管理を行ってください。
- シグナル→発注→約定のフローを本番稼働する際は、execution 層（ブローカー API 統合）とリスク管理（注文サイズ、ポジション上限等）を必ず組み合わせてください。
- news_collector は RSS を解析しますが、外部サイトの利用規約・スクレイピング規約を確認のうえ利用してください。
- config はプロジェクトルートの `.git` または `pyproject.toml` を基準に自動で .env をロードします。CI やテスト時に自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

もし README に追記してほしい「使い方の具体的な CLI スクリプト」「テスト実行方法」「運用ガイド（cron/タスクスケジューラ設定例）」などがあれば、目的に合わせて別セクションを作成します。