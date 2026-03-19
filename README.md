# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ（KabuSys）。  
DuckDB をデータレイクとして用い、J-Quants API からマーケットデータや財務データを取得して ETL->品質チェック->特徴量生成->研究・戦略評価へつなげることを目的としたモジュール群を含みます。

主な設計方針
- DuckDB を中心とした3層（Raw / Processed / Feature）データ設計
- J-Quants API のレート制御・リトライ・トークン自動リフレッシュ対応
- ETL は差分更新（バックフィル）を基本とし、冪等保存（ON CONFLICT）を行う
- 研究(Research)用モジュールは本番 API や発注にはアクセスしない（安全）
- ニュース収集は SSRF 対策・サイズ制限・トラッキング除去などを実施

## 機能一覧
- 環境変数/設定管理（kabusys.config）
  - .env 自動読み込み（プロジェクトルート検出、優先順位: OS > .env.local > .env）
  - 必須設定取得とバリデーション（環境: development / paper_trading / live、ログレベル等）
- データ取得・保存（kabusys.data）
  - J-Quants クライアント（jquants_client）：日次株価、財務データ、マーケットカレンダー取得
  - 保存ユーティリティ（冪等保存: ON CONFLICT）
  - DuckDB スキーマ定義と初期化（data.schema）
  - ETL パイプライン（data.pipeline）：差分取得・バックフィル・品質チェックの統合
  - ニュース収集（data.news_collector）：RSS 取得、正規化、抜粋、DB保存、銘柄抽出
  - カレンダー管理（data.calendar_management）：営業日判定、next/prev_trading_day 等
  - 品質チェック（data.quality）：欠損・スパイク・重複・日付不整合検出
  - 監査ログスキーマ（data.audit）：信号→発注→約定のトレーサビリティ
  - 統計ユーティリティ（data.stats）：Zスコア正規化等
- 研究用モジュール（kabusys.research）
  - factor_research：モメンタム／ボラティリティ／バリュー等の定量ファクター計算
  - feature_exploration：将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
  - data.stats の zscore_normalize を再エクスポート
- 発注・戦略・モニタリングのための骨組み（kabusys.strategy, kabusys.execution, kabusys.monitoring）
  - パッケージ構成上の名前空間を確保（実装は別モジュールで拡張想定）

## セットアップ手順

前提
- Python 3.10 以上（`Path | None` 等の構文を利用しているため）
- Git（.git をプロジェクトルート判定に使用）

推奨手順（Unix/macOS、Windows でも同様）
1. 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

2. 必要パッケージをインストール
   最低限必要なもの:
   - duckdb
   - defusedxml
   例:
   ```bash
   pip install duckdb defusedxml
   ```
   （プロジェクトに requirements.txt がある場合はそれを使ってください）

3. 環境変数の準備
   プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動読み込みを無効化できます）。

   必須環境変数（主要なもの）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD     : kabuステーション API パスワード（発注機能を使う場合）
   - SLACK_BOT_TOKEN       : Slack 通知を使う場合の Bot トークン
   - SLACK_CHANNEL_ID      : Slack 通知を送るチャンネル ID
   任意（デフォルトあり）
   - KABUSYS_ENV           : development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL             : DEBUG/INFO/...（デフォルト: INFO）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 で .env の自動読み込みを無効化
   - DUCKDB_PATH, SQLITE_PATH : DB ファイルの保存先（デフォルトは data/kabusys.duckdb など）

   .env の簡単な例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   DUCKDB_PATH=data/kabusys.duckdb
   ```

4. DuckDB スキーマ初期化
   Python REPL またはスクリプトで以下を実行してデータベースとテーブルを作成します:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   ```
   監査ログ専用 DB を初期化する場合:
   ```python
   from kabusys.data import audit
   conn = audit.init_audit_db("data/kabusys_audit.duckdb")
   ```

## 使い方（主な例）

以下は典型的なワークフローのサンプルコードです。実運用ではロギング設定・エラーハンドリングを適切に行ってください。

