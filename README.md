# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（ミニマル実装）。  
DuckDB をデータ層として利用し、データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、監査ログ等のコンポーネントを提供します。

---

## 主な特徴（機能一覧）

- データ取得・保存
  - J-Quants API クライアント（ページネーション、リトライ、トークン自動リフレッシュ、レート制御）
  - raw_prices / raw_financials / market_calendar 等を DuckDB に冪等保存
- ETL パイプライン
  - 差分更新（最終取得日からの差分取得、バックフィル）
  - 日次 ETL（カレンダー→株価→財務→品質チェック）
- データスキーマ管理
  - DuckDB のスキーマ初期化（raw / processed / feature / execution 層）
- 研究用ファクター計算
  - Momentum / Volatility / Value 等のファクターを prices_daily / raw_financials から計算
  - Zスコア正規化ユーティリティ
- 特徴量（feature）構築
  - 研究で算出した生ファクターを正規化・ユニバースフィルタを通して `features` テーブルへ保存
- シグナル生成
  - features + ai_scores を統合し final_score を計算、BUY / SELL シグナルを生成して `signals` に保存
  - Bear レジーム判定、エグジット（ストップロス・スコア低下）ロジック含む
- ニュース収集
  - RSS フィード取得、SSRF/サイズ/XML攻撃対策、記事の正規化と DuckDB への冪等保存
  - 記事から銘柄コード抽出・news_symbols への紐付け
- 監査・トレーサビリティ（監査テーブル群）
  - signal → order_request → executions の追跡を行うテーブル定義

---

## セットアップ手順

前提:
- Python 3.9+（型ヒントに Union 表記等を使用）
- DuckDB を利用（Python パッケージ duckdb）
- XML 安全パーサ（defusedxml）

1. リポジトリをクローン / コピー
   - 例: git clone <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # macOS / Linux
   - .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトに setup.py / pyproject.toml があれば pip install -e .）

4. 環境変数の設定
   - KabuSys の設定は環境変数または .env ファイルから自動読み込みされます（プロジェクトルートは .git または pyproject.toml を基準に探索）。
   - 自動読み込みを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須環境変数（Settings から抜粋）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション等の API パスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャネル ID（必須）

任意（デフォルト値あり）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

例 (.env)
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（クイックスタート）

1. DuckDB スキーマ初期化
```
python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
```
- ":memory:" を渡すとインメモリ DB を使用します。

2. 日次 ETL の実行（J-Quants からデータ取得 → 保存）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema('data/kabusys.duckdb')
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3. 特徴量の構築（research で計算した生ファクターを正規化して features へ保存）
```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features

conn = get_connection('data/kabusys.duckdb')
n = build_features(conn, target_date=date.today())
print(f"features upserted: {n}")
```

4. シグナル生成（features + ai_scores → signals）
```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import generate_signals

conn = get_connection('data/kabusys.duckdb')
count = generate_signals(conn, target_date=date.today())
print(f"generated signals: {count}")
```

5. ニュース収集ジョブ実行（RSS 取得 → raw_news / news_symbols へ保存）
```python
from kabusys.data.schema import get_connection
from kabusys.data.news_collector import run_news_collection

conn = get_connection('data/kabusys.duckdb')
# known_codes: 既知の銘柄コード集合を渡すと本文からコード抽出して紐付けを行う
res = run_news_collection(conn, sources=None, known_codes=set(['7203','6758']))
print(res)
```

ログは標準的な logging モジュールで出力されます。環境変数 LOG_LEVEL で制御してください。

---

## 主要なモジュール説明（概要）

- kabusys.config
  - 環境変数の読み込み・バリデーション。自動で .env / .env.local を読み込む仕組み。Settings オブジェクト経由で値を取得。

- kabusys.data.jquants_client
  - J-Quants API への安全なアクセス（レート制御、リトライ、トークン刷新）。
  - fetch_* / save_* 関数でデータ取得と DuckDB への冪等保存を提供。

- kabusys.data.schema
  - DuckDB のテーブル定義と初期化。init_schema() で全テーブルとインデックスを作成。

- kabusys.data.pipeline
  - run_daily_etl 等、日次 ETL のオーケストレーション。差分取得・バックフィル・品質チェックを実行。

- kabusys.research
  - ファクター計算（calc_momentum / calc_volatility / calc_value）および解析ユーティリティ（calc_forward_returns / calc_ic / factor_summary / rank）。

- kabusys.strategy.feature_engineering
  - 研究で得た生ファクターを統合・正規化・フィルタリングして features テーブルへ保存。

- kabusys.strategy.signal_generator
  - features と ai_scores を組み合わせ、最終スコアを計算して BUY / SELL シグナルを生成。SELL は保有ポジションに対するエグジット判定を含む。

- kabusys.data.news_collector
  - RSS フィードからニュースを取得し、前処理後に raw_news に冪等保存。SSRF/サイズ/XML 攻撃対策を備える。

- kabusys.data.audit
  - シグナル→注文→約定の監査ログ用テーブル群（監査/トレーサビリティ）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - stats.py
      - pipeline.py
      - calendar_management.py
      - audit.py
      - features.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
      - feature_engineering.py
      - signal_generator.py
    - execution/         (実装の骨組み。発注層の実装を想定)
    - monitoring/        (監視・モニタリング関連：DB/Slack等の連携想定)

---

## 注意点 / 設計上のポイント

- 冪等性
  - 保存処理は ON CONFLICT / DO UPDATE や INSERT ... DO NOTHING を用いて冪等に設計されています。複数回実行しても重複が残らないよう配慮されています。

- Look-ahead バイアス回避
  - 特徴量/シグナル生成は target_date 時点で利用可能な情報のみを使う設計です。取得時刻（fetched_at）を記録することでいつ情報が手に入ったかをトレースできます。

- セキュリティ
  - RSS 収集では SSRF 対策、受信サイズ制限、XML インジェクション対策（defusedxml）を実装。
  - J-Quants クライアントは 401 時の自動トークンリフレッシュを行います。

- 環境設定の自動読み込み
  - プロジェクトルートにある .env / .env.local を自動で読み込みます。テストや特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化できます。

---

## 貢献 / 拡張案

- execution 層のブローカー連携実装（kabu API / 他証券会社の適応）
- AI スコアの計算パイプライン（ai_scores テーブルへの投入）
- モニタリング / アラート（Slack 通知の実装）
- 品質チェックモジュールの拡張（quality モジュールを充実させる）
- 単体テスト、CI ワークフローの整備

---

追加で README に追記したい内容（例: API キー取得方法、サンプル .env.example、CI 実行方法、運用時の cron/スケジューリング例）があれば教えてください。必要に応じて README を拡張します。