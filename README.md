# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）のREADMEです。  
本リポジトリはデータ取得（J-Quants）→ ETL → 特徴量生成 → シグナル生成 → 発注/監査までを想定したモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株アルゴリズム取引のための内部ライブラリ群です。主な目的は以下のとおりです。

- J-Quants API からの市場データ（株価、財務、カレンダー）を安全に取得・保存する。
- DuckDB を用いたデータレイヤ（Raw / Processed / Feature / Execution）のスキーマ定義と初期化。
- 研究（research）モジュールで算出した生ファクターを変換・正規化して戦略用特徴量を構築。
- 特徴量と AI スコアを統合して売買シグナルを生成。
- RSS ベースのニュース収集・銘柄抽出。
- カレンダー管理・営業日判定・夜間更新ジョブ等のユーティリティ。

設計上の注意点:
- ルックアヘッドバイアスを防ぐため、処理は必ず target_date 時点のデータのみを参照する設計です。
- 外部への発注（ブローカー）との結合は execution 層で行う想定で、strategy 層は発注 API に依存しないよう分離されています。
- 冪等性（idempotency）を重視し、DB への保存は ON CONFLICT / トランザクションで安全に実行されます。

---

## 機能一覧

主要モジュールと提供機能（抜粋）:

- kabusys.config
  - .env ファイル / 環境変数の自動読み込み（プロジェクトルート検出）
  - 必須環境変数のラップ（ValueError を投げる）
- kabusys.data
  - jquants_client: J-Quants API クライアント（レートリミット / リトライ / トークン自動更新）
  - schema: DuckDB スキーマ定義と init_schema / get_connection
  - pipeline: 差分 ETL（prices / financials / calendar）と日次 ETL 実行 run_daily_etl
  - news_collector: RSS 取得・前処理・DB 保存、銘柄抽出
  - calendar_management: 営業日判定、next/prev_trading_day、calendar_update_job
  - stats: クロスセクション Z スコア正規化
  - features: zscore_normalize の公開再エクスポート
  - audit: 発注／約定の監査ログ用 DDL（監査トレーサビリティ）
- kabusys.research
  - factor_research: momentum, volatility, value のファクター計算
  - feature_exploration: 将来リターン計算、IC（スピアマン）計算、統計サマリー
- kabusys.strategy
  - feature_engineering.build_features: 生ファクターの統合・正規化・features テーブルへの upsert
  - signal_generator.generate_signals: features + ai_scores を元に BUY/SELL シグナルを生成
- kabusys.data.pipeline.run_daily_etl: 日次 ETL（カレンダー→株価→財務→品質チェック）の統合実行
- セキュリティ対策: RSS の SSRF 防止、XML パースの防御、受信バイト数制限等

---

## 必要な環境変数

config.Settings クラスで参照される主な環境変数（デフォルトや必須性を併記）:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu API（kabuステーション等）のパスワード
- SLACK_BOT_TOKEN — Slack 通知用トークン
- SLACK_CHANNEL_ID — Slack 通知先チャネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development|paper_trading|live)（デフォルト: development）
- LOG_LEVEL — ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)（デフォルト: INFO）

.env 自動読み込みについて:
- 起点はパッケージ内の config モジュールで、.git または pyproject.toml を持つ親ディレクトリをプロジェクトルートとみなします。
- 読み込み優先順位: OS 環境変数 > .env.local > .env
- 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順（ローカル開発用、例）

1. リポジトリをクローン:
   ```
   git clone <repository-url>
   cd <repository>
   ```

2. Python 仮想環境作成（例: venv）:
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージのインストール（プロジェクトに pyproject/requirements があればそれに従ってください）:
   ```
   pip install duckdb defusedxml
   # 他、必要に応じて pip install -r requirements.txt
   ```

4. 必須環境変数を設定（.env を作成）:
   - .env.example を参考に .env を用意してください。最低限 JQUANTS_REFRESH_TOKEN 等を設定する必要があります。
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     KABU_API_PASSWORD=yyyy
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

5. DuckDB スキーマ初期化:
   - Python REPL またはスクリプトで:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```

---

## 使い方（主要な API 例）

以下はライブラリの代表的な利用例（Python スクリプト）です。

1) DB 初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL の実行（J-Quants からデータ取得 → 保存 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)
print(result.to_dict())
```

3) 特徴量（features）構築
```python
from kabusys.strategy import build_features
from datetime import date
n = build_features(conn, target_date=date(2024, 1, 20))
print(f"upserted features: {n}")
```

