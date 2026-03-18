# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ (KabuSys)。  
DuckDB をデータ層に用い、J-Quants からの時系列・財務データ取得、RSS ニュース収集、特徴量生成、品質チェック、監査ログなどの基盤機能を提供します。

---

## 概要

KabuSys は以下の目的で設計された Python パッケージです。

- J-Quants API からの時系列株価（OHLCV）・財務データ・マーケットカレンダー取得（レート制限・リトライ・トークン自動更新対応）
- DuckDB に対するスキーマ定義・冪等保存（ON CONFLICT を利用）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- RSS ニュース収集と記事 → 銘柄コードの紐付け（セキュリティ対策多数）
- 研究用のファクター計算（モメンタム・バリュー・ボラティリティ等）
- 統計ユーティリティ（Zスコア正規化、IC 計算 等）
- 監査ログ（シグナル → 発注 → 約定のトレース用スキーマ）

設計方針としては「DuckDB を中心に SQL + 軽量 Python 実装」「外部依存を最小限に」「ETL/保存は冪等」「研究コードが本番発注 API に影響しないこと」を重視しています。

---

## 主な機能一覧

- 環境設定管理（.env の自動読み込み / 必須設定の検証）
- DuckDB スキーマ定義・初期化（raw / processed / feature / execution / audit 層）
- J-Quants クライアント
  - レート制限（120 req/min）対応
  - 冪等性・リトライ・トークン自動更新
  - daily_quotes / financial_statements / trading_calendar の取得と DuckDB への保存
- ETL パイプライン
  - 差分取得、バックフィル、品質チェックの一括実行（run_daily_etl）
- ニュース収集
  - RSS 取得（SSRF 対策、gzip サイズ制限、XML セーフパーサ）
  - 記事IDは正規化URLの SHA256（先頭32文字）
  - raw_news / news_symbols への冪等保存
- データ品質チェック（欠損 / 重複 / スパイク / 日付不整合）
- 研究モジュール
  - ファクター計算: calc_momentum, calc_volatility, calc_value
  - 将来リターン計算: calc_forward_returns
  - IC（Spearman rank）計算: calc_ic
  - ファクター統計サマリー: factor_summary
  - Zスコア正規化: zscore_normalize
- 監査ログスキーマ（signal_events / order_requests / executions）

重要: 研究用関数やデータ取得モジュールは「発注 API にはアクセスしない」旨の設計になっています（取引実行部分は別モジュールで扱う想定）。

---

## 前提・動作環境

- Python 3.10 以上（型注釈に `|` 演算子を使用）
- 必須 Python パッケージ（例）
  - duckdb
  - defusedxml

簡単なインストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# またはプロジェクト配布であれば: pip install -e .
```

（プロジェクトをパッケージ化している場合は requirements.txt や pyproject.toml を利用してください。）

---

## 環境変数 / 設定

KabuSys は .env ファイル、もしくは OS 環境変数から設定を読み込みます（プロジェクトルートに .git または pyproject.toml がある場合のみ自動読み込み）。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な必須環境変数（Settings クラスに対応）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注等を行う場合）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）

任意・デフォルト値:
- KABUS_API_BASE_URL: kabuAPI の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB などに使う SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 動作モード（development, paper_trading, live。デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG, INFO, ...。デフォルト INFO）

例 .env (プロジェクトルート):
```
JQUANTS_REFRESH_TOKEN="xxxxx"
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C01234567"
DUCKDB_PATH="data/kabusys.duckdb"
KABUSYS_ENV=development
```

---

## セットアップ手順

1. Python 仮想環境作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール
   ```bash
   pip install duckdb defusedxml
   ```

3. 環境変数を用意（.env をプロジェクトルートに配置）
   - 必須: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
   - 任意: DUCKDB_PATH（デフォルトは data/kabusys.duckdb）

4. DuckDB スキーマ初期化
   - Python REPL やスクリプトから:
     ```python
     from kabusys.data import schema
     from kabusys.config import settings

     conn = schema.init_schema(settings.duckdb_path)
     ```
   - :memory: に初期化する場合:
     ```python
     conn = schema.init_schema(":memory:")
     ```

5. 監査ログスキーマを追加する（必要時）
   ```python
   from kabusys.data import audit
   # 既存 conn に監査スキーマを追加
   audit.init_audit_schema(conn, transactional=True)
   ```

---

## 基本的な使い方（例）

いくつか代表的な操作の利用例を示します。

- ETL（J-Quants から差分取得して DB に保存）
  ```python
  from datetime import date
  from kabusys.data import schema, pipeline
  from kabusys.config import settings

  conn = schema.init_schema(settings.duckdb_path)
  result = pipeline.run_daily_etl(conn)  # デフォルトで今日の ETL を実行
  print(result.to_dict())
  ```

- ニュース収集ジョブ（RSS）
  ```python
  from kabusys.data import news_collector, schema
  from kabusys.config import settings

  conn = schema.init_schema(settings.duckdb_path)
  # known_codes は銘柄抽出で使用する有効な銘柄コードの集合
  res = news_collector.run_news_collection(conn, known_codes={"7203","6758"})
  print(res)  # ソースごとの新規保存件数
  ```

- J-Quants API トークン取得（明示的に）
  ```python
  from kabusys.data import jquants_client as jq
  token = jq.get_id_token()  # settings.jquants_refresh_token を使用
  print(token)
  ```

- 研究用関数（ファクター計算）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data import schema
  from kabusys.research import calc_momentum, calc_forward_returns, calc_ic

  conn = schema.init_schema(":memory:")  # 実データがある DB を利用するのが通常
  target = date(2024, 1, 31)
  momentum = calc_momentum(conn, target)
  fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
  ic = calc_ic(momentum, fwd, factor_col="mom_1m", return_col="fwd_1d")
  print(ic)
  ```

