# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。  
J-Quants 等からマーケットデータを取得して DuckDB に保存し、研究用ファクターの計算、特徴量作成、シグナル生成、ニュース収集、カレンダー管理などの機能を提供します。

バージョン: 0.1.0

---

## 主要な特徴

- データ取得・保存（J-Quants API クライアント）
  - 日次株価（OHLCV）・財務データ・JPX カレンダーのページネーション対応取得
  - API レート制御、リトライ、トークン自動リフレッシュ
- DuckDB ベースのスキーマ定義と初期化（冪等）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- ファクター計算（Momentum / Value / Volatility / Liquidity）
- 特徴量エンジニアリング（Z スコア正規化、ユニバースフィルタ）
- シグナル生成（ファクター＋AI スコアを統合、BUY/SELL 生成、Bear レジーム抑制）
- ニュース収集（RSS フィード → raw_news、SSRF 対策・トラッキングパラメータ除去）
- マーケットカレンダー管理（営業日判定・次/前営業日・期間内の営業日取得）
- 監査ログ（signal / order / execution のトレース設計）
- 外部ライブラリへの過度な依存を避けた実装（主に標準ライブラリ + 必要最小限の依存）

---

## 機能一覧（モジュール抜粋）

- kabusys.config
  - .env ファイル / 環境変数の自動読み込み（プロジェクトルート検出）および設定取得
  - 必須環境変数チェック
- kabusys.data.jquants_client
  - J-Quants API 呼び出し、取得データを DuckDB に保存するユーティリティ
- kabusys.data.schema
  - DuckDB のテーブル定義と初期化（init_schema）
- kabusys.data.pipeline
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- kabusys.data.news_collector
  - RSS フィードの取得・整形・DB保存、記事と銘柄コードの紐付け
- kabusys.research
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary
- kabusys.strategy
  - build_features（特徴量作成）
  - generate_signals（売買シグナル生成）
- kabusys.data.calendar_management
  - 営業日判定 / next_trading_day / prev_trading_day / calendar_update_job
- kabusys.data.audit
  - 監査ログ（signal_events, order_requests, executions）定義

---

## 要件

- Python 3.10 以上（代替的な型表記（|）などを使用しているため）
- 主な依存パッケージ（最低限）
  - duckdb
  - defusedxml
- （任意）その他: requests 等は入っていません。標準ライブラリの urllib を使用します。

インストール例（仮に setuptools/pyproject が整備されている場合）:
```bash
python -m pip install -U pip
python -m pip install duckdb defusedxml
# またはリポジトリから editable install:
# pip install -e .
```

---

## 環境変数（主なもの）

設定は .env / .env.local / OS 環境変数から読み込まれます。自動ロードはデフォルトで有効です。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須:
- JQUANTS_REFRESH_TOKEN
  - J-Quants 用リフレッシュトークン（jquants_client で ID トークン取得に使用）
- SLACK_BOT_TOKEN
  - Slack 通知に使用するトークン（Slack 連携部分がある場合）
- SLACK_CHANNEL_ID
  - Slack チャンネル ID

その他:
- KABU_API_PASSWORD
  - kabuステーション API のパスワード
- KABU_API_BASE_URL
  - kabu API のベース URL（既定: http://localhost:18080/kabusapi）
- DUCKDB_PATH
  - DuckDB ファイルパス（既定: data/kabusys.duckdb）
- SQLITE_PATH
  - 監視用 SQLite（既定: data/monitoring.db）
- KABUSYS_ENV
  - "development" / "paper_trading" / "live"（既定: development）
- LOG_LEVEL
  - "DEBUG","INFO","WARNING","ERROR","CRITICAL"（既定: INFO）

設定はコードから次のように参照できます:
```python
from kabusys.config import settings
token = settings.jquants_refresh_token
```

---

## セットアップ手順（例）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   ```bash
   pip install --upgrade pip
   pip install duckdb defusedxml
   # dev 用に linters / test ライブラリ等があれば追加
   ```

4. 環境変数を用意
   - プロジェクトルートに `.env` を作成し、必要な値を設定（.env.example を参照する想定）。
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     LOG_LEVEL=INFO
     ```

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
     ```

---

## 使い方（主要な操作例）

以下は最小限の呼び出し例です。実運用ではログ設定やエラー処理、スケジューラ（cron, Airflow 等）に組み込む想定です。

1. 日次 ETL を実行（市場カレンダー取得 → 株価 → 財務 → 品質チェック）
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定して任意の日で実行可能
print(result.to_dict())
conn.close()
```

2. 特徴量をビルド
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import build_features

conn = init_schema("data/kabusys.duckdb")
n = build_features(conn, date(2026, 1, 20))
print(f"features upserted: {n}")
conn.close()
```

3. シグナル生成
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import generate_signals

conn = init_schema("data/kabusys.duckdb")
count = generate_signals(conn, date(2026, 1, 20))
print(f"signals generated: {count}")
conn.close()
```

4. RSS ニュース収集（既知銘柄セットを与えて紐付け）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: トヨタ、ソニー、ソフトバンク等
result = run_news_collection(conn, known_codes=known_codes)
print(result)  # {source_name: saved_count}
conn.close()
```

5. カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
conn.close()
```

---

## ローカル開発・デバッグのヒント

- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を基準に検索します。テストや CI で無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 環境を切り替えるには `KABUSYS_ENV=development|paper_trading|live` を設定します。`settings.is_live` や `is_paper` をコードで参照可能です。
- ログレベルは `LOG_LEVEL` 環境変数で調整できます（"DEBUG" 等）。
- J-Quants API のレート制限（120 req/min）やリトライポリシーは jquants_client に実装済みです。大量取得時は留意してください。
- RSS の取得では SSRF 対策や最大受信サイズ制限が実装されています（defusedxml を使用）。

---

## ディレクトリ構成（抜粋）

以下は主なファイル・ディレクトリの構成（リポジトリ内の `src/kabusys` を中心に抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - stats.py
      - pipeline.py
      - calendar_management.py
      - features.py
      - audit.py
      - (その他: quality.py 等想定)
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
    - monitoring/  # __all__ に含まれるが、コードベースに実装ファイルがある想定

ドキュメントや設計仕様（DataPlatform.md / StrategyModel.md 等）が参照されています。実運用向けの追加モジュール（監視、実行ブローカーラッパ、Slack 通知など）を組み合わせて利用してください。

---

## 貢献・拡張案

- risk management / position sizing の追加（ポートフォリオ最適化）
- execution 層のブローカー実装（kabuステーション連携ラッパ）
- 単体テストと CI（DuckDB のインメモリ DB を用いたテスト）
- モニタリング・アラート（品質チェックや ETL エラー通知）

---

もし README に追記したい実行スクリプトや、CI / Docker 環境での起動方法、具体的な .env.example を追加希望であれば教えてください。必要に応じてサンプルの CLI スクリプトや systemd/cron の例も作成します。