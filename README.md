# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（KabuSys）。  
データ取得・ETL、データ品質検査、特徴量生成、研究用ユーティリティ、監査ログなどを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群から構成されます。

- J-Quants 等の外部 API からの市場データ取得と DuckDB への保存（冪等）
- RSS ニュース収集と銘柄紐付け
- DuckDB スキーマ定義／初期化
- ETL（差分更新・バックフィル・品質チェック）のパイプライン
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と研究用ユーティリティ（IC 計算など）
- 監査ログ（シグナル → 発注 → 約定 のトレーサビリティ）
- 実行／戦略／モニタリング層のプレースホルダ（拡張用）

設計上のポイント：
- DuckDB を中心としたローカルデータプラットフォーム
- API 呼び出しはレート制御・リトライ・トークン自動更新
- ETL は差分更新とバックフィルを考慮
- データ品質チェックを分離し、問題を集約して報告
- 研究モジュールは本番発注 API にアクセスしない

---

## 主な機能一覧

- 環境設定管理（.env の自動読み込み、必須環境変数チェック）
- J-Quants API クライアント（ページネーション・リトライ・レートリミット対応）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_* 系で DuckDB に冪等保存
- DuckDB スキーマ定義と初期化（raw / processed / feature / execution 層）
- ETL パイプライン（差分取得・保存・品質チェック）
  - run_daily_etl や個別 ETL ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS 取得、URL 正規化、記事保存、銘柄コード抽出）
- 研究用ユーティリティ
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（data.stats）
- 監査ログ初期化（signal_events / order_requests / executions 等）

---

## セットアップ手順

前提
- Python 3.9+（typing の union 型等を想定）
- ネットワークアクセス（J-Quants / RSS フィード）

1. リポジトリをチェックアウト／コピー

2. 仮想環境作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール  
   本コードベースで使用している主要パッケージ例：
   - duckdb
   - defusedxml

   例:
   ```bash
   pip install duckdb defusedxml
   ```
   （プロジェクトに requirements.txt / pyproject.toml があればそれを利用してください）

4. 環境変数の設定  
   プロジェクトルートに `.env`（または `.env.local`）を置くと、自動で読み込まれます（ただし環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化）。

   必須環境変数（Settings クラスで参照）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabu API のパスワード（発注関連を使う場合）
   - SLACK_BOT_TOKEN: Slack 通知を使う場合
   - SLACK_CHANNEL_ID: Slack チャンネル ID
   （DB パスやモードは省略可：DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL）

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=REPLACE_ME
   KABU_API_PASSWORD=REPLACE_ME
   SLACK_BOT_TOKEN=REPLACE_ME
   SLACK_CHANNEL_ID=REPLACE_ME
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマ初期化  
   以下の例のようにスクリプトや REPL から初期化します。

   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)
   ```

6. 監査ログ（オプション）初期化
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 基本的な使い方（例）

- 日次 ETL 実行（市場カレンダー・株価・財務・品質チェック）

  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  # DB 初期化（まだであれば）
  conn = init_schema(settings.duckdb_path)

  # ETL 実行（target_date を省略すると今日）
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- J-Quants から株価を直接取得（テストや部分フェッチ用）

  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes

  records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  print(len(records))
  ```

- RSS ニュース収集と銘柄紐付け

  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.config import settings
  from kabusys.data.schema import init_schema

  conn = init_schema(settings.duckdb_path)
  # known_codes は抽出時に参照する銘柄コード集合（例: 全上場銘柄コードをロード）
  known_codes = {"7203", "6758", "9984"}
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- 研究用ファクター計算（例：モメンタム）

  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  recs = calc_momentum(conn, target_date=date(2024,2,20))
  # recs は各銘柄の mom_1m / mom_3m / mom_6m / ma200_dev を含む dict のリスト
  ```

- IC（情報係数）計算

  ```python
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

  fwd = calc_forward_returns(conn, target_date=date(2024,2,20))
  # factor_records は別途 calc_momentum 等で生成したもの
  ic = calc_ic(factor_records, fwd, factor_col="mom_1m", return_col="fwd_1d")
  print(ic)
  ```

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD (必須 for kabu api) — 発注 API 認証パスワード
- KABUSYS_ENV — 実行モード: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB などに使用する SQLite（デフォルト data/monitoring.db）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID — Slack 通知に使用

自動ロード:
- プロジェクトルート（.git または pyproject.toml を起点）上の `.env` / `.env.local` を自動で読み込みます。
- 自動ロードを無効にする場合: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py        # J-Quants API クライアント + 保存ユーティリティ
    - news_collector.py       # RSS ニュース収集・保存・銘柄抽出
    - schema.py               # DuckDB スキーマ定義・初期化
    - pipeline.py             # ETL パイプライン（run_daily_etl 等）
    - features.py             # 特徴量関連の公開インターフェース
    - stats.py                # 基本統計・正規化ユーティリティ
    - calendar_management.py  # カレンダー管理・営業日判定
    - audit.py                # 監査ログ定義・初期化
    - etl.py                  # ETLResult の再エクスポート
    - quality.py              # データ品質チェック
  - research/
    - __init__.py
    - feature_exploration.py  # 将来リターン、IC、統計サマリー
    - factor_research.py      # momentum / value / volatility 等
  - strategy/
    - __init__.py
    # （戦略実装はここに配置）
  - execution/
    - __init__.py
    # （発注・ブローカーインタフェース）
  - monitoring/
    - __init__.py
    # （監視・外部通知）

---

## 実装上の注意点 / トラブルシューティング

- DuckDB ファイルの親ディレクトリが存在しない場合、init_schema / init_audit_db が自動で作成します。
- J-Quants の ID トークンはモジュール内でキャッシュ・自動更新され、401 時は 1 回リフレッシュして再試行します。
- ニュース取得で XML を扱うため defusedxml を利用して XML Bomb 等の攻撃を防いでいます。
- RSS フェッチ時は SSRF を防ぐためスキーム／ホストの検証やリダイレクト検査を行います。
- ETL の品質チェックは Fail-Fast ではなく、すべてのチェックの結果を収集して返します。必要に応じて呼び出し側でエラー判定し処理を停止してください。
- production（live）環境での発注は慎重に取り扱ってください。KABUSYS_ENV を適切に設定し、paper_trading モードを整備してから移行してください。

---

## 参考・次のアクション

- 戦略や実行ロジックは `strategy/` と `execution/` に実装して連携させます。監査ログ（audit）を利用してシグナルから約定までを追跡できるようにしてください。
- 特徴量・AI スコアの保存は features / ai_scores テーブルを使って管理します。
- 必要に応じて Slack 通知や監視ジョブ（monitoring）を実装してください。

---

この README はコードベースの現状実装（src/kabusys 以下）をもとに作成しています。運用ルールや外部設定（APIキー管理、資格情報保護、発注ポリシー等）は別途ドキュメント化して運用してください。