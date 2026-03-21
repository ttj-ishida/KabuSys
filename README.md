# KabuSys

KabuSys は日本株を対象とした自動売買システムのライブラリ群です。データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなど、戦略運用に必要な主要コンポーネントを提供します。

バージョン: 0.1.0

---

## 概要

このリポジトリは、次の機能を備えたモジュール群で構成されています。

- J-Quants API からの株価・財務・カレンダー取得（レート制御・リトライ・トークン自動更新）
- DuckDB ベースのスキーマと冪等な保存ロジック
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- 研究用のファクター計算（モメンタム・ボラティリティ・バリュー等）
- 特徴量エンジニアリング（正規化・ユニバースフィルタ・features テーブル書き込み）
- シグナル生成（ファクター＋AI スコアの統合、BUY/SELL 生成、SELL 優先）
- ニュース収集（RSS、SSRF 対策、トラッキングパラメータ除去、銘柄抽出）
- マーケットカレンダー管理（JPX カレンダーの夜間更新・営業日判定）
- 発注・約定・ポジションなどの監査ログスキーマ

設計上の特徴として、ルックアヘッドバイアス回避（target_date 時点のみ参照）、DB への冪等保存、外部 API への過度な依存排除（研究モジュールは DB のみ参照）を重視しています。

---

## 主な機能一覧

- data/jquants_client.py: J-Quants API クライアント（fetch / save / トークン管理 / レート制御）
- data/schema.py: DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- data/pipeline.py: 日次 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- data/news_collector.py: RSS からのニュース収集・前処理・DB 保存（SSRF 対策あり）
- data/calendar_management.py: market_calendar の更新および営業日ユーティリティ
- research/factor_research.py: モメンタム・ボラティリティ・バリューのファクター計算
- research/feature_exploration.py: 将来リターン計算・IC（スピアマン）・統計サマリ
- strategy/feature_engineering.py: features テーブル生成（Zスコア正規化・ユニバースフィルタ）
- strategy/signal_generator.py: final_score 計算、BUY/SELL シグナル生成、signals テーブルへの保存
- data/stats.py: zscore_normalize 等の共通統計ユーティリティ
- config.py: 環境変数読み込み（.env/.env.local の自動ロード）と Settings API

---

## 前提 / 必要環境

- Python 3.10 以上（PEP 604 の union 型記法や型ヒントを使用）
- pip install 可能な環境
- 必要な Python パッケージ（最低限）:
  - duckdb
  - defusedxml

詳細な requirements.txt はプロジェクトに含めていないため、インストール時に次のようにしてください:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# パッケージをプロジェクトとして使う場合（編集可能インストール）
pip install -e .
```

（プロジェクトに requirements.txt / pyproject.toml がある場合はそちらに従ってください。）

---

## 環境変数（必須/任意）

config.Settings から利用される主要な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知に使うボットトークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — モニタリング用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml を探索）にある `.env` と `.env.local` を自動読み込みします。
  優先順位: OS 環境変数 > .env.local > .env
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（例）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・依存インストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb defusedxml
   # またはプロジェクトに pyproject.toml があれば:
   pip install -e .
   ```

3. 環境変数の設定
   - プロジェクトルートに `.env`（必要なキーを記載）を作成するか、OS 環境に設定します。
   - 例 (.env):
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. DuckDB スキーマ初期化（最初に一度だけ）
   Python REPL またはスクリプトで:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```

---

## 使い方（主な API 例）

以下は、代表的な実行例です。すべて DuckDB の接続オブジェクト（kabusys.data.schema.init_schema が返す接続）を受け取ります。

- DB 初期化
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL（市場カレンダー・株価・財務の差分取得 + 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())
  ```

- features の構築（target_date を基準）
  ```python
  from kabusys.strategy import build_features
  from datetime import date
  cnt = build_features(conn, date(2024, 1, 1))
  print(f"features upserted: {cnt}")
  ```

- シグナル生成
  ```python
  from kabusys.strategy import generate_signals
  from datetime import date
  total_signals = generate_signals(conn, date(2024, 1, 1))
  print(f"total signals: {total_signals}")
  ```

- ニュース収集（既知銘柄コードセットを渡して紐付け）
  ```python
  from kabusys.data.news_collector import run_news_collection
  known_codes = {"7203", "6758", "9984"}  # 例
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- カレンダー夜間更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"saved calendar rows: {saved}")
  ```

- 設定取得 (プログラム内で)
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

注意:
- 研究系の関数（kabusys.research.*）は prices_daily / raw_financials を参照するのみで、実行時に外部 API を呼びません。
- run_daily_etl などは内部で例外をキャッチし、結果オブジェクトにエラーメッセージや品質問題を格納します。戻り値の ETLResult を確認してください。

---

## ログ・運用上の注意

- LOG_LEVEL 環境変数でログレベルを調整してください（INFO/DEBUG など）。
- 本番運用時は KABUSYS_ENV=live を設定し、設定値（API のベースURL 等）を適切に行ってください。settings.is_live / is_paper / is_dev をコードで参照できます。
- J-Quants の API レート制限（デフォルト 120 req/min）を守るため、jquants_client に内部レートリミッタとリトライ制御が実装されています。
- ニュース収集は外部 RSS に依存するため、SSRF や大きなレスポンス等に対する防御（スキーム検査・ホスト検査・サイズ制限・gzip 解凍後チェック）を行っていますが、運用時にソース URL の管理には注意してください。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数 / Settings
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント / 保存ロジック
    - schema.py                 — DuckDB スキーマ定義・初期化
    - pipeline.py               — ETL パイプライン（run_daily_etl 等）
    - news_collector.py         — RSS 収集・前処理・保存
    - calendar_management.py    — カレンダー更新・営業日ユーティリティ
    - features.py               — data.stats の再エクスポート
    - stats.py                  — zscore_normalize 等
    - audit.py                  — 監査ログ用スキーマ（signal_events 等）
  - research/
    - __init__.py
    - factor_research.py        — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py    — forward returns / IC / 統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py    — features テーブル作成
    - signal_generator.py       — generate_signals（BUY/SELL 生成）
  - execution/                  — 発注系（空の __init__ を含む）
  - monitoring/                 — モニタリング用（将来的なモジュール）

---

## 貢献 / 開発メモ

- 型ヒントとドキュメンテーションストリングに従って実装しています。内部の設計仕様参照（例: StrategyModel.md, DataPlatform.md）に基づく注釈があるため、実装変更時は対応するドキュメントを更新してください。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基準に行います。CI やテスト環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用して明示的に環境を注入してください。
- DuckDB スキーマは init_schema() によって冪等的に作成されます。データ移行やスキーマ変更は既存データを考慮して行ってください。

---

必要であれば、README にサンプル .env.example やデプロイ手順（systemd / cron / Airflow / Kubernetes CronJob 等）を追加できます。追加希望があれば目的（ローカル実行・本番運用・コンテナ化）を教えてください。