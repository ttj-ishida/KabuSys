# KabuSys

日本株向け自動売買プラットフォームのライブラリ群（KabuSys）です。  
データ取得（J-Quants）、DuckDB ベースのデータスキーマ、ETL パイプライン、ニュース収集、ファクター（研究）モジュール、監査ログ等を含むユーティリティ群を提供します。

> 注意: 本リポジトリは発注/約定を直接行う実装も想定しています。実運用（特に `KABUSYS_ENV=live`）で使用する場合は十分なテストと安全対策を行ってください。

---

## 主な特徴

- データ取得
  - J-Quants API クライアント（ページネーション・リトライ・トークン自動リフレッシュ・レートリミット対応）
  - 株価日足 / 財務データ / JPX マーケットカレンダーの取得・DuckDB への冪等保存

- ETL / データ基盤
  - DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - 日次差分 ETL（バックフィル対応・品質チェック含む）
  - 市場カレンダー管理（営業日判定、next/prev トレーディングデイ）

- ニュース収集
  - RSS フィード取得（SSRF対策、受信サイズ制限、XML デファンス）
  - 記事の正規化・ID (SHA-256) 生成・DuckDB への冪等保存
  - 銘柄コード抽出（テキストから 4 桁コード抽出）

- 研究（Research）ユーティリティ
  - モメンタム / ボラティリティ / バリュー 等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
  - Zスコア正規化ユーティリティ

- 監査（Audit）
  - シグナル→発注→約定のトレーサビリティ用テーブル定義と初期化ユーティリティ

- データ品質チェック
  - 欠損、重複、スパイク、日付不整合を検出するチェック群

---

## 必要な環境変数

設定は `.env` / `.env.local` または環境変数から読み込まれます。自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われ、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。

必須（最低限）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API 用パスワード（発注連携がある場合）
- SLACK_BOT_TOKEN — Slack 通知に使う Bot トークン
- SLACK_CHANNEL_ID — Slack チャネル ID

任意:
- KABUSYS_ENV — 動作モード（`development`（デフォルト） / `paper_trading` / `live`）
- LOG_LEVEL — ログレベル（`DEBUG|INFO|WARNING|ERROR|CRITICAL`）
- DUCKDB_PATH — デフォルト DB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト `data/monitoring.db`）

設定取得は `from kabusys.config import settings` で行えます（プロパティ経由で型・妥当性チェックあり）。

---

## セットアップ

（ここではライブラリを開発環境で使う想定の一般的手順を示します）

1. Python（3.10+ を推奨）環境を用意

2. 必要パッケージをインストール（例）
   - duckdb
   - defusedxml

   例:
   ```bash
   python -m pip install duckdb defusedxml
   ```

   ※ プロジェクトの requirements ファイルがあればそれを使用してください。

3. 環境変数を用意（`.env` または `.env.local`）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=yyyyy
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   ```

4. DuckDB スキーマ初期化
   - Python REPL やスクリプトで:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

   - 監査ログ用 DB を別途初期化する場合:
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（代表的な操作例）

以下はライブラリの主要 API を使う最小例です。

- 日次 ETL 実行（株価・財務・カレンダーの差分取得 + 品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- J-Quants から日足を取得して保存（手動）
```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import init_schema

conn = init_schema(":memory:")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
```

- RSS ニュース取得と保存（既知銘柄セットを使った紐付け）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)
```

- 研究系ファクター計算（例: モメンタム）
```python
from datetime import date
from kabusys.research import calc_momentum
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2024,2,28))
# records は各銘柄ごとの辞書のリスト
```

- 将来リターン・IC 計算（例）
```python
from kabusys.research import calc_forward_returns, calc_ic

fwd = calc_forward_returns(conn, target_date=date(2024,2,28), horizons=[1,5,21])
# factor_records は別途 calc_momentum 等で得たファクターリスト
ic = calc_ic(factor_records, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

- Zスコア正規化
```python
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(records, columns=["mom_1m", "ma200_dev"])
```

- マーケットカレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
```

- 監査スキーマ追加（既存接続に）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

---

## ディレクトリ構成（概要）

プロジェクトの重要なモジュール構成は以下のとおりです（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（fetch/save）
    - news_collector.py            — RSS ニュース収集・保存
    - schema.py                    — DuckDB スキーマ定義・初期化
    - stats.py                     — 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - features.py                  — 特徴量ユーティリティ公開（再エクスポート）
    - calendar_management.py       — カレンダー管理・バッチジョブ
    - audit.py                     — 監査ログスキーマ初期化
    - quality.py                   — データ品質チェック群
    - etl.py                       — ETL の公開インターフェース（再エクスポート）
  - research/
    - __init__.py                  — 研究系 API 再エクスポート
    - feature_exploration.py       — 将来リターン計算 / IC / 統計サマリー
    - factor_research.py           — momentum/value/volatility 等の計算
  - strategy/                       — 戦略モデル関連（空の __init__ を含む）
  - execution/                      — 発注 / 実行関連（空の __init__ を含む）
  - monitoring/                     — 監視 / メトリクス（空の __init__ を含む）

---

## 運用上の注意点 / ベストプラクティス

- センシティブなトークン（J-Quants、kabu、Slack など）は直接ソース管理に入れないでください。`.env.local` を `.gitignore` に含めることを推奨します。
- 自動ロードされる .env の優先順位: OS 環境 > .env.local > .env。テスト等で自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants クライアントはレート制限（120 req/min）とリトライ/バックオフを実装していますが、過度の並列化は API 制限に抵触する可能性があります。バッチ実行時は注意してください。
- ETL は品質チェックを行いますが、チェック結果をもとに停止するかどうかは呼び出し側の判断に委ねられます。重要な品質エラーはログと結果に表れます。
- 実取引（live）モードでは特に冪等性・監査ログ（order_request_id 等）・エラーハンドリングを厳格に運用してください。

---

## 貢献・拡張

- 新しい RSS ソースの追加、既存関数の拡張、研究用ファクターの追加などはモジュール単位で拡張可能です。
- DuckDB スキーマの変更は互換性に注意して行ってください（ON DELETE 制約やバージョン差分に依存する実装注記あり）。
- テストを追加する場合、`KABUSYS_DISABLE_AUTO_ENV_LOAD` を設定して外部環境の影響を避けると良いです。

---

README は以上です。その他、サンプルスクリプトや運用手順（cron / Airflow でのスケジューリング、Slack 通知の組み込み等）を追加でご希望であれば、その用途に合わせた具体例を作成します。