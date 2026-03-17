# KabuSys — 日本株自動売買システム

簡易説明
---
KabuSys は日本株を対象とした自動売買プラットフォームのコアライブラリ群です。データ収集（J‑Quants / RSS）、ETL、データ品質チェック、DuckDB ベースのスキーマ、監査ログ（発注→約定のトレース）など、売買ロジックを実装するための基盤機能を提供します。strategy／execution／monitoring の各レイヤーは拡張できるように分離されています。

主な特徴
---
- J‑Quants API クライアント
  - 株価日足、財務データ、マーケットカレンダー取得
  - API レート制御（120 req/min 固定間隔スロットリング）
  - リトライ（指数バックオフ）および 401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録し Look‑ahead Bias 対策
  - DuckDB へ冪等的保存（ON CONFLICT DO UPDATE）
- RSS ニュース収集
  - RSS から記事を抽出し raw_news に保存
  - URL 正規化（utm 等除去）による冪等性（SHA‑256 ハッシュ ID）
  - SSRF / XML BOM / Gzip Bomb 対策（スキーム検査、プライベートIPチェック、defusedxml、受信サイズ制限）
  - 銘柄コード抽出と news_symbols への紐付け機能
- DuckDB スキーマ
  - Raw / Processed / Feature / Execution 層を想定した豊富なテーブル定義
  - 監査ログ（signal_events, order_requests, executions）を別モジュールで初期化可能
  - インデックス定義・テーブル初期化 API を提供
- ETL パイプライン
  - 差分更新（最終取得日 + バックフィル）で効率的に更新
  - カレンダー先読み、品質チェック（欠損・スパイク・重複・日付不整合）を統合
  - 各ステップは独立してエラーハンドリング（1 ステップ失敗でも残りを継続）
- データ品質チェック（quality モジュール）
  - 欠損、スパイク（前日比閾値）、重複、将来日付／非営業日の検出
  - QualityIssue オブジェクトで詳細情報とサンプル行を返却

セットアップ手順
---
前提
- Python 3.10 以上（型ヒントのユニオン演算子（|）等を使用）
- インターネット接続（J‑Quants / RSS）
- 必要ライブラリ（例）:
  - duckdb
  - defusedxml
  - （プロジェクトで管理される requirements.txt / pyproject.toml に従ってください）

例: 仮想環境でのセットアップ
```bash
python -m venv .venv
source .venv/bin/activate
# 必要なパッケージをインストール（プロジェクトに requirements.txt / pyproject.toml がある想定）
pip install duckdb defusedxml
# パッケージを編集可能モードでインストールする場合
pip install -e .
```

環境変数
- 自動で .env と .env.local（プロジェクトルート: .git または pyproject.toml があるディレクトリ）を読み込みます。
  - 自動ロードを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 必須（Settings._require で参照されるもの）
  - JQUANTS_REFRESH_TOKEN — J‑Quants のリフレッシュトークン
  - KABU_API_PASSWORD — kabu ステーション API 用パスワード
  - SLACK_BOT_TOKEN — Slack 通知用ボットトークン
  - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
- 任意 / デフォルト
  - KABUSYS_ENV — {development, paper_trading, live}（デフォルト: development）
  - LOG_LEVEL — {DEBUG, INFO, WARNING, ERROR, CRITICAL}（デフォルト: INFO）
  - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 sqlite パス（デフォルト: data/monitoring.db）

基本的な使い方
---

1) 設定（settings）の利用
```python
from kabusys.config import settings

print(settings.jquants_refresh_token)  # 必須: 環境変数から取得
print(settings.duckdb_path)           # Path オブジェクト（デフォルト data/kabusys.duckdb）
```

2) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # files の親ディレクトリが無ければ自動作成
```

3) 監査ログ（order/event/execution）用テーブルを追加
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)  # 既存コネクションに監査テーブルを追加（UTCタイムゾーン設定含む）
```

4) 日次 ETL 実行（株価／財務／カレンダー取得 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定しないと今日を対象に実行
print(result.to_dict())
```

5) ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
# known_codes: 銘柄抽出に使う有効コードセット（None なら紐付けをスキップ）
known_codes = {"7203", "6758", "6954"}  # 例
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: 新規保存件数}
```

6) 直接 API を呼ぶ（J‑Quants）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

id_token = get_id_token()  # refresh token から id_token を取得
quotes = fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,1,31))
# save は jquants_client.save_daily_quotes を利用
```

注意事項（設計上のポイント）
---
- API レート制御: jquants_client は 120 req/min に合わせた固定間隔スロットリングを行います。複数プロセスから並列に呼ぶ場合は注意してください（グローバルな制御はされません）。
- 冪等性: raw テーブルへの保存は ON CONFLICT を利用して冪等に動作します。
- セキュリティ対策:
  - news_collector は SSRF、XML Bomb、Gzip Bomb 等の攻撃に対する複数対策を施しています。
  - .env の自動ロードは OS 環境変数を保護する仕組みを一部備えています（.env.local は上書き可能）。
- テスト容易性: id_token を外部から注入できる設計になっています（ユニットテスト時のモックが容易）。

ディレクトリ構成
---
（プロジェクトの src 下を想定）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py      — J‑Quants API クライアント（取得 + 保存）
      - news_collector.py      — RSS ニュース収集と保存
      - pipeline.py           — ETL パイプライン（差分取得・品質チェック）
      - schema.py             — DuckDB スキーマ定義・初期化
      - audit.py              — 監査ログスキーマ（発注→約定トレース）
      - quality.py            — データ品質チェック
    - strategy/
      - __init__.py           — 戦略層（各戦略プラグインを配置）
    - execution/
      - __init__.py           — 発注 / ブローカー連携用インターフェース
    - monitoring/
      - __init__.py           — 監視・メトリクス用（未実装 placeholder）
- pyproject.toml / setup.cfg 等（プロジェクトルートに配置想定）
- .env / .env.local           — 開発時の環境変数（自動読み込み対象）

よくある操作例
---
- DB 初期化（初回）:
  - Python スクリプトで init_schema() を呼ぶと必要なディレクトリが作成されテーブルが作成されます。
- 日次ETL のスケジューリング:
  - cron / Airflow / prefect 等から run_daily_etl を呼び出してください。ETL はカレンダー先読みやバックフィル機能を持ちます。
- ニュース定期収集:
  - run_news_collection を期間ごとに実行し raw_news と news_symbols を更新します（既存記事は ON CONFLICT によりスキップ）。

開発・拡張
---
- strategy や execution ディレクトリに独自の戦略・発注モジュールを追加して本体と連携してください。
- テスト時は環境変数自動ロードをオフにするために KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し、必要な環境をテスト側で注入してください。
- ニュース収集の URL フェッチ部分（_urlopen 等）はモック可能な作りになっています。

ライセンス / コントリビュート
---
本 README にはライセンス情報を含めていません。実際の配布時は適切な LICENSE ファイルを追加してください。バグ修正や機能追加はルートの issue/pull request にて受け付けてください。

補足（問い合わせ先）
---
実装上の不明点や拡張に関する相談がある場合、リポジトリの Issues を利用してください。README にない実行方法や CI/デプロイ手順はプロジェクト固有の運用ドキュメントで管理してください。