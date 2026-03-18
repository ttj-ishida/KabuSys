# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）のリポジトリ内 README。  
このパッケージはデータ収集（J-Quants / RSS）、データ品質チェック、特徴量生成、研究用ユーティリティ、監査ログ・ETL ワークフローなどを提供します。

---

## プロジェクト概要

KabuSys は、主に以下を目的としたモジュール群を備えた日本株自動売買プラットフォームの基礎ライブラリです。

- J-Quants API からの株価・財務・カレンダー取得（レート制御・リトライ・トークン自動更新）
- RSS ニュース収集と記事 → 銘柄紐付け（SSRF 対策、トラッキング除去、冪等保存）
- DuckDB を用いたスキーマ定義・初期化と ETL パイプライン
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- 研究（Research）用のファクター計算・将来リターン・IC 計算・統計サマリ
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）用スキーマ

パッケージ名: kabusys（バージョン 0.1.0）

---

## 主な機能一覧

- 環境設定/自動 .env ロード
  - `.env` / `.env.local` をプロジェクトルートから自動読み込み（環境変数からの取得を優先）
  - 自動ロードを無効にするフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- J-Quants クライアント（data.jquants_client）
  - レート制御（120 req/min）
  - リトライ（指数バックオフ、401 時の自動トークンリフレッシュ）
  - 日足、財務、マーケットカレンダー取得 + DuckDB 保存用ユーティリティ
- ニュース収集（data.news_collector）
  - RSS フィード取得、前処理、記事ID（正規化URL の SHA-256）による冪等保存
  - SSRF / gzip / XML Bomb 対策
  - 銘柄コード抽出と news_symbols への紐付け
- DuckDB スキーマ管理（data.schema / data.audit）
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義と初期化
- ETL パイプライン（data.pipeline）
  - 差分更新、バックフィル、品質チェック、日次 ETL の実行
- データ品質チェック（data.quality）
  - 欠損、重複、スパイク、日付不整合の検出
- 研究用ユーティリティ（research）
  - calc_momentum, calc_volatility, calc_value（ファクター計算）
  - calc_forward_returns, calc_ic, factor_summary, rank（特徴量解析）
  - zscore_normalize（data.stats 経由で提供）

---

## セットアップ手順（ローカル開発向け）

1. Python 環境を用意（推奨: 3.9+）
2. 仮想環境作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール  
   ※ このリポジトリは requirements.txt を含まないため、主に必要な外部依存は以下です。
   - duckdb
   - defusedxml
   例:
   ```
   pip install duckdb defusedxml
   ```
   （プロジェクトでさらに Slack 連携等を使う場合は別途 slack-sdk 等を追加してください）
4. プロジェクトのルートに `.env`（および必要なら `.env.local`）を作成
   - 自動で読み込まれます（詳しくは下記「環境変数」参照）。

---

## 必要な環境変数（例）

以下は本パッケージで参照される主な環境変数です。プロジェクトに合わせて `.env` を作成してください。

- J-Quants
  - JQUANTS_REFRESH_TOKEN (必須)
- kabuステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (任意、デフォルト `http://localhost:18080/kabusapi`)
- Slack（通知等）
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- DB パス等（任意）
  - DUCKDB_PATH (デフォルト `data/kabusys.duckdb`)
  - SQLITE_PATH (デフォルト `data/monitoring.db`)
- 実行環境 / ログ
  - KABUSYS_ENV (`development` / `paper_trading` / `live`, デフォルト `development`)
  - LOG_LEVEL (`DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`, デフォルト `INFO`)
- 自動 .env ロード無効化（テスト等）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

簡単な `.env` の例:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要な操作例）

下記は Python REPL / スクリプトからの基本的な利用例です。

1) DuckDB スキーマ初期化
```
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ":memory:" でインメモリ可
```

2) 日次 ETL 実行（市場カレンダー・株価・財務・品質チェック）
```
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # 引数で target_date 等を指定可能
print(result.to_dict())
```

3) ニュース収集ジョブ実行
```
from kabusys.data.news_collector import run_news_collection
# known_codes は既知の銘柄コードセット (例: set(["7203","6758"]))
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: saved_count, ...}
```

