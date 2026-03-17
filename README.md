# KabuSys

日本株向け自動売買システムのコアライブラリ（KabuSys）。  
主にデータ収集・ETL、データ品質チェック、ニュース収集、マーケットカレンダー管理、監査ログ（トレーサビリティ）などの機能を提供します。戦略・発注実装は strategy / execution モジュールを通じて組み合わせる設計です。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要なデータ基盤と補助モジュールをまとめた Python パッケージです。主な目的は以下です。

- J-Quants API から株価・財務・市場カレンダーを取得して DuckDB に永続化する（冪等保存）
- RSS フィードからニュースを収集し正規化して保存、銘柄コードとの紐付けを行う
- ETL パイプライン（差分取得・バックフィル・品質チェック）を提供
- マーケットカレンダー（JPX）を管理し営業日判定や前後営業日の取得をサポート
- 監査ログ（signal → order_request → execution の一連のトレース）を DuckDB に記録
- 環境変数 / .env の自動読み込みと設定管理

設計上の特徴（抜粋）:
- API レート制限・リトライ・トークン自動リフレッシュ対策
- Look-ahead bias 防止のため fetched_at を UTC で記録
- SSRF 対策、受信バイト上限、XML の安全パースなどのセキュリティ対策
- DuckDB を用いた軽量で高速な組み込みデータベース

---

## 機能一覧

- 設定管理
  - .env ファイルまたは OS 環境変数から設定を読み込み（自動ロードを環境変数で無効化可能）
  - 必須キーの検証と便利なアクセス（kabusys.config.settings）
- データ取得（kabusys.data.jquants_client）
  - 日次株価（OHLCV）取得（ページネーション対応）
  - 財務データ（四半期 BS/PL）取得
  - JPX マーケットカレンダー取得
  - レート制限・リトライ・トークン自動リフレッシュ対応
  - DuckDB への冪等保存（ON CONFLICT ... DO UPDATE）
- ニュース収集（kabusys.data.news_collector）
  - RSS 収集、URL 正規化、記事ID（SHA-256）生成
  - SSRF/Zip/巨大レスポンス対策、defusedxml による安全なパース
  - DuckDB へのバルク挿入（INSERT ... RETURNING）と銘柄紐付け
- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
  - 差分更新・バックフィルの自動計算
  - 品質チェック（欠損・重複・スパイク・日付不整合）の実行
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定・次/前営業日の取得・期間内営業日の取得
  - 夜間バッチによるカレンダー差分更新ジョブ
- スキーマ管理（kabusys.data.schema）
  - DuckDB 用のスキーマ定義と初期化 API（init_schema / get_connection）
  - Raw / Processed / Feature / Execution 層のテーブルを定義
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等、監査に必要なテーブルと初期化 API
  - UTC タイムゾーン固定、トランザクション オプションあり
- データ品質チェック（kabusys.data.quality）
  - 各種チェックを実行して QualityIssue のリストを返却

---

## 必要要件

- Python 3.10 以上（typing の | 演算子などを使用）
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml

（プロジェクトでの実際の依存は環境に合わせて requirements.txt を用意してください）

---

## セットアップ手順

1. 仮想環境を作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. 必要なパッケージをインストール
   ```bash
   pip install duckdb defusedxml
   ```
   - 実際の配布では requirements.txt / pyproject.toml を用意して pip install -r requirements.txt や pip install . を行ってください。

3. 環境変数を設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（読み込みは .git または pyproject.toml を基準に決定）。
   - 自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主な環境変数（必須）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack のチャンネル ID（必須）

   任意 / デフォルトあり
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite (monitoring) のパス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/…（デフォルト: INFO）

   例 .env（テンプレート）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
   KABU_API_PASSWORD=your_kabu_api_password_here
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマ初期化
   - Python REPL やスクリプトから schema.init_schema を呼び出して DB を初期化します。

   例:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   # またはメモリDB
   # conn = schema.init_schema(":memory:")
   ```

5. 監査ログスキーマ初期化（必要な場合）
   ```python
   from kabusys.data import audit, schema
   conn = schema.init_schema("data/kabusys.duckdb")
   audit.init_audit_schema(conn, transactional=True)
   ```

---

## 使い方（主な API と実例）

※ 以下は簡単な利用例です。実運用ではログ設定・例外処理・スケジューラを組み合わせてください。

- 日次 ETL を実行する
  ```python
  from kabusys.data import schema, pipeline
  conn = schema.init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn)
  print(result.to_dict())
  ```

- J-Quants から日次株価を直接取得して保存する
  ```python
  from kabusys.data import jquants_client as jq
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  print(f"saved {saved}")
  ```

- RSS ニュース収集ジョブを動かす
  ```python
  from kabusys.data import news_collector as nc
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")
  results = nc.run_news_collection(conn, sources=None, known_codes={"7203","6758"})
  print(results)
  ```

- マーケットカレンダー周り（営業日判定）
  ```python
  from kabusys.data import schema, calendar_management as cm
  conn = schema.init_schema("data/kabusys.duckdb")
  from datetime import date
  d = date(2024, 1, 1)
  print(cm.is_trading_day(conn, d))
  print(cm.next_trading_day(conn, d))
  ```

- 品質チェックの単体実行
  ```python
  from kabusys.data import schema, quality
  conn = schema.init_schema("data/kabusys.duckdb")
  issues = quality.run_all_checks(conn)
  for i in issues:
      print(i.check_name, i.severity, i.detail)
  ```

---

## ディレクトリ構成

以下はパッケージルート（src/kabusys）配下の主要ファイル構成（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py                      # 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py            # J-Quants API クライアント（fetch/save）
      - news_collector.py           # RSS ニュース収集
      - schema.py                   # DuckDB スキーマ定義・初期化
      - pipeline.py                 # ETL パイプライン（日次処理等）
      - calendar_management.py      # マーケットカレンダーの補助・ジョブ
      - audit.py                    # 監査ログスキーマ（トレーサビリティ）
      - quality.py                  # データ品質チェック
    - strategy/
      - __init__.py                  # 戦略モジュール（実装の起点）
    - execution/
      - __init__.py                  # 発注 / 実行モジュール（実装の起点）
    - monitoring/
      - __init__.py                  # 監視用モジュール（拡張ポイント）

---

## 運用上の注意 / ベストプラクティス

- 環境（KABUSYS_ENV）は production の live と paper_trading を区別して使用してください。設定ミスで実際の発注を行わないように注意すること。
- J-Quants API のレート制限（120 req/min）を遵守する設計になっていますが、大量バッチを実行する際はさらにスロットリングやスケジューリングを検討してください。
- DuckDB のファイル（DUCKDB_PATH）は定期的にバックアップを取ってください。監査ログは原則削除しない想定です。
- ニュース収集では外部 URL の安全性検査や受信サイズ制限が組み込まれていますが、未知のフィード追加時は注意深くテストしてください。
- audit 初期化時に SET TimeZone='UTC' を行うため、すべてのタイムスタンプは UTC 基準で扱われます。アプリ側も UTC で統一することを推奨します。

---

## 今後の拡張ポイント（例）

- strategy / execution の具象実装（ポートフォリオ最適化、リスク制御、kabu API との連携）
- モニタリング（Slack 通知やメトリクス収集）の実装
- CI / 自動テスト用の fixtures と統合テスト（DuckDB インメモリ利用）
- requirements.txt / pyproject.toml によるパッケージング、セットアップスクリプトの追加

---

ご不明点や README に追加したい使用例・コマンドがあれば教えてください。