# KabuSys

KabuSys は日本株のデータ収集・前処理・特徴量生成・シグナル生成を行う自動売買基盤向けの Python モジュール群です。DuckDB をデータ層に用い、J-Quants API から市場データ・財務データ・カレンダーを取得し、研究（research）→ 特徴量（feature）→ 戦略（strategy）→ 発注（execution）へと繋ぐパイプラインを提供します。

本 README はリポジトリ内の主要機能・セットアップ・基本的な使い方・ディレクトリ構成をまとめたものです。

## プロジェクト概要

- データ層（DuckDB）に生データ / 整形済みデータ / 特徴量 / 取引ログなどのスキーマを管理する。
- J-Quants API クライアントで株価・財務・カレンダーを差分取得し、冪等に保存する。
- 研究用モジュールでファクター（モメンタム / ボラティリティ / バリュー）を計算する。
- 戦略モジュールで特徴量正規化・統合スコア計算・BUY/SELL シグナル生成を行う。
- ニュース収集（RSS）モジュールで記事を収集し、銘柄との紐付けを行う。
- カレンダー管理・ETL パイプライン・監査ログなど運用に必要なユーティリティを提供。

設計上のポイント:
- ルックアヘッドバイアス対策（target_date 時点のデータのみを使用）
- 冪等性（ON CONFLICT / upsert）を重視
- 外部 API 呼び出しは data 層で集中管理し、strategy 層は発注 API に依存しない設計
- DuckDB を用いることでローカルファイル DB として軽量に運用可能

## 主な機能一覧

- データ取得・保存
  - J-Quants API クライアント（jquants_client）
  - 差分 ETL パイプライン（data.pipeline.run_daily_etl など）
  - 市場カレンダーの夜間更新ジョブ（data.calendar_management.calendar_update_job）
- スキーマ管理
  - DuckDB スキーマ初期化 / 接続（data.schema.init_schema / get_connection）
- 研究 / ファクター
  - モメンタム / ボラティリティ / バリュー計算（research.factor_research）
  - 将来リターン・IC・統計サマリ（research.feature_exploration）
  - Z スコア正規化ユーティリティ（data.stats.zscore_normalize）
- 特徴量 / シグナル
  - 特徴量合成と features テーブルへの保存（strategy.feature_engineering.build_features）
  - 最終スコア計算と BUY/SELL シグナル生成（strategy.signal_generator.generate_signals）
- ニュース収集
  - RSS フィード収集、防御的 XML パース、記事の DB 保存（data.news_collector）
  - 記事 → 銘柄抽出（extract_stock_codes）と紐付け保存
- ユーティリティ
  - 環境変数 / 設定管理（config.Settings）
  - 監査ログ（data.audit）など（初期化DDL有）

## 必要条件 / 依存

- Python 3.10 以上（型ヒントに | None 等を使用）
- 必要パッケージ（代表例）
  - duckdb
  - defusedxml
- ネットワークアクセス：J-Quants API へアクセスするための認証情報

（プロジェクトルートに requirements.txt があればそれを利用してください。ここではソースから読み取れる主要依存を記載しています。）

## 環境変数（主なもの）

以下は本コードベースで参照される主要な環境変数です（config.Settings に定義あり）。

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (省略可) — kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (省略可) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (省略可) — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (省略可) — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (省略可) — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL

自動で .env / .env.local をロードする仕組みがあり、テストや明示的制御のために KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化できます。

## セットアップ手順

1. リポジトリをクローンして仮想環境を準備します。

   - 例:
     python -m venv .venv
     source .venv/bin/activate

2. 必要パッケージをインストールします（pip 等）。

   - 例:
     pip install duckdb defusedxml

   - 開発用にパッケージ化されているなら:
     pip install -e .

3. 環境変数ファイルを作成します（プロジェクトルートに .env を配置）。

   例: .env
   JQUANTS_REFRESH_TOKEN=xxxx...
   KABU_API_PASSWORD=your_kabu_pass
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=Cxxxxxx
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

   （.env.example がある場合はそれを参考にしてください）

4. DuckDB スキーマを初期化します（例は Python REPL やスクリプトで実行）。

   例:
   from kabusys.data.schema import init_schema
   from kabusys.config import settings
   conn = init_schema(settings.duckdb_path)

   これで必要なテーブルが作成されます。

