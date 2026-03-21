# KabuSys

バージョン: 0.1.0

KabuSys は日本株のデータプラットフォームと自動売買戦略パイプラインを提供する Python パッケージです。J-Quants API から市場データ・財務データ・マーケットカレンダーを取得し、DuckDB に保存、ファクター計算・特徴量生成・シグナル生成までを行うためのモジュール群を含みます。ニュース収集、監査ログ、マーケットカレンダ管理などのユーティリティも備えています。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（簡易例）
- 環境変数（.env）
- ディレクトリ構成
- 補足 / トラブルシューティング

---

## プロジェクト概要

本リポジトリは以下の責務を分離して実装しています。

- data: J-Quants クライアント、ETL パイプライン、DuckDB スキーマ、ニュース収集などのデータ層
- research: ファクター計算・特徴量探索の研究用ユーティリティ
- strategy: 特徴量を統合してシグナルを生成するロジック
- execution: 発注・約定・ポジション管理層（パッケージ構造上のモジュールプレースホルダ）
- monitoring: 監視・監査用のユーティリティ（audit 等）

設計上のポイント:
- DuckDB を永続ストレージとして使用（デフォルト: data/kabusys.duckdb）
- J-Quants API のレート制御・リトライ・トークン自動更新を実装
- ETL/feature/signal の各処理は冪等性（idempotent）を保つように設計
- ルックアヘッドバイアス防止のため、target_date 時点のデータのみを使用

---

## 機能一覧

主な機能（抜粋）:

- データ取得・保存
  - J-Quants API クライアント（jquants_client）
  - 株価（日足）・財務データ・マーケットカレンダーの取得と DuckDB 保存
  - raw / processed / feature / execution のスキーマ定義と初期化

- ETL / データパイプライン
  - 差分取得・バックフィル・品質チェックを含む日次 ETL（run_daily_etl）
  - カレンダー更新ジョブ（calendar_update_job）

- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（calc_momentum 等）
  - 将来リターン計算、IC 計算、ファクター統計サマリー

- 特徴量・シグナル処理
  - ファクター正規化・features テーブルへの保存（build_features）
  - ai_scores と統合して final_score を算出、BUY/SELL シグナル生成（generate_signals）

- ニュース収集
  - RSS フィード取得・前処理・raw_news 保存・銘柄抽出（news_collector）

- 監査・トレーサビリティ
  - signal_events / order_requests / executions など監査テーブル定義（audit モジュール）

---

## セットアップ手順

前提:
- Python 3.9+（typing の union 表記等に依存）
- DuckDB を使用（python パッケージ duckdb）
- ネットワークアクセス（J-Quants / RSS フィード）

推奨インストール手順（開発環境）:

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   - 必須例: duckdb, defusedxml
   - setup.py / pyproject.toml がある場合は pip install -e . または pip install -r requirements.txt
   例（最低限）:
   ```
   pip install duckdb defusedxml
   ```

4. 環境変数設定（.env の作成）
   ルートに .env または .env.local を作成します（次節参照）。

5. DuckDB スキーマ初期化（例）
   Python REPL またはスクリプトで：
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```

環境変数の自動読み込み:
- パッケージ import 時にプロジェクトルート（.git または pyproject.toml を探索）から .env/.env.local を自動読み込みします。
- テスト等で自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（簡易例）

以下は典型的なワークフロー例です。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL 実行（J-Quants から差分取得）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量生成（features テーブル作成）
```python
from datetime import date
from kabusys.strategy import build_features

count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

4) シグナル生成（signals テーブル作成）
```python
from datetime import date
from kabusys.strategy import generate_signals

num = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals generated: {num}")
```

5) ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203", "6758"})
print(res)
```

注意:
- 各 API 関数は DuckDB 接続オブジェクト（duckdb.DuckDBPyConnection）を受け取ります。
- run_daily_etl では品質チェック（quality.run_all_checks）をオプションで有効化できます。

---

## 環境変数（.env 例）

必須/推奨の環境変数（Settings により参照されます）:

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン

- KABU_API_PASSWORD (必須)  
  kabuステーション API 利用時のパスワード

- KABU_API_BASE_URL (任意, デフォルト http://localhost:18080/kabusapi)  
  kabu API のベース URL

- SLACK_BOT_TOKEN (必須)  
  Slack 通知用ボットトークン

- SLACK_CHANNEL_ID (必須)  
  Slack 通知先チャンネル ID

- DUCKDB_PATH (任意, デフォルト data/kabusys.duckdb)  
  DuckDB ファイルパス

- SQLITE_PATH (任意, デフォルト data/monitoring.db)  
  監視用 SQLite ファイルパス

- KABUSYS_ENV (任意, default "development")  
  有効値: development / paper_trading / live

- LOG_LEVEL (任意, default "INFO")  
  有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL

簡易 .env.example:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

自動読み込みの挙動:
- OS環境変数 > .env.local > .env の順で読み込みます。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます。

---

## ディレクトリ構成

主要ファイル / モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - data/
    - __init__.py
    - schema.py                     — DuckDB スキーマ定義 / init_schema
    - jquants_client.py             — J-Quants API クライアント (fetch/save)
    - pipeline.py                   — ETL パイプライン (run_daily_etl 等)
    - news_collector.py             — RSS ニュース収集・保存
    - stats.py                      — zscore_normalize 等の統計ユーティリティ
    - features.py                   — data.stats の再エクスポート
    - calendar_management.py        — マーケットカレンダー管理
    - audit.py                      — 監査ログスキーマ
    - pipeline.py                   — ETL 管理
  - research/
    - __init__.py
    - factor_research.py            — momentum/volatility/value の計算
    - feature_exploration.py        — forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py        — build_features
    - signal_generator.py           — generate_signals
  - execution/
    - __init__.py                   — 発注層プレースホルダ（将来的な実装）
  - monitoring/
    - (監視/ログ関連モジュール。audit 等を含む)

その他:
- data/kabusys.duckdb    — デフォルト DuckDB ファイル (生成される)
- data/monitoring.db     — 監視用 SQLite（デフォルトパス）

---

## 補足 / トラブルシューティング

- DuckDB のファイルパスは Settings.duckdb_path で指定可能。init_schema は親ディレクトリがなければ自動作成します。
- J-Quants API のレート制限（120 req/min）に従って内部でスロットリングしています。大量取得時は遅延が発生します。
- API 401 レスポンスは自動的にリフレッシュトークンでトークン更新を試み、1 回だけリトライします。
- ETL・DB 操作はトランザクションでラップしており、失敗時はロールバックを行います（可能な限り冪等性を確保）。
- .env 自動読み込みはプロジェクトルートの検出 (.git または pyproject.toml) を基準に行います。テスト環境等での切り替えは KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- news_collector は SSRF / XML Bomb / 非 http(s) スキーム等に対する対策を実装していますが、外部フィードを利用する際はソースの信頼性を確認してください。

---

この README はコードベースの主要な使い方と構成をまとめたものです。詳細な仕様（StrategyModel.md / DataPlatform.md 等）や追加のユーティリティはドキュメントフォルダや個別モジュールの docstring を参照してください。質問や改善案があればお気軽にお知らせください。