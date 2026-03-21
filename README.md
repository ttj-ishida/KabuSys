# KabuSys

バージョン: 0.1.0

KabuSys は日本株のデータ収集・前処理・特徴量生成・シグナル生成・監査までを一貫して扱う自動売買基盤（モジュール群）です。DuckDB をローカル DB として利用し、J-Quants API から市場データ・財務データ・カレンダーを取得、RSS からニュースを収集して特徴量と AI スコアを統合し、戦略的な売買シグナルを生成します。

主な設計方針
- ルックアヘッドバイアスを排除するため「target_date 時点の情報のみ」を使って計算
- DuckDB に対する操作は冪等（ON CONFLICT / 日付単位の置換）を意識
- 外部 API 呼び出しはレート制御・リトライ・トークン自動更新等を考慮
- テストしやすい設計（トークン注入や自動 env ロード停止フラグ等）

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
  - 必須環境変数のチェック（J-Quants / kabu / Slack 等）
- データ取得（J-Quants クライアント）
  - 株価日足（ページネーション対応・レート制御・リトライ・トークン自動更新）
  - 財務データ（四半期 BS/PL）
  - JPX マーケットカレンダー
  - データを DuckDB に冪等保存する save_* 関数群
- ETL パイプライン
  - 差分取得（最終取得日の追跡）とバックフィル
  - 日次 ETL（calendar → prices → financials → 品質チェック）
- スキーマ管理
  - DuckDB のテーブル定義・インデックス作成（init_schema）
  - Raw / Processed / Feature / Execution 層を定義
- ニュース収集
  - RSS フィード取得（SSRF 対策・gzip 上限・XML 脆弱性対策）
  - 記事正規化・ID（URL 正規化 + SHA256）生成・raw_news への冪等保存
  - 銘柄コード抽出と news_symbols への紐付け
- 特徴量（Research）
  - Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Spearman ρ）、ファクター統計サマリー
  - Z スコア正規化ユーティリティ
- 戦略（Strategy）
  - build_features: 生ファクターを正規化・フィルタ適用して features テーブルへ保存
  - generate_signals: features と ai_scores を統合して final_score を算出し BUY/SELL シグナルを生成、signals テーブルへ保存
  - Bear レジーム抑制、エグジット（ストップロス・スコア低下）判定など実装
- カレンダー管理（market_calendar 操作ヘルパ）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- 監査ログ（audit）
  - signal_events / order_requests / executions 等の監査テーブル定義（トレーサビリティ）

---

## 要件

- Python 3.10 以上（PEP 604 の `X | Y` アノテーション等を使用）
- 主要依存（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、外部 RSS）

実際のプロジェクトでは requirements.txt / pyproject.toml に依存が記載されている想定です。少なくとも上記パッケージはインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール（最低限）
   ```
   pip install duckdb defusedxml
   ```
   プロジェクトに pyproject.toml / requirements がある場合はそれに従ってください。開発用に pip install -e . でインストールできるように構成している場合もあります。

4. 環境変数設定
   - プロジェクトルートに `.env`（および任意で `.env.local`）を作成すると、自動で読み込まれます（ただし CWD ではなくパッケージファイルの位置からプロジェクトルートを探索します）。
   - 主な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD     : kabu ステーション API のパスワード
     - SLACK_BOT_TOKEN       : Slack Bot Token
     - SLACK_CHANNEL_ID      : 通知先 Slack チャンネル ID
   - 任意 / デフォルト
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
   - 自動 .env 読み込みを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. DuckDB スキーマ初期化
   - デフォルト DB パスを使う例:
     ```
     python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
     ```
   - メモリ DB:
     ```
     python -c "from kabusys.data.schema import init_schema; init_schema(':memory:')"
     ```

---

## 使い方（基本例）

以下は代表的な利用フローの簡単なコード例です。実行は Python スクリプトやバッチジョブから行います。

1. 設定参照
   ```python
   from kabusys.config import settings
   print(settings.jquants_refresh_token)
   ```

2. DB 接続とスキーマ初期化
   ```python
   from kabusys.data.schema import init_schema, get_connection
   conn = init_schema('data/kabusys.duckdb')  # スキーマ作成 + 接続
   # または既存 DB に接続:
   # conn = get_connection('data/kabusys.duckdb')
   ```

3. 日次 ETL 実行
   ```python
   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn)  # target_date を指定可能
   print(result.to_dict())
   ```

4. 特徴量ビルド（戦略用）
   ```python
   from kabusys.strategy import build_features
   from datetime import date
   count = build_features(conn, date.today())
   print("features upserted:", count)
   ```

5. シグナル生成
   ```python
   from kabusys.strategy import generate_signals
   from datetime import date
   total = generate_signals(conn, date.today(), threshold=0.6)
   print("signals generated:", total)
   ```

6. ニュース収集
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   known_codes = {'7203','6758', ...}  # 既知銘柄コードセット
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(results)
   ```

7. カレンダー夜間更新ジョブ
   ```python
   from kabusys.data.calendar_management import calendar_update_job
   saved = calendar_update_job(conn)
   print("saved calendar rows:", saved)
   ```

注意点
- run_daily_etl 等はネットワーク呼び出し（J-Quants）を行うため、認証情報とネットワーク接続が必要です。
- ETL の差分・バックフィル挙動や品質チェックは実装内の引数で調整できます。

---

## ディレクトリ構成（主要ファイル）

（パッケージルート: src/kabusys）

- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py        — J-Quants API クライアント（取得 + 保存）
  - schema.py                — DuckDB スキーマ定義・init_schema
  - pipeline.py              — ETL パイプライン（run_daily_etl 等）
  - news_collector.py        — RSS 収集 / 保存ロジック
  - calendar_management.py   — market_calendar ヘルパと更新ジョブ
  - features.py              — zscore_normalize の再エクスポート
  - stats.py                 — 統計ユーティリティ（z-score 等）
  - audit.py                 — 監査ログ用 DDL（signal_events 等）
  - quality.py               — （品質チェックモジュール想定、pipeline と連携）
- research/
  - __init__.py
  - factor_research.py       — momentum/volatility/value ファクター計算
  - feature_exploration.py   — 将来リターン・IC・統計サマリー等
- strategy/
  - __init__.py (build_features, generate_signals を公開)
  - feature_engineering.py   — features テーブル生成ロジック
  - signal_generator.py      — final_score 計算 / BUY・SELL シグナル生成
- execution/
  - __init__.py              — 発注 / execution 層モジュール群（将来的に実装）
- monitoring/
  - (監視用モジュールを想定してエクスポート用に確保)

---

## 実運用上の注意事項

- 本リポジトリの一部モジュールは実際の運用で十分な検証が必要です（特に注文周りや実取引接続）。
- データ取得は API レート制限やトークン管理、ネットワーク障害に対するリトライ設計を組み込んでいますが、実行頻度や同時実行数は運用方針に合わせて調整してください。
- 監査テーブル（audit）を整備してトレース可能にすることで、不正確な挙動の解析や問題発生時のフォールバックが容易になります。
- DuckDB ファイルはファイルロック挙動やバックアップ方針を検討してください（複数プロセスからの同時書き込みなど）。

---

## 参考（主な環境変数）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化

---

必要であれば、README にコマンド例（systemd / cron の定期実行例）、CI 用のテスト実行やローカル開発のための docker-compose 設定例、あるいは詳細な環境変数テンプレート（.env.example）を追加で作成します。どれを追加しますか？