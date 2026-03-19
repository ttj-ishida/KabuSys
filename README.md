# KabuSys

KabuSys は日本株向けの自動売買プラットフォームのライブラリ群です。データ取得（J-Quants）、ETL、データ品質チェック、特徴量生成、リサーチユーティリティ、ニュース収集、監査ログ等を備え、DuckDB をバックエンドにして運用・研究用途のワークフローを提供します。

--- 

## 主な特徴（機能一覧）

- 環境設定管理
  - .env / .env.local をプロジェクトルートから自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - 必須環境変数の取得ヘルパー（settings）

- データ取得・保存（J-Quants）
  - 株価日足（OHLCV）・財務データ・マーケットカレンダーの取得（ページネーション対応）
  - Rate limiting・リトライ・トークン自動リフレッシュ対応
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）

- ETL パイプライン
  - 差分更新（バックフィル対応）、市場カレンダー先読み、品質チェック統合
  - run_daily_etl による一括実行と ETL 結果オブジェクト（ETLResult）

- データスキーマ管理
  - DuckDB 用スキーマ初期化（raw / processed / feature / execution / audit 層）
  - 監査ログ（signal → order_request → executions）の初期化ユーティリティ

- データ品質チェック
  - 欠損データ、スパイク（急騰・急落）、重複、日付不整合チェック（QualityIssue を返す）

- ニュース収集
  - RSS フィード取得・前処理・記事ID生成（URL 正規化 + SHA-256）
  - SSRF 防止、受信サイズ上限、XML 安全パーサ利用（defusedxml）
  - raw_news / news_symbols への冪等保存

- リサーチ / ファクター計算
  - モメンタム / ボラティリティ / バリューなどの定量ファクター計算（DuckDB 上の prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Spearman ρ）計算、ファクター統計サマリー
  - Zスコア正規化ユーティリティの提供

- その他
  - 市場カレンダー管理（営業日判定、next/prev trading day、期間内営業日の取得）
  - 監視・発注層のスキーマ（signal_queue, orders, trades, positions など）

---

## 動作環境 / 依存

- Python 3.10+
  - （モジュール内で | 型ヒント等を使用しているため Python 3.10 以上を想定しています）
- 必要パッケージ（例）
  - duckdb
  - defusedxml

インストール例（仮にパッケージ化されている場合）:
```
pip install -e .
pip install duckdb defusedxml
```
あるいは最低限:
```
pip install duckdb defusedxml
```

---

## 環境変数（主なもの）

Settings クラスは環境変数から値を取得します。必須のものは _require により未設定時に例外を出します。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード（発注系を利用する場合）
- SLACK_BOT_TOKEN — Slack 通知を使う場合
- SLACK_CHANNEL_ID — Slack 通知先チャンネル

任意 / デフォルトあり:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/...（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB 等の SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" を設定すると .env 自動ロードを無効化

プロジェクトルートの .env / .env.local が自動で読み込まれます（読み込み順: OS 環境 > .env.local > .env）。読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate (または Windows の場合 .venv\Scripts\activate)
3. 依存をインストール
   - pip install duckdb defusedxml
   - （パッケージ化されている場合は pip install -e .）
4. 環境変数を用意
   - プロジェクトルートに .env（.env.example を参考に）を配置
   - 必須トークン等を設定
5. DuckDB スキーマ初期化
   - Python REPL やスクリプトで以下を実行:
     ```
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - 監査ログ専用 DB を使う場合:
     ```
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")
     ```

---

## 使い方（主要な例）

- DuckDB 接続と ETL 実行（日次 ETL）
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- J-Quants からデータを直接取得して保存
  ```python
  import duckdb
  from kabusys.data import jquants_client as jq

  conn = duckdb.connect("data/kabusys.duckdb")
  # トークンは settings.jquants_refresh_token を利用
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  print("saved", saved)
  ```

- ニュース収集ジョブ
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 事前に管理する有効銘柄コードセット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- リサーチ／ファクター計算例
  ```python
  from datetime import date
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  target = date(2024, 1, 31)

  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)

  fwd = calc_forward_returns(conn, target, horizons=[1,5,21])

  # 例: mom のカラム 'mom_1m' と fwd の 'fwd_1d' で IC を計算
  ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
  print("IC:", ic)
  ```

- データ品質チェック
  ```python
  from kabusys.data.quality import run_all_checks
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  issues = run_all_checks(conn, target_date=date.today())
  for i in issues:
      print(i)
  ```

---

## ディレクトリ構成

（主要ファイル・モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント & 保存ユーティリティ
    - news_collector.py      — RSS ニュース収集／保存
    - schema.py              — DuckDB スキーマ定義と init_schema
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - features.py            — 特徴量インターフェース
    - calendar_management.py — カレンダー管理ユーティリティ
    - quality.py             — データ品質チェック
    - audit.py               — 監査ログ（order/signals/executions）スキーマ
    - etl.py                 — ETL 公開インターフェース（ETLResult 再エクスポート）
  - research/
    - __init__.py
    - feature_exploration.py — 将来リターン / IC / ファクターサマリ
    - factor_research.py     — momentum, volatility, value の計算
  - strategy/                 — 戦略層（未実装のエントリ）
  - execution/                — 発注／実行層（未実装のエントリ）
  - monitoring/               — 監視系（プレースホルダ）

---

## ログ・デバッグ

- LOG_LEVEL 環境変数でログレベルを制御できます（DEBUG/INFO/...）。
- ETL やデータ取得処理は例外をキャッチしてログに出力します。細かい動作を知りたい場合は LOG_LEVEL=DEBUG を設定してください。

---

## 注意事項 / 設計上のポイント

- DuckDB の INSERT 文で冪等性（ON CONFLICT ... DO UPDATE / DO NOTHING）を使用しています。スキーマ設計時の制約（DuckDB のバージョン差異）に注意してください。
- ニュース収集は SSRF や XML 攻撃を考慮した安全設計になっていますが、外部フィードを運用する際はホワイトリスト運用が望ましいです。
- J-Quants のレート制限（120 req/min）をモジュールで制御していますが、運用上の負荷設計は別途検討してください。
- 本リポジトリには発注処理の実装（kabuステーション連携等）が含まれる可能性があるため、本番口座で実行する場合は十分なテストと安全措置（paper_trading モードの活用など）を行ってください。

---

README の内容はコードベースの現状に基づいています。追加の実行スクリプトや CLI、CI 設定がある場合はそれらに合わせて README を拡張してください。必要であればサンプル .env.example のテンプレートも作成できます。