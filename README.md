# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（パイプライン・リサーチ・戦略・発注監査を含む）。  
このリポジトリはデータ取得（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどの主要モジュールを提供します。

---

## 概要

KabuSys は以下の機能群を備えた内部ライブラリです。

- J-Quants API から株価・財務・市場カレンダーを安全に取得
- DuckDB を利用したデータスキーマ（生データ → 整形データ → 特徴量 → 実行ログ）
- ETL（差分取得・バックフィル・品質チェック）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）
- 特徴量の正規化と戦略向け features テーブル作成
- final_score に基づくシグナル生成（BUY / SELL）
- RSS ベースのニュース収集と銘柄紐付け（SSRF 対策・サイズ制限・冪等保存）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- 発注・約定・ポジション・監査ログのスキーマ

設計上の要点：
- ルックアヘッドバイアス回避（target_date 時点のデータのみ使用）
- 冪等性（DB への保存は ON CONFLICT / トランザクションで安全）
- 外部依存を極力抑え、DuckDB と標準ライブラリ中心で実装

---

## 主な機能一覧

- data/
  - jquants_client: レート制御・再試行・トークン自動更新付き API クライアント
  - pipeline: 差分ETL（prices / financials / calendar）と日次 ETL 実行
  - schema: DuckDB スキーマ定義と init_schema
  - news_collector: RSS 取得・前処理・raw_news 保存・銘柄抽出
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - stats: zscore_normalize などの統計ユーティリティ
- research/
  - factor_research: momentum / volatility / value の計算
  - feature_exploration: 将来リターン計算、IC 計算、統計サマリー
- strategy/
  - feature_engineering.build_features: raw ファクターを正規化して features に保存
  - signal_generator.generate_signals: features と ai_scores を統合して signals を生成
- config: .env 自動読み込み・必須環境変数チェック（settings オブジェクト）
- audit / execution / monitoring（スキーマおよび監査ロジック）

---

## 要件

- Python 3.9 以上（型ヒントに Union 型等を利用しているため）
- 必要 Python パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS など）
- J-Quants API の認証情報（refresh token）
- kabuステーション等の設定（発注層を利用する場合）

（必要なパッケージはプロジェクトの requirements.txt / pyproject.toml に合わせてインストールしてください）

---

## 環境変数（主なもの）

このライブラリは .env / .env.local（プロジェクトルート）または OS 環境変数から設定を読み込みます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

必須：
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API 用パスワード
- SLACK_BOT_TOKEN — Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意（デフォルトあり）：
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG / INFO / ...（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用途の SQLite（デフォルト: data/monitoring.db）

注意: Settings オブジェクトから `settings.jquants_refresh_token` などで取得できます。

---

## セットアップ手順（開発向け）

1. リポジトリをクローン
   - git clone <repo>

2. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - またはプロジェクト指定の requirements / pyproject からインストール

4. 環境変数設定
   - プロジェクトルートに `.env` を作成（.env.example を参考に）
   - あるいは OS 環境変数として必要な値を設定

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで初期化:
     ```
     from kabusys.data.schema import init_schema
     from kabusys.config import settings
     conn = init_schema(settings.duckdb_path)
     ```
   - インメモリ DB を使う場合: init_schema(":memory:")

---

## 使い方（主要ワークフロー例）

以下はライブラリ関数を直接呼ぶ簡単な例です。運用ではジョブスケジューラ（cron / Airflow / systemd timer 等）から呼ぶ想定です。

1) データベース初期化
```
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL（J-Quants から差分取得）
```
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

3) 特徴量構築（features テーブルに保存）
```
from kabusys.strategy import build_features
from datetime import date

n = build_features(conn, date(2025, 3, 1))
print(f"features upserted: {n}")
```

4) シグナル生成（signals テーブルに保存）
```
from kabusys.strategy import generate_signals
from datetime import date

count = generate_signals(conn, date(2025, 3, 1))
print(f"signals written: {count}")
```

5) ニュース収集（RSS）と銘柄紐付け
```
from kabusys.data.news_collector import run_news_collection

known_codes = {"7203", "6758", ...}  # 有効な銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

6) カレンダー更新ジョブ（夜間バッチ）
```
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

7) J-Quants 直接操作（例: ID トークン取得）
```
from kabusys.data.jquants_client import get_id_token
token = get_id_token()
```

---

## 開発者向けヒント

- settings は `kabusys.config.settings` で使えます。必須の環境変数が不足していると ValueError が発生します。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml がある場所）を基準に行われます。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB 接続は同一プロセス内で再利用することを推奨します（コネクション作成は軽量ですが、トランザクション管理は意識してください）。
- news_collector は外部 RSS を取得するため SSRF 対策・レスポンスサイズ上限・gzip 解凍後チェック等を行います。
- jquants_client は内部で固定間隔のレート制限（120 req/min）・指数バックオフ・401 の自動リフレッシュを実装しています。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント
    - news_collector.py            — RSS 収集・保存
    - schema.py                    — DuckDB スキーマ定義 / init_schema
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - stats.py                     — zscore_normalize 等の統計ユーティリティ
    - calendar_management.py       — カレンダー管理・更新ジョブ
    - features.py                  — data.stats の再エクスポート
    - audit.py                     — 監査ログスキーマ
    - execution/ (発注層の実装置き場)
  - research/
    - __init__.py
    - factor_research.py           — momentum / volatility / value 計算
    - feature_exploration.py       — forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py       — build_features
    - signal_generator.py          — generate_signals
  - execution/                      — 発注 / 実行に関する名前空間（空の __init__ 等）
  - monitoring/                     — 監視・メトリクス等（将来的拡張）

（README は主要モジュールの抜粋です。実装の詳細は各ファイルの docstring を参照してください。）

---

## 注意事項 / 制限

- 本ライブラリは「発注 API（証券会社と直接やり取りする部分）」を含みますが、実際のブローカー連携は環境依存であり、運用前に十分なテストが必要です。特に live 環境では設定ミスが重大な損失を招く恐れがあります。
- J-Quants API の利用は利用規約・レート制限に従ってください。jquants_client は保護策を講じていますが、運用側でも適切な監視とリトライ方針を設定してください。
- DuckDB のバージョン差分により一部 SQL/制約の挙動が異なる場合があります。schema.init_schema は DuckDB 互換性を前提に設計されていますが、本番稼働前に環境での動作確認を行ってください。

---

## 貢献・ライセンス

- 本リポジトリに CONTRIBUTING.md や LICENSE が無い場合は、プロジェクトポリシーに従ってください。PR・Issue は README・docstring の案内に従って作成してください。

---

質問や追加したいドキュメント（例: CLI、デプロイ手順、運用 runbook）などがあれば教えてください。必要に応じて README を拡張します。