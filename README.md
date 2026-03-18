# KabuSys

日本株向けの自動売買・データ基盤ライブラリ KabuSys のリポジトリ用 README（日本語）

この README はコードベース内のモジュール実装に基づき、プロジェクトの概要、主要機能、セットアップ手順、基本的な使い方、ディレクトリ構成を説明します。

注意: 本リポジトリはライブラリ／モジュール群の実装を含みます。実行には外部 API（J-Quants 等）やデータベース（DuckDB）等の環境が必要です。

---

## プロジェクト概要

KabuSys は日本株を対象としたデータプラットフォーム兼自動売買フレームワークです。主に以下を目的としています。

- J-Quants API からの時系列・財務・市場カレンダーの取得・保存（DuckDB）
- RSS ニュース収集と記事の正規化・銘柄紐付け
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ETL パイプラインの実行（差分更新、バックフィルを考慮）
- 研究（ファクター計算、将来リターン・IC 計算、統計要約）
- 発注/監査（テーブル定義・監査ログ機能を含むベース実装）
- 設定や環境変数の管理（自動 .env ロード等）

設計方針として、DuckDB によるローカル永続化、冪等性を意識した INSERT（ON CONFLICT）、外部ライブラリへの過度な依存回避（研究・統計系は標準ライブラリのみで実装された関数を含む）、および外部 API への堅牢なアクセス制御（レートリミット、リトライ、トークン自動更新）を重視しています。

---

## 主な機能一覧

- 環境設定管理
  - .env と OS 環境変数の読み込み（自動ロード、上書き制御、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）
  - 必須変数チェック（例: JQUANTS_REFRESH_TOKEN 等）

- Data（data パッケージ）
  - jquants_client: J-Quants API クライアント（レート制御、リトライ、トークン自動更新、ページネーション対応）
  - news_collector: RSS フィード収集、URL 正規化、SSRF 対策、gzip 制限、記事保存（冪等）
  - schema: DuckDB 用スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - pipeline / etl: 差分 ETL（価格・財務・カレンダー）、バックフィル、品質チェック連携
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - calendar_management: 市場カレンダー管理・営業日判定ユーティリティ
  - audit: 監査ログテーブル（signal → order_request → execution のトレース）
  - stats: 共通統計ユーティリティ（zscore 正規化等）

- Research（research パッケージ）
  - factor_research: Momentum / Volatility / Value ファクター計算（prices_daily / raw_financials を参照）
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー

- 実行・戦略（strategy / execution / monitoring）
  - パッケージの骨組みを提供（詳細ロジックは戦略実装に依存）

---

## 前提（推奨環境）

- Python 3.10+（型ヒントに | 演算子を使用）
- 必要パッケージ（例）
  - duckdb
  - defusedxml

インストール例:
```
pip install duckdb defusedxml
```
実運用では追加のパッケージ（Slack クライアント、kabu API クライアント等）が必要になる場合があります。

---

## 環境変数（主なもの）

以下はコード内で参照する主な環境変数（必須は README の時点で明記）。

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client が ID トークンを取得するのに使用）
- KABU_API_PASSWORD: kabu ステーション API 用パスワード
- SLACK_BOT_TOKEN: Slack ボット用トークン（通知等に使用）
- SLACK_CHANNEL_ID: Slack 送信先チャンネル ID

任意 / デフォルトあり:
- KABUSYS_ENV: "development" / "paper_trading" / "live"（デフォルト "development"）
- LOG_LEVEL: "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"（デフォルト "INFO"）
- DUCKDB_PATH: DuckDB のファイルパス（デフォルト "data/kabusys.duckdb"）
- SQLITE_PATH: 監視 DB 等の SQLite パス（デフォルト "data/monitoring.db"）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: この変数をセットすると .env 自動ロードを無効化

プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると無効化）。

---

## セットアップ手順（開発・最短起動例）

1. リポジトリをクローンしてルートに移動
2. Python 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```
3. 必要パッケージをインストール
   ```
   pip install duckdb defusedxml
   ```
   実運用ではロギングや Slack 連携のために追加ライブラリを入れることを検討してください。

4. 環境変数を用意
   - プロジェクトルートに `.env` を作成（もしくは環境変数で設定）
   - 必須のトークン類（JQUANTS_REFRESH_TOKEN など）を設定

5. DuckDB スキーマを初期化
   Python で次のように初期化します（デフォルトパスを使用する場合）:
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)  # settings.duckdb_path は Path オブジェクト
   ```
   これで必要なテーブルとインデックスが作成されます。

