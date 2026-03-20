# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（モジュール群）。  
データ収集（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査（発注〜約定トレーサビリティ）など、戦略実装と運用に必要な基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の責務を持つ Python モジュール群です。

- 市場データ・財務データ・カレンダーの差分取得と DuckDB への冪等保存
- リサーチ用のファクター計算（モメンタム、ボラティリティ、バリュー等）
- 特徴量正規化（Z スコア）と features テーブルへの保存
- features と AI スコアを統合した売買シグナル生成（BUY / SELL）
- RSS からのニュース収集と銘柄紐付け
- JPX カレンダー管理（営業日判定 / next/prev_trading_day 等）
- 発注・約定・ポジションを記録するためのスキーマと監査ログ用 DDL

設計上の特徴:
- DuckDB を中心にローカルにデータを保持（:memory: も可）
- J-Quants API 用のレート制限・リトライ・トークン自動リフレッシュ実装
- ETL / DB 操作は冪等（ON CONFLICT / トランザクション）で設計
- ルックアヘッドバイアスを避けるため、target_date 時点のデータみを使用

---

## 機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション・リトライ・トークン管理）
  - pipeline: 日次 ETL（差分取得・保存・品質チェック）
  - schema: DuckDB スキーマ初期化・接続ヘルパー
  - news_collector: RSS 取得・記事前処理・DB 保存・銘柄抽出
  - calendar_management: JPX カレンダー管理・営業日判定
  - stats: 汎用統計ユーティリティ（zscore_normalize）
- research/
  - factor_research: モメンタム・ボラティリティ・バリューのファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）や統計サマリ
- strategy/
  - feature_engineering: 生ファクターを統合して features テーブルを作成
  - signal_generator: features + ai_scores を統合してシグナル生成
- execution/: 発注実装（雛形）
- monitoring/: 監視・モニタリング（雛形）
- config.py: .env 自動読み込み・環境設定（必須環境変数へのアクセスラッパ）

---

## 動作要件

- Python 3.10 以上（注: 構文に | 型注釈を使用）
- 必要な外部パッケージ（例）:
  - duckdb
  - defusedxml

（パッケージはプロジェクトの packaging / requirements に従ってインストールしてください）

---

## 環境変数

以下の環境変数を使用します（必須は明示）。プロジェクトルートの `.env` / `.env.local` を自動で読み込みます（無効化は下記参照）。

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD: kabuステーション API 用パスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

オプション（デフォルトあり）:
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: データベースパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: 起動時の .env 自動読み込みを無効化

例 `.env`（プロジェクトルート）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順（開発環境）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   - 基本:
     ```
     pip install duckdb defusedxml
     ```
   - 開発用にパッケージをインストールする場合（setup.py/pyproject があれば）:
     ```
     pip install -e .
     ```

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、環境変数として設定してください。
   - 自動ロードを無効化したい場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. DuckDB スキーマを初期化
   - Python REPL またはスクリプトで初期化します:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
     ```

---

## 使い方（主要ワークフロー例）

以下はライブラリ関数を直接呼び出す例です。運用ではこれらをスケジューラ（cron / Airflow 等）から実行します。

1) 日次 ETL を実行（市場カレンダー / 日足 / 財務）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
conn.close()
```

2) 特徴量の構築（features テーブルへのアップサート）
```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, target_date=date.today())
print("features upserted:", count)
conn.close()
```

3) シグナル生成（features + ai_scores を参照して signals に書き込む）
```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import generate_signals

conn = get_connection("data/kabusys.duckdb")
num = generate_signals(conn, target_date=date.today(), threshold=0.6)
print("signals generated:", num)
conn.close()
```

4) ニュース収集ジョブ（RSS から raw_news 保存・銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes は抽出に利用する有効銘柄コード集合（省略可能）
known_codes = {"7203", "6758", "9984"}
res_map = run_news_collection(conn, known_codes=known_codes)
print(res_map)
conn.close()
```

5) カレンダー更新ジョブ（JPX カレンダーを更新）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("calendar saved:", saved)
conn.close()
```

注意:
- 上記はライブラリ API を直接利用する例です。実運用ではログ出力設定、例外ハンドリング、ジョブのリトライや通知（Slack 等）を組み合わせてください。
- ETL / API 呼び出しは外部ネットワークと連携するため、環境変数の設定とネットワークアクセス権限が必要です。

---

## 開発・デバッグのヒント

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）を起点に行われます。テスト時に自動読み込みを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB に対するスキーマ初期化は init_schema() を使用します。既存テーブルがある場合は安全にスキップされます。
- J-Quants API へのリクエストは内部でレート制御とリトライを行います。401 受信時はトークン自動更新を行います。
- RSS フェッチには SSRF や XML Bomb 対策（スキーム検証、プライベートアドレス除外、受信サイズ上限、defusedxml）を組み込んでいます。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイル/モジュール:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - stats.py
    - pipeline.py
    - calendar_management.py
    - features.py
    - audit.py
    - audit (続きの DDL/インデックス定義が含まれます)
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
  - monitoring/
    - (監視関連モジュール: テンプレート / 実装ファイル)

各ファイルは README にて説明した機能単位で分割されています。詳細はソース内の docstring を参照してください。

---

## 貢献 / 問い合わせ

バグ修正や機能追加は Pull Request を歓迎します。Issue には再現手順・ログ・環境（Python バージョン・DuckDB バージョン等）を添えてください。

---

この README はコードベースの主要機能をまとめた概略ドキュメントです。より詳細な仕様（StrategyModel.md / DataPlatform.md 等）がリポジトリにある場合はそちらを参照してください。