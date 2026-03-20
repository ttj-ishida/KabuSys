# KabuSys

日本株向け自動売買基盤ライブラリ（KabuSys）。  
データ収集（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、監査ログ、マーケットカレンダー管理などを備えたモジュール群を提供します。

---

## 概要

KabuSys は以下の目的で設計された Python モジュール群です。

- J-Quants API から株価・財務・マーケットカレンダーを取得して DuckDB に蓄積する ETL パイプライン
- 研究フェーズで計算した生ファクターを正規化して features テーブルへ保存する特徴量エンジニアリング
- 正規化済みファクターと AI スコアを統合して売買シグナルを生成する戦略ロジック
- RSS からニュースを収集・前処理して DB に保存し、銘柄紐付けするニュース収集器
- マーケットカレンダー管理・判定ユーティリティ、監査ログテーブル定義、発注/約定/ポジションのスキーマなど
- DuckDB を中心とした軽量で冪等性のあるデータ保存処理

設計上のポイント:
- ルックアヘッドバイアスを避けるため、すべて target_date 時点またはそれ以前の情報だけを利用
- DuckDB を用いたスキーマとトランザクションによる原子性
- API レート制御、リトライ、トークン自動リフレッシュ等を備えた J-Quants クライアント
- XML/HTTP/SSRF・DoS 等のセキュリティ対策（ニュース収集）

---

## 主な機能一覧

- データ取得・保存
  - J-Quants クライアント: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への冪等保存関数: save_daily_quotes, save_financial_statements, save_market_calendar
- ETL
  - 差分更新ロジック（バックフィル対応）を持つ run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - 品質チェック呼び出し（quality モジュール連携）
- 特徴量（Feature）処理
  - research 層で計算した raw factor を正規化して features テーブルへ保存（strategy.feature_engineering.build_features）
  - zscore_normalize（data.stats）
- シグナル生成
  - 正規化済みの特徴量 + ai_scores を統合して final_score を計算、BUY / SELL シグナルを作成（strategy.signal_generator.generate_signals）
  - Bear レジーム抑制、ストップロス等のエグジットロジック
- ニュース収集
  - RSS 取得、URL 正規化、記事 ID 生成、raw_news 保存、銘柄抽出・紐付け（data.news_collector）
- カレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day などのユーティリティ（data.calendar_management）
  - calendar_update_job による差分取得・保存
- スキーマ管理
  - DuckDB スキーマ初期化（init_schema）と接続ユーティリティ（data.schema）
- 監査ログ（audit）
  - signal_events, order_requests, executions 等の監査用テーブル定義

---

## セットアップ手順

推奨環境
- Python 3.10 以上（型記法に | を使用しているため）
- DuckDB を利用（ローカルファイルまたは :memory:）

最低依存パッケージ（プロジェクトに requirements.txt がない場合の例）:
- duckdb
- defusedxml

手順例:

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb defusedxml

   （プロジェクトに pyproject.toml / requirements.txt がある場合はそれに従ってください）

3. (任意) 開発出力インストール
   - pip install -e .

4. 環境変数の設定
   - KabuSys は .env/.env.local の自動ロード機能を備えています（プロジェクトルートに .git または pyproject.toml が存在する場合に有効）。
   - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須の環境変数（Settings で参照されるもの）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション API のパスワード
- SLACK_BOT_TOKEN       : Slack への通知に使う Bot トークン（プロジェクトで利用する場合）
- SLACK_CHANNEL_ID      : Slack チャンネル ID

任意 / デフォルト
- KABUSYS_ENV           : development / paper_trading / live（デフォルト: development）
- LOG_LEVEL             : DEBUG/INFO/...（デフォルト: INFO）
- KABUS_API_BASE_URL    : kabuAPI の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : SQLite path（監視系など、デフォルト: data/monitoring.db）

例: .env（プロジェクトルート）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（主要な API と実行例）