- Zスコア正規化
  ```python
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(records, ["mom_1m", "mom_3m"])
  ```

---

## セキュリティ・運用上の注意

- J-Quants / kabu API の認証情報は厳重に保護してください。
- ニュース収集部は SSRF・XML Bomb 等を考慮した実装になっていますが、運用ネットワークのポリシーと合わせて確認してください。
- DuckDB ファイルのバックアップ・スナップショットは運用上推奨されます（特に監査ログや発注履歴を保存する場合）。
- KABUSYS_ENV が `live` のときは実際の発注処理（別モジュール）が有効になる可能性があるため、本番切替は慎重に行ってください。

---

## ディレクトリ構成

（主なファイル・モジュールのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                         # 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py               # J-Quants API クライアント（取得 + 保存）
      - news_collector.py               # RSS ニュース収集
      - schema.py                       # DuckDB スキーマ定義・init_schema
      - stats.py                        # 統計ユーティリティ（zscore_normalize）
      - pipeline.py                     # ETL パイプライン（run_daily_etl 等）
      - features.py                     # features 公開インターフェース
      - calendar_management.py          # 市場カレンダー管理
      - audit.py                        # 監査ログスキーマ / 初期化
      - etl.py                          # ETL 公開 API（ETLResult 再エクスポート）
      - quality.py                      # データ品質チェック
    - research/
      - __init__.py
      - feature_exploration.py          # 将来リターン / IC / summary / rank
      - factor_research.py              # momentum / volatility / value の計算
    - strategy/
      - __init__.py                     # 戦略関連のエントリポイント（未実装の余地あり）
    - execution/
      - __init__.py                     # 発注実行関連（実装場所）
    - monitoring/
      - __init__.py                     # 監視・メトリクス関連（入り口）
- pyproject.toml (想定)
- .env.example (推奨して用意)

---

## 開発・拡張メモ

- DuckDB の SQL を中心にデータ処理を行っており、高速な集計が可能です。大きなデータセットでは適切なインデックス（スキーマで定義済）を利用してください。
- ニュースの銘柄抽出は単純に 4 桁数字を検出して known_codes と照合する実装です。必要に応じて NLP や辞書ベースの前処理を追加してください。
- 発注・ブローカー連携部分は別モジュール（execution）を想定しています。実装時は監査ログ（audit）と密に連携し、idempotency（order_request_id）を確保してください。
- テストを容易にするため、jquants_client._urlopen や news_collector._urlopen、get_id_token の id_token 注入などはモック差し替えが容易に設計されています。

---

この README はコードベースに基づく簡易ドキュメントです。各モジュールの詳細はソースコード内のドキュメンテーション文字列（docstring）を参照してください。質問や利用例の追加が必要であれば教えてください。