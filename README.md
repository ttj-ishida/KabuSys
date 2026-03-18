# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（軽量版）。  
データ収集（J-Quants）、DuckDB ベースのデータスキーマ、ETL パイプライン、ニュース収集、ファクター計算（リサーチ用）、
監査ログ用スキーマなどを含むモジュール群を提供します。

主に研究/データ基盤・バッチ ETL・特徴量算出・発注フローの監査ログ基盤を提供することを目標としています。
（実際の発注 API 呼び出しや本番ブローカー連携は別モジュール／運用層で実装）

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート判定）
  - 必須設定取得のラッパー（settings オブジェクト）
- データ取得 / 保存
  - J-Quants API クライアント（レート制御、リトライ、トークン自動更新）
  - 日足（OHLCV）、財務データ、マーケットカレンダーの取得・DuckDB への保存（冪等）
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義と初期化
  - 監査ログ（signal_events, order_requests, executions）用スキーマの初期化
- ETL パイプライン
  - 日次差分 ETL（カレンダー取得 → 日足取得 → 財務取得 → 品質チェック）
  - 差分／バックフィル／品質チェック（欠損・スパイク・重複・日付不整合）機能
- ニュース収集
  - RSS フィード取得（SSRF 対策、gzip、XML の安全パース）
  - 記事正規化（URL トラッキング除去）、SHA-256 ベースの ID、DuckDB への冪等保存
  - 記事と銘柄コードの紐付け（抽出ロジック含む）
- リサーチ用ユーティリティ
  - Momentum / Volatility / Value 等のファクター計算（prices_daily, raw_financials を参照）
  - 将来リターン計算、IC（Spearman ρ）計算、ファクター統計サマリー
  - Z スコア正規化ユーティリティ
- 監査・トレーサビリティ
  - order_request_id 等の冪等キーを含む監査テーブル、UTC タイムスタンプ強制など設計済み

---

## 動作条件（推奨）

- Python 3.10+
- duckdb
- defusedxml

※ 依存パッケージはプロジェクトの配布方法により requirements.txt / pyproject.toml に含めてください。
簡単に試す場合:
pip install duckdb defusedxml

---

## 環境変数（主要）

必須（アプリで使用されるもの）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API 用パスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

任意 / デフォルトあり
- KABUSYS_ENV: 実行環境 (development｜paper_trading｜live)。デフォルト: development
- LOG_LEVEL: ログレベル (DEBUG/INFO/...)
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用DB）パス（デフォルト: data/monitoring.db）

自動 .env 読み込み制御
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化します。

自動読み込みの挙動
- プロジェクトルート（.git または pyproject.toml の存在）を起点に `.env` → `.env.local` の順で読み込みます。
- OS の環境変数が優先され、`.env.local` は上書き（override）されます。

設定値は kabusys.config.settings オブジェクトから取得できます:
from kabusys.config import settings
token = settings.jquants_refresh_token

---

## セットアップ手順（ローカルで試す）

1. リポジトリをクローン
   git clone <repository-url>
   cd <repository>

2. Python 仮想環境を作成・有効化（推奨）
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール
   pip install duckdb defusedxml

   （実運用では他に HTTP クライアントや Slack SDK、テストライブラリ等を追加してください）

4. 環境変数を設定
   - プロジェクトルートに .env を作成するか OS 環境変数を設定してください。
   - 例（.env）:
     JQUANTS_REFRESH_TOKEN=xxxx
     KABU_API_PASSWORD=xxxx
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development

5. DuckDB スキーマを初期化
   - Python REPL またはスクリプトから:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

   - 監査スキーマを追加する場合:
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn, transactional=True)

---

## 使い方（代表的な例）

以下はいくつかの典型的な操作例です。実際はこれらをラッパー CLI やワークフロースクリプトから呼び出します。

- DuckDB スキーマ初期化（例）
```
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ファイルがなければ作成
```

- 日次 ETL の実行
```
from datetime import date
from kabusys.data.schema import get_connection, init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")  # 初回のみ
res = run_daily_etl(conn, target_date=date.today())
print(res.to_dict())
```

- ニュース収集（RSS）と銘柄紐付け
```
from kabusys.data.news_collector import run_news_collection
# known_codes は有効な銘柄コード集合（例: 上場銘柄の4桁コード）
result = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
print(result)  # {source_name: saved_count}
```

- J-Quants 日足取得（低レベル）
```
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = save_daily_quotes(conn, records)
```

- ファクター計算（研究用）
```
from datetime import date
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic

# conn は DuckDB 接続（prices_daily, raw_financials が必要）
target = date(2024,1,31)
mom = calc_momentum(conn, target)
fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

- Zスコア正規化
```
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(records, columns=["mom_1m", "mom_3m"])
```

---

## 主要モジュール・ディレクトリ構成

（ソースは src/kabusys 以下を想定）

- src/kabusys/
  - __init__.py
  - config.py                        -- 環境設定／.env 自動読み込み
  - data/
    - __init__.py
    - jquants_client.py               -- J-Quants API クライアント（取得＋保存）
    - news_collector.py               -- RSS 収集・前処理・DB 保存・銘柄抽出
    - schema.py                       -- DuckDB スキーマ定義／初期化
    - pipeline.py                     -- ETL パイプライン（run_daily_etl 等）
    - features.py                      -- 特徴量ユーティリティ公開（zscore 等）
    - stats.py                        -- 統計ユーティリティ（zscore_normalize 等）
    - calendar_management.py          -- マーケットカレンダー管理（営業日判定等）
    - audit.py                        -- 監査ログスキーマ（signal/order/execution）
    - etl.py                          -- ETL の公開インターフェース
    - quality.py                      -- 品質チェックロジック
  - research/
    - __init__.py                     -- 研究用ユーティリティ公開
    - factor_research.py              -- Momentum/Volatility/Value 計算
    - feature_exploration.py          -- 将来リターン / IC / サマリー等
  - strategy/                          -- 戦略層（未実装／拡張用）
  - execution/                         -- 発注実装（未実装／拡張用）
  - monitoring/                        -- 監視用モジュール（未実装／拡張用）

---

## 開発上の注意 / 実装上の留意点

- DuckDB への INSERT は可能な限り冪等（ON CONFLICT）で実装してあり、ETL の再実行が可能です。
- J-Quants API に対してはモジュール内でレート制御・リトライ・401→トークンリフレッシュを実装しています。
- ニュース収集は SSRF 対策・gzip 上限チェック・defusedxml を用いた安全パースを行っています。
- 環境変数の自動読み込みはプロジェクトルートを基準に行います。テスト等で自動読み込みを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- KABUSYS_ENV の値は "development" / "paper_trading" / "live" のいずれかである必要があります。

---

## よくある操作例（チェックリスト）

- 初回: init_schema() → init_audit_schema()
- 毎日バッチ: run_daily_etl(conn)
- 新規 RSS 取り込み: run_news_collection(conn, known_codes=...)
- 研究実験: calc_momentum / calc_volatility / calc_value → zscore_normalize → calc_ic

---

もし README に追加したいサンプル CLI スクリプトや、CI / Docker 用の例、依存の完全リスト（requirements.txt／pyproject.toml）や .env.example を追加したい場合は、その内容（希望するコマンドや依存リスト）を教えてください。README をそれに合わせて拡張します。