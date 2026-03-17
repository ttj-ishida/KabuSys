# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（KabuSys）。  
データ取得（J-Quants）、ETL パイプライン、ニュース収集、データ品質チェック、DuckDB ベースのスキーマ定義、監査ログなどを含むモジュール群です。

主な利用対象は戦略開発者・データエンジニアで、ローカル環境やバッチ処理でのデータ取得・保管および監査トレースを想定しています。

---

## 機能一覧

- 環境変数/設定管理
  - .env / .env.local をプロジェクトルートから自動読み込み（必要に応じ無効化可能）
  - KABUSYS_ENV / LOG_LEVEL 等の検証付き設定アクセス

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーの取得
  - API レート制限（120 req/min）遵守の RateLimiter
  - リトライ（指数バックオフ、最大 3 回）、401 の自動トークンリフレッシュ対応
  - 取得タイムスタンプ（fetched_at）で Look-ahead Bias をトレース
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- ニュース収集 (`kabusys.data.news_collector`)
  - RSS フィード収集、前処理（URL 除去・空白正規化）
  - 記事 ID は正規化 URL の SHA-256（先頭32 文字）で冪等性確保
  - SSRF 対策（スキーム検証、プライベートホスト拒否、リダイレクトチェック）
  - レスポンスサイズ制限（メモリ DoS 対策）
  - DuckDB へのバルク保存（INSERT ... RETURNING を利用）

- DuckDB スキーマ管理 (`kabusys.data.schema`)
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - init_schema(): 冪等なスキーマ初期化・接続取得

- ETL パイプライン (`kabusys.data.pipeline`)
  - 差分取得（最終取得日 + バックフィル）、保存、品質チェックを順次実行
  - run_daily_etl(): 市場カレンダー → 株価 → 財務 → 品質チェックの統合ワークフロー
  - 品質チェックは fail-fast とせず検出結果を集約

- データ品質チェック (`kabusys.data.quality`)
  - 欠損データ、主キー重複、スパイク（前日比閾値）、日付不整合（未来日付/非営業日）検出
  - QualityIssue オブジェクトで詳細サンプルを返す

- 監査ログ（トレーサビリティ） (`kabusys.data.audit`)
  - signal_events / order_requests / executions 等の監査テーブルを提供
  - 発注→約定まで UUID 連鎖で完全トレース

---

## 要件

- Python 3.10 以上（PEP 604 の union 型表記や型ヒントを使用）
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml
- 標準ライブラリ：urllib, json, logging, datetime, pathlib など

（プロジェクトの packaging/requirements.txt に合わせてインストールしてください）

---

## セットアップ手順

1. リポジトリをクローンし仮想環境を作成
   - git clone ...
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb defusedxml
   - （プロジェクトに setup.cfg / pyproject.toml 等があれば pip install -e .）

3. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動読み込みされます（デフォルト）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   例（.env）:
   - JQUANTS_REFRESH_TOKEN=your_refresh_token
   - KABU_API_PASSWORD=your_kabu_password
   - SLACK_BOT_TOKEN=xoxb-...
   - SLACK_CHANNEL_ID=CXXXXXXX
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - KABUSYS_ENV=development
   - LOG_LEVEL=INFO

4. DuckDB スキーマ初期化（例）
   - Python REPL かスクリプトで:
     - from kabusys.data import schema
     - conn = schema.init_schema("data/kabusys.duckdb")

---

## 使い方（抜粋例）

- DuckDB スキーマの初期化
  - from kabusys.data import schema
  - conn = schema.init_schema("data/kabusys.duckdb")

- J-Quants の ID トークン取得
  - from kabusys.data.jquants_client import get_id_token
  - token = get_id_token()  # JQUANTS_REFRESH_TOKEN は settings 経由で取得

