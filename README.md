# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
J-Quants 等の外部データソースからデータを取得して DuckDB に保存し、研究（research）で算出したファクターを加工して戦略用の特徴量を作成、シグナルを生成するためのモジュール群を提供します。

---

## 概要

KabuSys は以下の責務を持つモジュール群で構成されています。

- データ取得（J-Quants API）・保存（DuckDB）
- ETL パイプライン（差分更新・バックフィル）
- 市場カレンダー管理（JPX）
- ニュース収集（RSS）と記事→銘柄紐付け
- 研究（factor 計算・特徴量探索）用ユーティリティ
- 戦略層（特徴量正規化・シグナル生成）
- 発注／実行／監査のためのスキーマ定義（Execution / Audit）

設計上のポイント：

- DuckDB を中心とした軽量なオンディスク DB（:memory: も可）
- 冪等性（ON CONFLICT / UPSERT）を重視した保存処理
- Look-ahead bias を防ぐ日付厳格性（target_date 時点のみを参照）
- API 呼び出しはレート制御・リトライ・自動トークンリフレッシュ対応
- 外部依存を最小にして、研究コードと本番ロジックを分離

---

## 機能一覧

主な機能（抜粋）：

- data/jquants_client
  - J-Quants から株価・財務・カレンダーを取得（ページネーション対応）
  - レートリミット固定間隔スロットリング、リトライ、401→トークン自動リフレッシュ
  - DuckDB へ冪等保存（save_daily_quotes / save_financial_statements / save_market_calendar）
- data/schema
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution / Audit 層）
  - init_schema(db_path) で DB を初期化
- data/pipeline
  - 日次 ETL（run_daily_etl）：カレンダー → 株価 → 財務 → 品質チェック
  - 差分更新／バックフィルロジック、取得範囲の自動算出
- data/news_collector
  - RSS からニュースを取得して raw_news に保存
  - URL 正規化、SSRF 対策、受信サイズ制限、記事ID を SHA256 で生成
  - 記事と銘柄コードの紐付け（news_symbols）
- research
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
  - zscore_normalize（クロスセクション Z スコア正規化）
- strategy
  - build_features(conn, target_date)：raw ファクターを統合・正規化して features テーブルへ保存
  - generate_signals(conn, target_date, ...)：features + ai_scores を統合して signals を生成
- config
  - 環境変数や .env ファイルから設定を読み込む Settings インスタンス（settings）

---

## 動作要件

必須（代表的なもの）：

- Python 3.9+
- duckdb
- defusedxml

※ 他にも標準ライブラリ以外のパッケージを使う可能性があるため、プロジェクトの requirements を確認してください。

---

## セットアップ手順

1. リポジトリをクローン / コピー

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトが pip パッケージ化されている場合）pip install -e .

4. 環境変数の設定
   - プロジェクトルートに `.env` を配置すると自動で読み込まれます（自動ロードはデフォルト有効）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

   主要な環境変数（必須）：
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD : kabuステーション API パスワード（execution 層で利用）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID : Slack 通知用
   - DUCKDB_PATH : デフォルト data/kabusys.duckdb
   - SQLITE_PATH : 監視用 SQLite（デフォルト data/monitoring.db）
   - KABUSYS_ENV : development / paper_trading / live（デフォルト development）
   - LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）

   例 (.env)
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DB スキーマ初期化
   下記のように DuckDB を初期化します（親ディレクトリが自動作成されます）。

   Python 例：
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)
   ```

---

## 使い方（代表的なワークフロー例）

以下はライブラリを直接 Python から呼び出す例です。

- 日次 ETL を実行（市場カレンダー・株価・財務を差分取得して保存）：

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)  # 初回は init_schema、既存DBは get_connection でも可
result = run_daily_etl(conn)  # target_date を指定しなければ today を使用
print(result.to_dict())
```

- 特徴量作成（strategy.feature_engineering）：

```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features

conn = get_connection(settings.duckdb_path)
count = build_features(conn, target_date=date(2024, 1, 31))
print(f"features upserted: {count}")
```

- シグナル生成：

```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import get_connection
from kabusys.strategy import generate_signals

conn = get_connection(settings.duckdb_path)
total = generate_signals(conn, target_date=date(2024, 1, 31))
print(f"signals written: {total}")
```

- ニュース収集ジョブ（RSS 取得 → DB 保存 → 銘柄紐付け）：

```python
from kabusys.config import settings
from kabusys.data.schema import get_connection
from kabusys.data.news_collector import run_news_collection

conn = get_connection(settings.duckdb_path)
# sources を渡さない場合は DEFAULT_RSS_SOURCES を使用
results = run_news_collection(conn, known_codes={"7203", "6758"})
print(results)  # {source_name: saved_count, ...}
```

- J-Quants から直接データを取得して保存（低レベル）：

```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
```

注意事項：
- すべての書き込み処理は基本的に冪等（ON CONFLICT DO UPDATE / DO NOTHING）を意識して実装されています。
- generate_signals / build_features は target_date 時点のデータのみを参照することでルックアヘッドを防止します。
- J-Quants API はレート制限（120 req/min）に従って呼び出されます。jquants_client は内部でスロットリングとリトライを行います。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須 for execution) — kabu API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live
- LOG_LEVEL — ログレベル（INFO 等）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動ロードを無効化

settings はコード中で次のように使えます：

```python
from kabusys.config import settings
print(settings.duckdb_path)  # Path オブジェクト
```

---

## ディレクトリ構成

主要ファイル / モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings
  - data/
    - __init__.py
    - schema.py — DuckDB スキーマ定義 & init_schema / get_connection
    - jquants_client.py — J-Quants API クライアント（fetch/save）
    - pipeline.py — ETL（run_daily_etl, run_prices_etl, ...）
    - news_collector.py — RSS 取得・保存・銘柄抽出
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - features.py — データ層の特徴量ユーティリティ（再エクスポート）
    - calendar_management.py — 市場カレンダーの判定・更新ロジック
    - audit.py — 監査ログスキーマ（signal_events / order_requests / executions）
  - research/
    - __init__.py
    - factor_research.py — calc_momentum / calc_volatility / calc_value
    - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank
  - strategy/
    - __init__.py
    - feature_engineering.py — build_features (正規化・ユニバースフィルタ)
    - signal_generator.py — generate_signals (final_score 計算、BUY/SELL 生成)
  - execution/  (placeholder / 実装ファイルはコードベースに依存)
  - monitoring/  (監視用ロジック・DB 等: 実装ファイルは別途)

---

## 追加の設計メモ（運用者向け）

- DB 初期化は一度行えば良く、その後は get_connection() で接続できます。
- ETL は差分更新を基本とするため、初回は初期ロードが必要（init により min date が定義されています）。
- ニュース収集は外部 RSS の仕様差異に強くないため、ソースごとにフェールセーフ（例外は個別にキャッチして継続）しています。
- シグナル生成は Bear レジーム判定やエグジット（ストップロス等）を含みます。weights や threshold は generate_signals の引数で調整可能です。
- config.Settings は .env を自動読み込みしますが、テスト時や一時的に無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。

---

## ライセンス / 貢献

（この README ではソースリポジトリに記載されている LICENSE を参照してください）

---

README に書かれていない詳細（各モジュールの追加設定、品質チェックモジュール、監査ログの運用など）はソースコード内の docstring を参照してください。必要であれば、README の拡張（運用ガイド、cron ジョブ例、Docker 化手順 等）を作成します。