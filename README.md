# KabuSys

日本株向け自動売買プラットフォームのライブラリ実装（モジュール群）
（ETL、ファクター計算、特徴量生成、シグナル生成、J-Quants / RSS データ収集、DuckDB スキーマ管理 等）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要なデータ基盤と戦略層の基礎実装を提供するパッケージです。  
主な目的は次の通りです。

- J-Quants API から株価・財務・カレンダーを取得して DuckDB に蓄積する ETL（差分更新・冪等保存）
- RSS によるニュース収集と銘柄紐付け
- 研究用のファクター計算（momentum / volatility / value 等）とクロスセクション正規化
- 戦略用特徴量（features）生成とシグナル（BUY / SELL）生成ロジック
- DuckDB スキーマの初期化・管理
- 発注・実行・監査のためのスキーマ骨格（execution / audit）

設計方針としては、ルックアヘッドバイアス回避、冪等性（ON CONFLICT）、API リトライ・レート制御、セキュリティ対策（RSS の SSRF 防止等）を重視しています。

---

## 機能一覧

主な機能（モジュール別）

- config
  - .env / 環境変数読み込み、自動ロード（プロジェクトルートを探索）
  - 必須設定値取得（settings オブジェクト）
- data
  - jquants_client: J-Quants API クライアント（リトライ・レート制限・token リフレッシュ）
  - news_collector: RSS フィード取得・前処理・記事保存・銘柄抽出
  - schema: DuckDB スキーマ定義（Raw / Processed / Feature / Execution 層）と init_schema()
  - pipeline: 日次 ETL（差分取得・保存・品質チェック）と個別ジョブ（prices/financials/calendar）
  - features / stats: Zスコア正規化等の統計ユーティリティ
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - audit: 発注 → 約定のトレーサビリティ用スキーマ（監査ログ）
- research
  - factor_research: momentum / volatility / value の計算（prices_daily / raw_financials を参照）
  - feature_exploration: 将来リターン計算・IC（Spearman）・統計サマリー
- strategy
  - feature_engineering.build_features: research の raw ファクターをマージ・フィルタ・正規化して features テーブルへ UPSERT
  - signal_generator.generate_signals: features / ai_scores / positions を参照して final_score を計算し signals テーブルへ書き込み
- execution（スキーマは用意、実際のブローカー接続は含まれない）
- monitoring（監視・ログ、Slack 通知等のための設定値）

主要な設計注記:
- すべての DB 書き込みは冪等（ON CONFLICT）または日単位差し替えで原子性を確保
- 研究・戦略コードは発注 API に依存しない（安全な境界分離）

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の | 型ヒント等を使用）
- DuckDB（Python パッケージとして duckdb を使用）
- defusedxml（RSS パース用）
- （任意）ネットワークアクセス: J-Quants API・RSS 取得のため

1. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb defusedxml

   （プロジェクト化している場合は pip install -e . / requirements.txt を用意してください）

3. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動的に読み込まれます（config.py）。  
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   主な必須環境変数（config.Settings が要求するもの）
   - JQUANTS_REFRESH_TOKEN: J-Quants の refresh token
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注層を使用する場合）
   - SLACK_BOT_TOKEN: Slack 通知に使用する Bot Token
   - SLACK_CHANNEL_ID: Slack チャンネル ID
   - 省略可能:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG/INFO/...
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（デフォルト）

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマ初期化
   - Python から schema.init_schema() を呼んで DB を準備します（詳細は下の「使い方」参照）。

---

## 使い方（簡単なワークフロー例）

以下は最短で ETL → 特徴量作成 → シグナル作成までの実行例です。

1. DuckDB を初期化する（初回のみ）

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は環境変数 DUCKDB_PATH に従う（デフォルト data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)
```

2. 日次 ETL を実行（J-Quants から差分取得して DB 保存）

```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3. 特徴量（features）を構築

```python
from kabusys.strategy import build_features
from datetime import date

count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

4. シグナルを生成

```python
from kabusys.strategy import generate_signals
from datetime import date

total_signals = generate_signals(conn, target_date=date.today(), threshold=0.60)
print(f"signals created: {total_signals}")
```

5. ニュース収集（RSS を DB に保存して銘柄紐付け）

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes: 抽出対象の有効な銘柄コードの集合（例: prices_daily より取得）
rows = conn.execute("SELECT DISTINCT code FROM prices_daily").fetchall()
known_codes = {r[0] for r in rows}

results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

6. カレンダー更新ジョブ（夜間バッチ）

```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"market_calendar saved: {saved}")
```

注意:
- これらは同期的に実行する簡易例です。実運用ではジョブ管理（cron / Airflow 等）・ロギング・監視を組み合わせてください。
- 発注（execution）層はスキーマと監査ログを備えていますが、実際のブローカー連携ロジックは別途実装が必要です。

---

## よく使う API（抜粋）

- kabusys.data.schema
  - init_schema(db_path) -> DuckDB 接続（スキーマ作成）
  - get_connection(db_path)

- kabusys.data.jquants_client
  - fetch_daily_quotes(...)
  - save_daily_quotes(conn, records)
  - fetch_financial_statements(...)
  - save_financial_statements(conn, records)
  - fetch_market_calendar(...)
  - save_market_calendar(conn, records)

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, id_token=None, ...)

- kabusys.research
  - calc_momentum(conn, date)
  - calc_volatility(conn, date)
  - calc_value(conn, date)
  - calc_forward_returns(...)
  - calc_ic(...)

- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold=0.6, weights=None)

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - pipeline.py
    - stats.py
    - features.py
    - calendar_management.py
    - audit.py
    - pipeline.py
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
  - monitoring/  (モニタリング用モジュール用意予定)

各モジュールは README 中で説明したとおり、Raw → Processed → Feature → Execution の階層設計に従います。

---

## 運用上の注意・設計上のポイント

- 環境変数の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API 呼び出しはレート制限とリトライを組み込んでいます。API キーの管理・監視を行ってください。
- ETL は差分更新かつ冪等保存を行う設計ですが、初回ロード時は大量データを投入するため十分なディスク容量と時間を確保してください。
- features / signals の計算ロジックはルックアヘッドバイアスに配慮して target_date 時点のデータのみを参照するよう設計されています。
- RSS 処理は外部データを多数扱うため、SSRF 防止・XML 攻撃対策（defusedxml）・レスポンス上限等の安全機構を盛り込んでいます。

---

## 貢献・拡張案

- 発注（execution）層のブローカー接続実装（kabuステーション API 等）
- AI スコア算出プロセスの追加（ai_scores テーブルへの埋め込み）
- モニタリング・アラート（Slack 連携）の具体実装
- 性能改善（DuckDB クエリ最適化、並列 ETL）

---

この README はコードベース（src/kabusys）からの主要機能説明に基づいて作成されています。実運用する際は環境変数・API キーの管理、バックアップ、監査ログ保存ポリシー等を整備してください。