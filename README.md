# KabuSys

日本株向けの自動売買システム用ライブラリ（モジュール群）。データ取得・ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、DuckDB スキーマ・監査ログなど、研究〜運用までの主要機能を備えます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要ワークフロー例）
- 環境変数 / 設定
- ディレクトリ構成
- 備考（設計方針・安全対策）

---

プロジェクト概要
----------------
KabuSys は日本株の自動売買パイプラインを構築するための内部ライブラリ群です。主な目的は次のとおりです。

- J-Quants API から株価・財務・カレンダー等のデータを差分取得して DuckDB に保存する ETL。
- 研究（research）で計算した生ファクターを正規化・統合し、戦略用特徴量（features）を作成。
- 正規化済みファクターと AI スコアを統合して売買シグナル（signals）を生成。
- RSS ベースのニュース収集と銘柄抽出（raw_news / news_symbols）。
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）。
- 発注〜約定〜監査ログのためのスキーマ定義（監査用テーブル群を含む）。

設計上、発注 API（kabuステーション等の実際のブローカー接続）への依存を最小化し、DuckDB を中心にデータを扱うことでローカルでも再現可能な研究／バックテスト環境を提供します。

機能一覧
--------
- データ取得（J-Quants）: 株価日足 / 財務データ / マーケットカレンダー（ページネーション・レート制御・リトライ・トークン自動更新対応）
- ETL パイプライン: 差分取得・バックフィル・品質チェック（quality モジュールと連携）
- DuckDB スキーマ初期化 / 接続ユーティリティ（init_schema / get_connection）
- 特徴量計算（研究モジュールと統合）
  - モメンタム、ボラティリティ、バリュー等の計算（prices_daily / raw_financials を参照）
  - Zスコア正規化ユーティリティ
- 戦略: feature_engineering.build_features / signal_generator.generate_signals
- ニュース収集: RSS フィード取得（SSRF 対策、サイズ制限、トラッキングパラメータ除去）、raw_news 保存、銘柄抽出
- マーケットカレンダー管理: is_trading_day / next_trading_day / prev_trading_day / calendar_update_job
- 監査ログスキーマ（signal_events / order_requests / executions など）
- ユーティリティ: URL 正規化、テキスト前処理、統計関数（zscore_normalize、rank、IC 計算）等

セットアップ手順
----------------
前提:
- Python 3.9+（typing 機能を利用）
- DuckDB が必要（Python パッケージとして duckdb をインストール）

1. リポジトリをチェックアウトする（パッケージ化されている想定）
   - 開発環境ではソースルートに移動して以下を実行：
     ```
     git clone <repo-url>
     cd <repo-dir>
     ```

2. 依存パッケージをインストールする
   - 最低必要: duckdb, defusedxml
   - 例:
     ```
     python -m pip install duckdb defusedxml
     ```
   - 実運用で Slack 通知等が必要な場合は slack-sdk 等を追加してください。

3. 環境変数の設定
   - 必須環境変数 (後述の「環境変数 / 設定」参照) をシェルや .env ファイルに設定します。
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただしテストなどで自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します）。

4. DuckDB スキーマ初期化
   - Python REPL もしくはスクリプトから次を実行して DB ファイルを作成・テーブルを初期化します。
     ```python
     from kabusys.data import schema
     from kabusys.config import settings

     # デフォルトでは settings.duckdb_path -> data/kabusys.duckdb
     conn = schema.init_schema(settings.duckdb_path)
     conn.close()
     ```
   - テストや一時利用ではインメモリ DB を使えます:
     ```python
     conn = schema.init_schema(":memory:")
     ```

使い方（主要ワークフロー例）
------------------------

1) 日次 ETL（株価・財務・カレンダー取得 + 品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection, init_schema
from kabusys.config import settings

# DB 初期化（まだなら）
conn = init_schema(settings.duckdb_path)

# 今日分の ETL を実行
result = run_daily_etl(conn, target_date=date.today())

