# KabuSys — 日本株自動売買システム README (日本語)

KabuSys は日本株向けのデータ基盤・特徴量計算・シグナル生成・ETL を備えた自動売買フレームワークです。
本リポジトリは Data / Research / Strategy / Execution 層を分離して実装しており、DuckDB を中心としたローカルデータベースでの冪等なデータ保存と、
J-Quants API 等からのデータ収集、RSS ニュース収集、特徴量正規化、スコア統合 → シグナル生成までのワークフローを提供します。

主な設計方針:
- ルックアヘッドバイアスの排除（target_date 時点のデータのみを参照）
- 冪等性（INSERT ... ON CONFLICT / トランザクション）
- 外部 API 呼び出しは data 層に集約
- テスト可能なインタフェース（id_token 注入など）
- セキュリティ対策（RSS の SSRF 対策、XML パースの安全化 等）

---

## 目次
- プロジェクト概要
- 機能一覧
- 前提条件 / 必要ライブラリ
- セットアップ手順
- 環境変数 (.env) の設定例
- 基本的な使い方（コード例）
  - DB 初期化
  - 日次 ETL 実行
  - 特徴量構築
  - シグナル生成
  - ニュース収集・銘柄抽出
  - カレンダー更新ジョブ
- ディレクトリ構成（主要ファイルと説明）
- 注意事項 / 実装ノート

---

## プロジェクト概要
KabuSys は以下のレイヤーを含みます。
- Data: J-Quants クライアント、ETL パイプライン、DuckDB スキーマ、ニュース収集、カレンダー管理、統計ユーティリティ
- Research: ファクター計算（モメンタム / ボラティリティ / バリュー）やファクター探索（IC・統計サマリ）
- Strategy: 特徴量エンジニアリング（正規化・ユニバースフィルタ）およびシグナル生成（最終スコア算出、BUY/SELL 判定）
- Execution: 発注・約定・ポジション管理のインタフェース（実装は層として分離）
- Monitoring: 監視・アラート連携（Slack 等。設定は環境変数経由）

---

## 機能一覧
- J-Quants API からの株価・財務・カレンダー取得（ページネーション対応、トークン自動リフレッシュ、レート制御・リトライ）
- DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分更新、バックフィル、品質チェック呼び出し）
- ファクター計算（mom_1m / mom_3m / mom_6m / ma200_dev、atr, volume_ratio, per, roe など）
- クロスセクション Z スコア正規化（data.stats.zscore_normalize）
- 特徴量構築（build_features: 正規化・ユニバースフィルタ・日付単位で冪等保存）
- シグナル生成（generate_signals: コンポーネントスコア統合、Bear レジーム抑制、BUY/SELL 書き込み）
- RSS からのニュース収集（SSRF / XML 攻撃防止、トラッキングパラメータ除去、銘柄コード抽出）
- マーケットカレンダー管理（営業日判定、next/prev trading day、夜間更新ジョブ）
- 監査ログスキーマ（signal_events, order_requests, executions 等）

---

## 前提条件 / 必要ライブラリ
- Python 3.9+（コードは型ヒントで | を利用しているため 3.10 を想定する箇所がありますが、typing の backport によって 3.9 でも動く可能性あり）
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- 標準ライブラリ以外は requirements.txt / pyproject.toml に依存関係を記載してください（本 README には最小限を示します）。

インストール例:
```
pip install duckdb defusedxml
# またはプロジェクトに pyproject.toml があれば
pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ
2. 必要な Python パッケージをインストール
   - 例: pip install -r requirements.txt または pip install duckdb defusedxml
3. 環境変数設定（.env をプロジェクトルートに配置）
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
   - 任意: DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL
   - config モジュールはプロジェクトルート（.git または pyproject.toml がある親階層）から自動で .env/.env.local を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
4. DuckDB スキーマ初期化（例: data/schema.init_schema）
   - Python REPL またはスクリプトで次を実行:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
     ```
5. ETL 実行・特徴量構築・シグナル生成は以下の節参照

---

## 環境変数 (.env) の設定例
プロジェクトルートに .env を置くと自動読み込みされます（優先順: OS 環境 > .env.local > .env）。

