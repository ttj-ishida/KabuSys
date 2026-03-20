# KabuSys

日本株向けの自動売買／データプラットフォームライブラリです。  
株価・財務・ニュースを収集して DuckDB に蓄積し、研究/戦略モジュールで特徴量を生成、シグナル化して実行層へ受け渡すことを想定したモジュール群を提供します。

---

## プロジェクト概要

KabuSys は以下の責務を持つコンポーネントで構成されたシステムです。

- データ収集（J-Quants API、RSS）
- データ格納（DuckDB スキーマ定義・初期化）
- ETL パイプライン（差分取得、品質チェック）
- 研究用ファクター計算（モメンタム／ボラティリティ／バリュー等）
- 特徴量エンジニアリング（正規化・ユニバースフィルタ）
- シグナル生成（最終スコア計算、BUY/SELL 判定）
- 発注／監査／モニタリングのためのスケルトン（execution / monitoring）

設計方針の一部：
- ルックアヘッドバイアスを避けるため、各処理は target_date 時点で利用可能なデータのみを使用します。
- DuckDB をローカル DB として採用し、ON CONFLICT 等を用いて冪等性を担保します。
- 外部通信はレート制御、リトライ、トークン自動更新など安全策を実装しています。

---

## 主な機能一覧

- 環境設定読み込み（.env / OS 環境変数、自動ロード／無効化オプション）
- DuckDB スキーマ定義と初期化（init_schema）
- J-Quants API クライアント
  - 株価日足、財務データ、市場カレンダー取得（ページネーション対応）
  - レートリミット制御、リトライ、トークン自動更新
  - DuckDB への冪等保存（save_daily_quotes / save_financial_statements / save_market_calendar）
- ETL パイプライン（run_daily_etl）
  - 差分取得、バックフィル、品質チェック呼び出し
- ニュース収集（RSS）と DB 保存（fetch_rss / save_raw_news / run_news_collection）
  - SSRF 対策、XML 攻撃対策（defusedxml）、トラッキングパラメータ除去、記事ID は正規化 URL の SHA-256（先頭32文字）
- 研究用ファクター計算（calc_momentum / calc_volatility / calc_value）
- 特徴量エンジニアリング（build_features）
  - ユニバースフィルタ、Z スコア正規化、±3 クリップ、features テーブルへの UPSERT（日付単位で置換）
- シグナル生成（generate_signals）
  - 特徴量 + ai_scores を統合して final_score を算出、Bear レジーム抑制、BUY / SELL 判定、signals テーブルへの日付単位置換
- 統計ユーティリティ（zscore_normalize、IC / ランク計算、要約統計）

---

## 事前準備 / セットアップ

要求環境（目安）
- Python 3.10 以上（型ヒントの | 演算子等を使用）
- DuckDB（Python パッケージ）
- defusedxml（RSS/XML 用）
- （任意）その他の運用ライブラリ（logging 等は標準ライブラリ）

例：仮想環境を作成して必要パッケージを入れる
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# パッケージとしてプロジェクトを編集可能インストールする場合
pip install -e .
```

環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（省略時 http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知に使用する Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite のパス（デフォルト data/monitoring.db）
- KABUSYS_ENV: environment（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化する場合は 1 を設定

.env ファイルはプロジェクトルート（.git または pyproject.toml を起点に検出）に置くと、自動で読み込まれます（.env → .env.local の順で上書き）。自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。

---

## データベース初期化

DuckDB スキーマを作成する例：

Python スクリプト/REPL から
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)  # settings.duckdb_path は Path オブジェクト
# conn は duckdb.DuckDBPyConnection
```

インメモリで試す場合：
```python
from kabusys.data.schema import init_schema
conn = init_schema(":memory:")
```

---

## 使い方（代表的なワークフロー例）

1. ETL（日次データ収集）
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)  # 初回は init_schema を呼ぶ
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2. 特徴量作成（features テーブルへの投入）
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features

conn = get_connection(settings.duckdb_path)
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

3. シグナル生成
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import get_connection
from kabusys.strategy import generate_signals

conn = get_connection(settings.duckdb_path)
n_signals = generate_signals(conn, target_date=date.today(), threshold=0.60)
print(f"signals generated: {n_signals}")
```

4. ニュース収集（RSS）
```python
from kabusys.config import settings
from kabusys.data.schema import get_connection
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = get_connection(settings.duckdb_path)
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(results)
```

注意点：
- 各処理は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取り DB を直接更新します。
- build_features / generate_signals は target_date に対して日付単位で既存データを削除してから挿入するため冪等性が保たれます。
- J-Quants API 呼び出しはレート制御・再試行・401 時のトークン自動リフレッシュを行います。

---

## 簡単な CLI/ジョブ化

上記のスクリプトを cron / systemd timer / Airflow 等から呼び出して日次バッチ化する想定です。運用時には以下を検討してください：

- ログ設定（LOG_LEVEL, ログローテーション）
- バックアップ／スナップショット（DuckDB ファイルの扱い）
- モニタリング（Slack 通知等）
- 本番では KABUSYS_ENV を "live" に設定し、paper_trading などで挙動を切り替える実装を活用

---

## 主要モジュール・ディレクトリ構成

リポジトリ配下の主要構成（src/kabusys）:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み、Settings クラス（各種キーとシステムフラグを提供）
  - data/
    - __init__.py
    - schema.py           — DuckDB スキーマ定義と init_schema / get_connection
    - jquants_client.py   — J-Quants API クライアント（fetch_* / save_*）
    - pipeline.py         — ETL パイプライン（run_daily_etl 他）
    - news_collector.py   — RSS 取得・パース・DB 保存
    - features.py         — zscore_normalize の再エクスポート
    - stats.py            — 統計ユーティリティ（zscore_normalize）
    - calendar_management.py — market_calendar 関連ユーティリティ
    - audit.py            — 監査ログ用テーブル定義 / 初期化（トレーサビリティ）
    - (その他: quality, etc. を参照する想定)
  - research/
    - __init__.py
    - factor_research.py  — calc_momentum / calc_volatility / calc_value
    - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank
  - strategy/
    - __init__.py
    - feature_engineering.py — build_features（正規化、ユニバースフィルタ、写し込み）
    - signal_generator.py    — generate_signals（final_score 計算、BUY/SELL 判定）
  - execution/
    - __init__.py
    - （発注・ブローカー連携の実装を追加する想定）
  - monitoring/
    - （監視・レポーティング関連の実装を追加する想定）

各モジュールはドキュメンテーション文字列（docstring）で設計方針・処理フローが記載されています。README 上の使用例はライブラリ API を直接呼び出すシンプルなものです。

---

## 設定 / 運用に関する注意

- 環境変数が不足していると Settings のプロパティが ValueError を送出します（必須項目を確認してください）。
- J-Quants API の呼び出しではレート制限（120 req/min）を厳守しています。大量取得時は時間がかかる点に注意してください。
- ニュース収集では外部 URL の安全性（SSRF, private IP, XML bomb 等）に対する防御を行っていますが、運用時の例外ハンドリング・監視は必須です。
- DuckDB のバージョンに依存する機能（制約、INDEX、RETURNING 等）があるため、使用する DuckDB のバージョン互換性に注意してください。
- schema.init_schema は ON CONFLICT や INDEX 作成などを行い、既存 DB に対して冪等にスキーマを適用します。

---

もし README をテンプレート（.env.example）や具体的な cron ジョブ例、より詳細な運用手順（Slack 通知や kabu API と連携する execution 層の実装例など）へ拡張したい場合は、その用途（開発環境 / テスト / 本番）を教えてください。さらに具体的なサンプルスクリプトを作成します。