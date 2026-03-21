# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）のリポジトリ内ドキュメントです。本 README はパッケージ内の主要機能・セットアップ手順・使い方・ディレクトリ構成を日本語でまとめています。

---

## プロジェクト概要

KabuSys は日本株のデータ収集（J-Quants API）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどの機能を備えた自動売買基盤向けライブラリ群です。設計は以下を重視しています。

- データパイプラインの冪等性（ON CONFLICT / トランザクションによる原子性）
- ルックアヘッドバイアスの排除（target_date 時点のみ参照）
- API レート制御・リトライ（J-Quants 用の RateLimiter / 再試行ロジック）
- DB スキーマ管理（DuckDB）
- 安全対策（RSS の SSRF/サイズ検査、XML パースの安全化 等）
- research（ファクター計算）層と strategy（特徴量・シグナル生成）層の明確な分離

現在のパッケージバージョン: 0.1.0

---

## 主な機能一覧

- データ取得（J-Quants API）
  - 株価日足（OHLCV）のページネーション対応取得
  - 財務データ（四半期 BS/PL）
  - JPX マーケットカレンダー
  - レート制限 / リトライ / トークン自動リフレッシュ
- DuckDB スキーマ定義と初期化（init_schema）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
  - 日次 ETL 実行エントリポイント（run_daily_etl）
- ファクター計算（research）
  - momentum / volatility / value 等の定量ファクター
  - forward returns / IC / 統計サマリー等の解析ユーティリティ
- 特徴量生成（strategy.feature_engineering.build_features）
  - 生ファクターの正規化・合成・features テーブルへの UPSERT
- シグナル生成（strategy.signal_generator.generate_signals）
  - features と ai_scores を統合して final_score を計算し BUY/SELL を作成
  - Bear レジーム抑制、エグジット条件（ストップロス等）
- ニュース収集（data.news_collector）
  - RSS フィード取得、前処理、raw_news 保存、銘柄紐付け
  - SSRF 対策・gzip/サイズ制限・XML の安全パース
- マーケットカレンダー管理（data.calendar_management）
  - 営業日判定 / 翌営業日・前営業日の取得 / 夜間更新ジョブ
- 監査ログ（data.audit）
  - シグナル→発注→約定のトレーサビリティ用テーブル定義

---

## 必要条件 / 依存

- Python 3.10 以上（型ヒントの `X | None` 等の構文を使用）
- 必要な Python パッケージ（最低限）:
  - duckdb
  - defusedxml
- 追加で用途に応じて:
  - （HTTP周り・テストなどで）標準ライブラリのみで実装されているため他依存は最小限

※ 実際のプロジェクトでは requirements.txt / poetry 等で依存管理を行ってください。

---

## セットアップ手順（簡易）

1. リポジトリをクローンしてワークスペースを用意
   - git clone ...

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Unix)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール
   - pip install duckdb defusedxml

   （プロジェクトで requirements.txt や pyproject.toml がある場合はそれに従ってください）

4. 環境変数を設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（デフォルトで自動ロード有効）。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

  .env に設定が必要な主なキー（.env.example を参照してください）:
  - JQUANTS_REFRESH_TOKEN=...
  - KABU_API_PASSWORD=...
  - KABU_API_BASE_URL=http://localhost:18080/kabusapi  (省略可、デフォルト)
  - SLACK_BOT_TOKEN=...
  - SLACK_CHANNEL_ID=...
  - DUCKDB_PATH=data/kabusys.duckdb  (デフォルト)
  - SQLITE_PATH=data/monitoring.db    (デフォルト)
  - KABUSYS_ENV=development|paper_trading|live  (省略時 development)
  - LOG_LEVEL=INFO|DEBUG|...  (省略時 INFO)

.env の読み込みルール:
- OS 環境変数 > .env.local > .env の優先度
- `export KEY=value` 形式やシングル/ダブルクォート、コメントの扱いに対応するパーサが実装されています。

---

## 初期化（DuckDB スキーマ作成）

Python REPL やスクリプトから DuckDB スキーマを初期化します。

例:

from kabusys.data.schema import init_schema
from kabusys.config import settings

db_path = settings.duckdb_path  # デフォルト "data/kabusys.duckdb"
conn = init_schema(db_path)
# conn は duckdb.DuckDBPyConnection を返す

