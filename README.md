# KabuSys

日本株向けの自動売買システム（ライブラリ）。  
データ取得（J-Quants）、ETL、特徴量計算、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログといった機能を提供します。  
（このREADMEは src/kabusys 配下のコードベースに基づく概要・セットアップ・使い方をまとめたものです）

目次
- プロジェクト概要
- 主な機能
- 必要条件
- セットアップ手順
- 環境変数（.env の例）
- 使い方（主要 API の利用例）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株運用向けのバックエンドライブラリ群です。  
設計方針の概要：
- データレイヤを明確に分離（Raw / Processed / Feature / Execution）
- DuckDB をローカルデータベースとして採用
- J-Quants API を用いた株価・財務・カレンダー取得（レート制御、リトライ、トークン自動更新）
- 研究用の factor 計算・特徴量正規化・シグナル生成ロジックを備える
- ニュース収集（RSS）と銘柄紐付け機能を持つ
- 発注層（execution）や監査ログ（audit）用のスキーマ定義を含む
- ルックアヘッドバイアス防止や冪等性（idempotency）を重視した実装

---

## 主な機能一覧

- データ取得 / 保存
  - J-Quants クライアント（レートリミット・リトライ・トークン自動更新）
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB への冪等保存）
- ETL パイプライン
  - run_daily_etl: カレンダー → 株価 → 財務 の差分取得、品質チェック統合
  - 差分更新（最終取得日からの差分 fetch）・バックフィル対応
- スキーマ管理
  - DuckDB のスキーマ定義と初期化（init_schema）
  - Raw / Processed / Feature / Execution 層のテーブル
- 研究 / 特徴量
  - ファクター計算（momentum, volatility, value）
  - z-score 正規化ユーティリティ
  - forward return / IC（Spearman）/ 統計サマリ機能
- 特徴量→シグナル
  - build_features: research フェーズの生ファクターを正規化して features テーブルへ格納
  - generate_signals: features と ai_scores を統合して BUY/SELL シグナルを生成して signals テーブルへ格納
- ニュース収集
  - RSS フィード取得（SSRF 対策・gzip 対応・トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存
  - テキスト前処理と銘柄コード抽出（4桁コード）
- カレンダー管理
  - market_calendar の差分更新ジョブ
  - 営業日判定・前後営業日の取得・期間内営業日取得ユーティリティ
- 監査（Audit）
  - signal_events / order_requests / executions 等の監査テーブル定義

---

## 必要条件

- Python 3.10 以上（型注釈に | 記法を使用）
- 必要ライブラリ（最低限）
  - duckdb
  - defusedxml
- （オプション）J-Quants API 利用、Slack 通知等を行う場合はそれぞれの API トークンが必要

インストール例（仮）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# パッケージ化されている場合:
# pip install -e .
```

注意: 実際のプロジェクトでは追加の依存（logging ライブラリ、テストツール、CI 等）があるかもしれません。requirements.txt がある場合はそれを使用してください。

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境作成・有効化、依存インストール
3. 環境変数設定（.env） — 以下節を参照
4. DuckDB スキーマの初期化（例：Python 実行）
   - 例:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - ":memory:" を渡せばインメモリ DB を使用できます（テスト用）
5. （初回）ETL 実行などでデータ取得
   - run_daily_etl を呼んでカレンダー・株価・財務を差分取得
6. 特徴量作成 → シグナル生成
   - build_features / generate_signals を呼び出す

環境変数の自動ロード:
- パッケージの config モジュールはプロジェクトルート（.git または pyproject.toml を探索）から `.env` / `.env.local` を自動で読み込みます（環境変数が未設定の場合のみ `.env` を、`.env.local` は上書き）。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利）。

---

## 環境変数（.env の例）

以下の環境変数を設定してください（必須項目は実稼働時に必要です）。

.example .env
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# kabuステーション API（もし使用する場合）
KABU_API_PASSWORD=your_kabu_password
# KABU_API_BASE_URL はオプション（デフォルト: http://localhost:18080/kabusapi）
# KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack (任意だが一部機能で必須)
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB パス（デフォルト）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境: development / paper_trading / live
KABUSYS_ENV=development

# ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL
LOG_LEVEL=INFO

# テスト用: 自動 .env ロードを無効にする
# KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

注意:
- 必須環境変数を Settings プロパティから取得する関数は未設定時に ValueError を送出します（例: settings.jquants_refresh_token）。
- `.env.local` はローカル専用の上書きファイルとして扱われ、OS 環境変数より優先して上書きされます（ただし OS 環境変数の保護はされます）。

---

## 使い方（主要 API の例）

以下は基本的な Python からの呼び出し例です。実際はスクリプトやワーカーを用いて日次バッチやスケジューリングしてください。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ファイルなければ自動作成
```

2) 日次 ETL 実行（データ取得 → 保存 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量（features）構築
```python
from kabusys.strategy import build_features
from datetime import date

count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

4) シグナル生成
```python
from kabusys.strategy import generate_signals
from datetime import date

total_signals = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"total signals written: {total_signals}")
```

5) ニュース収集（RSS → raw_news / news_symbols）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

known_codes = {"7203", "6758", "9984"}  # 有効銘柄コードセット
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)
```

6) カレンダー更新バッチ（夜間ジョブ）
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"calendar rows saved: {saved}")
```

エラーハンドリングやログ出力は各関数内で行われ、ETL の戻り値オブジェクトやログを参照して運用判断してください。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 配下の主なファイル／モジュールです（このリポジトリに含まれるものに基づく一覧）。

- src/kabusys/
  - __init__.py
  - config.py         # 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py    # J-Quants API クライアント（fetch/save）
    - pipeline.py         # ETL パイプライン
    - schema.py           # DuckDB スキーマ定義・初期化
    - stats.py            # 統計ユーティリティ（zscore_normalize 等）
    - news_collector.py   # RSS 取得・保存・銘柄抽出
    - calendar_management.py  # カレンダー関連ユーティリティ・更新ジョブ
    - features.py         # data 層の特徴量ユーティリティ公開
    - audit.py            # 監査ログ（signal_events / order_requests / executions）
    - (その他: quality 等想定)
  - research/
    - __init__.py
    - factor_research.py      # モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py  # forward returns / IC / summary / rank
  - strategy/
    - __init__.py
    - feature_engineering.py  # build_features
    - signal_generator.py     # generate_signals
  - execution/   # 発注・execution 層（空の __init__ を含む）
  - monitoring/  # 監視・アラート用（未実装ファイル等を含む可能性あり）

---

## 運用上の注意・設計上のポイント

- 冪等性:
  - DB への保存は ON CONFLICT / INSERT ... DO UPDATE / DO NOTHING を多用しているため、再実行に対して冪等です。
- ルックアヘッドバイアス対策:
  - 特徴量・シグナル生成は target_date 時点のデータのみを用いる設計を心掛けています。
  - J-Quants の取得時には fetched_at を UTC で記録し、いつそのデータが「利用可能」だったかを追跡できます。
- セキュリティ:
  - RSS 収集では SSRF 対策・XML パースの hardened ライブラリ（defusedxml）を使用。
  - J-Quants のトークンは自動リフレッシュを行いますが、トークン管理は安全な手段で行ってください。
- テスト:
  - config モジュールは自動 .env ロードを行うため、テストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使うか環境を制御して下さい。

---

この README はコードの主要点に基づく概要です。各モジュール内の docstring に詳しい設計・仕様・実装上の注意が記載されています。実運用前に CI テスト・ローカルでの総合テスト・監査（auditing）を必ず行ってください。