# KabuSys

日本株向けの自動売買/データ基盤ライブラリ（KabuSys）のコードベース README（日本語）

このリポジトリは、J-Quants 等から取得したマーケットデータを DuckDB に蓄積し、研究 → 特徴量生成 → シグナル算出 → 発注・監視へとつなぐための基盤モジュール群を含みます。戦略ロジック（feature / signal）や ETL、ニュース収集、監査スキーマなどを提供します。

- 現在のバージョン: 0.1.0（src/kabusys/__init__.py）

---

## プロジェクト概要

KabuSys は以下のレイヤーを想定した日本株自動売買システム用のライブラリ群です。

- Data Layer: J-Quants API からデータを取得し、DuckDB に保存する ETL（差分取得・品質チェック含む）。
- Feature Layer: 研究結果（raw factors）を正規化・合成して戦略用の特徴量を作成。
- Strategy Layer: 正規化済み特徴量と AI スコア等を統合して銘柄の最終スコアを算出し、BUY/SELL シグナルを生成。
- Execution / Audit: 発注・約定・ポジション・監査のスキーマを定義（発注連携のための基盤を提供）。
- News Collection: RSS からニュースを収集して記事・銘柄紐付けを行う。

設計上のポイント:
- ルックアヘッドバイアスを防ぐため、常に target_date 時点で入手可能なデータのみを使用する方針。
- DuckDB を中心に冪等性（ON CONFLICT 等）とトランザクションを重視した実装。
- 外部依存を最小限に抑え、標準ライブラリで多くを実装（ただし DuckDB, defusedxml 等を利用）。

---

## 主な機能一覧

- data.jquants_client
  - J-Quants API クライアント（レート制御、リトライ、トークン自動更新）
  - fetch / save のペア（株価 / 財務 / カレンダー）
- data.schema
  - DuckDB のスキーマ定義と初期化関数（init_schema）
- data.pipeline
  - 日次 ETL 実行（run_daily_etl）、差分更新ロジック、品質チェック統合
- data.news_collector
  - RSS 収集、テキスト前処理、raw_news / news_symbols への保存、銘柄抽出
- data.calendar_management
  - market_calendar を基にした営業日関連ユーティリティ（is_trading_day, next_trading_day 等）
- data.stats
  - zscore_normalize 等、戦略・研究で共有する統計ユーティリティ
- research.factor_research / feature_exploration
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman）算出、ファクター統計サマリ
- strategy.feature_engineering
  - 複数ファクターを統合して features テーブルへ保存（build_features）
- strategy.signal_generator
  - features と ai_scores を組み合わせて final_score を算出し signals を生成（generate_signals）
- audit / execution テーブル定義
  - 監査ログ用スキーマ、発注・約定・ポジションなどのテーブル定義

注: execution や monitoring の具象的な外部ブローカー連携実装は別途実装が必要です（本コードベースは基盤を提供）。

---

## セットアップ手順

前提:
- Python 3.9/3.10 以降（typing の union 表記などを使用しています。環境に合わせて動作確認してください）
- Git, virtualenv 等

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. 仮想環境作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - 最低限必要なパッケージ:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使用してください）
   - もしパッケージを編集しながら使う場合:
     - pip install -e .

4. 環境変数設定 (.env)
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（src/kabusys/config.py）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時などで便利）。
   - 必須環境変数（config.Settings が参照します）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード（発注連携がある場合）
     - SLACK_BOT_TOKEN — Slack 通知を使う場合の Bot トークン
     - SLACK_CHANNEL_ID — Slack チャンネル ID
   - 任意/デフォルト:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
     - KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 env ロードを無効化するフラグ（値は任意）

   例 .env（プロジェクトルート）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx...
   KABU_API_PASSWORD=secret
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

5. データベース初期化
   - DuckDB ファイルを初期化して必要テーブルを作成:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - in-memory を試す場合: init_schema(":memory:")

---

## 使い方（主要ユースケース例）

以下は Python REPL / スクリプトでの基本的な実行例です。

1) DuckDB 接続と ETL（日次）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) 特徴量のビルド（戦略用 features を作成）
```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2024, 1, 1))
print(f"features upserted: {n}")
```