- 日次 ETL 実行
  - from datetime import date
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn, target_date=date.today())
  - print(result.to_dict())

  run_daily_etl は以下を順に実行します:
  1. 市場カレンダー（先読み）
  2. 株価日足（差分 + backfill）
  3. 財務データ（差分 + backfill）
  4. 品質チェック（run_quality_checks=True の場合）

- RSS ニュース収集
  - from kabusys.data.news_collector import run_news_collection
  - results = run_news_collection(conn, sources=None, known_codes={"7203","6758"}, timeout=30)
  - # results はソース毎の新規保存件数辞書

- 品質チェックのみ実行
  - from kabusys.data.quality import run_all_checks
  - issues = run_all_checks(conn, target_date=None)
  - for i in issues: print(i)

- 自動環境読み込みについて
  - kabusys.config は起点ファイルの親ディレクトリから .git または pyproject.toml を探索してプロジェクトルートを特定し、そこにある `.env` / `.env.local` を自動で読み込みます。
  - テスト等で自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 主要 API と設計上の注意点

- jquants_client:
  - RateLimiter により 120 req/min を厳守
  - リトライ: 指数バックオフ、408/429/5xx を再試行、401 なら自動でリフレッシュして1回再試行
  - fetch_* 系はページネーション対応
  - save_* 系は ON CONFLICT を使って冪等に保存

- news_collector:
  - RSS の XML 解析に defusedxml を使用（XML 攻撃対策）
  - リダイレクト時に _SSRFBlockRedirectHandler を利用して内部アドレスや不正スキームを拒否
  - レスポンスサイズ上限・gzip 解凍後のサイズチェックあり

- pipeline:
  - 差分更新の際は DB の最終取得日を基にバックフィル（デフォルト 3 日）して API 後出し修正を吸収
  - 各処理は独立してエラーハンドリングされ、1ステップ失敗でも残りを続行（結果オブジェクトにエラーを格納）

- schema / audit:
  - DuckDB にて Raw/Processed/Feature/Execution 層を定義
  - 監査テーブルは UTC タイムスタンプ前提、発注の冪等キー（order_request_id）や broker_execution_id のユニーク性を担保

---

## ディレクトリ構成

（抜粋 — 実際のファイル数はリポジトリに依存します）

- src/kabusys/
  - __init__.py                      -- パッケージ定義
  - config.py                        -- 環境変数・設定管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py              -- J-Quants API クライアント + 保存ロジック
    - news_collector.py              -- RSS 収集・前処理・保存
    - schema.py                      -- DuckDB スキーマ定義・init
    - pipeline.py                    -- ETL パイプライン（run_daily_etl 等）
    - audit.py                       -- 監査ログスキーマ（signal/order/execution）
    - quality.py                     -- データ品質チェック
  - strategy/
    - __init__.py                    -- 戦略関連モジュール（未実装ファイル群のエントリ）
  - execution/
    - __init__.py                    -- 発注/ブローカー連携関連（未実装ファイル群のエントリ）
  - monitoring/
    - __init__.py                    -- 監視・メトリクス系（未実装ファイル群のエントリ）

---

## 開発・運用上の注意

- 環境変数の扱い:
  - 必須環境変数（取得時に ValueError を投げる）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - デフォルト値が存在する設定:
    - KABUSYS_ENV (default: development)、KABUSYS_ENV は development/paper_trading/live のいずれか
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み制御

- テスト時:
  - ネットワーク依存コード（_jquants_client._request、news_collector._urlopen 等）はモック可能に実装されています。外部 API 呼び出しはテストで差し替えてください。

- セキュリティ:
  - news_collector は SSRF、XML Bomb、巨大レスポンス等に対する対策を幾つか実装していますが、外部 URL の取り扱いは運用で慎重に管理してください。

---

README に記載しきれない細かな使用例や API の詳細は、各モジュール（kabusys.data.jquants_client, kabusys.data.news_collector, kabusys.data.pipeline, kabusys.data.schema, kabusys.data.quality, kabusys.data.audit）を参照してください。質問や追加のドキュメント生成が必要であれば教えてください。