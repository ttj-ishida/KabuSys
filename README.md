# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ。  
J-Quants からのデータ収集、DuckDB によるデータ格納、ETL パイプライン、データ品質チェック、特徴量計算（リサーチ用ユーティリティ）などを提供します。

※ 本リポジトリはライブラリ実装の抜粋を含みます。発注や取引に直接接続するコード（本番注文処理等）は分離される設計です。

---

## 主な特徴

- J-Quants API クライアント
  - 日次株価（OHLCV）、財務データ、JPX カレンダーの取得（ページネーション対応）
  - レートリミット制御、リトライ、401 時のトークン自動リフレッシュ
  - 取得データの fetched_at を記録し look-ahead bias を抑制

- データレイヤ（DuckDB）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
  - 冪等的な保存（ON CONFLICT DO UPDATE / DO NOTHING）を実現

- ETL パイプライン
  - 差分更新（最終取得日からの差分フェッチとバックフィル）
  - 市場カレンダー先読み、品質チェック（欠損・重複・スパイク・日付不整合）

- ニュース収集
  - RSS フィードから記事取得、正規化、DB 保存、銘柄コード抽出
  - SSRF / XML 攻撃対策、応答サイズ制限などセキュリティ考慮

- リサーチ用ユーティリティ
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
  - Z スコア正規化（クロスセクション）

- データ品質・監査
  - 品質チェックモジュール（quality）で多面的な検査を実行
  - 監査ログ用スキーマ（audit）でシグナル → 発注 → 約定のトレーサビリティ確保

---

## 動作要件

- Python 3.10 以上（typing の | 演算子等を使用）
- 主要依存ライブラリ:
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィードなど）を行う場合は外部接続が必要

（依存管理はプロジェクト側で requirements.txt / pyproject.toml を用意してください）

---

## セットアップ

1. Python と依存パッケージをインストール

   例（pip）:
   ```
   python -m pip install duckdb defusedxml
   ```

2. 環境変数を設定（.env または OS 環境変数）
   - 自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（CWD 依存しない探索）。
   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

   必須の環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants の refresh token
   - KABU_API_PASSWORD: kabuステーション API 用パスワード（発注を使用する場合）
   - SLACK_BOT_TOKEN: Slack 通知を使う場合
   - SLACK_CHANNEL_ID: Slack 通知先チャネルID

   任意（デフォルト値あり）:
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）

   `.env` の書式は Bash 形式に準拠します。コメント、クォート、export プレフィックス等をサポートします。

3. DuckDB スキーマ初期化

   Python スクリプト例:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   ```

   監査ログ専用 DB を初期化する場合:
   ```python
   from kabusys.data import audit
   conn = audit.init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（代表的な API）

- 日次 ETL を実行する（市場カレンダー取得、差分取得、品質チェックを実行）

  ```python
  from datetime import date
  import kabusys
  from kabusys.data import schema, pipeline

  # DB 初期化（まだのとき）
  conn = schema.init_schema("data/kabusys.duckdb")

  # run_daily_etl はターゲット日を受け取り ETLResult を返す
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- J-Quants から日足をフェッチして保存する（個別で使いたい場合）

  ```python
  from kabusys.data import jquants_client as jq
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")

  # トークンは settings.jquants_refresh_token を用いる（環境変数）
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  ```

- ニュース収集ジョブ（RSS → raw_news、news_symbols への紐付け）

  ```python
  from kabusys.data import news_collector as nc
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")

  # known_codes を渡すと本文中の4桁銘柄コードを抽出して紐付けする
  known_codes = {"7203", "6758", "9984"}  # 例
  stats = nc.run_news_collection(conn, sources=None, known_codes=known_codes)
  print(stats)  # {source_name: saved_count}
  ```

- リサーチ（ファクター計算 / IC / サマリ）

  ```python
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, zscore_normalize
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  tgt = date(2024, 1, 31)

  mom = calc_momentum(conn, tgt)
  vol = calc_volatility(conn, tgt)
  val = calc_value(conn, tgt)

  fwd = calc_forward_returns(conn, tgt, horizons=[1,5,21])
  # 例: mom の mom_1m と fwd の fwd_1d の IC を計算
  ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
  summary = factor_summary(mom, ["mom_1m", "mom_3m", "ma200_dev"])
  normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
  ```

- 品質チェック（ETL 後に自動で実行されますが単体でも可）

  ```python
  from kabusys.data import quality
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  issues = quality.run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)
  ```

---

## 主要モジュール一覧（抜粋）

- kabusys.config: 環境変数 / 設定管理（自動 .env ロード、必須キー取得）
- kabusys.data.jquants_client: J-Quants API クライアント（fetch / save 関数）
- kabusys.data.schema: DuckDB スキーマ定義と init_schema()
- kabusys.data.pipeline: ETL パイプライン（run_daily_etl 等）
- kabusys.data.news_collector: RSS 取得・前処理・保存ロジック
- kabusys.data.quality: データ品質チェック
- kabusys.data.stats: Z スコア正規化など統計ユーティリティ
- kabusys.research: factor 計算・exploration ユーティリティ
- kabusys.data.audit: 監査ログ（signal / order_request / executions）

---

## ディレクトリ構成

（主要ファイルを抜粋した構成）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/              # 発注関連（プレースホルダ）
      - __init__.py
    - strategy/               # 戦略関連（プレースホルダ）
      - __init__.py
    - monitoring/             # 監視・メトリクス（プレースホルダ）
      - __init__.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - stats.py
      - pipeline.py
      - features.py
      - calendar_management.py
      - audit.py
      - etl.py
      - quality.py
    - research/
      - __init__.py
      - feature_exploration.py
      - factor_research.py

---

## 環境変数（要約）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意 / デフォルト:
- KABUSYS_ENV (development | paper_trading | live) — default: development
- LOG_LEVEL — default: INFO
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると .env の自動読み込みを無効化

.env.example を参考に .env を作成してください。Settings のプロパティは未設定時に例外を投げるものがあります（必須キー）。

---

## 注意事項 / トラブルシューティング

- DuckDB のバージョン差分により一部の制約やインデックス挙動が異なる場合があります（README 内の DDL は DuckDB 1.5 系に合わせた注記あり）。
- ネットワーク周り（RSS / J-Quants）でのエラーはログに詳細を出す設計です。ログレベルを DEBUG に上げると内部処理が追いやすくなります。
- ETL は各ステップでエラーハンドリングを行い、可能な限り他ステップを継続します。致命的エラーは ETLResult.errors に蓄積されます。
- RSS の取得は SSRF 対策・サイズ制限・XML 攻撃対策を組み込んでいますが、運用で扱う RSS ソースは事前に信頼できるものを選んでください。

---

## ライセンス・貢献

（リポジトリに合わせて適切な LICENSE を追加してください）

貢献・バグ報告は Pull Request / Issue を通じて受け付けます。重要な変更（テーブル定義、スキーマ変更等）は下位互換性に注意して行ってください。

---

以上。README に記載してほしい追加情報（例: 実行スクリプト、CI 設定、より詳細な .env.example）や、英語版 README を希望する場合は知らせてください。