以下は基本的なワークフロー例です。実行前に必要な環境変数と DuckDB の初期化を行ってください。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ":memory:" を指定するとインメモリ DB
```

2) 日次 ETL（市場カレンダー・株価・財務の差分取得）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

3) 特徴量作成（features テーブルへ保存）
```python
from datetime import date
from kabusys.strategy import build_features
count = build_features(conn, target_date=date(2024, 1, 31))
print("features upserted:", count)
```

4) シグナル生成（signals テーブルへ保存）
```python
from kabusys.strategy import generate_signals
total = generate_signals(conn, target_date=date(2024, 1, 31))
print("signals written:", total)
```

5) ニュース収集ジョブ実行
```python
from kabusys.data.news_collector import run_news_collection
known_codes = {"7203", "6758", "6501"}  # 既知の銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # ソースごとの新規保存件数
```

6) カレンダー関連ユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date
print(is_trading_day(conn, date(2024, 1, 1)))
print(next_trading_day(conn, date(2024, 1, 1)))
```

ログ出力レベルや動作モード（paper/live）は環境変数 KABUSYS_ENV, LOG_LEVEL で制御します。

---

## よく使うモジュール一覧（エントリポイント）

- kabusys.config
  - settings: 環境変数を扱う Settings オブジェクト
  - 自動 .env ロード（.env -> .env.local、OS 環境変数保護）

- kabusys.data
  - schema.init_schema, get_connection
  - jquants_client: fetch_* / save_* / get_id_token
  - pipeline.run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - news_collector.run_news_collection
  - calendar_management: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
  - stats.zscore_normalize

- kabusys.research
  - calc_momentum, calc_volatility, calc_value
  - calc_forward_returns, calc_ic, factor_summary, rank

- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold, weights)

---

## ディレクトリ構成

プロジェクトの主要ファイル / モジュール（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                        — 環境変数/設定管理
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（fetch/save）
    - news_collector.py              — RSS ニュース収集・前処理・保存
    - schema.py                      — DuckDB スキーマ定義と init_schema
    - pipeline.py                    — ETL パイプライン（差分取得・保存・品質チェック）
    - stats.py                       — zscore_normalize 等の統計ユーティリティ
    - calendar_management.py         — マーケットカレンダー管理・判定
    - features.py                    — data.stats の再エクスポート
    - audit.py                       — 監査ログ スキーマ（signal_events, order_requests, executions）
    - execution/                      — （空パッケージ／発注周りの拡張用）
  - research/
    - __init__.py
    - factor_research.py             — momentum/value/volatility の計算
    - feature_exploration.py         — 将来リターン/IC/統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py         — features テーブル構築（正規化・フィルタ）
    - signal_generator.py            — final_score 計算と signals の作成
  - execution/                        — 実行層（発注/ブローカー連携）用拡張ポイント
  - monitoring/                       — 監視・メトリクス用の拡張ポイント

（上記は現状の実装ファイルの抜粋。将来的に execution/monitoring の具象実装を追加可能）

---

## 注意事項 / 運用上のヒント

- 環境変数の自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）に依存します。テストや CI で自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のファイルはデフォルトで data/kabusys.duckdb に作成されます。init_schema は親ディレクトリを自動作成します。
- J-Quants の API レート制限（120 req/min）やリトライポリシーを jquants_client が内部で管理しますが、大量バッチや並列処理を行う場合は運用側でも配慮してください。
- ニュース収集では外部 URL を扱うため、SSRF 対策・受信サイズ制限・gzip 解凍後のサイズ検査など多数の防御機構が入っています。RSS ソースを追加する際は既知の安全な配信元のみを登録してください。
- シグナルから実際の発注・ブローカー連携は execution 層で実装する想定です。generate_signals は signals テーブルまでを書き込む責務に留め、発注は別層へ委任してください（設計分離）。

---

## 貢献 / 拡張ポイント

- execution パッケージ: 実際のブローカー API（kabuステーション）と接続する実装を追加
- monitoring: ETL・戦略・発注のメトリクス・アラート実装
- quality: data.pipeline が参照する品質チェック群の拡充
- docs: StrategyModel.md / DataPlatform.md 等の設計ドキュメントとの整合性チェック

---

必要であれば、README に含めるサンプル .env.example、より詳細なデプロイ手順（systemd / cron / GitHub Actions など）や運用手順（バックアップ、マイグレーション、テスト戦略）も作成できます。どの情報を追加しますか？