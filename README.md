# KabuSys

日本株向け自動売買システムのライブラリ群（ミニマム実装）。  
このリポジトリはデータ取得・ETL、特徴量作成、シグナル生成、ニュース収集、監査スキーマなどを含むモジュール群を提供します。

主な目的は「ルックアヘッドバイアスを避けつつ、DuckDB を用いたデータレイク → 特徴量 → シグナル生成」のワークフローを安定して実行できることです。

---

## 概要

- データ取得：J-Quants API から株価・財務・市場カレンダー等を取得（jquants_client）。
- ETL：差分更新／バックフィル／品質チェック（data.pipeline）。
- スキーマ：DuckDB 用スキーマ定義と初期化（data.schema）。
- ニュース：RSS 収集・前処理・銘柄紐付け（data.news_collector）。
- 研究用：ファクター計算・探索（research.*）。
- 戦略：特徴量エンジニアリングおよびシグナル生成（strategy.*）。
- 実行・監視：発注・監査・モニタリング関連の雛形（execution、monitoring）。

設計上のポイント：
- すべての ETL/戦略処理は target_date 時点のデータのみを参照してルックアヘッドを防止。
- DuckDB を永続ストレージ／分析基盤として利用。
- API 呼び出しはレート制御・リトライ・トークン自動更新を含む堅牢実装。
- 冪等（idempotent）な DB 保存を徹底（ON CONFLICT / トランザクション）。

---

## 機能一覧

- data
  - jquants_client: J-Quants API クライアント（ページネーション、リトライ、レート制御、保存ユーティリティ）
  - schema: DuckDB スキーマ定義 & 初期化（init_schema, get_connection）
  - pipeline: 日次 ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - news_collector: RSS 取得・前処理・raw_news 保存、銘柄抽出・紐付け
  - calendar_management: 営業日判定・next/prev_trading_day、calendar_update_job
  - stats / features: Zスコア正規化など統計ユーティリティ
  - audit: 監査ログ・トレーサビリティ用スキーマ（signal_events, order_requests, executions...）
- research
  - factor_research: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman ρ）、統計サマリー
- strategy
  - feature_engineering.build_features: ファクター取得 → ユニバースフィルタ → 正規化 → features テーブル UPSERT
  - signal_generator.generate_signals: features + ai_scores を統合して final_score を算出、BUY/SELL シグナルを signals テーブルに保存
- その他
  - 環境変数管理（kabusys.config.Settings）、.env 自動読み込み（プロジェクトルート検出）

---

## セットアップ手順

前提
- Python 3.9+（typing 機能を利用）
- DuckDB を使用（Python パッケージ duckdb）
- defusedxml（RSS の安全なパースに使用）

推奨インストール（開発環境）:
1. 仮想環境を作成・有効化（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb defusedxml

（プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください。パッケージ配布がある場合は pip install -e . も可能です。）

3. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml を含むディレクトリ）に `.env` または `.env.local` を作成することで自動読み込みされます。
   - 自動読み込みを抑止する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

主要な環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu API 用パスワード（必須）
- KABU_API_BASE_URL: kabu API URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV: environment (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）

注意: Settings の必須フィールド（_require 関数）を参照した場合、未設定だと ValueError が発生します。

---

## 使い方（簡単なコード例）

以下は最小限の操作例です。実行前に環境変数を整えてください。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")  # ディレクトリを自動作成
```

2) 日次 ETL を実行（J-Quants トークンは settings から取得）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を与えないと today が使われる
print(result.to_dict())
```

3) 特徴量の作成（target_date に対して features テーブルを作成）
```python
from kabusys.strategy import build_features
from datetime import date

n = build_features(conn, date(2025, 1, 6))
print(f"features upserted: {n}")
```

4) シグナル生成
```python
from kabusys.strategy import generate_signals
from datetime import date

count = generate_signals(conn, date(2025, 1, 6))
print(f"signals written: {count}")
```

