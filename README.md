# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（KabuSys）。データ取得・ETL、データ品質チェック、特徴量計算、ニュース収集、監査ログ/schema 管理などを提供します。

主に以下の用途を想定しています：
- J-Quants API からの市場データ取得と DuckDB への蓄積（差分更新）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ファクター（モメンタム・バリュー・ボラティリティ等）の計算と正規化
- RSS ベースのニュース収集と銘柄紐付け
- 監査ログ（発注→約定のトレーサビリティ）用スキーマ

---

## 主な機能

- 環境変数管理
  - `.env` / `.env.local` を自動読み込み（プロジェクトルート検出）
  - 必須設定の取得とバリデーション（settings オブジェクト）
- データ取得（J-Quants クライアント）
  - 株価日足（ページネーション対応）
  - 財務データ（四半期 BS/PL）
  - 市場カレンダー
  - レート制限（120 req/min）・リトライ・トークン自動リフレッシュ対応
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
  - 初期化ユーティリティ（init_schema / init_audit_db）
- ETL パイプライン
  - 差分取得・バックフィル（後出し修正吸収）
  - 品質チェック実行の組み込み（quality モジュール）
  - 日次 ETL の統合エントリ（run_daily_etl）
- データ品質チェック（quality）
  - 欠損、スパイク（前日比閾値）、重複、日付不整合の検出
- 研究用ユーティリティ（research）
  - モメンタム／ボラティリティ／バリュー計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
  - z-score 正規化ユーティリティの再公開
- ニュース収集（news_collector）
  - RSS フィードの安全な取得（SSRF・XML Bomb 対策）
  - URL 正規化・トラッキングパラメータ除去・記事ID生成（SHA-256）
  - raw_news / news_symbols への冪等保存
- 監査ログ（audit）
  - signal / order_request / executions の監査スキーマと初期化

---

## 動作要件（推奨）

- Python 3.10+（コード中での型注釈（|）等の利用に準拠）
- 推奨パッケージ（最低限）:
  - duckdb
  - defusedxml

requirements.txt がない場合は手動でインストールしてください:
```
pip install duckdb defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン／配置する
2. Python 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # Linux / macOS
   .venv\Scripts\activate      # Windows
   ```
3. 依存パッケージをインストール
   ```
   pip install duckdb defusedxml
   ```
   （プロジェクトで requirements.txt / poetry が用意されている場合はそちらを利用してください）
4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと、自動で読み込まれます（自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意/デフォルト:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマ初期化
   Python で実行例:
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)
   # 接続 conn を以降の処理に渡して使う
   ```

6. 監査ログ用 DB 初期化（必要に応じて）
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（主要例）

- 日次 ETL を実行する（最小例）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # target_date を指定可
  print(result.to_dict())
  ```

- J-Quants から株価を手動取得して保存する
  ```python
  from kabusys.data import jquants_client as jq
  from kabusys.data.schema import init_schema
  from kabusys.config import settings
  from datetime import date

  conn = init_schema(settings.duckdb_path)
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  print(f"saved: {saved}")
  ```

- 研究用: ファクター計算・IC 計算
  ```python
  import duckdb
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
  from kabusys.data.stats import zscore_normalize
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  target = date(2024, 1, 31)

  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)
  fwd = calc_forward_returns(conn, target, horizons=[1,5,21])

  # 例: mom_1m と fwd_1d の IC
  ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
  print("IC:", ic)

  # Z-score 正規化
  normalized = zscore_normalize(mom, ["mom_1m", "ma200_dev"])
  ```

- ニュース収集ジョブの実行例
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  known_codes = {"7203", "6758", "6501"}  # 既知の銘柄コードセット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- データ品質チェックを実行（個別）
  ```python
  from kabusys.data.quality import run_all_checks
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  issues = run_all_checks(conn)
  for i in issues:
      print(i)
  ```

---

## 主要モジュールとディレクトリ構成

（主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント（取得・保存）
    - news_collector.py        — RSS ニュース収集、正規化、保存
    - schema.py                — DuckDB スキーマ定義と init_schema
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - quality.py               — データ品質チェック
    - stats.py                 — z-score など統計ユーティリティ
    - calendar_management.py   — market_calendar 管理ユーティリティ
    - audit.py                 — 監査ログテーブル定義・初期化
    - features.py              — data.stats の公開ラッパ
    - etl.py                   — ETLResult の再エクスポート
  - research/
    - __init__.py
    - feature_exploration.py   — 将来リターン・IC・統計サマリー
    - factor_research.py       — momentum/value/volatility の計算
  - strategy/
    - __init__.py              — 戦略関連のエントリポイント（実装はここで拡張）
  - execution/
    - __init__.py              — 発注/約定処理用のエントリポイント（拡張）
  - monitoring/
    - __init__.py              — 監視 / メトリクス用（拡張）

簡易ツリー（抜粋）:
```
src/kabusys/
├─ config.py
├─ data/
│  ├─ jquants_client.py
│  ├─ news_collector.py
│  ├─ schema.py
│  ├─ pipeline.py
│  ├─ quality.py
│  └─ ...
├─ research/
│  ├─ feature_exploration.py
│  └─ factor_research.py
├─ strategy/
├─ execution/
└─ monitoring/
```

---

## 注意点 / 補足

- 環境変数自動読み込み
  - config.py はプロジェクトルート（.git または pyproject.toml を基準）を探して `.env` / `.env.local` を自動読み込みします。テスト等で無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants 認証
  - get_id_token() は refresh token を使用し id token を取得します。_request() は 401 を受けた場合に自動でリフレッシュして再試行します（一度のみ）。
- 安全対策
  - news_collector は SSRF 対策、XML パースの安全化（defusedxml）、レスポンスサイズ制限、トラッキングパラメータ除去など実運用上の安全措置を多数実装しています。
- DuckDB のバージョン差異
  - README 内のスキーマや外部キー/ON DELETE の挙動は DuckDB バージョンに依存する点があります。コメントにもある通り、現状の DuckDB バージョンで未サポートの機能は考慮されています（例: ON DELETE CASCADE 等は省略）。
- 本番発注について
  - このコードベースはデータ取得・研究・ETL を主目的としており、発注系（execution / strategy）の実装は拡張ポイントとして分離されています。実際の証券会社 API を使った自動発注を行う際は十分な安全対策（サンドボックス / paper_trading 設定 / 二重確認ログなど）を行ってください。

---

## 開発・拡張のヒント

- strategy / execution / monitoring パッケージは空の __init__.py が配置されており、ここに戦略・発注実装や監視ロジックを実装していく設計です。
- research モジュールは外部 API に触れず DuckDB の prices_daily / raw_financials のみ参照する方針なので、研究用スクリプトやバックテスト基盤の土台として利用しやすくなっています。
- ETL の差分ロジックやバックフィル日数は pipeline.run_daily_etl の引数で調整可能です。

---

必要があれば、README に含めるコマンドやスニペットをプロジェクト固有のセットアップ（Poetry / Docker / CI）向けにカスタマイズしたバージョンも作成します。どの形式（シンプルな手順・Docker Compose・CI ジョブなど）を優先したいか教えてください。