# KabuSys

日本株向けの自動売買／データ基盤ライブラリ（KabuSys）のリポジトリ用 README。  
このドキュメントはソースコード（src/kabusys/**）を基に、プロジェクト概要、機能、セットアップ、基本的な使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株のデータ収集（J-Quants 等）・ETL・特徴量作成・シグナル生成・ニュース収集・監査トレーサビリティを意識したデータ基盤＋戦略ライブラリです。  
主に以下レイヤーを持ちます。

- Data Layer：J-Quants など外部 API からの取得 / DuckDB への保存（生データ・整形データ・特徴量など）
- Research Layer：ファクター計算・特徴量探索（ルックアヘッドバイアスを避ける設計）
- Strategy Layer：特徴量を合成してシグナル（BUY/SELL）を生成
- Execution / Audit：発注・約定・ポジション・監査ログ（スキーマ準備済み）
- News Collection：RSS から記事を収集し銘柄紐付けを行う

設計方針として、ルックアヘッドバイアス回避、冪等な DB 書き込み、API レート制御、エラーハンドリング（リトライ）などに配慮しています。

---

## 機能一覧

主要な機能（モジュール単位）

- 環境設定管理
  - 自動でプロジェクトルートの `.env` / `.env.local` を読み込む（無効化も可能）
  - 必須環境変数取得ユーティリティ
- Data / ETL
  - J-Quants API クライアント（認証・ページネーション・リトライ・レートリミット）
  - DuckDB スキーマ定義と初期化（init_schema）
  - ETL パイプライン（日次差分更新、カレンダー・株価・財務データの取得）
  - 市場カレンダー管理（営業日判定・次営業日/前営業日取得）
  - ニュース収集（RSS 取得、XML の安全パース、URL 正規化、銘柄抽出、DB 保存）
  - 各種データ保存関数（生データ -> raw_*、整形 -> prices_daily / features 等）
- Research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
  - Z スコア正規化ユーティリティ
- Strategy
  - 特徴量構築（build_features）: research 側の raw factor を正規化して features テーブルへ保存
  - シグナル生成（generate_signals）: features と ai_scores を統合して final_score を算出、BUY/SELL シグナルを作成して signals テーブルへ保存
- Audit / Execution（スキーマ）
  - 監査ログ（signal_events, order_requests, executions 等）と実行レイヤーのスキーマが定義済み

セキュリティ・堅牢性:
- RSS の SSRF 対策、受信サイズ制限、defusedxml による安全な XML パース
- J-Quants クライアントのレート制御とリトライ、401でのトークンリフレッシュ
- DuckDB への保存は冪等（ON CONFLICT）で実装

---

## セットアップ手順

動作環境（最低限の目安）
- Python 3.10 以上（ソース内の型アノテーションに `X | None` 構文を使用）
- 必要パッケージ（最低限）:
  - duckdb
  - defusedxml

例: 仮想環境とパッケージのインストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# 必要に応じてプロジェクトを editable install (pyproject.toml/setup.py があれば)
# pip install -e .
```

環境変数（必須／推奨）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD : kabuステーション API のパスワード（発注連携を行う場合）
- KABU_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN : Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID : Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV : 実行環境 (development / paper_trading / live)、デフォルト development
- LOG_LEVEL : ログレベル（DEBUG/INFO/...）、デフォルト INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 にすると .env 自動読み込みを無効化

.env の自動読み込み
- パッケージの `kabusys.config` モジュールはプロジェクトルート（.git または pyproject.toml がある場所）から `.env` と `.env.local` を自動読み込みします。自動読み込みを止めたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例: .env（必要なキーの最小例）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単な例）

以下はライブラリを用いた基本操作の例です。実行は Python スクリプトやジョブランナーから行います。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL の実行（J-Quants からデータ取得して保存）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)
print(result.to_dict())
```

3) 特徴量の構築（features テーブルの作成/更新）
```python
from kabusys.strategy import build_features
from datetime import date
count = build_features(conn, target_date=date(2025, 1, 20))
print(f"features upserted: {count}")
```

4) シグナル生成（signals テーブルへ保存）
```python
from kabusys.strategy import generate_signals
from datetime import date
total = generate_signals(conn, target_date=date(2025, 1, 20))
print(f"signals generated: {total}")
```

5) ニュース収集ジョブの実行
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
# known_codes: 銘柄リスト（set）を渡すと記事から銘柄抽出して紐付けを行う
result = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(result)
```

6) 市場カレンダー判定の利用例
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date
d = date(2025, 1, 1)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意点
- 上記関数はいずれも DuckDB 接続（kabusys.data.schema.init_schema で得られるもの）を前提としています。
- 実稼働ではトークンやパスワードなどの機密情報は環境変数／シークレット管理で管理してください。
- ETL や外部 API 呼び出しはネットワークやレート制限の影響を受けます。ログや再試行ポリシーを監視してください。

---

## ディレクトリ構成（主要ファイル）

（リポジトリ内での Python_PACKAGE = src/kabusys/ を想定）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込みと Settings オブジェクト（settings）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（認証・fetch/save）
    - pipeline.py
      - 日次 ETL、個別 ETL ジョブ定義
    - schema.py
      - DuckDB スキーマ定義と init_schema / get_connection
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - features.py
      - zscore_normalize の再エクスポート
    - news_collector.py
      - RSS 取得・正規化・DB 保存・銘柄抽出
    - calendar_management.py
      - 市場カレンダー管理（is_trading_day 等）
    - audit.py
      - 監査ログ関連の DDL（signal_events, order_requests, executions 等）
    - (その他: quality モジュール等は pipeline から参照想定)
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum, calc_volatility, calc_value
    - feature_exploration.py
      - calc_forward_returns, calc_ic, factor_summary, rank
  - strategy/
    - __init__.py
      - build_features, generate_signals をエクスポート
    - feature_engineering.py
      - 生ファクターを正規化し features テーブルへ保存
    - signal_generator.py
      - features + ai_scores を統合して シグナル（signals）を生成
  - execution/
    - __init__.py
      - （発注連携や broker adaptor はこの下に実装予定）
  - monitoring/
    - （監視用ツール、監査・メトリクス用の実装を想定）

---

## 実務上の注意・運用上のヒント

- ルックアヘッドバイアスに注意:
  - research/strategy の関数は target_date 時点で利用可能なデータのみ参照するよう設計されています。ETL の時刻や fetched_at の扱いを運用ルールに合わせてください。
- DB の冪等性:
  - raw -> processed -> feature 層への保存は ON CONFLICT 等で冪等に実装されています。トランザクションでの処理も考慮されていますが、運用時のバックアップやマイグレーション計画は重要です。
- ロギングとモニタリング:
  - LOG_LEVEL、Slack 通知等を組み合わせて ETL の失敗や品質問題を即時検知できるようにしてください。
- テストと CI:
  - config の自動読み込みはテストで邪魔になることがあるため、テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して外部依存を切り離して下さい。

---

## よく使う API 一覧（短いリファレンス）

- kabusys.config.settings: アプリケーション設定オブジェクト
- kabusys.data.schema.init_schema(db_path): DuckDB スキーマ初期化
- kabusys.data.pipeline.run_daily_etl(conn, target_date=None): 日次 ETL 実行
- kabusys.data.jquants_client.fetch_daily_quotes(...), save_daily_quotes(...)
- kabusys.strategy.build_features(conn, target_date): features 作成
- kabusys.strategy.generate_signals(conn, target_date, threshold=0.6): signals 作成
- kabusys.data.news_collector.run_news_collection(conn, sources, known_codes): RSS 収集

---

プロジェクトの拡張や実運用にあたっては、発注・ブローカー接続（execution 層）やリスク管理、監査ログ運用ポリシーを適切に設計してから導入してください。必要であれば README を運用手順書（Runbook）やデプロイ手順に合わせて追補します。