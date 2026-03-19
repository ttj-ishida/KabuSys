# KabuSys

日本株向けの自動売買システム用ライブラリ（モジュール群）。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査用スキーマなどを含む研究／運用パイプラインの基盤を提供します。

## 主な目的
- J-Quants API による株価・財務・カレンダー等の取得と DuckDB への保存（冪等）
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）
- 特徴量正規化・合成（features テーブル作成）
- 戦略シグナル生成（BUY / SELL 判定）
- RSS ベースのニュース収集と銘柄紐付け
- マーケットカレンダー管理（営業日判定, next/prev_trading_day 等）
- ETL / バッチジョブの実装補助と品質チェック基盤

---

## 機能一覧
- data
  - jquants_client: J-Quants API クライアント（レートリミット制御、リトライ、トークン自動更新、ページネーション）
  - schema: DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - pipeline: ETL（差分取得・保存・品質チェック）、日次 ETL 実装
  - news_collector: RSS 収集、前処理、raw_news 保存、銘柄抽出
  - calendar_management: JPX カレンダーの更新と営業日ユーティリティ
  - stats / features: z-score 正規化などの統計ユーティリティ
  - audit: 監査ログ（signal_events, order_requests, executions 等）のスキーマと初期化
- research
  - factor_research: mom/vol/val 等のファクター計算（prices_daily / raw_financials を使用）
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、統計サマリー
- strategy
  - feature_engineering: research の raw ファクターを正規化・フィルタ適用して features テーブルへ保存
  - signal_generator: features と ai_scores を統合して final_score を算出し signals テーブルを生成
- execution / monitoring
  - 実行層・監視層用のプレースホルダ／インターフェース（発注実装は外部／ブローカー連携側で実装）

---

## 動作要件・依存関係
- Python >= 3.10（型注釈の union 表記や typing の使用に依存）
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- （プロジェクトに pyproject.toml / requirements.txt があればそれを利用してください）
- 環境変数管理は .env ファイルまたは OS 環境変数から読み込みます（自動ロード機能あり）

---

## 環境変数（主なもの）
このライブラリは実運用で複数の機密・設定値を環境変数から読む設計です。最低限設定が必要なものは以下。

- JQUANTS_REFRESH_TOKEN : J-Quants 用リフレッシュトークン（必須）
- KABU_API_PASSWORD     : kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL     : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID      : Slack チャンネル ID（必須）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : SQLite（監視DB）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV           : 実行環境 (development|paper_trading|live)（デフォルト: development）
- LOG_LEVEL             : ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)

自動で .env / .env.local をプロジェクトルートから読み込みます。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順（開発環境向け、例）
1. Python 環境用意（3.10+ 推奨）
2. リポジトリをクローン
3. 仮想環境作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
4. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （もしパッケージ化されていれば）pip install -e .
5. プロジェクトルートに .env を配置（.env.example を参考に作成）

例 .env 中身（サンプル）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 初期 DB 構築・基本的な使い方（コード例）
以下は Python REPL / スクリプトから基本ジョブを実行する例です。

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は環境変数 DUCKDB_PATH などから決定されます
conn = init_schema(settings.duckdb_path)
```

- 日次 ETL の実行（J-Quants から差分取得）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量の構築（features テーブルへの UPSERT）
```python
from datetime import date
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
n = build_features(conn, target_date=date.today())
print(f"built {n} features")
```

- シグナル生成（signals テーブルへ書き込み）
```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
count = generate_signals(conn, target_date=date.today())
print(f"generated {count} signals")
```

- ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
# known_codes に有効な銘柄コードのセット（例: 全上場銘柄コレクション）を渡すと銘柄紐付けを実行します
res = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
print(res)
```

- カレンダー更新バッチ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
saved = calendar_update_job(conn)
print(f"saved {saved} calendar rows")
```

---

## 推奨ワークフロー（運用例）
1. init_schema() で DB を初期化
2. nightly cron / GitHub Actions 等で
   - run_daily_etl() を実行して prices/financials/calendar を差分取得・保存
   - calendar_update_job() を必要に応じて実行（定期）
   - run_news_collection() を定期実行して raw_news を蓄積
3. ETL 後に build_features() を実行して features を作成
4. generate_signals() を実行して signals を作成
5. signals を execution 層（ブローカー API）に渡して発注・約定を処理し、orders / executions / positions / audit を更新

---

## ディレクトリ構成
（主要ファイルとモジュールを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - calendar_management.py
      - features.py
      - stats.py
      - audit.py
      - pipeline.py
      - (その他 data 関連モジュール)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
      - feature_engineering.py
      - signal_generator.py
    - execution/
      - __init__.py
      - (発注・ブローカ連携の実装場所)
    - monitoring/
      - (監視・アラート連携の実装場所)
- pyproject.toml / setup.cfg / requirements.txt （存在する場合）

---

## 開発上の注意点
- DuckDB の日時/日付の取り扱いや SQL の型に注意してください（コード内で変換ユーティリティを提供）。
- ETL は差分取得・バックフィルを行うよう設計されています。初回ロード時は期間指定を行ってください。
- features / signals の処理はルックアヘッドバイアスを避けるため target_date 時点のデータのみ参照するよう実装されています。
- jquants_client は HTTP のレート・リトライ・トークン自動更新を行います。API レート制限を守る設計です。
- RSS 収集は SSRF や XML Bomb に対する防護（スキームチェック、defusedxml、サイズ制限）を実装しています。
- 環境変数の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）から行われます。CIやテストで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## テスト・拡張
- 各モジュールは外部依存（API トークン・HTTP 呼び出し・DB）を引数注入できるようになっています。テスト時はモック（id_token、ネットワーク、DuckDB の in-memory モード ":memory:"）を利用してください。
- strategy / execution 層はポートフォリオ管理や発注ロジックに合わせて拡張してください。監査（audit）スキーマを用いてトレーサビリティを担保することを推奨します。

---

何か特定のセットアップ手順（CI、Docker、ブローカー接続）のテンプレートや、README に載せたい具体的な例・コマンドがあれば教えてください。必要に応じてサンプル .env.example や簡易デプロイスクリプトも作成します。