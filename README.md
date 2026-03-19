# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム（データプラットフォーム + 戦略層 + 実行/監査層）を目指すリポジトリです。DuckDB をデータ層に用い、J-Quants API や RSS ニュース、kabu ステーション等と連携して以下の機能を提供します。

- データ取得（J-Quants からの日足・財務データ・マーケットカレンダー）
- ETL パイプライン（差分取得、保存、品質チェック）
- ニュース収集・銘柄紐付け（RSS）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）
- 特徴量作成（正規化・ユニバースフィルタ適用）
- シグナル生成（最終スコア算出・BUY/SELL 判定）
- DuckDB スキーマ（原始～実行までのテーブル定義）
- 発注 / 監査レイヤー（スキーマとユーティリティ）

以下はこのコードベースの README（日本語）です。

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 簡単な使い方（サンプル）
- 環境変数（.env）
- ディレクトリ構成 / モジュール説明
- 実運用での注意点 / テストに関するメモ

---

## プロジェクト概要

KabuSys は、J-Quants 等の外部データソースから市場データと財務データを収集・加工して DuckDB に保存し、研究で得たファクターを元に特徴量（features）を作成、シグナルを生成する一連のワークフローを提供します。ニュース収集やマーケットカレンダー管理、ETL の差分更新、品質チェック、監査ログ用スキーマなども備え、戦略層と実行層を分離して設計されています。

設計上の重要点:
- ルックアヘッドバイアス防止（target_date を基準とした計算）
- 冪等性（DB への保存は ON CONFLICT / トランザクションで安全化）
- ネットワーク呼び出しはリトライ・レート制限に配慮
- 外部ライブラリ依存を極力抑えた実装（ただし duckdb, defusedxml などは使用）

---

## 機能一覧

主な機能（モジュール単位）:

- kabusys.config
  - .env / 環境変数の読み込み、設定アクセス（例: JQUANTS_REFRESH_TOKEN）
- kabusys.data.jquants_client
  - J-Quants API クライアント（ページネーション、トークンリフレッシュ、保存ユーティリティ）
- kabusys.data.schema
  - DuckDB スキーマ定義および初期化（raw / processed / feature / execution レイヤー）
- kabusys.data.pipeline
  - 日次 ETL（差分取得、backfill、品質チェック）
- kabusys.data.news_collector
  - RSS からニュース収集、前処理、raw_news 保存、銘柄抽出
- kabusys.data.calendar_management
  - 市場カレンダーの管理、営業日判定ユーティリティ
- kabusys.research.*
  - ファクター計算（momentum / value / volatility）と解析ユーティリティ（IC, forward returns）
- kabusys.strategy.feature_engineering
  - ファクターの正規化（Zスコア）、ユニバースフィルタ、features テーブルへの upsert
- kabusys.strategy.signal_generator
  - features と ai_scores を統合して final_score を計算、BUY / SELL シグナル生成、signals テーブルへ書き込み
- kabusys.data.news_collector
  - RSS 取得・XML パース（defusedxml 利用）、SSRF 対策、サイズ制限、挿入時の冪等性対応
- kabusys.data.audit
  - 発注・シグナル→約定フローの監査ログ用テーブル定義

---

## セットアップ手順

前提:
- Python 3.9+（typing の一部機能を利用）
- DuckDB を使用（Python パッケージ duckdb）
- ネットワークアクセス、J-Quants / Slack / kabu API の認証情報

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-root>

2. Python 仮想環境を作成・有効化
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール
   pip install -U pip
   pip install duckdb defusedxml

   （開発用途で editable install を望む場合）
   pip install -e .

   ※ 実運用では追加の依存（HTTP クライアントやロギング連携、Slack SDK 等）を導入する可能性があります。

4. 環境変数を設定
   プロジェクトルート（.git または pyproject.toml がある場所）に `.env` / `.env.local` を置くと自動で読み込まれます（自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   必須環境変数（※後述の「環境変数」参照）を .env に設定してください。

5. DuckDB スキーマ初期化
   Python REPL やスクリプトから初期化できます（下記 Usage を参照）。

---

## 簡単な使い方（サンプル）

以下は最小限の実行例です。実行前に .env に必要な値を設定してください。

1) DuckDB スキーマ初期化

from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)  # settings.duckdb_path は Path を返す

2) 日次 ETL（J-Quants から市場データ等を取得 → DuckDB に保存）

from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定しない場合は今日を基準

ETLResult オブジェクトに取得・保存件数や品質チェック結果が含まれます。

3) 特徴量ビルド（features テーブル作成）

from datetime import date
from kabusys.strategy import build_features

count = build_features(conn, target_date=date(2025, 1, 31))
print(f"features を作成/更新した銘柄数: {count}")

