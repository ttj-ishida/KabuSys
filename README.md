# KabuSys

日本株向け自動売買基盤（ライブラリ）です。データ取得（J-Quants）、DuckDB ベースのデータ管理、ファクター計算、特徴量エンジニアリング、シグナル生成、ニュース収集、ETL パイプライン、マーケットカレンダー管理、監査ログなどを含むモジュール群を提供します。

---

## 目次
- プロジェクト概要
- 主な機能
- 必要な環境変数
- セットアップ手順
- 使い方（簡易サンプル）
- ディレクトリ構成
- 補足・設計方針

---

## プロジェクト概要
KabuSys は日本株の自動売買システムの基盤ライブラリです。J-Quants API などから市場データ・財務データ・ニュースを取得して DuckDB に保存し、研究用ファクター計算、特徴量作成、AI スコア統合、売買シグナル生成、ETL バッチを実行できるように設計されています。発注ロジック（ブローカー連携）は execution 層で拡張することを想定しています。

主な設計方針:
- ルックアヘッドバイアス防止（target_date 時点のデータのみを使用）
- 冪等（idempotent）な DB 保存（ON CONFLICT / upsert）
- DuckDB をローカル永続化ストアとして利用
- 外部依存は最小化（標準ライブラリ中心、DuckDB / defusedxml 等のみ）

---

## 主な機能一覧
- データ取得・保存
  - J-Quants API クライアント（差分取得・ページネーション・トークン自動リフレッシュ・レートリミット・リトライ）
  - 株価日足（OHLCV）、財務データ、マーケットカレンダーの取得・保存
- データ管理
  - DuckDB スキーマ定義・初期化（raw / processed / feature / execution 層）
  - ETL パイプライン（差分更新・バックフィル・品質チェック）
- 研究・特徴量
  - ファクター計算（モメンタム / バリュー / ボラティリティ 等）
  - Z スコア正規化などの統計ユーティリティ
  - 特徴量構築（feature_engineering）
- 戦略
  - features と AI スコアを統合して final_score を算出し、BUY/SELL シグナルを生成
  - Bear レジーム抑制、ストップロス/スコア低下による売却判定など
- ニュース収集
  - RSS フィードの取得、前処理、raw_news / news_symbols への保存（SSRF 対策・XML 脆弱性対策）
- カレンダー管理
  - JPX マーケットカレンダーの取得 / 営業日判定 / next/prev_trading_day 等
- 監査ログ
  - signal → order_request → execution のトレースを保存する監査テーブル群

---

## 必要な環境変数
config.Settings クラスで参照される主要な環境変数（必須）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- SLACK_BOT_TOKEN (必須) — Slack 通知用 bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID

その他の任意/デフォルト値を持つ環境変数:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）。デフォルト "development"
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）。デフォルト "INFO"
- KABU_API_BASE_URL — kabuAPI のベース URL。デフォルト "http://localhost:18080/kabusapi"
- DUCKDB_PATH — DuckDB ファイルパス。デフォルト "data/kabusys.duckdb"
- SQLITE_PATH — sqlite（監視用 DB）パス。デフォルト "data/monitoring.db"
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する場合に "1" を設定

自動 .env ロード:
- パッケージ import 時にプロジェクトルート（.git または pyproject.toml を探索）を検出すると `.env` → `.env.local` の順で読み込みます。
  - `.env` は既存の OS 環境変数を上書きしません（override=False）。
  - `.env.local` は上書きする（override=True）ため開発環境での上書きに利用できます。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例（.env の最低構成）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
