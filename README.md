# KabuSys

日本株向けの自動売買システム基盤ライブラリです。J-Quants 等から市場データを収集して DuckDB に格納し、研究用ファクター計算・特徴量生成、戦略シグナル生成、ニュース収集、監査ログといったデータパイプライン／戦略レイヤを提供します。

主な設計方針：
- ルックアヘッドバイアス回避（計算は target_date 時点のデータのみ使用）
- DuckDB を中心とした冪等な保存（ON CONFLICT / トランザクション）
- 外部 API 呼び出しは専用クライアントに集約（レート制御・リトライ・トークン自動更新）
- 研究（research）と運用（strategy/execution）を分離

---

## 機能一覧

- 環境変数/設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（無効化可能）
  - 必須環境変数チェック・型変換・環境種別（development / paper_trading / live）検証
- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアント（ページネーション・レート制限・リトライ・トークン自動更新）
  - 株価・財務・カレンダー取得 → DuckDB への冪等保存
- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義と索引
  - init_schema(), get_connection()
- ETL パイプライン（kabusys.data.pipeline）
  - 日次差分 ETL（市場カレンダー → 株価 → 財務）と品質チェックの実行（run_daily_etl）
- ニュース収集（kabusys.data.news_collector）
  - RSS 収集・テキスト前処理・ID 正規化（SHA-256）・SSRF 対策・raw_news, news_symbols 保存
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、next/prev_trading_day、カレンダー更新ジョブ
- 研究用ファクター計算（kabusys.research）
  - momentum / volatility / value 等のファクター計算と特徴量探索ユーティリティ（IC, forward returns）
- 特徴量生成（kabusys.strategy.feature_engineering）
  - 生ファクターの正規化（Zスコア）、ユニバースフィルタ、features テーブルへの UPSERT
- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して final_score を計算、BUY/SELL シグナルを signals テーブルへ書き込み
- 監査ログ（kabusys.data.audit）
  - signal → order_request → execution までのトレーサビリティテーブル（監査ログ層）
- 汎用統計ユーティリティ（kabusys.data.stats）
  - クロスセクション Z スコア正規化等

---

## セットアップ手順

前提
- Python 3.10 以上（コード中で | 型注釈・future annotations を使用）
- Git クライアント

1. リポジトリをクローン
   - git clone <リポジトリURL>
2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. パッケージおよび依存ライブラリのインストール
   - pip install -e .
   - 必須依存（手動インストールが必要な場合）:
     - duckdb
     - defusedxml
   例:
   - pip install duckdb defusedxml
4. 環境変数 / .env の準備
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必須変数（例）:
     - JQUANTS_REFRESH_TOKEN=（J-Quants のリフレッシュトークン）
     - KABU_API_PASSWORD=（kabuステーション API パスワード）
     - SLACK_BOT_TOKEN=（Slack Bot Token）
     - SLACK_CHANNEL_ID=（通知先チャネルID）
     - DUCKDB_PATH=data/kabusys.duckdb  （省略可、既定値）
     - KABUSYS_ENV=development|paper_trading|live  （既定: development）
     - LOG_LEVEL=INFO|DEBUG|...  （既定: INFO）
   - 例 .env:
     JQUANTS_REFRESH_TOKEN=xxxxx
     KABUS_API_PASSWORD=xxxxx
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C0123456
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=DEBUG

---

## 使い方（簡単なクイックスタート）

以下は Python REPL / スクリプトでの基本操作例です。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

# ファイル DB を初期化（親ディレクトリがなければ自動作成）
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL（J-Quants からデータ取得 → 保存 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を省略すると今日
print(result.to_dict())
```

3) 特徴量の構築（features テーブルへの書き込み）
```python
from kabusys.strategy import build_features
from datetime import date

n = build_features(conn, target_date=date(2025, 1, 6))
print(f"features upserted: {n}")
```

4) シグナル生成（signals テーブルへの書き込み）
```python
from kabusys.strategy import generate_signals
from datetime import date

count = generate_signals(conn, target_date=date(2025, 1, 6))
print(f"signals written: {count}")
```

5) ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection

# known_codes は銘柄抽出時に有効とみなす銘柄セット（任意）
res = run_news_collection(conn, known_codes={"7203", "6758"})
print(res)  # {source_name: saved_count}
```

6) カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print("calendar saved:", saved)
```

注意点:
- run_daily_etl 等は内部で J-Quants API を叩きます。認証トークンや API レート・ネットワーク状況に応じた実行管理が必要です。
- production（運用）では KABUSYS_ENV を適切に設定し、paper_trading / live の切り替え／安全対策を行ってください。

---

## 主要な API / モジュール（例）

- kabusys.config.settings
  - settings.jquants_refresh_token / settings.kabu_api_password / settings.kabu_api_base_url
  - settings.slack_bot_token / settings.slack_channel_id
  - settings.duckdb_path / settings.sqlite_path
  - settings.env / settings.log_level / settings.is_live / settings.is_paper / settings.is_dev
- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
- kabusys.data.schema
  - init_schema(db_path), get_connection(db_path)
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...)
  - run_prices_etl, run_financials_etl, run_calendar_etl
- kabusys.data.news_collector
  - fetch_rss, save_raw_news, run_news_collection
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold=0.6, weights=None)

---

## ディレクトリ構成

プロジェクトの主要ファイル・ディレクトリ構成（抜粋）:
- src/
  - kabusys/
    - __init__.py
    - config.py                       — 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py             — J-Quants API クライアント（fetch/save）
      - schema.py                     — DuckDB スキーマ定義・初期化
      - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
      - news_collector.py             — RSS ニュース収集・保存
      - calendar_management.py        — マーケットカレンダー管理
      - audit.py                      — 監査ログスキーマ
      - stats.py                      — 統計ユーティリティ（zscore_normalize）
      - features.py                   — data-level の features 再エクスポート
      - execution/                     — 発注関連（未実装ファイル群の入口）
    - research/
      - __init__.py
      - factor_research.py            — momentum/volatility/value 計算
      - feature_exploration.py        — forward returns / IC / summary
    - strategy/
      - __init__.py
      - feature_engineering.py        — ファクター正規化・features 更新
      - signal_generator.py           — final_score 計算・signals 生成
    - execution/                       — 発注・約定・ポジション管理（パッケージ）
    - monitoring/                      — 監視関連（パッケージ、README 未記載）
- pyproject.toml (想定)
- .env.example（プロジェクトルートに置くと分かりやすい）

---

## 注意事項 / ベストプラクティス

- 環境設定は .env(.local) に保存して Git 管理対象外にしてください（シークレット扱い）。
- J-Quants の API レート・認証には注意してください（ライブラリはレート制御を行いますが、上位でのスケジューリングも必要です）。
- 本ライブラリは戦略の候補実装・基盤提供を目的としています。実際の資金を投入する前に paper_trading 環境で挙動確認を行ってください。
- DuckDB ファイルは定期バックアップ・排他制御を行ってください（複数プロセスでの同時書き込みは注意が必要です）。
- production 実行時は KABUSYS_ENV を `live` に設定し、ログレベル・監視・アラートを構築してください。

---

必要であれば、README に以下の追加情報を記載できます：
- 具体的な依存パッケージとバージョン（requirements.txt）
- CI/CD / デプロイ手順（Airflow / cron 等でのジョブスケジューリング例）
- テストの実行手順とカバレッジ
- 各種設定ファイル（.env.example）のテンプレート

補足や追記してほしいセクションがあれば教えてください。