3) シグナル生成
```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import generate_signals

conn = get_connection("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2024, 1, 1), threshold=0.6)
print(f"signals written: {count}")
```

4) ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes は銘柄抽出に使う有効銘柄コードの集合（例: {"7203","6758", ...}）
result = run_news_collection(conn, sources=None, known_codes=known_codes)
print(result)  # {source_name: 新規保存件数}
```

5) J-Quants の生データ取得を直接使う（テスト用）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = save_daily_quotes(conn, records)
```

注意点:
- config.Settings は必須環境変数が未設定だと例外を投げます。自動 .env 読み込み機能があるため、.env を用意しておくと便利です。
- generate_signals / build_features は DuckDB の `features`, `ai_scores`, `positions`, `prices_daily` 等のテーブルが適切に埋まっていることが前提です。

---

## よく使う API の説明（短め）

- init_schema(db_path) -> DuckDB 接続
  - 指定パスの DuckDB を初期化し、必要なテーブルを作成して接続を返す。

- run_daily_etl(conn, target_date=None, ...)
  - 市場カレンダー、株価、財務データを差分取得して保存し、（オプションで）品質チェックを実行する。ETLResult を返す。

- build_features(conn, target_date)
  - research のファクターを取得して合成 / 正規化し、features テーブルへ UPSERT（冪等）する。

- generate_signals(conn, target_date, threshold, weights)
  - features と ai_scores を統合して final_score を計算し、BUY/SELL シグナルを signals テーブルへ書き込む（冪等）。

- run_news_collection(conn, sources=None, known_codes=None)
  - RSS を収集して raw_news に保存し、必要に応じて銘柄タグ付けを行う。

---

## ディレクトリ構成

主要なファイル・ディレクトリ（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数設定 / 自動 .env 読み込み
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント（取得・保存）
    - news_collector.py         — RSS ニュース収集 / 前処理 / DB 保存
    - schema.py                 — DuckDB スキーマ定義と初期化
    - stats.py                  — zscore_normalize 等統計ユーティリティ
    - pipeline.py               — ETL パイプライン（run_daily_etl 等）
    - features.py               — data.stats の再エクスポート
    - calendar_management.py    — マーケットカレンダー関連ユーティリティ
    - audit.py                  — 監査ログ用 DDL（signal_events, order_requests, executions）
  - research/
    - __init__.py
    - factor_research.py        — momentum/value/volatility 等のファクター計算
    - feature_exploration.py    — 将来リターン / IC / 統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py    — build_features
    - signal_generator.py       — generate_signals
  - execution/                  — 発注層（パッケージプレースホルダ）
  - monitoring/                 — 監視関連（パッケージプレースホルダ）

（上記に加え、プロジェクトルートに .env/.env.local/.gitignore 等を配置する想定）

---

## トラブルシューティング

- 環境変数未設定で ValueError が出る
  - settings.jquants_refresh_token 等の必須変数が .env/環境に設定されているか確認してください。

- DuckDB の初期化で権限エラー
  - 指定した db_path の親ディレクトリが存在するか、書き込み権限があるか確認してください。init_schema は親ディレクトリを自動作成しますが、ファイルシステム権限が必要です。

- RSS フェッチで SSL/ネットワークエラー
  - fetch_rss は SSRF 等に対する検査を厳格に行います。URL のスキーム（http/https）や最終リダイレクト先のホストがプライベートネットワークではないことを確認してください。

- J-Quants API に対するレートエラー（429）
  - jquants_client は再試行と指数バックオフを実装していますが、短時間に大量のリクエストをしない運用を心がけてください。

---

## 今後の拡張 / 注意点

- execution 層のブローカー接続（発注送信、状態管理）や Slack 通知の具体実装はプロジェクト外または別モジュールで実装する想定です。
- ai_scores の生成（外部 AI モデル）やポートフォリオ最適化ロジックは本リポジトリ外で行い、ai_scores テーブルや portfolio_targets へ書き込むことで連携します。
- テスト・CI、依存関係の明示的な管理（requirements.txt / pyproject.toml）を整備することを推奨します。

---

必要であれば、README に含める .env.example のテンプレートや、サンプルスクリプト（例: daily_job.py）を作成します。どのような追加情報が必要か教えてください。