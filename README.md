# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム（プロトタイプ）です。  
J-Quants API と DuckDB を用いたデータプラットフォーム、特徴量生成・研究モジュール、発注／監査向けのスキーマ群などを含みます。

主な設計方針：
- DuckDB をデータベース層に使用（冪等な INSERT / ON CONFLICT を採用）
- J-Quants API から株価・財務・市場カレンダーを取得（レート制御、リトライ、トークン自動リフレッシュ）
- RSS ベースのニュース収集（SSRF/XML BOM 対策、トラッキングパラメータ除去）
- 研究（factor / feature）モジュールは本番の発注 API にアクセスしない（安全設計）
- 品質チェック（欠損・スパイク・重複・日付不整合）を ETL の一部として実行

バージョン: 0.1.0

---

## 機能一覧

- 環境変数 / .env 自動読み込み（`.env` → `.env.local`、OS 環境変数優先）
- J-Quants API クライアント
  - 日足（OHLCV）取得、財務データ取得、マーケットカレンダー取得
  - レートリミット対応、リトライ、トークン自動リフレッシュ
  - DuckDB への冪等保存ユーティリティ（raw_prices / raw_financials / market_calendar 等）
- ETL パイプライン（差分更新・バックフィル対応）
  - run_daily_etl や個別 ETL（価格・財務・カレンダー）を提供
- スキーマ管理（DuckDB）
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義と初期化
- ニュース収集（RSS）
  - RSS 取得、前処理、raw_news への冪等保存、銘柄コード抽出
  - SSRF/サイズ/圧縮/XML 攻撃対策
- データ品質チェック
  - 欠損データ、スパイク、重複、日付不整合を検出（QualityIssue を返す）
- 研究用ユーティリティ
  - ファクター（momentum / volatility / value）計算
  - 将来リターン計算、IC（Spearman rank correlation）計算、ファクター統計サマリー
  - Zスコア正規化ユーティリティの提供
- 監査ログスキーマ（order_requests / executions / signal_events 等）
- カレンダー管理ユーティリティ（営業日判定、next/prev_trading_day、バッチ更新）

---

## 必要条件

- Python 3.10 以上（PEP 604 の union 演算子（X | Y）を使用しているため）
- pip, virtualenv 等
- 必須 Python パッケージ（最低限）:
  - duckdb
  - defusedxml

例:
pip install duckdb defusedxml

（プロジェクトに requirements.txt があればそれに従ってください）

---

## 環境変数（主要）

config.Settings により以下の環境変数を参照します。最低限必要な環境変数はアプリを動かすために設定してください。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション（発注用）のパスワード
- SLACK_BOT_TOKEN — 通知用 Slack Bot トークン
- SLACK_CHANNEL_ID — 通知先 Slack チャンネル ID

任意 / デフォルトあり:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（data/monitoring.db）
- KABUSYS_ENV — 環境 ("development" / "paper_trading" / "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG","INFO",...)（デフォルト: INFO）

自動環境読み込み:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）から `.env` → `.env.local` を読み込みます。
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用）。

簡単な .env 例:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順（ローカル）

1. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージのインストール
   - pip install duckdb defusedxml

   （必要に応じてその他ツールをインストール）

3. 環境変数設定
   - リポジトリルートに `.env` を作成するか、OS 環境変数で設定します。
   - 必須のトークン等（上記）を設定してください。

4. DuckDB スキーマ初期化
   - Python コマンドでスキーマを作成:
     - python -c "from kabusys.data import schema; schema.init_schema('data/kabusys.duckdb')"
   - これにより `data/kabusys.duckdb` が作成され、全テーブルが初期化されます。

---

## 使い方（サンプル）

以下は代表的な操作例です。各モジュールの関数は DuckDB の接続オブジェクトを受け取るパターンが多く、スクリプトやジョブに組み込みやすくなっています。