## 基本的な使い方（抜粋）

以下は主要なワークフローの最小例です。すべての関数は duckdb 接続（duckdb.DuckDBPyConnection）を引数に取ります。

- DB 初期化（先述）
  from kabusys.data.schema import init_schema
  from kabusys.config import settings
  conn = init_schema(settings.duckdb_path)

- 日次 ETL 実行（市場カレンダー / 株価 / 財務 を差分取得し保存）
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # 省略時は今日を対象
  print(result.to_dict())

- 特徴量を作成（features テーブル更新）
  from kabusys.strategy import build_features
  from datetime import date
  n = build_features(conn, target_date=date(2024, 1, 31))
  print(f"features upserted: {n}")

- シグナル生成
  from kabusys.strategy import generate_signals
  from datetime import date
  total = generate_signals(conn, target_date=date(2024, 1, 31))
  print(f"signals created: {total}")

- ニュース収集ジョブ（RSS から raw_news を保存し銘柄紐付け）
  from kabusys.data.news_collector import run_news_collection
  known_codes = {"7203", "6758", ...}  # 有効な銘柄コードの集合
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)

- カレンダー更新ジョブ（夜間バッチ）
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")

注意:
- 各関数は内部で例外を投げることがあるので、運用では適切な例外処理・ログ出力を行ってください。
- generate_signals / build_features は target_date のデータのみを参照するため、ETL を先に実行して最新データを用意する必要があります。

## スニペット: 簡単なバッチスクリプト例

例: daily_job.py
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.strategy import build_features, generate_signals

def main():
    conn = init_schema(settings.duckdb_path)
    etl_res = run_daily_etl(conn)
    trading_day = etl_res.target_date
    build_features(conn, trading_day)
    generate_signals(conn, trading_day)

if __name__ == "__main__":
    main()

## 設計上の注意点 / 運用メモ

- J-Quants API のレート制限（120 req/min）に従うためモジュール内で固定間隔レートリミッタを実装しています。
- ETL は差分更新を前提にしています。初回ロード時はかなりのデータ量を取得する可能性があります。
- features / signals / raw_* テーブルは冪等（日付単位での置換、ON CONFLICT 等）を意識して構成されています。
- ニュース収集は外部 RSS を処理するため SSRF・XML Bomb・大容量レスポンス等に対する防御処理が含まれています。
- 環境（KABUSYS_ENV）が "live" の場合、発注・execution 層の扱いに注意してください（実際の発注は別途ブローカー接続層が必要です）。

## ディレクトリ構成

リポジトリの主要ファイル・モジュールを抜粋した構成:

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント & 保存ロジック
    - news_collector.py               — RSS 収集 / raw_news 保存 / 銘柄抽出
    - schema.py                       — DuckDB スキーマ定義・初期化
    - stats.py                        — 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py                     — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py          — 市場カレンダー管理・更新ジョブ
    - audit.py                        — 監査ログ用 DDL（order_requests / executions 等）
    - features.py                     — features インターフェース（再エクスポート）
  - research/
    - __init__.py
    - factor_research.py              — モメンタム / ボラ / バリュー等の計算
    - feature_exploration.py          — 将来リターン / IC / 統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py          — 生ファクターの合成・正規化・features へ保存
    - signal_generator.py             — final_score 計算・BUY/SELL シグナル生成
  - execution/
    - __init__.py                     — 発注周りのエントリ（将来拡張）
  - monitoring/
    - (監視・通知系モジュール想定)

上記は主要なモジュールの抜粋です。さらに細かいモジュールや将来的な拡張点（ブローカー接続、リスク管理、ポートフォリオ最適化など）があります。

## 貢献 / 拡張ポイント

- 発注ブリッジ（kabu API / 各ブローカー）を実装して execution 層と連携
- リスク管理ルール（ドローダウン・ポジション制限）を signal/event 層に組み込む
- AI スコアのパイプライン（news → NLP モデル → ai_scores テーブル）
- テスト・CI の整備（単体テスト / ETL 小規模モックテスト）

---

不明点や README に追記したい使い方（例: サンプル .env.example、systemd / cron での運用例、Docker 化など）があれば教えてください。必要に応じて具体的な起動スクリプトや運用手順を追記します。