例 (.env):
```
JQUANTS_REFRESH_TOKEN=あなたの_jquants_refresh_token
KABU_API_PASSWORD=あなたの_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意:
- 環境変数が必須で未設定の場合、config.Settings の対応プロパティで ValueError を送出します。
- 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト時の利用想定）。

---

## 基本的な使い方（コード例）

以下は最小の実行例（DuckDB にスキーマ初期化 → 日次 ETL → 特徴量構築 → シグナル生成）。

1) DB 初期化
```python
from datetime import date
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL 実行（J-Quants API からデータを取得して保存）
```python
from kabusys.data.pipeline import run_daily_etl
# target_date を指定しない場合は今日が対象
result = run_daily_etl(conn)
print(result.to_dict())
```

3) 特徴量構築（features テーブルへ日付単位でアップサート）
```python
from kabusys.strategy import build_features
build_count = build_features(conn, date.today())
print(f"features upserted: {build_count}")
```

4) シグナル生成（signals テーブルへ書き込み）
```python
from kabusys.strategy import generate_signals
count = generate_signals(conn, date.today(), threshold=0.6)
print(f"signals written: {count}")
```

5) ニュース収集（RSS を収集して raw_news・news_symbols に保存）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
# known_codes は銘柄抽出に使う有効なコード集合（set of '7203', ...）
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203", "6758"})
print(res)
```

6) カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn, lookahead_days=90)
print(f"calendar saved: {saved}")
```

---

## ディレクトリ構成（主要ファイルと役割）
以下は src/kabusys 配下の主要モジュールと簡単な説明です。

- kabusys/
  - __init__.py — パッケージ初期化（version など）
  - config.py — 環境変数 / 設定管理（.env 自動ロード、Settings）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（認証・取得・保存）
    - schema.py — DuckDB スキーマ定義と init_schema/get_connection
    - pipeline.py — ETL パイプライン（run_daily_etl, run_prices_etl など）
    - news_collector.py — RSS 取得・前処理・DB 保存・銘柄抽出
    - calendar_management.py — market_calendar 管理（営業日判定 / update job）
    - audit.py — 監査ログスキーマ（signal_events, order_requests, executions）
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - features.py — data.stats の再エクスポート
    - quality.py — （品質チェックモジュール、pipeline から呼ばれる想定）
    - pipeline.py — ETL 全体のオーケストレーション
  - research/
    - __init__.py — 研究用 API 再エクスポート
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリ
  - strategy/
    - __init__.py — build_features, generate_signals を公開
    - feature_engineering.py — 特徴量作成（ユニバースフィルタ、Z スコア正規化）
    - signal_generator.py — final_score 計算と signals への書き込み
  - execution/ — 発注・execution 層（プレースホルダ）
  - monitoring/ — 監視・通知（Slack 等。設定は config.Settings 経由）

---

## 注意事項 / 実装ノート
- J-Quants API: レート制限（120 req/min）を守るため固定間隔スロットリングを実装しています。get_id_token (refresh) の自動処理やリトライ（指数バックオフ）も組み込まれています。
- RSS ニュース: defusedxml を利用した安全な XML パース、SSRF 防止（リダイレクト先検査、プライベートホスト拒否）、応答サイズ制限を行います。
- DuckDB スキーマ: ON CONFLICT を用いた冪等保存を基本としています。スキーマ初期化は init_schema() を使用してください。
- 設定管理: config.Settings により必須キーはプロパティアクセス時に検査されます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動 .env 読み込みを無効化できます。
- シグナル生成・特徴量構築は target_date に依存するため、常に対象日を明示して実行するか、ETL 後に営業日調整（pipeline.run_daily_etl 内で自動）を利用してください。
- ロギング: 各モジュールは logging を利用します。LOG_LEVEL 環境変数で制御してください。

---

## 貢献・ライセンス
- プロジェクトの拡張、バグ修正、ドキュメント改善は歓迎します。PR を送る際はユニットテスト（可能な範囲で）を追加してください。
- ライセンス情報はリポジトリルートの LICENSE を参照してください（本 README には含めていません）。

---

質問や追加したい使い方（例: 発注の実装例、Slack 通知設定、Quality チェックの詳細）などがあれば教えてください。README を補足して具体的な操作手順やサンプルスクリプトを追加します。