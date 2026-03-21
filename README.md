# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム向けライブラリです。データの収集（J-Quants）、ETL、特徴量生成、戦略のシグナル生成、ニュース収集、監査・スキーマ管理までを一貫して提供することを目的としています。

主な設計方針は「ルックアヘッドバイアス排除」「冪等性」「テスト容易性」「外部依存の最小化（戦略／研究コードは発注層に依存しない）」です。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（簡易サンプル）
- ディレクトリ構成（主なファイル・モジュール）
- 環境変数・設定
- 運用上の注意

---

## プロジェクト概要

KabuSys は内部的に DuckDB を用いたローカルデータベースを保持し、J-Quants API などから株価・財務・カレンダー等のデータを取得・保存します。研究（research）で作成したファクターを用いた特徴量生成、正規化、戦略によるシグナル生成、RSS ベースのニュース収集、監査ログの整備などをサポートします。

主に以下のレイヤーを提供します：
- Raw Layer：取得した生データ（raw_prices / raw_financials / raw_news 等）
- Processed Layer：整形済みの市場データ（prices_daily / fundamentals 等）
- Feature Layer：戦略・AI用の特徴量（features / ai_scores）
- Execution Layer：シグナル・注文・約定・ポジション等（signals / orders / trades / positions）
- 研究用ユーティリティ：ファクター計算、特徴量探索（IC 等）

---

## 機能一覧

- データ取得（J-Quants クライアント）
  - 日足（OHLCV）、財務データ、JPX カレンダーの取得（ページネーション・レート制御・リトライ）
  - 取得データを DuckDB に冪等保存
- ETL パイプライン
  - 差分取得（最終取得日を基に差分を自動算出）、バックフィル対応
  - 品質チェック呼び出しポイント
  - 日次 ETL エントリ (`run_daily_etl`)
- スキーマ管理
  - DuckDB のテーブル定義と初期化 (`init_schema`)
- 特徴量生成（strategy.feature_engineering）
  - 研究で計算した生ファクターを読み込み、ユニバースフィルタ、Zスコア正規化、クリッピング、features テーブルへの UPSERT を実施
- シグナル生成（strategy.signal_generator）
  - features と ai_scores を統合して final_score を計算、BUY/SELL シグナル生成、SELL はエグジット条件（ストップロス等）に基づき判定
- 研究ユーティリティ（research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- ニュース収集（data.news_collector）
  - RSS フィード収集、SSRF対策、トラッキングパラメータ除去、記事ID生成（SHA256先頭32文字）、raw_news / news_symbols への保存
- マーケットカレンダー管理（data.calendar_management）
  - カレンダーの夜間更新、営業日判定ユーティリティ（next_trading_day 等）
- 監査（data.audit）
  - signal → order_request → executions 等のトレーサビリティテーブル定義（監査ログ）

---

## セットアップ手順

前提:
- Python 3.10 以降（コード中に `Path | None` 等の構文を使用）
- pip または Poetry 等のパッケージマネージャ

1. リポジトリをクローン / 取得
   - 例: git clone ...

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 必須（代表例）:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml
   - 実際の pyproject.toml / requirements.txt があればそちらを使用してください:
     - pip install -e . など

4. 環境変数の設定
   - 主要な環境変数は下記「環境変数・設定」セクション参照。
   - プロジェクトルートに `.env` と `.env.local` を置くと、自動でロードされます（設定ファイル検出は .git または pyproject.toml を基準に行われます）。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. DuckDB スキーマ初期化
   - Python REPL などで:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
   - ":memory:" を渡すとインメモリ DB を使用できます（テスト用）。

---

## 使い方（簡易サンプル）

以下は各主要 API の利用例です。実行は Python スクリプトやバッチジョブから行ってください。

1) DB 初期化
```
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL 実行（市場カレンダー、株価、財務データの差分取得）
```
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)
print(result.to_dict())
```

3) 特徴量生成（特定日）
```
from datetime import date
from kabusys.strategy import build_features

