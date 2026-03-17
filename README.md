# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。J-Quants API から市場データ（株価・財務・マーケットカレンダー）と RSS ニュースを収集して DuckDB に蓄積し、ETL パイプライン・品質チェック・監査ログ等を提供します。戦略層・実行層・監視層のための基盤コンポーネントを含み、発注やモニタリング用の拡張ポイントを備えています。

バージョン: 0.1.0

---

## 主な特徴

- J-Quants API クライアント
  - 日次株価（OHLCV）、四半期財務データ、JPX マーケットカレンダーを取得
  - レート制限（120 req/min）・指数バックオフ・401 トークン自動リフレッシュ対応
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead bias を防止

- DuckDB ベースのデータスキーマ
  - Raw / Processed / Feature / Execution の多層スキーマ定義
  - 冪等な INSERT（ON CONFLICT）を用いた保存ロジック
  - 監査ログ（signal / order_request / execution）の専用スキーマ

- ETL パイプライン
  - 差分更新（最終取得日からの差分取り込み）・バックフィル対応
  - 市場カレンダー先読み（lookahead）を考慮した営業日調整
  - 品質チェック（欠損・スパイク・重複・日付不整合）を一括実行

- ニュース収集モジュール
  - RSS フィード取得、記事正規化、トラッキングパラメータ除去、記事ID は正規化 URL の SHA-256（先頭 32 文字）
  - SSRF 対策、XML 攻撃対策（defusedxml）、受信サイズ制限による DoS 対策
  - 記事と銘柄コードの紐付け（news_symbols）

- カレンダー管理（JPX）
  - 営業日判定、前後営業日の取得、期間内営業日列挙、夜間バッチ更新ジョブ

---

## 必要環境 / 依存ライブラリ

- Python 3.10 以上（型アノテーションに Path | None 等を使用）
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml

※ パッケージのインストールはプロジェクト側で requirements.txt / pyproject.toml を用意してください。最低限上記パッケージが必要です。

---

## セットアップ手順

1. リポジトリをクローン（またはソースを配置）
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクト化されていれば）pip install -e .

4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動的に読み込みます（CWD ではなくパッケージファイル位置からプロジェクトルートを検出）。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

必須環境変数（Settings により読み込まれます）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）

任意 / デフォルトあり:
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: running environment（development / paper_trading / live、デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）

例 .env
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## 使い方（簡易サンプル）

以下は最小限の操作例です。実運用ではロギング設定やエラーハンドリング、スケジューリングを追加してください。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
# またはメモリ:
# conn = schema.init_schema(":memory:")
```

2) 日次 ETL 実行
```python
from datetime import date
from kabusys.data import pipeline, schema

conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB に接続
result = pipeline.run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

3) RSS ニュース収集（既存の known_codes を与える例）
```python
from kabusys.data import news_collector, schema
import duckdb

conn = schema.get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758"}  # 有効な銘柄コードセット（実際は銘柄一覧をロード）
results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)
```

4) カレンダー夜間更新ジョブ
```python
from kabusys.data import calendar_management, schema

conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print(f"saved calendar rows: {saved}")
```

5) 監査ログ（audit）初期化（信頼済みの DuckDB 接続へ追加）
```python
from kabusys.data import audit, schema
conn = schema.get_connection("data/kabusys.duckdb")
audit.init_audit_schema(conn)
```

6) J-Quants の単体呼び出し例（トークン自動取得あり）
```python
from kabusys.data import jquants_client as jq
records = jq.fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))
# DuckDB に接続して保存:
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
jq.save_daily_quotes(conn, records)
```

注意点:
- run_daily_etl 等は内部で複数の外部 API を呼びます。環境変数の設定とネットワークアクセスが必要です。
- jquants_client は API レート制限・リトライ・ページネーションを備えていますが、実行頻度は運用に応じて設計してください。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                   - 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py         - J-Quants API クライアント（取得・保存ロジック）
      - news_collector.py         - RSS ニュース収集と DB 保存
      - schema.py                 - DuckDB スキーマ定義・初期化
      - pipeline.py               - ETL パイプライン（run_daily_etl 等）
      - calendar_management.py    - マーケットカレンダーの管理 / ジョブ
      - quality.py                - データ品質チェック
      - audit.py                  - 監査ログ（signal / order_request / execution）初期化
      - pipeline.py               - ETL 実装（差分更新・品質チェックを含む）
    - strategy/
      - __init__.py               - 戦略関連の拡張ポイント（未実装の枠）
    - execution/
      - __init__.py               - 発注/実行エンジン関連の拡張ポイント（未実装の枠）
    - monitoring/
      - __init__.py               - 監視・アラートの拡張ポイント（未実装の枠）

各モジュールの役割:
- config: 環境変数の読み込み（.env/.env.local 自動読み込み）と Settings 抽象
- data: データ取得・保存・ETL・品質チェック・監査ログに関する主要ロジック
- strategy: 戦略実装を配置するための名前空間（実装はプロジェクト側で追加）
- execution: 証券会社 API 連携や注文管理の実装ポイント
- monitoring: Slack 等を使った運用監視・通知の実装ポイント

---

## 運用上の注意 / ベストプラクティス

- 環境分離: KABUSYS_ENV を使い development / paper_trading / live を区別し、実際の発注処理は live でのみ有効化するなどのガードを必ず実装してください。
- シークレット管理: .env は git 管理しないでください。シークレットは Vault / Secrets Manager 等に保管し、CI/CD で注入してください。
- バックフィルと差分戦略: run_prices_etl / run_financials_etl はデフォルトで backfill を行います。大規模バックフィル時は API レートや DB サイズに注意。
- 品質チェック: run_daily_etl の品質チェックは Fail-Fast ではなく問題を列挙します。重大（error）問題を検出した場合は運用フローでアラートを出す設計を推奨します。
- テスト容易性: jquants_client の _urlopen や news_collector のネットワークレイヤーは差し替え可能に設計されているため、単体テスト時はモックしてください。

---

## 今後の拡張案（参考）

- strategy 層に具体的なアルゴリズム（例: モメンタム、ペアトレード）を実装
- execution 層で kabuステーションや外部ブローカーとの通信実装、注文のリトライ/状態管理
- モニタリング: Slack/Prometheus 連携でアラートやメトリクスを収集
- CI/CD 用の tests / linters の追加、型チェック（mypy）や静的解析の導入

---

問題・要望・ドキュメント追記希望があれば、どの項目を優先して拡充したいか教えてください。README を用途（開発者向け、運用手順向け、API リファレンス向け）に合わせてさらに詳細化できます。