print(result.to_dict())
conn.close()
```

2) 特徴量の構築（research の生ファクターを集約 → features へ保存）
```python
from datetime import date
import duckdb
from kabusys.strategy import build_features
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
conn.close()
```

3) シグナル生成（features + ai_scores を参照 → signals へ保存）
```python
from datetime import date
import duckdb
from kabusys.strategy import generate_signals
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {count}")
conn.close()
```

4) ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）
```python
import duckdb
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = duckdb.connect(str(settings.duckdb_path))
# known_codes を与えると記事中の4桁コード抽出→news_symbols に保存される
known_codes = {"7203", "6758", "9432", ...}
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
conn.close()
```

5) カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
saved = calendar_update_job(conn)
print(f"calendar rows saved: {saved}")
conn.close()
```

環境変数 / 設定
----------------
KabuSys は .env ファイルまたは環境変数から設定を読み込みます（config.Settings）。

主要な環境変数:
- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須): kabuステーション等の API パスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須): Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須): Slack 通知先チャネル ID
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 ("development" / "paper_trading" / "live")（デフォルト: development）
- LOG_LEVEL: ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")（デフォルト: INFO）

自動 .env ロード:
- パッケージ初期化時にプロジェクトルート（.git または pyproject.toml を親ディレクトリで探索）から `.env` と `.env.local` を自動ロードします。
- テスト等で自動ロードを無効化するには、環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                             — 環境変数/設定管理
  - data/
    - __init__.py
    - jquants_client.py                    — J-Quants API client（レート制御・リトライ・トークン管理）
    - news_collector.py                    — RSS 取得、前処理、DB 保存（SSRF/サイズ制限対策）
    - schema.py                            — DuckDB スキーマ定義 & init_schema
    - stats.py                             — zscore_normalize 等の統計ユーティリティ
    - pipeline.py                          — ETL パイプライン（run_daily_etl など）
    - calendar_management.py               — カレンダー判定・バッチ更新
    - audit.py                             — 監査ログ DDL
    - features.py                          — 公開インターフェース（zscore_normalize 再エクスポート）
  - research/
    - __init__.py
    - factor_research.py                   — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py               — forward returns / IC / summary 等
  - strategy/
    - __init__.py
    - feature_engineering.py               — features の生成（build_features）
    - signal_generator.py                  — シグナル生成（generate_signals）
  - execution/
    - __init__.py                          — （将来的な発注層）
  - monitoring/                            — （監視関連 DB/スクリプト想定）
  - その他のユーティリティやモジュール

備考（設計方針・安全対策）
------------------------
- ルックアヘッドバイアス防止: features / signals の計算は target_date 時点でシステムが利用可能なデータのみを使用するよう設計されています（fetched_at を保存してトレース可能）。
- J-Quants クライアント:
  - レート制限（120 req/min）に合わせた固定間隔レートリミッタを実装。
  - リトライ（指数バックオフ）、401 受信時のトークン自動リフレッシュ対応。
- ニュース収集:
  - RSS の XML パースは defusedxml を使用して XML Bomb 等を防止。
  - SSRF 対策: リダイレクト先のスキーム / プライベートアドレスチェック、最大受信バイト数制限、gzip 解凍後のサイズ検査。
  - URL 正規化とトラッキングパラメータ除去により記事IDを冪等に生成。
- DuckDB 保存は冪等（ON CONFLICT / DO UPDATE / DO NOTHING / RETURNING を活用）で複数回実行しても整合性を保てる設計。
- トランザクション管理: 複数挿入はトランザクションで囲み、失敗時はロールバックして安全性を確保。

開発・拡張のポイント
--------------------
- execution 層（発注ロジック）や broker インタフェースは最小限のスケルトンを残しているため、個別ブローカー実装を追加してください。
- AI スコア（ai_scores）や外部モデルは独立して更新可能で、signal_generator はそれらを参照して最終スコアを計算します。
- quality モジュール（品質チェック）は pipeline.run_daily_etl で呼ばれます。詳細なチェック実装や閾値は環境に合わせて調整してください。

ライセンス / 貢献
-----------------
この README に含まれる情報はコードベースに基づく概要です。実際の配布時には LICENSE や CONTRIBUTING のファイルを追加してください。

---

他に README に載せたい実行例や CI / テストの記述、あるいは依存リスト（requirements.txt）生成などの希望があれば教えてください。