build_features(conn, date(2024, 1, 5))
```

4) シグナル生成（特定日）
```
from kabusys.strategy import generate_signals
from datetime import date

total_signals = generate_signals(conn, date(2024, 1, 5))
print("signals:", total_signals)
```

5) ニュース収集ジョブ（RSS 取得→保存→銘柄紐付け）
```
from kabusys.data.news_collector import run_news_collection

known_codes = {"7203", "6758", "9984"}  # 既知銘柄セット
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

6) カレンダー更新ジョブ（夜間バッチ）
```
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("saved calendar rows:", saved)
```

注意: 実運用環境（live）では KABUSYS_ENV 等を設定し、paper_trading / live に応じた運用ポリシーを適用してください。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内部の主なモジュールと役割です（src/kabusys 以下）。

- __init__.py
  - パッケージ初期化、バージョン情報

- config.py
  - 環境変数の自動ロード (.env/.env.local)
  - Settings クラス（J-Quants トークン、kabu API、Slack、DB パス、環境モード等）

- data/
  - jquants_client.py：J-Quants API クライアント（フェッチ・保存）
  - schema.py：DuckDB スキーマ定義と init_schema / get_connection
  - pipeline.py：ETL パイプライン（run_daily_etl 等）
  - news_collector.py：RSS 収集と raw_news / news_symbols 保存
  - calendar_management.py：JPX カレンダー管理（営業日判定、更新ジョブ）
  - stats.py：Zスコア正規化等の統計ユーティリティ
  - features.py：data.stats の公開ラッパー
  - audit.py：監査ログ（signal_events, order_requests, executions 等）
  - quality.py（参照はあるが実装ファイルはプロジェクト内に存在する想定）

- research/
  - factor_research.py：momentum / volatility / value のファクター計算
  - feature_exploration.py：将来リターン・IC・統計サマリー等
  - __init__.py：便宜的な re-export

- strategy/
  - feature_engineering.py：features テーブルへ書き込むパイプライン（正規化・フィルタ）
  - signal_generator.py：final_score 計算・BUY/SELL 生成・signals テーブルへの保存
  - __init__.py：build_features, generate_signals のエクスポート

- execution/
  - （発注関連モジュールを配置する想定、現在空の __init__ が存在）

- monitoring/
  - （モニタリング関連モジュール用ディレクトリ。README 上では触れているが詳細実装はプロジェクトで管理）

---

## 環境変数・設定

config.Settings で参照される主な環境変数例:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL (省略可) — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack bot トークン（通知等に使用）
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (省略可) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (省略可) — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (省略可) — "development" | "paper_trading" | "live"（デフォルト: development）
- LOG_LEVEL (省略可) — "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化

サンプル .env（.env.example）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 運用上の注意

- Python バージョンは 3.10 以上を推奨（型ヒントで `|` を使用）。
- J-Quants API のレート制限（120 req/min）に合わせた実装がありますが、大量並列リクエストは控えてください。
- DuckDB のファイルパスは単一プロセスで扱うことを想定しています。複数プロセスからの同時書き込みは注意が必要です。
- ニュース収集は外部 RSS を取得するため SSRF や XML 攻撃対策（defusedxml、ホストの私的アドレス拒否、応答サイズ制限等）を実装していますが、運用時にソースの信頼性を検討してください。
- 本コードは戦略ロジックと発注（execution）層を分離する設計です。実際の発注フロー（証券会社 API との連携）を組み込む際は audit / orders / executions テーブルの仕様に従って実装してください。
- production（live）モードでは十分な監視・手動インターベンション体制を整えてください。paper_trading モードを用いた検証を推奨します。

---

必要であれば、README をさらに拡張して以下を追加可能です：
- 詳細な DB スキーマ説明（各テーブルのカラム解説）
- 品質チェック（quality モジュール）の使い方とルール
- CI / デプロイ手順（コンテナ化、cron/airflow 連携例）
- テスト・モック（外部 API をモックする方法）

ほか、ご希望の追加セクションや具体的な運用スクリプト例（systemd/cron/Airflow）などがあれば教えてください。README を追補して作成します。