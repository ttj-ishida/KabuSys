# KabuSys

日本株向け自動売買システム（ライブラリ）です。  
データ取得（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどを含むエンドツーエンドの基盤コンポーネント群を提供します。

---

## 概要

KabuSys は以下の層で構成された自動売買プラットフォームの基礎ライブラリです。

- Data 層: J-Quants からのデータ取得、Raw / Processed / Feature レイヤーの DuckDB スキーマ管理、ETL パイプライン
- Research 層: ファクター計算、特徴量探索（IC 等）
- Strategy 層: 特徴量の正規化・合成、最終スコア計算、買い／売りシグナル生成
- Execution / Audit 層: 発注・約定・ポジション・監査ログのスキーマ（ライブラリ提供）
- News: RSS からのニュース収集と銘柄紐付け
- Config: 環境変数管理（.env 自動ロード）

設計方針として、ルックアヘッドバイアス回避や冪等性（ON CONFLICT / トランザクション）に配慮しています。また、外部依存を最小化（主要処理は標準ライブラリ + duckdb）しています。

---

## 主な機能一覧

- J-Quants API クライアント（認証、ページネーション、レート制御、リトライ、トークン自動リフレッシュ）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
- DuckDB スキーマ定義と初期化（init_schema）
- ETL パイプライン（差分取得 / backfill / 品質チェックを含む run_daily_etl）
- 特徴量計算（research.factor_research）
  - Momentum / Volatility / Value 等
- 特徴量正規化・合成（strategy.feature_engineering.build_features）
- シグナル生成（strategy.signal_generator.generate_signals）
  - コンポーネントスコア（momentum, value, volatility, liquidity, news）を統合
  - Bear レジーム抑制、ストップロス等のエグジット判定
- ニュース収集（data.news_collector）
  - RSS 取得・前処理・ID生成（URL 正規化 + SHA256）・DB 保存・銘柄抽出
  - SSRF / XML Bomb / レスポンスサイズ制限などセキュリティ対策実装
- マーケットカレンダー管理（data.calendar_management）
  - 営業日判定・前後営業日取得・夜間カレンダー更新ジョブ
- 統計ユーティリティ（data.stats: zscore_normalize、research 側で利用）
- 自動 .env ロード機能（プロジェクトルートの .env / .env.local を自動で読み込み）

---

## セットアップ手順

前提:
- Python 3.10 以上（| 型記法や型ヒントで 3.10 相当が使われています）
- DuckDB が必要（Python パッケージとして duckdb をインストール）

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存関係のインストール
   - pip install -r requirements.txt
     - もし requirements.txt が無ければ最低限:
       - pip install duckdb defusedxml

   - 開発用: pip install -e . （パッケージ化されている場合）

4. 環境変数設定
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を作成します。
   - 主要な環境変数（README に記載の通り）を設定してください。例:

     .env の例:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

   - 自動 .env 読み込みはデフォルトで有効です。テスト等で無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. データベースの初期化
   - Python から DuckDB スキーマを初期化します（次節の使い方参照）。

---

## 使い方（簡単なコード例）

以下は代表的な操作の使用例です。実行前に環境変数と依存パッケージが整っていることを確認してください。

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

# デフォルトパス: data/kabusys.duckdb（settings.duckdb_path を使用する場合は settings.duckdb_path を参照）
conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL 実行（J-Quants から差分取得して保存）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量ビルド（duckdb 接続と基準日を渡す）
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2024, 1, 31))
print(f"features upserted: {count}")
```

- シグナル生成（features + ai_scores + positions を参照）
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
total_signals = generate_signals(conn, target_date=date(2024, 1, 31))
print(f"signals written: {total_signals}")
```

- ニュース収集ジョブ（RSS 取得・DB 保存・銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes は銘柄コードの集合（例: set(["7203", "6758", ...])）
res = run_news_collection(conn, known_codes=None)  # known_codes を与えれば銘柄抽出を実行
print(res)
```

- マーケットカレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

- 設定取得（環境変数）
```python
from kabusys.config import settings