4) 研究用ファクター計算と IC 計算
```
from datetime import date
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic

d = date(2025, 1, 15)
momentum_records = calc_momentum(conn, d)
forward_records = calc_forward_returns(conn, d, horizons=[1,5,21])
ic = calc_ic(momentum_records, forward_records, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

5) Z-score 正規化（クロスセクション）
```
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(momentum_records, ["mom_1m", "mom_3m"])
```

6) J-Quants から生データを直接取得して保存（例）
```
from kabusys.data import jquants_client as jq
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
```

7) 設定値（環境変数）の取得
```
from kabusys.config import settings
print(settings.duckdb_path)          # Path オブジェクト
print(settings.is_live)              # 実行環境判断
```

注意:
- 各モジュールは DuckDB 接続を受け取る設計です。実際の運用では接続の扱いやトランザクション管理に注意してください。
- デフォルトで .env / .env.local をプロジェクトルート（.git または pyproject.toml がある親ディレクトリ）から自動読み込みします。自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成

この README は現状のコードベース（src/kabusys 配下）に基づきます。代表的なファイルを簡単に列挙します。

- src/kabusys/
  - __init__.py
  - config.py                       -- 環境変数/設定管理（.env 自動ロード含む）
  - data/
    - __init__.py
    - jquants_client.py             -- J-Quants API クライアント + 保存ユーティリティ
    - news_collector.py             -- RSS 取得・前処理・DB 保存・銘柄抽出
    - schema.py                     -- DuckDB スキーマ定義 & init_schema / get_connection
    - stats.py                      -- zscore_normalize 等の統計ユーティリティ
    - pipeline.py                   -- ETL パイプライン（run_daily_etl 等）
    - features.py                   -- features の公開インターフェース
    - calendar_management.py        -- market_calendar 管理・営業日判定・カレンダー更新ジョブ
    - audit.py                      -- 監査ログ（signal/events/orders/executions）定義 & 初期化
    - etl.py                        -- ETL 用型の公開（ETLResult）
    - quality.py                    -- データ品質チェック
  - research/
    - __init__.py
    - factor_research.py            -- ファクター計算（momentum/value/volatility）
    - feature_exploration.py        -- 将来リターン計算・IC・統計サマリ・rank
  - strategy/                        -- 戦略層（未実装ファイル群のエントリ）
  - execution/                       -- 発注実行層（未実装ファイル群のエントリ）
  - monitoring/                      -- モニタリング（未実装ファイル群のエントリ）

各ファイルは README 内「機能一覧」で紹介した責務に沿って設計されています。

---

## 開発上の注意点 / 仕様メモ

- DuckDB をメインの時系列データストアとして使用。init_schema() は冪等にテーブルを作成します。
- J-Quants API はレート制御を厳守するため内部でスロットリングしています。大量取得時は時間がかかる点に注意してください。
- RSS の取得部はセキュリティ対策（SSRF、XML Bomb、gzip サイズ制限）を実装済みです。
- 監査ログは UTC タイムゾーンでの運用を前提としています（init_audit_schema は接続の TimeZone を UTC に固定します）。
- settings.KABUSYS_ENV は "development", "paper_trading", "live" のいずれかで厳密チェックされます。
- 大量データを扱うため、ETL は差分更新・チャンク処理を行い冪等性を保つ実装になっています。

---

## サポート / 拡張ポイント

- Slack 通知や kabuステーション連携、戦略実行部分は本体の枠組みとして残してあり、用途に応じて実装を追加できます。
- データ取得のバックフィルやジョブスケジューラ（cron / Airflow 等）と組み合わせて運用してください。
- DuckDB のバージョンによりサポートする SQL 機能（外部キーの挙動など）が異なるため、実運用環境ではバージョンの確認を推奨します。

---

必要であれば、README に以下を追加できます：
- 詳細な .env.example（完全な一覧）
- CI / テスト実行方法
- デプロイ / 運用手順（systemd / Docker / Airflow など）
- API 使用時のレート・エラーハンドリング動作の詳細

追加希望や、README の英語版が必要であれば教えてください。