注意:
- init_schema は親ディレクトリ（data/ 等）が存在しない場合は自動作成します。
- ":memory:" を渡すとインメモリ DB を利用できます（テスト用途等）。

---

## 使い方（主要ワークフロー例）

以下は代表的なワークフローの呼び出し例です。いずれも Python スクリプト内で実行します。

1) 日次 ETL を実行（市場カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック）

from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # target_date を省略すると今日
print(result.to_dict())

2) 特徴量の構築（features テーブルに保存）

from datetime import date
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
n = build_features(conn, target_date=date(2026, 3, 20))
print(f"features にアップサートした銘柄数: {n}")

3) シグナル生成（signals テーブルに保存）

from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
count = generate_signals(conn, target_date=date(2026, 3, 20))
print(f"生成したシグナル数: {count}")

4) ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）

from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
# known_codes は銘柄コードの集合。抽出ロジックが有効なコードだけを返す。
known_codes = {"7203","6758",...}
results = run_news_collection(conn, known_codes=known_codes)
print(results)

5) マーケットカレンダー更新（夜間バッチ）

from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
saved = calendar_update_job(conn)
print(f"カレンダー保存レコード数: {saved}")

---

## 設定とログ

- 設定値は `kabusys.config.Settings` 経由で取得します（環境変数ベース）。
  - 例: from kabusys.config import settings; settings.jquants_refresh_token
- 環境 (`KABUSYS_ENV`) により動作モードを区別できます（development / paper_trading / live）。
- ログレベルは `LOG_LEVEL` 環境変数で指定します（DEBUG/INFO/...）。
- 一部モジュール（J-Quantsクライアント、RSSフェッチ等）は追加の警告・安全対策ログを出力します。

---

## 推奨ワークフロー（運用時の例）

1. DuckDB のスキーマ初期化（init_schema）
2. 夜間バッチ:
   - calendar_update_job（カレンダー更新）
   - run_daily_etl（データ収集）
   - build_features（特徴量構築）
   - generate_signals（シグナル作成）
   - signal_queue 生成 → execution 層で発注
3. ニュース収集ジョブは定期的に実行して raw_news を更新
4. 監査ログ（data.audit）の整合性を保ちながら発注/約定フローを永続化

---

## ディレクトリ構成

パッケージは `src/kabusys` 配下に格納されています。主要ファイル/モジュールは以下の通りです（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py  (環境変数・設定管理)
  - data/
    - __init__.py
    - jquants_client.py      (J-Quants API クライアント)
    - schema.py              (DuckDB スキーマ + init_schema/get_connection)
    - pipeline.py            (ETL パイプライン: run_daily_etl 等)
    - news_collector.py      (RSS ニュースの取得・保存)
    - calendar_management.py (マーケットカレンダー管理)
    - audit.py               (監査ログテーブル定義)
    - stats.py               (zscore_normalize 等統計ユーティリティ)
    - features.py            (data.stats の再エクスポート)
  - research/
    - __init__.py
    - factor_research.py     (momentum/volatility/value の計算)
    - feature_exploration.py (forward returns / IC / summary)
  - strategy/
    - __init__.py
    - feature_engineering.py (build_features)
    - signal_generator.py    (generate_signals)
  - execution/               (発注/実行関連のスケルトン)
  - monitoring/              (監視・メトリクス関連のスケルトン)

各モジュールの詳細な設計はソース中の docstring に記載されています。特にデータスキーマや戦略仕様（StrategyModel.md 等）が参照ドキュメントとして想定されています。

---

## テスト / 開発メモ

- 多くの関数は外部依存（HTTP、DB）を注入可能に実装してあり、ユニットテストでモックしやすく設計されています（例: id_token 注入、_urlopen の差し替えなど）。
- データ取得は差分更新（最終取得日ベース）やバックフィルをサポートしているため、初回ロードと日次運用で挙動が異なる点に注意してください。
- DuckDB への接続は `init_schema`（初回）と `get_connection`（既存DB接続）を使い分けてください。

---

## 貢献・ライセンス

この README はパッケージ内の実装に基づく概要説明です。実運用・公開にあたっては追加のドキュメント（StrategyModel.md, DataPlatform.md, security.md 等）やテスト・CIを整備してください。

---

問題・不明点があれば、どの機能（ETL / feature / signal / news 等）について知りたいかを教えてください。具体的なコード例や追加のセットアップ手順（Docker, systemd, cron ジョブ例など）も提供できます。