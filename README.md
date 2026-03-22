# KabuSys

KabuSys は日本株向けの自動売買フレームワークです。データ収集（J-Quants 等）・ETL・ファクター計算・特徴量生成・シグナル生成・バックテスト・簡易ポートフォリオシミュレーションまでのワークフローを提供します。DuckDB をデータストアとして利用し、研究（research）と本番処理を分離した設計になっています。

主な用途:
- マーケットデータの差分取得と品質管理
- ファクター（Momentum / Value / Volatility / Liquidity 等）の計算
- ファクターの正規化・特徴量生成（features テーブル）
- AI スコア等と統合したシグナル生成（signals テーブル）
- 日次単位のバックテスト（ポートフォリオシミュレータ、評価指標）
- RSS ベースのニュース収集と銘柄紐付け

---

## 主な機能一覧

- データ取得 / 保存
  - J-Quants API クライアント（rate limit / retry / token refresh 対応）
  - 株価・財務・市場カレンダーの取得と DuckDB への冪等保存（ON CONFLICT）
- ETL パイプライン
  - 差分取得（最終取得日を元に自動算出）とバックフィル対応
  - 品質チェック（欠損・重複・スパイクなど）
- ニュース収集
  - RSS フィード取得、テキスト前処理、記事の保存、銘柄コード抽出
  - SSRF 対策・受信サイズ制限・XML 安全パーサ利用
- 研究（research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- 戦略（strategy）
  - 特徴量エンジニアリング（Zスコア正規化、ユニバースフィルタ、クリッピング）
  - シグナル生成（最終スコアの計算、Bear 相場抑制、BUY/SELL の作成）
- バックテスト（backtest）
  - インメモリ DuckDB コピーでの安全なバックテスト実行
  - ポートフォリオシミュレータ（スリッページ・手数料モデル、約定ロジック）
  - パフォーマンス評価指標（CAGR, Sharpe, Max Drawdown, Win Rate 等）
- スキーマ管理
  - DuckDB のスキーマ定義と初期化ユーティリティ（init_schema）

---

## 要件

- Python 3.10+
- 必須外部ライブラリ（一例）
  - duckdb
  - defusedxml

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# あるいは requirements.txt を用意していれば `pip install -r requirements.txt`
```

---

## セットアップ手順

1. リポジトリをクローンして作業環境を準備する（仮想環境推奨）。
2. 依存パッケージをインストール（上記参照）。
3. 環境変数を設定する（.env をプロジェクトルートに置くと自動読み込みされます）。

推奨される .env の例:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

- 自動ロード: `kabusys.config` はプロジェクトルートを .git または pyproject.toml を基準に検索し、`.env` / `.env.local` を自動で読み込みます。テスト等で自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 必須の環境変数:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID

4. DuckDB スキーマの初期化:
```python
from kabusys.data.schema import init_schema
init_schema("data/kabusys.duckdb")  # ":memory:" も可能
```
これにより必要なテーブルとインデックスが作成されます。

---

## 使い方（代表的な操作）

- Backtest（コマンドライン）
  ```bash
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --db data/kabusys.duckdb \
    --cash 10000000
  ```
  出力に CAGR / Sharpe 等のサマリが表示されます。

- DuckDB スキーマ初期化（スクリプトから）
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  conn.close()
  ```

- ETL（株価差分取得の例）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_prices_etl
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  # target_date は通常当日（市場営業日）
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  conn.close()
  ```

  run_prices_etl やその他 ETL 関数は id_token を注入可能でテストが容易です。

- 特徴量生成（features テーブルに書き込む）
  ```python
  import duckdb
  from datetime import date
  from kabusys.strategy import build_features

  conn = duckdb.connect("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2023, 12, 1))
  conn.close()
  ```

- シグナル生成
  ```python
  import duckdb
  from datetime import date
  from kabusys.strategy import generate_signals

  conn = duckdb.connect("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2023, 12, 1))
  conn.close()
  ```

- ニュース収集（RSS 取得 → DB 保存）
  ```python
  import duckdb
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = duckdb.connect("data/kabusys.duckdb")
  # known_codes を渡すとテキストから銘柄コード抽出して news_symbols を作成します
  known_codes = {"7203", "6758", "9432"}
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  conn.close()
  ```

- バックテスト API（プログラム的に実行）
  ```python
  from datetime import date
  from kabusys.backtest.engine import run_backtest
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  result = run_backtest(conn, start_date=date(2022,1,1), end_date=date(2022,12,31))
  # result.history / result.trades / result.metrics を参照
  conn.close()
  ```

---

## 主要モジュール（簡易参照）

- kabusys.config
  - 環境変数読み込み・検証（.env 自動ロード、必須値チェック）
- kabusys.data.jquants_client
  - J-Quants API クライアント（取得・保存ユーティリティ）
- kabusys.data.news_collector
  - RSS 取得、記事正規化、raw_news 保存、銘柄抽出
- kabusys.data.schema
  - DuckDB スキーマ定義と init_schema / get_connection
- kabusys.data.pipeline
  - ETL パイプライン（差分更新・品質チェック）
- kabusys.strategy.feature_engineering
  - ファクター正規化・ユニバースフィルタ・features テーブルへのUPSERT
- kabusys.strategy.signal_generator
  - final_score 計算、BUY/SELL シグナル生成、signals 書き込み
- kabusys.research.*
  - ファクター計算・将来リターン・IC・統計解析（研究用）
- kabusys.backtest
  - engine/run（バックテストループ）、simulator（約定・履歴管理）、metrics（評価指標）

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - pipeline.py
    - schema.py
    - stats.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - backtest/
    - __init__.py
    - engine.py
    - simulator.py
    - metrics.py
    - run.py
    - clock.py
  - execution/  (発注周りの実装・ラッパーを配置する想定)
  - monitoring/ (監視・アラート用モジュールを配置する想定)

---

## 注意事項・運用メモ

- 環境変数の自動ロードはプロジェクトルートを .git または pyproject.toml で判定します。配布パッケージ内などでプロジェクトルートが見つからない場合は自動読み込みはスキップされます。
- J-Quants API 呼び出しはレート制限（120 req/min）を守る設計です。大量取得や並列化には注意してください。
- features / signals / positions などは日付単位で「削除して挿入（置換）」する処理を行い、日付単位で冪等性を保証します。
- 本リポジトリには実際の発注（ブローカー接続）ロジックは含まれていません（execution 層は空です）。実運用で発注を行う場合は execution 層を実装し、Kabu API 等の認証情報と安全対策を十分検討してください。
- テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使って .env の自動読み込みを無効化すると再現性が高まります。

---

## 貢献・拡張

- execution 層の具体的なブローカ連携
- AI スコア算出ロジックの追加（ai_scores テーブルの生成）
- 品質チェック（kabusys.data.quality の実装拡張）
- CI 用のテスト・ワークフロー整備

---

README に書かれている使用例はコード内 API を想定したものです。実環境で運用する際は十分なロギング、エラーハンドリング、シークレット管理、テストを行ってください。質問や補足があれば具体的な利用シナリオ（例: バックテストの期間や ETL の運用方針）を教えてください。必要に応じて README を追記・調整します。