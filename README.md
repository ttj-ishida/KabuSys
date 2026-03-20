# KabuSys

KabuSys は日本株向けの自動売買プラットフォームのコアライブラリです。  
データ取得（J-Quants API）、ETL、ニュース収集、特徴量生成、シグナル生成、監査ログ/スキーマ管理など、戦略開発から実運用までに必要な基盤機能を提供します。

---

## 主な特徴 (機能一覧)

- J-Quants API クライアント
  - 株価日足、財務データ、マーケットカレンダー取得（ページネーション対応、トークン自動リフレッシュ、レート制御、リトライ）
- ETL パイプライン
  - 差分取得（バックフィル対応）、保存（DuckDB へ冪等保存）、品質チェックフレームワーク
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化（冪等）
- ニュース収集
  - RSS フィード収集、テキスト前処理、記事ID生成（URL 正規化 + SHA-256）、銘柄抽出、DB 保存（冪等）
- 研究（Research）ユーティリティ
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）、将来リターン計算、IC（Spearman）算出、ファクター統計サマリー
- 特徴量エンジニアリング
  - 生ファクターの正規化（Z スコア）、ユニバースフィルタ（価格・流動性）、features テーブルへの UPSERT
- シグナル生成
  - 正規化済み特徴量と AI スコアを統合して final_score を計算、BUY/SELL シグナルを作成して signals テーブルへ書き込み
- カレンダー管理
  - JPX カレンダーの取り扱い（営業日判定、前後営業日の取得、夜間バッチ更新）
- 監査ログ（Audit）
  - signal → order_request → executions までを UUID ベースでトレース可能にするテーブル定義

---

## 前提条件

- Python 3.9+
- 必要パッケージ（主なもの）
  - duckdb
  - defusedxml

（プロジェクトで追加の外部ライブラリが必要な場合は setup/requirements に従ってインストールしてください。上記はコード内で明示的に使用されている主な依存です。）

---

## 環境変数 / 設定

config.Settings によって環境変数から設定を読み込みます。自動でプロジェクトルートの `.env` と `.env.local` を読み込みます（OS 環境変数が優先、`.env.local` は `.env` を上書き）。

必須（例）:
- JQUANTS_REFRESH_TOKEN - J-Quants のリフレッシュトークン
- KABU_API_PASSWORD - kabu ステーション等の API パスワード
- SLACK_BOT_TOKEN - Slack 通知に使う Bot トークン
- SLACK_CHANNEL_ID - Slack 送信先チャンネル ID

任意 / デフォルト:
- KABU_API_BASE_URL - kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH - 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV - 実行環境 (development / paper_trading / live)（デフォルト: development）
- LOG_LEVEL - ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)

自動 env ロードを無効化する:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます（テスト用途など）。

例 `.env`（一例）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

2. パッケージインストール（最低限）
   ```
   pip install duckdb defusedxml
   ```

   プロジェクトに配布用の setup/requirements があればそちらを利用してください（例: pip install -e .）。

3. 環境変数設定
   - ルートに `.env` を作成するか、必要な環境変数を OS に設定してください。

4. データベース初期化（DuckDB）
   - Python インタラクティブまたはスクリプトから schema.init_schema を呼び出して DB を初期化します（パスは settings.duckdb_path がデフォルト）。

---

## 使い方（短いサンプル）

以下は主要機能を呼び出す最小例です。実運用ではログ設定や例外処理、ジョブスケジューラ等を組み合わせてください。

- DB 初期化:
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # settings.duckdb_path は Path を返します
```

- 日次 ETL 実行（J-Quants から差分取得して保存）:
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

- 市場カレンダー更新ジョブ:
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
saved = calendar_update_job(conn)
print("calendar saved:", saved)
```

- ニュース収集と保存:
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# known_codes: 銘柄コードのセットを渡すと本文から銘柄抽出して news_symbols を作成します
results = run_news_collection(conn, known_codes={"7203", "6758"})
print(results)
```

- 特徴量構築:
```python
from kabusys.strategy import build_features
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
count = build_features(conn, date.today())
print("features upserted:", count)
```

- シグナル生成:
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
total_signals = generate_signals(conn, date.today(), threshold=0.6)
print("signals written:", total_signals)
```

---

## ディレクトリ構成

（コードベースの主要ファイル・モジュール）

- src/
  - kabusys/
    - __init__.py
    - config.py
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
    - monitoring/  (パッケージ名は __all__ に含まれますが、詳細は実装による)

この README に記載のとおり、モジュールは概ね次の責務に分離されています:
- data: データ取得・保存・スキーマ・ETL・カレンダー・ニュース等
- research: 研究用のファクター計算・解析ユーティリティ
- strategy: 特徴量合成・シグナル生成ロジック
- execution: 発注・約定・ポートフォリオ管理（発注層の実装を想定）
- config: 環境設定のロードと検証

---

## 実運用・運用上の注意

- 環境（KABUSYS_ENV）:
  - development / paper_trading / live の 3 種類を想定。live 実行時は特に注意してください（発注処理や API 認証情報）。
- 環境変数の管理:
  - `.env.local` はローカル上書き用で機密情報の保護に注意してください。OS 環境変数が優先されます。
- レート制限・リトライ:
  - J-Quants クライアントはレート制限（120 req/min）やリトライ（指数バックオフ）を実装していますが、同時多発で大量リクエストを投げないよう制御してください。
- データの冪等性:
  - 保存処理は基本的に ON CONFLICT / UPSERT を用いて冪等化されていますが、スキーマ変更時は注意してください。
- セキュリティ:
  - RSS 取得は SSRF・XML Bomb 対策済みの実装を含みますが、運用環境ではネットワークルールやプロキシで外部アクセスを制御してください。

---

## 連絡・貢献

この README はコードベースの主要機能をまとめたものです。実装の追加や修正、ドキュメント改善のプルリクエストは歓迎します。問題や質問があれば Issue を立ててください。

--- 

以上。必要であれば各モジュール（例: jquants_client、news_collector、pipeline、strategy）のより詳しい使用例や API 仕様ドキュメントを別ファイルとして追加できます。どの項目を優先して詳述しますか？