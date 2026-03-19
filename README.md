# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（KabuSys）。  
データ収集（J-Quants / RSS）、DuckDB スキーマ管理、ETL パイプライン、研究用ファクター計算、品質チェック、監査ログなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けバックエンドコンポーネント群です。主に以下の責務を持ちます。

- J-Quants API からの市場データ・財務データ・市場カレンダー取得（認証・リトライ・レートリミット対応）
- RSS を用いたニュース収集と銘柄紐付け（SSRF対策・XML安全パース・トラッキング除去）
- DuckDB を用いたデータスキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit レイヤ）
- 日次 ETL パイプライン（差分取得・品質チェック・冪等保存）
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）と評価ユーティリティ（IC, forward returns, Zスコア等）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ用スキーマ（signal → order → execution のトレーサビリティ）

設計方針として、本番の発注 API には依存せず（研究／データ処理側の責務に集中）、冪等性／安全性（XML/SSRF/トークン自動リフレッシュ）を重視しています。

---

## 主な機能一覧

- 環境設定管理（kabusys.config）
  - .env/.env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェック
- J-Quants クライアント（kabusys.data.jquants_client）
  - レートリミット制御、リトライ、トークンリフレッシュ
  - 株価日足・財務データ・マーケットカレンダーの取得と DuckDB への冪等保存
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、XML の安全パース、記事正規化、ID（SHA-256）生成
  - 銘柄コード抽出・news_symbols への紐付け
- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution / Audit 層の DDL
  - init_schema / get_connection の提供
- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl（カレンダー → 株価 → 財務 → 品質チェック）
  - 差分取得・バックフィル・品質チェックの実装
- データ品質チェック（kabusys.data.quality）
  - 欠損チェック、スパイク検出、重複チェック、日付整合性チェック
- 研究・特徴量（kabusys.research）
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
  - zscore 正規化ユーティリティ（kabusys.data.stats）
- 監査ログ初期化（kabusys.data.audit）
  - signal_events / order_requests / executions 等のテーブル定義と初期化関数

（strategy/execution/monitoring パッケージはプレースホルダとして存在）

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントに `X | Y` を使用）
- ネットワーク接続（J-Quants API、RSS フィード等）
- DuckDB（Python パッケージ `duckdb` を利用）

1. リポジトリをクローン
   - git clone ...（リポジトリ URL）

2. 仮想環境の作成と有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトがパッケージ化されている場合）pip install -e .

   必要に応じて他のパッケージ（ログハンドラ、Slack クライアント等）を追加してください。

4. 環境変数の設定
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動ロードされます（自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 主な環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - KABU_API_BASE_URL: kabuステーション API ベース URL（デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN: Slack ボットトークン（必須）
     - SLACK_CHANNEL_ID: Slack 送信先チャンネル ID（必須）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: environment (development | paper_trading | live)（デフォルト: development）
     - LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）

5. DuckDB スキーマ初期化
   - Python REPL / スクリプトで:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")  # デフォルトパスを使用するなら明示的に呼ぶ

6. 監査ログ用 DB 初期化（必要な場合）
   - from kabusys.data.audit import init_audit_db
   - audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   - または既存 conn に対して init_audit_schema(conn)

---

## 使い方（例）

以下は主要な使い方例です。実際の運用ではロギングやエラーハンドリングを適切に行ってください。

- DuckDB スキーマ作成
```
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL の実行
```
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- J-Quants データ取得（生データフェッチ）
```
from kabusys.data.jquants_client import fetch_daily_quotes
from datetime import date

rows = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
print(len(rows))
```

- ニュース収集ジョブ実行
```
from kabusys.data.news_collector import run_news_collection
# known_codes は銘柄コードセット（例: {'7203','6758',...}）
res = run_news_collection(conn, sources=None, known_codes=known_codes)
print(res)  # {source_name: saved_count}
```

- 研究用ファクター計算（例: モメンタム）
```
from datetime import date
from kabusys.research import calc_momentum

records = calc_momentum(conn, target_date=date(2025,1,31))
# records: list of dict with keys: date, code, mom_1m, mom_3m, mom_6m, ma200_dev
```

- 将来リターン・IC 計算
```
from kabusys.research import calc_forward_returns, calc_ic

fwd = calc_forward_returns(conn, target_date=date(2025,1,31), horizons=[1,5,21])
# factor_records は別途算出したファクター（list[dict]）
ic = calc_ic(factor_records, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

- Zスコア正規化
```
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(records, columns=["mom_1m", "ma200_dev"])
```

---

## 環境変数（まとめ）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルトあり）
- SLACK_BOT_TOKEN (必須) — Slack Bot Token
- SLACK_CHANNEL_ID (必須) — Slack Channel ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化する場合に 1 を設定

ヒント: `.env.example` をプロジェクトルートに置いて、`.env` を作成してください（コード内に .env.example そのものは含まれていませんが、README の手順に従って環境変数を配置してください）。

---

## ディレクトリ構成

（主要ファイル / モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得・保存）
    - news_collector.py            — RSS ニュース収集と保存
    - schema.py                    — DuckDB スキーマ定義・初期化
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - quality.py                   — データ品質チェック
    - stats.py                     — 統計ユーティリティ（zscore 等）
    - features.py                  — 特徴量関連の公開インターフェース
    - calendar_management.py       — 市場カレンダー管理・ユーティリティ
    - audit.py                     — 監査ログスキーマ初期化
    - etl.py                       — ETL 型の公開インターフェース（再エクスポート）
  - research/
    - __init__.py                  — 研究用ユーティリティの公開
    - factor_research.py           — Momentum/Volatility/Value 等の計算
    - feature_exploration.py       — forward returns / IC / summary 等
  - strategy/                       — 戦略関連（プレースホルダ）
    - __init__.py
  - execution/                      — 発注・実行関連（プレースホルダ）
    - __init__.py
  - monitoring/                     — 監視関連（プレースホルダ）

---

## 注意点 / 運用メモ

- J-Quants API のレート上限（120 req/min）に対応するため、jquants_client は内部でスロットリングを行います。
- fetch 系関数はページネーションに対応しています（pagination_key 対応）。
- save_* 関数は DuckDB への保存で冪等性（ON CONFLICT ... DO UPDATE/DO NOTHING）を提供します。
- news_collector は SSRF 対策・XML 安全パース・受信サイズチェックを実装していますが、運用時はフィードソースの信頼性を監視してください。
- データ品質チェック（quality）で重大な問題（error）が検出された場合は、運用フロー側で ETL の停止やアラート発行を行ってください。
- 本リポジトリは発注・ブローカー連携（実際の板寄せ・注文送信）の責務は限定的です。実際の運用で証券会社 API と接続する際は、さらに安全性・冪等性・監査の実装を強化してください。

---

## 参考（よく使う API）

- Schema 初期化: kabusys.data.schema.init_schema(db_path)
- ETL 実行: kabusys.data.pipeline.run_daily_etl(conn, target_date=...)
- News 収集: kabusys.data.news_collector.run_news_collection(conn, sources, known_codes)
- Factor 計算: kabusys.research.calc_momentum / calc_volatility / calc_value
- Forward Returns / IC: kabusys.research.calc_forward_returns / calc_ic
- Z-score: kabusys.data.stats.zscore_normalize

---

ご不明点があれば、どの機能のドキュメント（関数用途・引数・戻り値の詳細）を優先して展開するか教えてください。README をプロジェクトのテンプレートや CI 手順に合わせて拡張することも可能です。