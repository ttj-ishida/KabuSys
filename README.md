# KabuSys

日本株向け自動売買基盤（ライブラリ）  
本リポジトリは、J-Quants API などから市場データを取得・保存し、ファクター計算・特徴量生成・シグナル生成を行うためのモジュール群を提供します。DuckDB をデータ層として利用し、研究（research）・データ（data）・戦略（strategy）・実行（execution）・監査（audit）を分離した設計になっています。

主な用途:
- 市場データ（株価・財務・カレンダー）の差分ETL
- ファクター計算（Momentum / Volatility / Value 等）
- 特徴量（features）構築・正規化
- シグナル（BUY/SELL）生成ロジック
- ニュース収集・銘柄抽出
- DuckDB スキーマ初期化と監査テーブル定義

---

## 機能一覧

- data/
  - jquants_client: J-Quants API クライアント（トークン自動リフレッシュ、レート制限、リトライ）
  - pipeline: 日次差分ETL（市場カレンダー、株価、財務）
  - schema: DuckDB スキーマの定義と初期化（Raw / Processed / Feature / Execution 層）
  - news_collector: RSS 取得／前処理／DB 保存（SSRF対策・トラッキング除去）
  - calendar_management: 営業日判定やカレンダーの夜間更新ジョブ
  - stats: Zスコア正規化などの統計ユーティリティ
- research/
  - factor_research: モメンタム／ボラティリティ／バリュー等のファクター計算
  - feature_exploration: 将来リターン計算、IC 計算、ファクターサマリー
- strategy/
  - feature_engineering: research の生ファクターをマージして features テーブルへ保存
  - signal_generator: features と ai_scores を統合して final_score を算出、BUY/SELL シグナル生成
- config: 環境変数／.env 自動読み込みと設定管理
- execution / monitoring / audit: 実行・監視・監査用のスキーマ／インターフェース類（実装の拡張を想定）

設計上の特徴:
- ルックアヘッドバイアスを避ける設計（target_date 時点のデータのみを使用）
- DuckDB を用いた冪等な保存（ON CONFLICT / トランザクション）
- J-Quants API のレート制御・リトライ・トークン管理
- RSS 収集でのセキュリティ対策（SSRF、XML 脆弱性、サイズ制限）

---

## 必要条件

- Python 3.9+
- 必要な外部パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS フィード）

（プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを参照してください。ここではコードからの推定依存を記載しています。）

---

## インストール（ローカル開発）

1. レポジトリをクローン:
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成して有効化:
   ```
   python -m venv .venv
   source .venv/bin/activate   # POSIX
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール（例）:
   ```
   pip install duckdb defusedxml
   pip install -e .   # パッケージとしてインストールする場合（セットアップがあれば）
   ```

---

## 設定（環境変数 / .env）

config モジュールはプロジェクトルート（.git または pyproject.toml を基準）から自動で `.env` / `.env.local` を読み込みます。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

主要な環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL: ログ出力レベル ("DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL")

例（.env）:
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

## クイックスタート（主要な操作例）

以下は Python スクリプトからライブラリを利用する基本的な流れ例です。

1) DuckDB スキーマ初期化:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL 実行（市場カレンダー・株価・財務の差分取得）:
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定しなければ今日（内部で営業日に調整）
print(result.to_dict())
```

3) 特徴量（features）構築:
```python
from kabusys.strategy import build_features
from datetime import date
n = build_features(conn, target_date=date(2024, 1, 10))
print(f"features upserted: {n}")
```

4) シグナル生成:
```python
from kabusys.strategy import generate_signals
from datetime import date
count = generate_signals(conn, target_date=date(2024, 1, 10), threshold=0.6)
print(f"signals generated: {count}")
```

5) ニュース収集ジョブ:
```python
from kabusys.data.news_collector import run_news_collection
# known_codes は銘柄抽出に使う有効なコードの set（例: {'7203', '6758', ...}）
results = run_news_collection(conn, known_codes={'7203','6758'})
print(results)  # {source_name: 新規保存件数}
```

6) カレンダー更新ジョブ（夜間バッチ想定）:
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

注意:
- ETL／news collection 等は外部 API に依存するため、実行前に環境変数の設定（JQUANTS_REFRESH_TOKEN など）が必要です。
- 各処理はトランザクションや冪等性（ON CONFLICT）を考慮して実装されています。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 読み込みと Settings クラス
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存ユーティリティ）
    - schema.py              — DuckDB スキーマ定義・初期化
    - pipeline.py            — ETL パイプライン（日次 ETL 他）
    - news_collector.py      — RSS 取得・前処理・DB 保存
    - calendar_management.py — カレンダー管理 / 営業日判定 / update job
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - features.py            — data.stats の再エクスポート
    - audit.py               — 監査ログ用スキーマ定義（signal_events, order_requests, executions 等）
  - research/
    - __init__.py
    - factor_research.py     — momentum / volatility / value の計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — features テーブル構築処理
    - signal_generator.py    — final_score 計算と signals テーブル生成
  - execution/               — 実行層（空 placeholder / 実装想定）
  - monitoring/              — 監視層（空 placeholder / 実装想定）

各モジュールはソース内の docstring に詳細な設計方針・処理フローが記載されています。内部 API（関数名）を参照して利用してください。

---

## 開発・貢献

- コードの変更を行う際はユニットテスト（該当する場合）を追加してください。
- 外部 API を叩く箇所（jquants_client, news_collector など）は依存注入／モックが可能な設計です。ユニットテストではモックを使って外部通信を遮断してください。
- .env.example を用意して環境変数のドキュメント化を行うことを推奨します。

---

## 補足

- 本プロジェクトは実トレードに用いる前に十分な検証（バックテスト・ペーパートレード）を実施してください。
- KABUSYS_ENV により挙動を変える想定（development / paper_trading / live）です。実運用時は十分な権限管理・監査・監視を行ってください。

---

以上。README の内容はコード内 docstring・関数名・設定項目に基づいています。追加で CI / 実行スクリプト / 既存の requirements や pyproject.toml を反映したい場合は、そのファイル群を提供してください。