# KabuSys

日本株向け自動売買システムのライブラリ群。データ収集（J-Quants）、データ整形（DuckDB スキーマ）、特徴量作成、シグナル生成、ニュース収集、マーケットカレンダー管理など、戦略開発〜運用に必要なモジュールを含みます。

主な設計方針：
- ルックアヘッドバイアス回避（計算は target_date 時点のデータのみを使用）
- DuckDB を中心とした冪等的なデータ保存（ON CONFLICT 等を利用）
- 外部依存を最小化（標準ライブラリ中心。ただし duckdb / defusedxml 等は必要）
- テストしやすい設計（関数に接続やトークンを注入可能）

---

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（差分取得、ページネーション、リトライ、トークン自動更新）
  - raw_prices / raw_financials / market_calendar などの保存関数（冪等）
- ETL パイプライン
  - 日次 ETL（calendar / prices / financials の差分取得、品質チェック）
- DuckDB スキーマ管理
  - init_schema() による自動テーブル作成（Raw / Processed / Feature / Execution 層）
- 特徴量計算（research / strategy）
  - momentum / volatility / value の計算（prices_daily / raw_financials を参照）
  - クロスセクション Z スコア正規化
- 戦略関連
  - build_features: 特徴量を生成して features テーブルへ書き込み
  - generate_signals: features と ai_scores を統合して BUY/SELL シグナルを生成し signals テーブルへ書き込み
- ニュース収集
  - RSS フィード取得・前処理（URL 正規化、SSRF対策、XML 安全パース）
  - raw_news / news_symbols への冪等保存
- カレンダー管理
  - 営業日判定 / next/prev_trading_day / カレンダーの差分更新ジョブ
- 監査ログ（audit）
  - signal_events / order_requests / executions などの監査テーブル定義（トレーサビリティ）

---

## セットアップ手順

1. 仮想環境（推奨）を作成して有効化
   - python >= 3.10 を想定

   example:
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. パッケージ依存をインストール
   - 必要な主要パッケージ（最低限）:
     - duckdb
     - defusedxml
   - セットアップ例（プロジェクトに requirements.txt があればそちらを使用）:
   ```
   pip install duckdb defusedxml
   ```

   ※ このコードベースは標準ライブラリ中心で実装されていますが、実行環境によっては追加ライブラリが必要になることがあります。

3. ソースをインストール（編集して使う場合は develop モード）
   ```
   pip install -e .
   ```

4. 環境変数の設定
   - .env もしくは環境変数で設定します（config.Settings が自動でプロジェクトルートの .env/.env.local を読み込みます）。
   - 自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   例 (.env):
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # kabuステーション API
   KABU_API_PASSWORD=your_kabu_api_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # Slack 通知
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

   # DB パス
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 実行環境 / ログレベル
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡易ガイド）

以下は Python スクリプト内から主要機能を呼び出す最小例です。DuckDB 接続は kabusys.data.schema を使って初期化するのが推奨です。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

# ファイルDB を指定（":memory:" でメモリDB）
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL の実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# conn は init_schema の返り値
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量ビルド（strategy.feature_engineering.build_features）
```python
from datetime import date
from kabusys.strategy import build_features

count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

4) シグナル生成（strategy.signal_generator.generate_signals）
```python
from datetime import date
from kabusys.strategy import generate_signals

n_signals = generate_signals(conn, target_date=date.today())
print(f"signals written: {n_signals}")
```

5) ニュース収集（RSS）と保存
```python
from kabusys.data.news_collector import run_news_collection
# known_codes は銘柄コードのセット（news -> code 抽出に使用）
res = run_news_collection(conn, known_codes={"7203","6758"})
print(res)
```

6) カレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

7) J-Quants からデータを個別に取得して保存する例
```python
from kabusys.data import jquants_client as jq

# fetch -> save の流れ
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print(saved)
```

注意点:
- 実運用ではトークン管理・レート制御・ログ設定・例外ハンドリングが重要です。本ライブラリは再試行やレート制御を内蔵していますが、運用スクリプト側でもリトライや監視・通知を設けてください。
- generate_signals は features / ai_scores / positions テーブルを参照します。AI スコア等が未存在でも中立値で補完するロジックを持っています。

---

## 設定・環境変数一覧

主要な必須／推奨環境変数：

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション等の発注 API パスワード
- KABU_API_BASE_URL (任意) — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — environment（development, paper_trading, live）。デフォルト: development
- LOG_LEVEL (任意) — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）。デフォルト: INFO

自動 .env 読み込み:
- パッケージはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）にある `.env` / `.env.local` を自動的に読み込みます。テスト時や明示的に無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。

---

## ディレクトリ構成

主なファイル/モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py                — J-Quants API クライアント（取得・保存関数）
    - news_collector.py                — RSS 収集・保存
    - schema.py                        — DuckDB スキーマ定義 / init_schema
    - stats.py                         — 統計ユーティリティ（zscore_normalize）
    - pipeline.py                      — ETL パイプライン（run_daily_etl など）
    - calendar_management.py           — カレンダー管理（営業日判定・更新ジョブ）
    - audit.py                         — 監査ログ用 DDL
    - features.py                       — features 再エクスポート
  - research/
    - __init__.py
    - factor_research.py               — momentum/volatility/value の計算
    - feature_exploration.py           — forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py           — build_features
    - signal_generator.py              — generate_signals
  - execution/                         — 発注 / execution 層（未展開ファイルあり）
  - monitoring/                        — 監視関連（DB/ログ監視等。未列挙）
- pyproject.toml / setup.cfg / .gitignore 等（プロジェクトルート）

（上記は主要モジュールの抜粋です。詳細はソースツリーを参照してください）

---

## 開発・運用の注意事項

- DuckDB のバージョンや SQL 実装差で互換性が変わることがあります。運用前に init_schema() を実行してエラーが出ないことを確認してください。
- J-Quants のレート制限は 120 req/min を想定しています。jquants_client モジュールは内部でスロットリングと指数バックオフを実装していますが、大量取得スクリプトを並列で動かす場合は注意してください。
- ニュース収集は外部 RSS を扱うため SSRF / XML 脆弱性対策を実装していますが、追加の監査やタイムアウト設定（timeout）・ソース管理を行ってください。
- 本リポジトリ内の仕様コメント（StrategyModel.md / DataPlatform.md 等）を参照するとアルゴリズムやパラメータの背景が分かります。実運用ではモデルパラメータ（重み、閾値など）を慎重に検証してください。
- 本ライブラリは発注 API への直接送信は行わない設計（execution 層に依存しない）。実際の発注処理を行う場合は execution 層と監査（audit）を組み合わせた実装を追加してください。

---

必要であれば、README に追加する以下の項目も作成できます：
- 詳細な API リファレンス（各関数の引数/返り値）
- テスト実行方法 / CI 設定
- デプロイ（cron / Airflow など）例
- 運用チェックリスト（起動時・日次ジョブの監視、アラート例）

どの情報を追記希望か教えてください。