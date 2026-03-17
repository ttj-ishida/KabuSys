# KabuSys

日本株向けの自動売買プラットフォーム（ライブラリ）です。  
J-Quants や RSS フィード等から市場データ・ニュースを取得し、DuckDB に蓄積、品質チェック、ETL、監査ログ管理までを行うための基盤モジュール群を提供します。

主な目的は「データの取得・蓄積・検査・トレーサビリティ」を堅牢に実現し、戦略層・発注層へ安全にデータを供給することです。

## 機能一覧
- 環境変数管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェック
- J-Quants API クライアント（jquants_client）
  - 日足（OHLCV）、財務（四半期 BS/PL）、マーケットカレンダーの取得
  - レートリミット、リトライ、トークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT）
- ニュース収集（news_collector）
  - RSS 取得・XML パース（defusedxml）
  - URL 正規化、トラッキングパラメータ除去、記事ID生成（SHA-256）
  - SSRF・gzip・レスポンスサイズ制限等の安全対策
  - DuckDB への冪等保存（INSERT ... RETURNING、トランザクション）
  - 記事と銘柄コードの紐付け（news_symbols）
- DuckDB スキーマ定義・初期化（schema）
  - Raw / Processed / Feature / Execution 層を含む総合スキーマ
  - インデックス定義、監査テーブル初期化サポート
- ETL パイプライン（pipeline）
  - 差分取得（バックフィル対応）、保存、品質チェック実行
  - 日次 ETL エントリポイント（run_daily_etl）
- 市場カレンダー管理（calendar_management）
  - 営業日判定、前後営業日取得、夜間カレンダー更新ジョブ
- 監査ログ（audit）
  - signal → order_request → execution のトレーサビリティテーブル
  - 発注の冪等キー、UTC タイムスタンプ運用
- データ品質チェック（quality）
  - 欠損、スパイク（急騰・急落）、重複、日付不整合の検出
  - QualityIssue を返し呼び出し元が対応可

（strategy / execution / monitoring パッケージはエントリポイント用に用意されていますが、今回のコードでは実装ファイルは含まれていません）

## セットアップ（開発環境）
以下は開発マシンでのセットアップ例です。

1. リポジトリをクローン（既にある場合は不要）
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. Python 仮想環境作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate.bat  # Windows
   ```

3. 必要パッケージをインストール（例）
   ```
   pip install duckdb defusedxml
   ```
   - 実プロジェクトでは pyproject.toml / requirements.txt を参照して依存をインストールしてください。
   - 本コードでは urllib, json, logging 等は標準ライブラリを使用しています。

4. パッケージを編集可能モードでインストール（任意）
   ```
   pip install -e .
   ```

## 環境変数（設定）
settings クラスは環境変数から設定を読み取ります。主なキー：

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — SQLite（モニタリング用）ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

自動でプロジェクトルートの `.env` と `.env.local` を読み込みます（OS 環境変数が優先）。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

注意: 必須変数が未設定のとき settings は ValueError を投げます。`.env.example` を参考に `.env` を作成してください（リポジトリに同ファイルがある想定）。

## 使い方（主要ユースケース）

以下は Python REPL / スクリプトから利用する例です。

- DuckDB スキーマ初期化
```python
from kabusys.data import schema

# ファイル DB を初期化（親ディレクトリは自動作成）
conn = schema.init_schema("data/kabusys.duckdb")
# あるいはインメモリ:
# conn = schema.init_schema(":memory:")
```

- 日次 ETL の実行（J-Quants からデータ取得して保存・品質チェック）
```python
from kabusys.data import pipeline
from kabusys.data import schema
from datetime import date

conn = schema.init_schema("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）
```python
from kabusys.data import news_collector
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")

# 既知銘柄コードのセット（抽出に使用）
known_codes = {"7203", "6758", "9984"}

# デフォルトソースを使う場合は sources=None
results = news_collector.run_news_collection(conn, sources=None, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

- J-Quants API を直接呼び出して日足を取って保存する
```python
from kabusys.data import jquants_client as jq
from kabusys.data import schema
from datetime import date

conn = schema.init_schema("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print("saved:", saved)
```

- 品質チェックの単独実行
```python
from kabusys.data import quality
from kabusys.data import schema
from datetime import date

conn = schema.init_schema("data/kabusys.duckdb")
issues = quality.run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i)
```

## 実運用上の注意
- J-Quants のレート制限（120 req/min）を遵守するためにモジュールは内部でスロットリングを行います。並列化する場合は全体の呼び出し頻度に注意してください。
- ニュース収集では外部コンテンツを処理するため、XML エンティティ攻撃・SSRF・大容量レスポンスに対する防御ロジックを組み込んでいますが、運用環境のネットワークポリシーと合わせて検討してください。
- DuckDB のスキーマは冪等で作られます。既存データを消さずにテーブル追加・更新が可能です。
- 監査ログ（audit）は UTC を前提としています。アプリケーション側は updated_at 等を適切に更新してください。

## ディレクトリ構成
プロジェクトの主要ファイル / フォルダ構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント、保存関数
    - news_collector.py             — RSS ニュース収集・前処理・保存
    - schema.py                     — DuckDB スキーマ定義 / init_schema
    - pipeline.py                   — ETL パイプライン（日次ETL）
    - calendar_management.py        — 市場カレンダー更新 / 営業日ロジック
    - audit.py                      — 監査ログテーブル定義 / 初期化
    - quality.py                    — データ品質チェック
  - strategy/
    - __init__.py                   — 戦略パッケージ（拡張用）
  - execution/
    - __init__.py                   — 発注 / ブローカー連携（拡張用）
  - monitoring/
    - __init__.py                   — モニタリング用（拡張用）

データベース・テーブルの概要は schema.py の DDL コメントを参照してください（Raw / Processed / Feature / Execution / Audit 層に分離）。

## 開発・拡張ポイント
- strategy/ と execution/ は各戦略やブローカー固有実装を入れる場所です。戦略は signal_events を生成し、order_requests を作成して audit に記録する設計を想定しています。
- monitoring パッケージには Slack 通知やメトリクス Push（Prometheus 等）を追加できます。設定は config.Settings を通じて取得できます。
- テスト時は環境変数自動読み込みを無効化できます:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

## 貢献・ライセンス
この README はプロジェクトの概要説明です。実装の拡張・バグ修正・ドキュメント追加は歓迎します。ライセンスやコントリビュートガイドがある場合はリポジトリのルートファイル（LICENSE, CONTRIBUTING.md 等）を参照してください。

---

この README は現行のコードベースの主要機能をまとめたものです。詳細は各モジュールの docstring とソースコードを参照してください。必要であれば導入手順や運用手順（cron/スケジューラの例、Docker 化、CI 設定など）を追記できます。