---

## 基本的な使い方（例）

- 日次 ETL を実行（株価・財務・カレンダー取得＋品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  # 初期化済み接続を取得
  conn = init_schema(settings.duckdb_path)

  # ETL 実行（target_date を省略すると今日）
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- J-Quants から日足を直接取得して保存
  ```python
  import duckdb
  from kabusys.data import jquants_client as jq
  from kabusys.data.schema import init_schema
  from kabusys.config import settings
  from datetime import date

  conn = init_schema(settings.duckdb_path)
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  print(f"saved: {saved}")
  ```

- RSS ニュースを収集して DB に保存
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203", "6758"})
  print(results)
  ```

- リサーチ / ファクター計算の実行（例: モメンタム計算）
  ```python
  from datetime import date
  from kabusys.data.schema import get_connection
  from kabusys.research.factor_research import calc_momentum

  conn = get_connection("data/kabusys.duckdb")
  res = calc_momentum(conn, target_date=date(2024, 1, 31))
  # res は dict のリスト: [{"date":..., "code":..., "mom_1m":..., ...}, ...]
  print(len(res))
  ```

- 将来リターンや IC を計算
  ```python
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic
  # forward = calc_forward_returns(conn, target_date, horizons=[1,5,21])
  # ic = calc_ic(factor_records, forward, "mom_1m", "fwd_1d")
  ```

---

## ログ・挙動のポイント

- jquants_client は 120 req/min の制限を固定間隔スロットリングで守ります（内部に RateLimiter 実装）。
- リトライ: ネットワーク系エラーや 408/429/5xx は指数バックオフで最大 3 回リトライ。401 を受けた場合は ID トークンを自動でリフレッシュして1回リトライします。
- news_collector は SSRF 対策・gzip サイズ制限・XML デコーダの脆弱性対策（defusedxml）などを実装しています。
- .env ファイルの自動ロードはプロジェクトルート（.git または pyproject.toml を探索）をもとに行われます。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定できます。
- settings.env は "development" / "paper_trading" / "live" のいずれかで、is_live / is_paper / is_dev プロパティで判定可能です。

---

## ディレクトリ構成（主要ファイル・モジュール）

（src/kabusys をルートとする簡易ツリー）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理（settings オブジェクト）
  - data/
    - __init__.py
    - jquants_client.py           — J-Quants API クライアント（取得/保存ユーティリティ）
    - news_collector.py          — RSS 収集・正規化・DB 保存
    - schema.py                  — DuckDB スキーマ定義と init_schema / get_connection
    - stats.py                   — 統計ユーティリティ（zscore_normalize など）
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - features.py                — 特徴量ユーティリティ（再エクスポート）
    - calendar_management.py     — 市場カレンダー更新・営業日判定
    - etl.py                     — ETL インターフェース（ETLResult の再エクスポート）
    - quality.py                 — データ品質チェック
    - audit.py                   — 監査ログスキーマ・初期化
  - research/
    - __init__.py
    - factor_research.py         — Momentum / Volatility / Value ファクター計算
    - feature_exploration.py     — 将来リターン・IC・サマリー
  - strategy/
    - __init__.py                — 戦略ロジックを置くためのパッケージ（骨組み）
  - execution/
    - __init__.py                — 発注系実装用パッケージ（骨組み）
  - monitoring/
    - __init__.py                — 監視系（未実装/骨組み）

---

## 開発上の注意点 / 今後の拡張案

- strategy / execution / monitoring パッケージは骨組みのみ提供しているため、実際の売買ロジックやブローカー連携は各プロジェクトで実装してください。
- DuckDB の SQL 構文は将来のバージョン差異に影響を受ける可能性があるため、CI で使用する duckdb バージョンを固定することを推奨します。
- ニュースの銘柄抽出ロジックは単純な正規表現（4桁コード）に依存しているため、外部の EN/JP 名寄せやエンティティ抽出を導入すると精度向上が見込めます。
- ETL のスケーリング（大量データ取得・並列化）を行う場合は、jquants_client のレート制御を考慮したジョブ分割が必要です。

---

## ライセンス / コントリビューション

このリポジトリに含まれるライセンスは本 README には含まれていません。実際の配布では LICENSE ファイルを追加し、コントリビューションガイドライン（CONTRIBUTING.md）を用意してください。

---

README は以上です。必要であれば、具体的なセットアップスクリプト（example/ ディレクトリ）や Dockerfile／CI 設定のテンプレートも作成できます。どの情報を追加しますか？