```

---

## セットアップ手順

1. Python 環境
   - Python 3.9+ を推奨（型注釈に | 型などを使用）
2. リポジトリをクローン / プロジェクトルートへ移動
3. 必要パッケージをインストール（最小）
   - duckdb
   - defusedxml
   例:
   ```
   python -m pip install duckdb defusedxml
   ```
   開発時はローカル editable インストール:
   ```
   python -m pip install -e .
   ```
   （本リポジトリに setup.cfg/pyproject.toml がある場合それに従ってください）
4. 環境変数をセット（またはプロジェクトルートに .env/.env.local を作成）
5. DuckDB スキーマ初期化
   - Python スクリプト例:
     ```python
     from kabusys.data.schema import init_schema
     init_schema("data/kabusys.duckdb")
     ```
   - :memory: を指定するとインメモリ DB を使用できます（テスト用）
6. ログ設定、監視、定期ジョブのセットアップは運用に応じて行ってください（cron/airflow 等）

---

## 使い方（代表的な API 例）

以下は代表的なワークフローの簡単な使用例です。実運用ではエラーハンドリングやログ出力を適切に行ってください。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL を走らせる（J-Quants から市場データ・財務データ・カレンダーを取得）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())
```

3) 特徴量（features）を構築
```python
from datetime import date
from kabusys.strategy import build_features

n = build_features(conn, target_date=date(2026, 1, 20))
print("upserted features:", n)
```

4) シグナル生成
```python
from kabusys.strategy import generate_signals
from datetime import date

count = generate_signals(conn, target_date=date(2026, 1, 20))
print("signals generated:", count)
```

5) ニュース収集ジョブ（RSS）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes は銘柄コードの集合（抽出用） e.g. {"7203", "6758", ...}
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203", "6758"})
print(res)
```

6) カレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print("calendar saved:", saved)
```

---

## ディレクトリ構成（主要ファイル / モジュール）
リポジトリ内 `src/kabusys/` を基準に主要モジュールを列挙します。

- kabusys/
  - __init__.py
  - config.py              — 環境変数 / 設定管理（.env 自動ロード含む）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント & DuckDB 保存ユーティリティ
    - news_collector.py     — RSS 収集・前処理・DB 保存
    - pipeline.py           — ETL パイプライン（daily_etl 等）
    - schema.py             — DuckDB スキーマ定義 / init_schema
    - stats.py              — 統計ユーティリティ（zscore_normalize）
    - features.py           — features 用再エクスポート
    - calendar_management.py— マーケットカレンダー管理・更新ジョブ
    - audit.py              — 監査ログテーブル定義（signal, order_request, execution 等）
    - quality.py?           — （品質チェックモジュールへの参照あり。実装ファイルはこの一覧に含まれていない可能性あり）
  - research/
    - __init__.py
    - factor_research.py    — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py— 将来リターン / IC / 統計サマリー等
  - strategy/
    - __init__.py
    - feature_engineering.py— raw factor → 正規化 → features テーブルへの upsert
    - signal_generator.py   — final_score 計算、BUY/SELL シグナル生成、signals 保存
  - execution/
    - __init__.py
    - ... (発注/ブローカー連携層の拡張想定)
  - monitoring/
    - ... (監視/メトリクス関連モジュール想定)

（上記はコードベースに含まれるモジュールの要約です。実際のファイルはプロジェクトルートの構成を参照してください。）

---

## 補足・設計上の注意点
- DuckDB のテーブルは多くが PRIMARY KEY を定義しており、保存関数は upsert（ON CONFLICT）を意識した実装です。複数プロセスから同時に書き込む場合はトランザクション/ロックの競合に注意してください。
- J-Quants API のレート制限（120 req/min）を踏まえた RateLimiter 実装がありますが、非常に大規模なバックフィルでは追加のレート制御が必要となる場合があります。
- ニュース収集は RSS の解析や外部 URL へアクセスするため SSRF 対策、XML パースの安全化（defusedxml）や受信バイト数制限などのセキュリティ機構を備えています。
- strategy 層は発注 API を直接呼ばない設計です。signals テーブルを生成した後に execution 層でオーダー作成→ブローカー送信を行う想定です。
- テスト時は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使い自動 .env ロードを無効化して手動で設定することを推奨します。

---

もし README に追記したいサンプルスクリプト、CI 設定、あるいは実行例（cron/airflow 用）などがあれば教えてください。必要に応じてサンプルの systemd/cron/airflow ジョブや Dockerfile 例も作成します。