5) ニュース収集ジョブ（既知銘柄セットがある場合は紐付けする）
```python
from kabusys.data.news_collector import run_news_collection

known_codes = {"7203", "6758", "9984"}  # 例
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

6) 研究用ユーティリティ（将来リターン・IC）
```python
from kabusys.research import calc_forward_returns, calc_ic

fwd = calc_forward_returns(conn, date(2025,1,6))
# factor_records は research/factor_research で得たもの
# ic = calc_ic(factor_records, fwd, "mom_1m", "fwd_1d")
```

---

## 典型的なワークフロー

1. init_schema() で DB を準備
2. run_daily_etl() を実行して prices/raw_financials/market_calendar を更新
3. build_features() で features テーブルを作成
4. generate_signals() で signals テーブルに BUY/SELL を作成
5. execution 層へ渡して発注（execution モジュールの実装に依存）
6. audit テーブルでトレーサビリティを保存・追跡

---

## 設定・トラブルシュート

- .env 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml を含む）を起点に `.env` / `.env.local` を読み込みます。
  - .env.local は上書きされる（override=True）。OS 環境変数は保護されます。
  - 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

- 環境変数未設定エラー:
  - settings の必須プロパティ（例: JQUANTS_REFRESH_TOKEN）へアクセスすると未設定時に ValueError が投げられます。`.env.example` を参照して必須値を設定してください。

- DuckDB パス:
  - デフォルトは `data/kabusys.duckdb`（settings.duckdb_path）。ファイルパスの親ディレクトリは自動作成されます。

- ログレベル:
  - LOG_LEVEL 環境変数で設定（INFO デフォルト）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py           — J-Quants API クライアント & 保存ユーティリティ
    - news_collector.py           — RSS 収集・保存・銘柄抽出
    - schema.py                   — DuckDB スキーマ定義 & init_schema
    - pipeline.py                 — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py      — 営業日判定、calendar_update_job
    - features.py                 — zscore_normalize を再エクスポート
    - stats.py                    — 統計ユーティリティ（zscore 等）
    - audit.py                    — 監査ログスキーマ
    - quality.py?                 — （品質チェックモジュールがある想定）
  - research/
    - __init__.py
    - factor_research.py          — モメンタム・バリュー・ボラティリティ計算
    - feature_exploration.py      — forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py      — features テーブル作成ロジック
    - signal_generator.py         — final_score 計算・BUY/SELL 生成
  - execution/                     — 発注周り（雛形）
  - monitoring/                    — 監視・メトリクス（雛形）

（プロジェクトルート）
- .env.example (推奨: 実際はリポジトリに含める)
- pyproject.toml / setup.cfg / requirements.txt（利用する場合）

---

## 開発・拡張ノート

- strategy の重みや閾値は generate_signals の引数から上書き可能です（weights, threshold）。
- jquants_client の _RateLimiter は 120 req/min を想定しています。必要に応じて調整してください。
- news_collector は SSRF・XML Bomb 対策（defusedxml、ホスト検査、レスポンスサイズ制限）を組み込んでいます。
- DuckDB の SQL は SQL インジェクションに配慮してパラメタライズされたクエリを使用していますが、動的 SQL を追加する際は十分注意してください。
- execution / monitoring モジュールはプロジェクトに合わせてブリッジ実装（証券会社 API）や監視フレームワーク統合を行ってください。

---

## ライセンス / 貢献

この README はリポジトリから自動生成したコードを元に作成しています。実プロジェクトへ導入する際は社内ポリシー・API 利用規約を必ず確認してください。

貢献方法やライセンス情報はリポジトリのルートにある LICENSE / CONTRIBUTING を参照してください（存在する場合）。

---

必要であれば、README に以下を追記できます：
- より詳細な SQL スキーマ説明（各テーブルの列説明）
- CI / テスト実行方法
- デプロイ & 運用手順（cron / Airflow / GitHub Actions のサンプル）
- サンプル .env.example（テンプレート）

どれを追加したいか教えてください。