4) シグナル生成
```python
from kabusys.strategy import generate_signals
from datetime import date
count = generate_signals(conn, target_date=date(2024, 1, 20), threshold=0.6)
print(f"signals written: {count}")
```

5) RSS ニュース収集（raw_news / news_symbols への保存）
```python
from kabusys.data.news_collector import run_news_collection
# known_codes: 有効銘柄コードのセット（抽出時に利用）
res = run_news_collection(conn, known_codes={"7203","6758"})
print(res)  # {source_name: saved_count, ...}
```

6) カレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn, lookahead_days=90)
print(f"calendar saved: {saved}")
```

7) J-Quants から生データを直接取得して保存（テスト用途）
```python
from kabusys.data import jquants_client as jq
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,20))
saved = jq.save_daily_quotes(conn, records)
```

注意:
- settings から環境変数参照が行われるため、上記処理を行う前に必須環境変数を設定してください。
- ETL / API 呼び出しはネットワークと外部 API に依存します。レート制限・認証に注意してください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュールと簡易説明です。

- src/kabusys/
  - __init__.py  -- パッケージ定義（version 等）
  - config.py    -- 環境設定・.env 読み込みロジック / Settings
  - data/
    - __init__.py
    - jquants_client.py       -- J-Quants API クライアント（取得 / 保存ロジック）
    - news_collector.py       -- RSS 取得・前処理・DB 保存・銘柄抽出
    - schema.py               -- DuckDB スキーマ定義 / init_schema
    - stats.py                -- zscore_normalize 等の統計ユーティリティ
    - pipeline.py             -- ETL パイプライン（run_daily_etl 等）
    - calendar_management.py  -- カレンダー管理・営業日ユーティリティ
    - audit.py                -- 監査ログ用 DDL（signal_events / order_requests / executions 等）
    - features.py             -- features 再エクスポート
  - research/
    - __init__.py
    - factor_research.py      -- momentum / volatility / value のファクター計算
    - feature_exploration.py  -- forward returns / IC / factor summary
  - strategy/
    - __init__.py
    - feature_engineering.py  -- build_features（正規化・ユニバースフィルタ等）
    - signal_generator.py     -- generate_signals（final_score 計算、BUY/SELL 生成）
  - execution/
    - __init__.py  -- 発注・ブローカー連携はここを実装する想定
  - monitoring/     -- 監視・アラート機能（必要に応じて配置）

（コードの各ドキュメント文字列に詳細な仕様や設計方針が記載されています。内部のコメント・docstring を参照してください。）

---

## 運用上の注意・トラブルシューティング

- 環境変数未設定:
  - settings が必須変数を参照すると ValueError を投げます。例: JQUANTS_REFRESH_TOKEN が未設定。
- .env の自動ロード:
  - プロジェクトルート検出は .git または pyproject.toml を探します。配布後にルートが検出できない場合は自動ロードされません。その場合は明示的に環境変数をセットしてください。
- DuckDB ファイルの場所:
  - デフォルトは data/kabusys.duckdb。別パスを使う場合は init_schema/get_connection に指定してください。
- J-Quants API:
  - レート制限（120 req/min）を遵守するため内部でスロットリングが入ります。また 401 受信時はリフレッシュトークンで自動リフレッシュします。
- ニュース収集:
  - RSS の取得では SSRF・XML Bomb 等の攻撃対策が施されています。外部フィードは必ず https/http スキームであること、公開された RSS を使ってください。
- テスト:
  - 環境分離のため KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 にして自動 .env 読み込みを無効化できます。

---

## 参考・開発者向けメモ

- 戦略ロジックや閾値（例: デフォルトの BUY 閾値 0.60、Zscore クリップ ±3、最小株価 300 円 等）は各モジュール内部の定数で管理されています。必要に応じてパラメータ化してください。
- features テーブルは日付単位で置換（DELETE + bulk INSERT）して冪等性を保ちます。generate_signals も同様に日付単位で置換します。
- 研究用モジュール（kabusys.research）は外部ライブラリに依存せず、純粋な Python + DuckDB SQL で記述されています。分析用途の拡張に適しています。

---

この README はライブラリの主要な使い方と設計の要点をまとめたものです。詳細な仕様（StrategyModel.md、DataPlatform.md、DataSchema.md 等）はリポジトリ内ドキュメントや docstring を参照してください。必要であれば、サンプルスクリプトや CLI ユーティリティの追加ドキュメントも作成できます。