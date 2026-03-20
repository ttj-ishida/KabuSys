# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム（ライブラリ）です。J-Quants API などからデータを取得して DuckDB に保存し、ファクター計算・特徴量作成・シグナル生成・発注トラッキングまでのワークフローをサポートします。研究（research）用のファクター探索やニュース収集、マーケットカレンダー管理、監査ログ機能も備えています。

バージョン: 0.1.0

---

## 主な機能

- Data 層
  - J-Quants API クライアント（取得・保存・ページネーション・再試行・レート制御）
  - DuckDB 用スキーマ定義と初期化（冪等）
  - ETL パイプライン（差分取得、バックフィル、品質チェック）
  - ニュース収集（RSS → raw_news、記事ID正規化、SSRF対策、トラッキングパラメータ除去）
  - マーケットカレンダー管理（営業日/休日/SQ/半日判定、夜間更新ジョブ）

- Research / Strategy
  - ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - 特徴量エンジニアリング（Zスコア正規化、ユニバースフィルタ）
  - シグナル生成（コンポーネントスコアの統合、BUY/SELL 判定、SELL 優先）
  - ファクター評価ユーティリティ（forward returns, IC, summary）

- Execution / Audit
  - signal / order / execution / positions 等のテーブルスキーマ（監査・トレーサビリティ設計）
  - 監査ログ構造（signal_events, order_requests, executions）

- 共通ユーティリティ
  - 環境変数読み込み (.env / .env.local の自動ロード)
  - 統計ユーティリティ（Zスコア正規化）
  - ニュース記事テキスト前処理、銘柄コード抽出

---

## 動作環境・前提

- Python 3.10+
  - （コード中で | 型や型ヒントを使用）
- 必要パッケージ（例）
  - duckdb
  - defusedxml
  - （標準ライブラリのみで動作する部分も多いですが、上記は明示的に使用）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install "duckdb" "defusedxml"
# パッケージをローカルで編集可能インストールする場合
pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境の作成・有効化、依存パッケージのインストール
   （上記参照）

3. 環境変数を用意する
   - プロジェクトルートに `.env` / `.env.local` を作成すると、自動的に読み込まれます（ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードを無効化できます）。
   - 必須の環境変数（Settings 参照）
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード（発注連携がある場合）
     - SLACK_BOT_TOKEN — Slack 通知を使う場合
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル
   - オプション
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG / INFO / ...
     - DUCKDB_PATH — DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用途の SQLite（デフォルト: data/monitoring.db）

   例（.env の簡易例）:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマの初期化
   Python REPL、スクリプト、または CI/CD タスクから次を実行して DB とテーブルを作成します:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   # conn を使って追加操作も可能
   conn.close()
   ```

---

## 使い方（主要ワークフロー例）

以下は代表的な操作のサンプルコードです。実際はスクリプトやジョブランナーで組み合わせて運用します。

- 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
conn.close()
```

- 特徴量の構築（features テーブルへ挿入）
```python
from datetime import date
import duckdb
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, target_date=date.today())
print(f"features upserted: {n}")
conn.close()
```

- シグナル生成（signals テーブルへ挿入）
```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
total = generate_signals(conn, target_date=date.today())
print(f"signals written: {total}")
conn.close()
```

- ニュース収集ジョブ（RSS 収集 → raw_news 保存 → 銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9432"}  # 有効銘柄コードのセット（例）
results = run_news_collection(conn, known_codes=known_codes)
print(results)
conn.close()
```

- カレンダーの夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
conn.close()
```

---

## 主要モジュールと API（概要）

- kabusys.config
  - settings: 環境変数ベースの設定アクセス（例: settings.jquants_refresh_token）
  - 自動的にプロジェクトルートの .env / .env.local を読み込む（必要に応じて無効化可）

- kabusys.data
  - jquants_client: J-Quants API の取得・保存（fetch_*, save_*）
  - schema: DuckDB スキーマ定義と init_schema / get_connection
  - pipeline: run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - news_collector: fetch_rss, save_raw_news, run_news_collection
  - calendar_management: is_trading_day, next_trading_day, calendar_update_job
  - stats: zscore_normalize

- kabusys.research
  - factor_research: calc_momentum, calc_volatility, calc_value
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

- kabusys.strategy
  - feature_engineering.build_features
  - signal_generator.generate_signals

- kabusys.execution / kabusys.monitoring
  - 発注・モニタリング関連の骨組み（スキーマ設計に合わせたテーブルを利用）

---

## ディレクトリ構成（主要ファイル）

パッケージは `src/kabusys` 配下にあります。主要なファイル・サブパッケージ：

- src/kabusys/
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
  - monitoring/
    - (監視関連コードや DB 連携部分)

---

## 設定・運用上の注意点

- 環境変数は .env / .env.local をプロジェクトルートに配置すると自動読み込みされます。テスト時等に自動読み込みを抑止するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB の初期化は一度実行すれば良く、init_schema は冪等（既に存在するテーブルはそのまま）です。
- J-Quants API はレート制限があるため、jquants_client 内で固定間隔スロットリングとリトライロジックが組み込まれています。
- ニュース収集では SSRF・XML攻撃・Gzip bomb 等に対する対策（スキーム検証、プライベートIP検出、受信サイズ上限、defusedxml）を行っています。
- シグナル生成は features / ai_scores / positions を参照します。ルックアヘッドバイアスを防ぐため、target_date 時点で利用可能なデータのみを用います。
- 本リポジトリは研究・運用双方のワークフローを想定していますが、実際の発注（リアルマネー運用）を行う前に十分な検証を行ってください（paper_trading 環境の活用を推奨）。

---

## 開発・貢献

- バグ修正や機能追加はプルリクエストで受け付けます。
- コードの変更時は DuckDB スキーマや ETL の互換性に注意してください（DDL 変更は既存データとの互換性を壊す場合があります）。
- テストカバレッジの追加、外部 API のモック化を歓迎します。

---

## ライセンス

リポジトリに含まれる LICENSE ファイルを参照してください（本 README はライセンスに依存しません）。

---

何か特定の操作（例: 初回ロードスクリプト、cron 用ジョブ例、CI 設定、サンプル .env.example の自動生成など）を README に追加したい場合は教えてください。必要に応じて具体的なサンプルや実行スクリプトを追記します。