1. 日次 ETL（株価・財務・カレンダー取得、品質チェック）
   ```python
   from datetime import date
   import duckdb
   from kabusys.data import pipeline, schema

   conn = schema.init_schema("data/kabusys.duckdb")  # 初回のみ。既存なら get_connection
   result = pipeline.run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

2. カレンダー更新バッチ
   ```python
   from kabusys.data import calendar_management, schema
   conn = schema.get_connection("data/kabusys.duckdb")
   saved = calendar_management.calendar_update_job(conn)
   print("saved:", saved)
   ```

3. ニュース収集ジョブ（既存の銘柄セット known_codes を渡して銘柄紐付け）
   ```python
   from kabusys.data.news_collector import run_news_collection
   from kabusys.data import schema
   conn = schema.get_connection("data/kabusys.duckdb")
   known_codes = {"7203", "6758", "9984"}  # 例
   results = run_news_collection(conn, known_codes=known_codes)
   print(results)
   ```

4. 研究・ファクター計算例
   ```python
   from datetime import date
   from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
   from kabusys.data import schema, stats

   conn = schema.get_connection("data/kabusys.duckdb")
   target = date(2024, 1, 31)
   mom = calc_momentum(conn, target)
   vol = calc_volatility(conn, target)
   val = calc_value(conn, target)
   fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
   # あるファクターと fwd_1d のICを計算
   ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
   print("IC:", ic)
   # Zスコア正規化
   normalized = stats.zscore_normalize(mom, ["mom_1m", "ma200_dev"])
   ```

5. J-Quants API を直接利用してデータ取得・保存
   ```python
   from kabusys.data import jquants_client as jq
   import duckdb
   conn = duckdb.connect("data/kabusys.duckdb")
   records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
   saved = jq.save_daily_quotes(conn, records)
   print("saved:", saved)
   ```

## 主要モジュールとディレクトリ構成

（パッケージルート: src/kabusys）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・設定管理（.env 自動読み込み、必須チェック）
  - data/
    - __init__.py
    - jquants_client.py : J-Quants API クライアント（取得・保存・認証・レート制御）
    - news_collector.py : RSS 収集・正規化・DB保存・銘柄抽出
    - schema.py         : DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py       : ETL パイプライン（差分更新・品質チェック）
    - features.py       : 特徴量関連の公開 API（zscore_normalize を再エクスポート）
    - calendar_management.py : マーケットカレンダー管理（営業日判定等）
    - audit.py          : 監査ログ（signal/order/execution）スキーマ
    - etl.py            : ETLResult 等の公開インターフェース
    - quality.py        : データ品質チェック
    - stats.py          : 統計ユーティリティ（zscore_normalize）
  - research/
    - __init__.py
    - factor_research.py    : Momentum / Volatility / Value のファクター計算
    - feature_exploration.py: 将来リターン計算・IC・統計サマリー
  - strategy/    (名前空間: 戦略ロジックを配置する想定)
  - execution/   (名前空間: 発注・ブローカー連携を配置する想定)
  - monitoring/  (名前空間: モニタリング関連を配置する想定)

## 環境変数（まとめ）
- 必須
  - JQUANTS_REFRESH_TOKEN
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
  - KABU_API_PASSWORD (発注機能を使う場合)
- 推奨/任意
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - LOG_LEVEL (DEBUG|INFO|...) — デフォルト: INFO
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — デフォルト: data/monitoring.db
  - KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 をセットすると .env 自動読み込みを無効化

## 開発上の注意点 / 補足
- research モジュールは本番アカウントや発注 API を呼ばない設計です。研究・検証時は安全に使えます。
- jquants_client は内部で固定間隔スロットリング（120 req/min）とリトライロジックを実装しています。大量リクエストを行う際は注意してください。
- news_collector は外部 RSS を扱うため SSRF、XML Bomb、巨大レスポンスといった攻撃に対する防御措置を講じていますが、運用時はソースの信頼性を考慮してください。
- DuckDB の SQL はパラメータバインド（?）を利用しています。直接クエリ文字列連結等は避けてください。
- audit スキーマは UTC タイムスタンプを前提としており、init_audit_schema 内で TimeZone を UTC に設定します。

---

問題の切り分けや README の拡張（例: 実行スケジュール例、Docker 化、CI 用のテスト手順、より詳細な API 使用例など）をご希望でしたら、その用途に合わせて追記します。