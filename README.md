# KabuSys

KabuSys は日本株の自動売買基盤のプロトタイプ実装です。  
J-Quants などのデータソースから市場データを取得して DuckDB に保存し、研究（research）で算出したファクターを加工して特徴量を生成、戦略ロジックで売買シグナルを作成する一連のパイプラインを提供します。発注・実行・監視のためのスキーマも含まれ、全体の監査・トレーサビリティを意識して設計されています。

主な設計方針：
- ルックアヘッドバイアス回避（target_date 時点のデータのみを利用）
- DuckDB を中心としたローカル DB（大規模依存ライブラリを抑制）
- 冪等（idempotent）な DB 操作（ON CONFLICT / bulk insert）
- ネットワーク関連での安全対策（SSRF 防止・レスポンスサイズ制限）
- テストしやすい設計（トークン注入・内部関数のモックしやすさ）

---

## 機能一覧

- 環境変数 / 設定管理
  - 自動でプロジェクトルートの `.env`, `.env.local` を読み込む（必要に応じて無効化可能）
  - 必須環境変数の検査

- データ取得・保存（J-Quants クライアント）
  - 日足（OHLCV）・財務データ・マーケットカレンダーの取得（ページネーション対応）
  - レート制限・リトライ・トークン自動更新対応
  - DuckDB へ冪等保存（raw 層）

- ETL パイプライン
  - 差分取得（最終取得日に基づく差分）
  - バックフィル（後出し修正吸収）
  - 市場カレンダー・株価・財務データの統合 ETL（run_daily_etl）

- データスキーマ（DuckDB）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化（init_schema）

- 研究（research）モジュール
  - momentum / volatility / value などのファクター計算
  - 将来リターン（forward returns）・IC（Information Coefficient）・統計サマリー

- 特徴量エンジニアリング
  - ファクターの正規化（Zスコア）、ユニバースフィルタ、features テーブルへの保存（冪等）

- シグナル生成
  - features と ai_scores を統合して final_score を計算
  - Bear レジーム抑制、BUY/SELL シグナル生成、signals テーブルへの保存（冪等）
  - エグジット（ストップロス等）判定

- ニュース収集
  - RSS 取得・前処理・記事ID の正規化（SHA-256）・raw_news 保存
  - 銘柄コード抽出と news_symbols への紐付け
  - SSRF 対策・受信サイズ上限・XML 脆弱性対策（defusedxml）

- 監査ログ（audit）
  - signal → order_request → executions のトレースを残すためのスキーマと方針

---

## 必要条件 / 依存

- Python 3.10 以上（PEP 604 の union 型表記（X | Y）を使用）
- 必要なパッケージ（例）:
  - duckdb
  - defusedxml

インストール例（仮想環境推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# パッケージを編集可能インストール（リポジトリルートに pyproject.toml 等がある場合）
pip install -e .
```

（プロジェクトの pyproject.toml / requirements.txt があればそちらに従ってください）

---

## 環境変数（最低限必要なもの）

プロジェクトは環境変数から設定を取得します。最低限以下を設定してください（.env に書くのが便利です）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants の refresh token
- KABU_API_PASSWORD — kabu ステーション API のパスワード（発注連携に必要）
- SLACK_BOT_TOKEN — Slack 通知に使う Bot Token
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意／デフォルト:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化する（1 を設定）

.env の自動読込:
- プロジェクトルート（.git または pyproject.toml のあるディレクトリ）から `.env` と `.env.local` が自動で読み込まれます。
- 読み込み優先度: OS 環境 > .env.local > .env
- テストなどで自動読み込みを抑止するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## セットアップ手順（簡易）

1. リポジトリをクローンして仮想環境を用意
2. 依存パッケージをインストール（上記参照）
3. `.env` をプロジェクトルートに作成して必須変数を設定
   例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=your_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   ```
4. DuckDB スキーマを初期化
   Python REPL もしくはスクリプトで:
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)
   ```
   これによりデータディレクトリが自動作成され、必要なテーブルとインデックスが作成されます。

---

## 使い方（主要 API の例）

- 日次 ETL 実行（市場カレンダー → 株価 → 財務 → 品質チェック）
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)  # 初回のみ
result = run_daily_etl(conn)
print(result.to_dict())
```

- 特徴量生成（features テーブルに保存）
```python
from kabusys.strategy import build_features
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
n = build_features(conn, date(2024, 1, 10))
print(f"features upserted: {n}")
```

- シグナル生成
```python
from kabusys.strategy import generate_signals
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
count = generate_signals(conn, date(2024, 1, 10))
print(f"signals written: {count}")
```

- J-Quants から株価を直接取得（テストやデバッグ向け）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

# id_token を指定しない場合は設定された refresh token を用いて内部で取得します
records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,10))
print(len(records))
```

- RSS ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)
```

---

## ディレクトリ構成（主要ファイル）

以下は `src/kabusys` 以下の主要モジュール構成（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                     — 環境変数/設定管理（.env 自動読み込み）
  - data/
    - __init__.py
    - schema.py                    — DuckDB スキーマ定義と init_schema
    - jquants_client.py            — J-Quants API クライアント（取得・保存ユーティリティ）
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - news_collector.py            — RSS ニュース収集・前処理
    - features.py                  — zscore_normalize 再エクスポート
    - stats.py                     — 統計ユーティリティ（z-score 等）
    - calendar_management.py       — マーケットカレンダー管理
    - audit.py                     — 監査ログスキーマ（signal → order → execution）
  - research/
    - __init__.py
    - factor_research.py           — momentum/volatility/value 等のファクター計算
    - feature_exploration.py       — forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py       — ファクター正規化・features 生成
    - signal_generator.py          — final_score 計算・BUY/SELL シグナル作成
  - execution/                      — 発注・証券会社連携（骨組み）
  - monitoring/                     — モニタリング・アラート関連（骨組み）

（実装状況はモジュールごとに差があります。README 中の使用例は既実装の API を想定しています）

---

## 注意点 / 実運用に向けたメモ

- 本プロジェクトは自動売買のための基盤コンポーネントの集合であり、実際のライブ運用には追加のリスク管理、ネットワーク・認証の堅牢化、監査・バックアップ方針、証券会社 API の実装と十分なテストが必要です。
- 環境変数、認証情報、シークレットは適切に保護してください。
- DuckDB のファイルはローカルに保存されます。バックアップやストレージ管理を検討してください。
- ニュース収集や外部 API 呼び出し時はレート制限・取得失敗・パースエラーをハンドリングする設計になっていますが、運用では監視とアラートの整備が必要です。

---

## 貢献 / テスト

- 変更や機能追加は PR ベースでお願いします。ユニットテスト・静的解析を追加するとマージが容易になります。
- テスト実行、CI 設定、パッケージングはプロジェクトルートの設定に従ってください（pyproject.toml / setup 等）。

---

この README はコードベース（src/kabusys 以下）を参照して作成しています。追加で README に記載したいサンプルコマンドや運用手順があれば教えてください。