print(settings.jquants_refresh_token)
print(settings.duckdb_path)
print(settings.env)
```

---

## 環境変数（主要）

config.Settings で参照される主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視などで使う SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると自動 .env ロードを無効化

notes:
- 必須 env が未設定の場合、Settings のプロパティアクセスで ValueError が発生します。
- プロジェクトルートの `.env` と `.env.local` が自動で読み込まれます（OS 環境変数が優先）。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD` を設定してください。

---

## ディレクトリ構成（抜粋）

src/kabusys の主なモジュール構成:

- kabusys/
  - __init__.py
  - config.py                       -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py              -- J-Quants API クライアント（fetch/save）
    - news_collector.py              -- RSS ニュース収集・保存・銘柄抽出
    - schema.py                      -- DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py                    -- ETL パイプライン（run_daily_etl 等）
    - stats.py                       -- 統計ユーティリティ（zscore_normalize）
    - features.py                    -- data.stats の再エクスポート
    - calendar_management.py         -- マーケットカレンダー管理
    - audit.py                       -- 監査ログ関連 DDL（未完の部分あり）
    - pipeline.py                    -- ETL 実行ロジック
  - research/
    - __init__.py
    - factor_research.py             -- Momentum / Volatility / Value の計算
    - feature_exploration.py         -- forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py         -- features テーブル構築
    - signal_generator.py            -- final_score 計算と signals への書き込み
  - execution/                        -- 発注関連（空 __init__ が存在）
  - monitoring/                       -- 監視用コード（存在する場合）
  - その他: 実運用向けのジョブやユーティリティを含むモジュール群

（README 用に抜粋しています。各モジュール内に詳細な docstring と設計メモが含まれています）

---

## 運用上の注意 / ベストプラクティス

- ルックアヘッドバイアス防止:
  - 各種計算は target_date 時点のデータのみ使用するよう設計されています。ETL → features → signals の順序で実行してください。
- 冪等性:
  - DB 保存関数は ON CONFLICT / トランザクションで冪等を保証する設計です。ファイルを二重で投入しても問題になりにくいですが、ETL ログは確認してください。
- 本番環境:
  - KABUSYS_ENV を `live` に設定すると is_live フラグが有効になります。発注や実行ロジックを組み合わせる際は更なる安全チェックを追加してください（ここに含まれる戦略モジュールは発注の呼び出し自体は行いません）。
- セキュリティ:
  - news_collector は SSRF / XML injection / gzip bomb / レスポンスサイズ過大などの防御を含みますが、運用環境のプロキシやネットワーク設定にも注意してください。
- ロギング:
  - LOG_LEVEL を適切に設定し、重要なジョブ（ETL / signal generation / execution）では監査ログを残すことを推奨します。

---

## 開発・テスト

- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml がある場所）を基準に行われます。テスト時に環境分離が必要なら `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使用してください。
- 関数設計は依存注入しやすくなっており、duckdb 接続や id_token をテスト用のモック値で差し替えられます。
- news_collector のネットワーク呼び出しは内部でラッパーしているため、ユニットテストでは _urlopen や fetch_rss をモック可能です。

---

## 参考（よく使う関数一覧）

- schema.init_schema(db_path)
- schema.get_connection(db_path)
- data.jquants_client.get_id_token()
- data.jquants_client.fetch_daily_quotes(...) / save_daily_quotes(...)
- data.pipeline.run_daily_etl(conn, target_date=...)
- research.calc_momentum(conn, target_date)
- strategy.build_features(conn, target_date)
- strategy.generate_signals(conn, target_date)

---

もし README に追加したい運用手順（CI / Cron ジョブ設定、Slack 通知の実装例、kabu API 統合の手順等）があれば、用途に合わせたサンプルやテンプレートを追記します。必要な内容を教えてください。