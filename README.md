# KabuSys — 日本株自動売買システム

KabuSys は日本株のデータ収集・前処理・特徴量生成・シグナル生成・発注監査等を含む自動売買プラットフォームの基盤ライブラリです。DuckDB をデータストアに利用し、J-Quants API や RSS ニュース、kabuステーション等と連携する設計になっています。

注意: 本リポジトリは「ライブラリ / コア処理群」を提供するものであり、実際の運用でのライブ注文（資金リスク）を含む環境で使用する場合は十分な検証と安全対策が必要です。

## 主な特徴

- データ収集
  - J-Quants API から株価日足・財務データ・マーケットカレンダーを差分取得（ページネーション対応）
  - RSS フィードからニュース収集（SSRF対策、トラッキングパラメータ除去）
- データ格納とスキーマ管理
  - DuckDB に Raw / Processed / Feature / Execution 層のテーブルを定義するスキーマ（冪等）
- ETL パイプライン
  - 差分取得、バックフィル、品質チェックを行う日次 ETL（run_daily_etl）
- 研究（research）用ユーティリティ
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Spearman）計算、ファクターサマリー
- 特徴量エンジニアリング
  - ファクターの正規化（Z スコア）、ユニバースフィルタ、features テーブルへの UPSERT（冪等）
- シグナル生成
  - features と ai_scores を統合して final_score を算出し、BUY/SELL シグナルを生成・signals テーブルへ保存
  - Bear レジーム抑制、エグジット（ストップロスなど）の判定
- 発注監査・トレーサビリティ
  - signal_events / order_requests / executions 等の監査ログ設計（UUID 連鎖でトレース可能）
- モジュール設計
  - レート制御・リトライ・自動トークンリフレッシュ・SSRF防御などの実装

---

## 必要要件

- Python 3.9+（型注釈に PEP 604 等を利用）
- 主要依存（例）
  - duckdb
  - defusedxml
- インターネットアクセス（J-Quants API、RSS フィード 等）
- J-Quants のリフレッシュトークン等外部サービスの認証情報

（プロジェクトの pyproject.toml / requirements.txt がある場合はそちらに従ってください）

---

## 環境変数 / 設定

KabuSys は .env / .env.local または OS 環境変数から設定を自動で読み込みます（プロジェクトルートは .git または pyproject.toml を探索）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な必須環境変数（Settings クラスより）:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャネル ID（必須）

オプション配置やパス:

- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development, paper_trading, live）
- LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）

設定値が不足する場合は `kabusys.config.settings` 経由で参照したときに例外が発生します。

---

## セットアップ手順

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - その他プロジェクト依存がある場合は pyproject.toml / requirements.txt を参照してインストールしてください。

4. 環境変数を設定
   - プロジェクトルートに `.env`（または `.env.local`）を作成し必須環境変数を追加します（例）:

     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development

   - 環境変数は OS 環境に直接設定しても利用できます。

---

## 初期化（DB スキーマ作成）

DuckDB のスキーマを初期化します。デフォルトの DB パスは settings.duckdb_path（デフォルトは data/kabusys.duckdb）。

Python 例:

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # ファイルを自動で作成し、全テーブルを作成します
```

メモリ DB を使いたい場合は `":memory:"` を渡せます。

---

## 使い方（代表的な機能）

以下は主要なユーティリティの利用例です。実運用ではログ出力・例外処理・監視を整備してください。

1. 日次 ETL 実行（株価・財務・カレンダーの差分取得）
```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2. 特徴量の構築（features テーブルへの書き込み）
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features

conn = get_connection(settings.duckdb_path)
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

3. シグナル生成（features と ai_scores を元に signals を生成）
```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import generate_signals
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
total = generate_signals(conn, target_date=date.today())
print(f"signals written: {total}")
```

4. ニュース収集ジョブ（RSS 収集→raw_news 保存、銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
# known_codes は銘柄コードのセット（ex: {'7203','6758', ...}）
results = run_news_collection(conn, known_codes={'7203', '6758'})
print(results)
```

5. J-Quants からのデータ取得（直接呼び出し例）
```python
from kabusys.data.jquants_client import fetch_daily_quotes
from kabusys.config import settings

records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
print(len(records))
```

---

## 注意点 / 運用上の留意事項

- J-Quants API のレート制限（120 req/min）に従うよう内部に RateLimiter を実装していますが、運用時は API の使用制限・ターゲット数に注意してください。
- get_id_token はリフレッシュトークンを用いたトークン発行を行い、401 を受け取った場合に自動でリフレッシュします（1 回だけリトライ）。
- ETL はバックフィル（デフォルト3日）機能があり、API 側の後出し修正を吸収するよう設計されています。
- features / signals などは日付単位で「削除→挿入」の置換処理を行い、日付単位での冪等性を保っています。
- news_collector は RSS パースの安全策（defusedxml、SSRF 防止、サイズ上限）を実装していますが、外部フィード運用のリスクはプロジェクト側で管理してください。
- KABUSYS_ENV が `live` のときは実際の発注等に連携するケースが想定されるため、本番での鍵・シークレット管理と二重チェックを必ず行ってください。

---

## 主要モジュールと機能一覧（抜粋）

- kabusys.config
  - 環境変数自動読み込み、Settings クラス
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存用ユーティリティ）
  - schema: DuckDB スキーマ定義と初期化
  - pipeline: ETL 実行（差分、品質チェック等）
  - news_collector: RSS 収集・前処理・保存・銘柄抽出
  - calendar_management: 市場カレンダー管理・営業日判定ユーティリティ
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.research
  - factor_research: calc_momentum / calc_volatility / calc_value
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.strategy
  - feature_engineering.build_features
  - signal_generator.generate_signals
- kabusys.execution
  - 発注・約定管理関連（骨格／名前空間）

---

## ディレクトリ構成

プロジェクトの主要ファイル・ディレクトリ（抜粋）:

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
      - stats.py
      - features.py
      - calendar_management.py
      - audit.py
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
    - monitoring/  (監視用モジュールが入る想定)
- pyproject.toml / setup.cfg / requirements.txt  (プロジェクト設定・依存)
- .env.example  (環境変数の例: プロジェクトルートに置く想定)

（実際のリポジトリではさらにドキュメント・スクリプト・テストなどが含まれる可能性があります）

---

## 開発・テスト

- 単体テストや CI は別途用意してください（本コードベースではユニットテストは同梱されていません）。
- ネットワーク依存の関数（J-Quants 呼び出し、RSS フェッチ等）はモックしてテストすることを推奨します。
- pipeline.run_* や jquants_client の HTTP 部分はリトライ・レート制御の振る舞いが重要なので、ネットワーク障害や 401/429 のケースをテストケースに含めてください。

---

## 最後に（安全に関する注意）

本ライブラリはデータ収集からシグナル生成まで広範な機能を提供しますが、実際の資金を伴うライブ取引を行う前に以下を必ず実施してください:

- テスト環境・paper_trading モードで十分に検証する（KABUSYS_ENV=paper_trading）
- 発注ログ・監査ログが意図通り記録されていることを確認する
- 想定外の重複発注や通信障害時の振る舞いをハンドリングする
- 認証情報・シークレットは安全に保管（Vault 等の利用を推奨）

---

README の内容や利用方法について不明点があれば、どの部分を詳しく説明すべきか教えてください。サンプルの .env.example や運用チェックリストのテンプレートも作成できます。