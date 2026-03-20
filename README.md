# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ集です。  
このリポジトリはデータ取得（J-Quants）、ETL、特徴量算出、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどを含む一連の機能をモジュール化しています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の機能を備えた日本株自動売買システムの基盤ライブラリです。  
設計方針として、ルックアヘッドバイアス対策・冪等性（idempotency）・オフラインでの研究（research）サポート・外部 API のレート制御や堅牢なエラーハンドリングを重視しています。

主要コンポーネント（概略）:
- data: J-Quants クライアント、DuckDB スキーマ、ETL パイプライン、ニュース収集、カレンダー管理、統計ユーティリティ
- research: ファクター計算、特徴量探索ユーティリティ（IC, forward returns 等）
- strategy: 特徴量の正規化・合成（feature_engineering）、シグナル生成（signal_generator）
- execution: 発注・約定・ポジション管理（スケルトンあり）
- monitoring: 監視・通知（Slack 連携想定）など（モジュールは準備されている想定）

---

## 主な機能一覧

- J-Quants API クライアント
  - 株価日足、財務データ、マーケットカレンダー取得（ページネーション対応）
  - レート制御（120 req/min）、リトライ、トークン自動リフレッシュ
  - DuckDB への冪等保存ユーティリティ（ON CONFLICT / DO UPDATE 等）
- DuckDB スキーマ定義と初期化（raw / processed / feature / execution レイヤー）
- ETL パイプライン（差分更新・バックフィル・品質チェック呼び出し）
- ファクター計算（momentum, volatility, value など）
- 特徴量構築（Zスコア正規化・ユニバースフィルタ）と features テーブルへの保存
- シグナル生成（複数コンポーネントのスコア統合、BUY/SELL 判定、signals テーブル保存）
- ニュース収集（RSS）＋記事の前処理、銘柄コード抽出、raw_news / news_symbols 保存
- マーケットカレンダー管理（営業日判定、next/prev/trading days）
- 監査ログ（signal_events / order_requests / executions 等のDDL定義）
- 一般的な統計ユーティリティ（zscore_normalize など）

---

## 動作環境・前提

- Python 3.9+
- 依存ライブラリ（代表例）:
  - duckdb
  - defusedxml
- J-Quants API のリフレッシュトークン、kabuステーション API のパスワード等の環境変数が必要

（プロジェクトの requirements.txt がある場合はそちらを優先して下さい）

---

## セットアップ手順

1. リポジトリをクローン・移動

   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境作成（任意）

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Unix / macOS
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール

   例（pip）:

   ```bash
   pip install duckdb defusedxml
   # 開発時は editable install
   pip install -e .
   ```

   ※ packaging / pyproject.toml に依存関係が記載されている場合は `pip install -e .` や `pip install .` でインストールしてください。

4. 環境変数の設定

   プロジェクトルート（.git または pyproject.toml がある場所）に `.env` / `.env.local` を置くことで自動で環境変数を読み込みます（自動ロードはデフォルトで有効）。

   必須の環境変数例（.env）:

   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. DuckDB スキーマ初期化

   Python REPL やスクリプトから以下を実行して DB とテーブルを初期化します:

   ```python
   from kabusys.data.schema import init_schema, get_connection
   conn = init_schema("data/kabusys.duckdb")  # :memory: も可
   ```

---

## 使い方（主要ユースケース）

以下に典型的な操作フローと利用例を示します。

1. 日次 ETL の実行（市場カレンダー取得、株価・財務の差分取得、品質チェック）

   ```python
   from datetime import date
   import duckdb
   from kabusys.data.schema import init_schema
   from kabusys.data.pipeline import run_daily_etl

   conn = init_schema("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

2. 特徴量（features）構築

   - ETL により prices_daily / raw_financials が揃った後、strategy.feature_engineering.build_features を使って features テーブルを更新します。

   ```python
   from datetime import date
   from kabusys.strategy import build_features
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   count = build_features(conn, target_date=date(2025, 3, 1))
   print(f"features upserted: {count}")
   ```

3. シグナル生成

   ```python
   from datetime import date
   from kabusys.strategy import generate_signals
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   total = generate_signals(conn, target_date=date(2025, 3, 1))
   print(f"signals generated: {total}")
   ```

   - 重みや閾値は generate_signals の引数で上書き可能です。

4. ニュース収集（RSS）

   ```python
   from kabusys.data.news_collector import run_news_collection
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   results = run_news_collection(conn)
   print(results)  # {source_name: saved_count}
   ```

   - 銘柄抽出用の known_codes を渡すことで news_symbols テーブルへの紐付けも行えます。

5. マーケットカレンダー更新（夜間バッチ）

   ```python
   from kabusys.data.calendar_management import calendar_update_job
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   saved = calendar_update_job(conn)
   print(f"calendar saved: {saved}")
   ```

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: モニタリング用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境 ("development", "paper_trading", "live")（デフォルト: development）
- LOG_LEVEL: ログレベル ("DEBUG","INFO",...)（デフォルト: INFO）

注意: Settings クラスはこれらを参照します。必須値が不足していると起動時に例外が発生します。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要モジュールと役割の一覧です。

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得＋保存ユーティリティ）
    - news_collector.py     — RSS ニュース収集・保存
    - schema.py             — DuckDB スキーマ定義と init_schema
    - stats.py              — 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py— マーケットカレンダー管理（is_trading_day 等）
    - audit.py              — 監査ログ DDL 定義
    - features.py           — features ユーティリティのエクスポート
  - research/
    - __init__.py
    - factor_research.py    — momentum / volatility / value の計算
    - feature_exploration.py— forward returns / IC / summary 等（研究向け）
  - strategy/
    - __init__.py
    - feature_engineering.py— 生ファクターを統合・正規化して features に保存
    - signal_generator.py   — final_score 計算と signals テーブルへの保存
  - execution/
    - __init__.py
    - (発注・約定関連の実装ファイルが想定されます)
  - monitoring/
    - (監視 / 通知機能用モジュールが想定されます)

---

## 開発上の注意点 / 設計メモ

- ルックアヘッドバイアスを防ぐため、シグナル生成・特徴量計算は target_date 時点のデータのみを参照する設計になっています。
- DuckDB への保存は可能な限り冪等（ON CONFLICT 句や RETURNING）を使って実装されています。
- ネットワーク呼び出し（J-Quants, RSS 等）はレート制御・リトライ・SSRF や XML 攻撃対策（defusedxml）を組み込んでいます。
- テストや CI では環境変数の自動ロードを無効化するために `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用できます。
- settings.is_live / is_paper / is_dev を使って実行モードに応じた振る舞い（例: 実発注を抑制）を実装してください。

---

## 例: 最低限のスクリプト (全体の流れ)

```python
# run_daily.py
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.strategy import build_features, generate_signals

def main():
    conn = init_schema("data/kabusys.duckdb")
    etl_res = run_daily_etl(conn, target_date=date.today())
    print("ETL:", etl_res.to_dict())

    # 特徴量構築
    build_features(conn, date.today())
    # シグナル生成
    generate_signals(conn, date.today())

if __name__ == "__main__":
    main()
```

---

## さらに読むべき設計ドキュメント（リポジトリ内想定）

このコードベースは README に加えて次のような設計ドキュメント（プロジェクトルートに置かれる想定）を参照することを推奨します。

- DataPlatform.md
- StrategyModel.md
- Research/README.md

（これらはコード中のコメントで参照されています）

---

もし README に追記したい具体的な実行スクリプト例、CI 設定、または開発用の要求（型チェック / linters / テストの実行方法）があれば教えてください。必要に応じて README を拡張します。