- 日次 ETL を走らせる（市場カレンダー・株価・財務をまとめて取得・品質チェック）
  - python -c "from kabusys.data import pipeline, schema; conn = schema.init_schema('data/kabusys.duckdb'); res = pipeline.run_daily_etl(conn); print(res.to_dict())"

- 個別 ETL ジョブ
  - run_prices_etl/run_financials_etl/run_calendar_etl を呼ぶ（conn, target_date 指定）

- ニュース収集ジョブ
  - from datetime import date
    from kabusys.data import news_collector, schema
    conn = schema.get_connection('data/kabusys.duckdb')
    # known_codes は銘柄コードセット（抽出時のフィルタ）
    results = news_collector.run_news_collection(conn, known_codes={'7203','6758'})
    print(results)

- 研究用ファクター計算
  - from datetime import date
    import duckdb
    from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
    conn = duckdb.connect('data/kabusys.duckdb')
    t = date(2024,1,31)
    mom = calc_momentum(conn, t)
    vol = calc_volatility(conn, t)
    val = calc_value(conn, t)
    fwd = calc_forward_returns(conn, t, horizons=[1,5,21])
    # 例: mom の "mom_1m" と fwd の "fwd_1d" で IC を計算
    ic = calc_ic(mom, fwd, factor_col='mom_1m', return_col='fwd_1d')
    print('IC:', ic)

- DuckDB 接続の取得
  - from kabusys.data import schema
    conn = schema.get_connection('data/kabusys.duckdb')

注意:
- J-Quants API 呼び出しはレート制限・リトライ・トークン更新が組み込まれています。大量リクエストを行う場合は注意してください。
- research モジュールは外部 API や実際の発注を行いません（安全設計）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                      — 環境変数 / 設定管理（.env ロード等）
- data/
  - __init__.py
  - jquants_client.py             — J-Quants API クライアント（取得 + 保存ユーティリティ）
  - news_collector.py             — RSS ニュース収集・保存
  - schema.py                     — DuckDB スキーマ定義 / init_schema
  - stats.py                      — 統計ユーティリティ（zscore_normalize 等）
  - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
  - features.py                   — 特徴量ユーティリティ公開（再エクスポート）
  - calendar_management.py        — カレンダー更新 / 営業日判定ユーティリティ
  - audit.py                      — 監査ログ（order_requests / executions 等）初期化
  - etl.py                        — ETL 公開インターフェース（ETLResult 再エクスポート）
  - quality.py                    — データ品質チェック
- research/
  - __init__.py                   — 研究用 API のエクスポート
  - feature_exploration.py        — 将来リターン、IC、統計サマリー等
  - factor_research.py            — momentum / volatility / value などのファクター計算
- strategy/
  - __init__.py                   — 戦略関連（未実装/拡張箇所）
- execution/
  - __init__.py                   — 発注・証券会社連携（未実装/拡張箇所）
- monitoring/
  - __init__.py                   — 監視モジュール（未実装/拡張箇所）

（実際のリポジトリにはさらに README・docs・ツール群がある想定です）

---

## 開発上の注意点 / 補足

- 型ヒントや新しい記法（X | Y）を利用しているため Python 3.10 以上を想定しています。
- DuckDB の SQL 構文の違いやバージョン依存（外部キーの ON DELETE 制約や一部インデックスの挙動）に注意してください（コード内に対応コメントあり）。
- RSS パーサーでは defusedxml を利用して XML の安全性を確保しています。
- 自動環境読み込みはプロジェクトルート検出 (.git / pyproject.toml) を行うため、テスト時などに無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使用してください。
- 本リポジトリはサンプル/プロトタイプの実装を想定しており、実際の本番運用時には追加のエラーハンドリング、セキュリティ監査、テスト、監視が必要です。

---

必要があれば、README に CI / デプロイ手順やより具体的なコード例（strategy の使い方、kabu API 発注フロー、Slack 通知の使い方）を追記できます。どの部分を詳しく記載しますか？