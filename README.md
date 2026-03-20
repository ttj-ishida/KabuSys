# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買・データ基盤ライブラリです。J-Quants や RSS を用いて市場データ・財務・ニュースを収集・保存し、研究で作成した生ファクターを正規化・統合して戦略シグナルを生成することを目的とします。データ永続化には DuckDB を使用します。

主な設計方針:
- ルックアヘッドバイアスを防ぐ（計算は target_date 時点のデータのみを使用）
- Idempotent（冪等）な DB 保存
- 外部 API 呼び出しはラップしてリトライ/レート制御/トークンリフレッシュを実装
- 本番発注層（execution）への直接依存は基本持たない（監査/発注テーブルは定義済み）

---

## 機能一覧

- データ収集
  - J-Quants API クライアント（株価日足、財務データ、マーケットカレンダー）
    - レートリミット制御、リトライ、401 の自動トークンリフレッシュ
  - RSS ベースのニュース収集（SSRF 対策、トラッキングパラメータ削除、記事IDは正規化 URL の SHA256）
- データ永続化（DuckDB）
  - Raw / Processed / Feature / Execution 層のスキーマ定義と初期化
  - Idempotent な保存関数（ON CONFLICT DO UPDATE / DO NOTHING）
- ETL パイプライン
  - 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 差分取得・バックフィル対応
- 研究・戦略
  - ファクター計算（momentum / volatility / value 等）
  - クロスセクション Z スコア正規化ユーティリティ
  - 特徴量ビルド（build_features）
  - シグナル生成（generate_signals）：final_score の集約、BUY/SELL 生成、Bear レジーム抑制、SELL 優先ポリシー
- ニュース処理
  - RSS 取得・保存・銘柄抽出・ニュース⇄銘柄紐付け
- マーケットカレンダー管理（営業日判定、next/prev/get_trading_days、夜間更新ジョブ）
- 監査テーブル（signal → order → execution のトレーサビリティ構造）

---

## 前提 / 要件

- Python 3.10 以上（型ヒントに union 型（|）を利用）
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml

必要に応じてプロジェクトに requirements.txt を用意して pip install してください。

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

---

## 環境変数 / 設定

プロジェクトは .env（および .env.local）から設定を自動読み込みします（CWD ではなくパッケージ位置からプロジェクトルートを探索）。自動読み込みを無効化するには環境変数を設定します:

- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須の環境変数（Settings 参照）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabu ステーション API パスワード（発注等で使用）
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

任意 / デフォルト:
- KABUS_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

注意:
- settings 属性は kabusys.config.settings で提供され、コード内で参照できます。
- 必須値が未設定の場合は Settings が ValueError を投げます。

---

## セットアップ手順

1. リポジトリをクローン
```
git clone <repo-url>
cd <repo-dir>
```

2. 仮想環境作成・依存インストール
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# 実プロジェクトでは requirements.txt を用意して `pip install -r requirements.txt`
```

3. 環境変数設定
- プロジェクトルートに `.env` を作成（.env.example を参考に）
例（最小）:
```
JQUANTS_REFRESH_TOKEN=xxxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

4. DuckDB スキーマ初期化
Python REPL またはスクリプトで:
```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.config import settings

db_path = settings.duckdb_path  # Path オブジェクト
conn = init_schema(db_path)     # テーブル作成済みの DuckDB 接続が返る
```

---

## 使い方（主要な操作例）

以下は代表的な利用フロー例です。各関数はモジュールごとに分かれており、テストやバッチジョブから直接呼ぶ想定です。

- 日次 ETL（市場カレンダー・株価・財務・品質チェック）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量作成（build_features）
```python
from datetime import date
from kabusys.data.schema import get_connection, init_schema
from kabusys.strategy import build_features
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
n = build_features(conn, target_date=date.today())
print(f"built features for {n} codes")
```

- シグナル生成（generate_signals）
```python
from datetime import date
from kabusys.data.schema import get_connection, init_schema
from kabusys.strategy import generate_signals
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals generated: {count}")
```

- ニュース収集（RSS）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# known_codes を渡すと記事中の4桁コード抽出で絞り込む
known_codes = {"7203", "6758", "6954"}
res = run_news_collection(conn, sources=None, known_codes=known_codes, timeout=30)
print(res)  # ソースごとの新規保存件数
```

- J-Quants 生データ取得（クライアントを直接使う例）
```python
from kabusys.data import jquants_client as jq
from datetime import date

# トークンは settings から自動で取得・リフレッシュされます
quotes = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```

---

## よく使うモジュールと API

- kabusys.config
  - settings: 環境変数ベースの設定オブジェクト

- kabusys.data.schema
  - init_schema(db_path): DuckDB スキーマ初期化
  - get_connection(db_path): 既存 DB 接続

- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_* 関数で DuckDB に保存（冪等）

- kabusys.data.pipeline
  - run_daily_etl(...): 日次 ETL の統合エントリポイント

- kabusys.research
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank

- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold, weights)

- kabusys.data.news_collector
  - fetch_rss(url, source) / save_raw_news / run_news_collection

---

## 運用上の注意

- 環境（KABUSYS_ENV）は development / paper_trading / live のいずれかを指定してください。is_live フラグ等で挙動分岐できます。
- J-Quants のリクエストレートは 120 req/min に制限されています。クライアントは内部でレート制御を行いますが、大規模取得の際は注意してください。
- DuckDB に対するトランザクションは一部手動で扱われます（BEGIN/COMMIT/ROLLBACK）。長時間のトランザクションや並列書き込みは避けてください。
- ニュース収集では外部 URL の正規化や SSRF 対策を実装していますが、運用時のソース管理は慎重に行ってください。
- execution（発注）層は本リポジトリでスキーマと一部インタフェースを用意していますが、実際のブローカー接続や自動発注ロジックは運用ポリシーに沿って実装・テストしてください。特に live 環境での動作は十分な検証が必要です。

---

## ディレクトリ構成

（抜粋：src/kabusys を基準）
- kabusys/
  - __init__.py
  - config.py              — 環境変数/設定管理
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント + 保存処理
    - news_collector.py     — RSS ニュース収集・保存・銘柄抽出
    - schema.py             — DuckDB スキーマ定義 & 初期化
    - stats.py              — 統計ユーティリティ（zscore_normalize）
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py— マーケットカレンダー管理
    - features.py           — data レイヤの特徴量インターフェース
    - audit.py              — 監査ログ DDL（signal/order/execution トレース）
  - research/
    - __init__.py
    - factor_research.py    — ファクター計算（momentum/value/volatility）
    - feature_exploration.py— 研究用の IC/forward returns/summary 等
  - strategy/
    - __init__.py
    - feature_engineering.py— features テーブル作成ロジック（build_features）
    - signal_generator.py   — シグナル生成ロジック（generate_signals）
  - execution/              — 発注系（空の __init__ や今後の実装用）
  - monitoring/             — 監視・メトリクス（別モジュールに実装想定）

---

## 貢献・拡張案

- execution 層のブローカーアダプタ実装（kabuステーションとの統合）
- 品質チェックモジュール強化（quality モジュールが参照される想定）
- 並列 / バッチ最適化（大量データ取得時のパフォーマンスチューニング）
- テスト群の拡充（ユニット / 統合テスト、外部 API をモックした CI）

---

不明点や README に追加したい具体的な使い方（CLI サンプル、systemd ユニット、Dockerfile 等）があれば教えてください。必要に応じて README を拡張します。