4) シグナル生成

from kabusys.strategy import generate_signals
from datetime import date

total = generate_signals(conn, target_date=date(2025, 1, 31))
print(f"生成したシグナル数: {total}")

5) ニュース収集（RSS）ジョブ

from kabusys.data.news_collector import run_news_collection
from typing import Set

# known_codes は文字列の銘柄コードセット（例: {"7203", "6758", ...}）
results = run_news_collection(conn, known_codes=known_codes)
print(results)

6) カレンダー更新ジョブ（夜間バッチ向け）

from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"saved calendar rows: {saved}")

---

## 環境変数（.env）

主要な環境変数（Settings で参照されるもの）:

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン。jquants_client が ID トークン取得に使用します。

- KABU_API_PASSWORD (必須)
  - kabu ステーション API のパスワード（実行・発注連携で使用）

- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
  - kabu API のエンドポイント（ローカルテストやプロキシ設定用）

- SLACK_BOT_TOKEN (必須)
  - Slack 通知用ボットトークン（通知実装が有る場合）

- SLACK_CHANNEL_ID (必須)
  - Slack チャンネル ID（通知先）

- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
  - DuckDB ファイルのパス（":memory:" でインメモリ DB）

- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
  - 監視用 SQLite（別途使用する場合）

- KABUSYS_ENV (任意, デフォルト: development)
  - allowed: development, paper_trading, live

- LOG_LEVEL (任意, デフォルト: INFO)
  - allowed: DEBUG, INFO, WARNING, ERROR, CRITICAL

自動ロード:
- プロジェクトルートの `.env` → `.env.local` の順で自動読み込みされます（OS 環境変数が優先）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主なファイルと説明）

src/kabusys/
- __init__.py
  - パッケージのバージョンと公開モジュール定義

- config.py
  - 環境設定管理（.env 読み込み、必須環境変数チェック、settings オブジェクト）

- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント（取得・保存ユーティリティ）
  - schema.py
    - DuckDB の DDL（raw / processed / feature / execution 層）と init_schema
  - pipeline.py
    - ETL（差分取得、backfill、日次 ETL 実行）
  - news_collector.py
    - RSS フィード取得、前処理、raw_news / news_symbols 保存
  - calendar_management.py
    - JPX カレンダーの更新・営業日ユーティリティ
  - stats.py
    - 汎用統計ユーティリティ（zscore_normalize）
  - features.py
    - zscore_normalize の再エクスポート
  - audit.py
    - 監査ログ用テーブル定義（signal_events, order_requests, executions ...）
  - (その他: quality モジュール等が想定される)

- research/
  - __init__.py
  - factor_research.py
    - momentum/value/volatility などのファクター計算（prices_daily/raw_financials を参照）
  - feature_exploration.py
    - forward returns 計算、IC（Spearman）や要約統計
  - (research 系は本番発注層に依存しない研究/解析向け)

- strategy/
  - __init__.py
  - feature_engineering.py
    - 生ファクターをマージ・ユニバースフィルタ・正規化して features テーブルへ保存
  - signal_generator.py
    - features と ai_scores を統合して final_score を算出し signals テーブルへ保存

- execution/
  - __init__.py
  - （発注処理や broker API 連携ロジックを置く場所）

- monitoring/
  - （監視・アラート系コードを配置する想定）

---

## 実運用での注意点

- 認証情報（トークン/パスワード）は秘匿して運用してください。`.env` はバージョン管理に入れないこと。
- J-Quants の API レート制限や kabu ステーションの仕様に合わせて実行スケジューラを調整してください。
- DuckDB ファイルのバックアップやローテーションを検討してください（サイズやI/Oパターンによる）。
- シグナル生成から実際の発注に移す場合、リスク管理（ポジション制限、最大発注数、二重発注防止）の実装が必須です。
- テストでは外部 API 呼び出しをモックする設計になっています。jquants_client や news_collector のネットワーク呼び出しはモック可能です。

---

## テスト / 開発メモ

- ネットワーク依存の部分（J-Quants / RSS / kabu）は unit テストではモックすることを推奨します。
- config._find_project_root は __file__ を基点に探索するため、パッケージ化後も .env 自動ロードが動作する点を利用できます。テストでは環境変数を直接設定するか、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使って自動ロードを無効化できます。
- DuckDB のインメモリ接続（":memory:"）を使うとテストが容易です。

---

この README はコードベースの主要部分をまとめたもので、実際の運用・拡張にあたっては DataPlatform.md / StrategyModel.md 等の設計ドキュメントを参照してください（リポジトリ内に存在することを想定した設計文書に準拠した実装です）。必要であれば、各モジュールの API 例やコマンドラインツール、CI/CD の設定例も追加します。