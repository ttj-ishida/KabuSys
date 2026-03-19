# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（プロトタイプ）です。  
DuckDB をデータストア、J-Quants をデータソースとして想定し、データ取得（ETL）→特徴量作成→シグナル生成→発注監査までの主要機能を含みます。

バージョン: 0.1.0

---


## プロジェクト概要

KabuSys は以下の目的を持ったモジュール群で構成されています。

- J-Quants API から市場データ（株価・財務・カレンダー等）を安全に取得・保存
- DuckDB 上にデータスキーマを構築し、ETL（差分更新・バックフィル）を実行
- 研究（research）で作成した生ファクターを用いて特徴量を生成（正規化・ユニバースフィルタ）
- 正規化済み特徴量＋AIスコア等を統合して売買シグナルを生成
- ニュース（RSS）収集と銘柄紐付け
- 発注・約定・監査ログ用のスキーマ（監査トレーサビリティ設計）

設計方針としては「ルックアヘッドバイアス回避」「冪等性」「外部依存の最小化」「安全性（SSRF対策等）」を重視しています。


## 主な機能（抜粋）

- データ取得（J-Quants）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - レート制限・リトライ・トークン自動リフレッシュ実装（jquants_client）
- データ保存（DuckDB）
  - raw_prices, raw_financials, market_calendar 等の冪等保存（ON CONFLICT）
  - スキーマ初期化ユーティリティ（data.schema.init_schema）
- ETL パイプライン
  - 日次差分ETL（run_daily_etl）: カレンダー→株価→財務→品質チェック
  - 差分・バックフィルロジックをサポート
- 研究・特徴量
  - ファクター計算（momentum / volatility / value）
  - Zスコア正規化ユーティリティ（data.stats.zscore_normalize）
  - 特徴量構築（strategy.feature_engineering.build_features）
- シグナル生成
  - feature + ai_scores を統合して final_score 計算（strategy.signal_generator.generate_signals）
  - Bear レジーム抑制、BUY/SELL の日次置換（冪等）
  - エグジット条件（ストップロス等）
- ニュース収集
  - RSS フィード取得、前処理、記事ID生成、raw_news 保存、銘柄抽出（news_collector）
  - SSRF 防止・受信サイズ制限・XML 安全パーサ利用
- カレンダー管理
  - 営業日判定、next/prev_trading_day、calendar_update_job 等
- 監査ログ（audit）: signal_events / order_requests / executions など（設計重視）

---


## 要件

- Python 3.10+
- 必須パッケージ（代表）
  - duckdb
  - defusedxml

（プロジェクトに pyproject.toml / requirements.txt がある場合はそちらを参照してください）


## セットアップ手順

1. リポジトリをクローン（省略可）
   git clone <repo-url>

2. Python 仮想環境を作成・有効化
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール
   pip install duckdb defusedxml

   （プロジェクトに requirements がある場合は `pip install -r requirements.txt`）

4. パッケージをプロジェクト直下のソースから実行する場合
   - 開発環境が pip editable install をサポートしている場合:
     pip install -e .
   - あるいはスクリプト実行時に PYTHONPATH を設定:
     PYTHONPATH=src python path/to/script.py

5. DuckDB スキーマ初期化（例）
   python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

---


## 環境変数（設定）

自動で .env / .env.local をプロジェクトルートから読み込む仕組みがあります（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（発注連携時）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネルID

任意・デフォルトあり:
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"（デフォルト: INFO）

.env の例:
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=yyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development

---


## 使い方（代表的な API / 実行例）

以下はインタラクティブまたはスクリプトから呼ぶ簡単な例です。すべて DuckDB 接続オブジェクト（duckdb.connect() の返り値）を受け取ります。

- スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL 実行
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量構築（features テーブル作成）
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2025, 1, 31))
print("built features:", count)
```

- シグナル生成（signals テーブル書き込み）
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
num = generate_signals(conn, target_date=date(2025, 1, 31))
print("signals written:", num)
```

- ニュース収集ジョブ（RSS 収集 → raw_news 保存）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes に有効な銘柄コードセットを渡すと銘柄紐付けを行う
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(res)
```

- J-Quants からデータを直接取得する（テスト用途）
```python
from kabusys.data.jquants_client import fetch_daily_quotes
quotes = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
print(len(quotes))
```

---


## ディレクトリ構成（主要ファイル）

（プロジェクトの src/kabusys 以下を抜粋）

- src/kabusys/__init__.py
- src/kabusys/config.py
  - 環境変数の自動ロード・Settings クラス
- src/kabusys/data/
  - jquants_client.py — J-Quants API クライアント、レート制限・リトライ・保存関数
  - news_collector.py — RSS 取得・前処理・DB保存・銘柄抽出
  - schema.py — DuckDB スキーマ定義 / init_schema / get_connection
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - calendar_management.py — 市場カレンダー管理・営業日判定
  - features.py — data.stats のエクスポート
  - audit.py — 監査ログスキーマ（signal_events, order_requests, executions 等）
- src/kabusys/research/
  - factor_research.py — momentum / volatility / value 等のファクター計算
  - feature_exploration.py — 将来リターン計算・IC・統計サマリ
- src/kabusys/strategy/
  - feature_engineering.py — features テーブル構築（正規化・ユニバースフィルタ）
  - signal_generator.py — final_score 計算・BUY/SELL 生成・signals 保存
- src/kabusys/execution/   (発注レイヤー・将来的な実装想定)
- src/kabusys/monitoring/  (監視用ユーティリティ等、将来的な実装想定)

注: audit.py やその他一部モジュールはスキーマ定義や設計方針が中心で、運用側の接続実装や外部ブローカー連携は別途実装が必要です。

---


## 注意事項 / 運用上のポイント

- 本ライブラリは実運用を前提とした設計指針を示していますが、実際の資金を使う前に徹底したテスト（ペーパートレード）とコードレビューが必要です。
- 発注（execution）やブローカー連携は慎重に実装・テストしてください（冪等性・エラー耐性・監査ログを必須に）。
- J-Quants の API レート制限や認証周りは jquants_client に組み込まれていますが、運用時は追加のモニタリングやスロットリング調整を検討してください。
- データスキーマは DuckDB のバージョンや将来の要件で変更される可能性があります。マイグレーション方法を別途設計してください。
- 環境変数の自動ロードはプロジェクトルートの .env / .env.local を読み込みます。CI 等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

もし README に追加したい項目（例: CLI コマンド一覧、CI/デプロイ手順、より詳細なスキーマ図など）があれば教えてください。必要に応じてサンプル .env.example や起動スクリプトのテンプレートも作成します。