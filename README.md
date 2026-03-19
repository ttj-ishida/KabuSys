# KabuSys

日本株向けの自動売買システム用ライブラリ（KabuSys）のリポジトリ用 README。

このドキュメントはソースコード（src/kabusys/ 以下）に基づき、プロジェクト概要・機能・セットアップ・基本的な使い方・ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買・データプラットフォーム用途の Python モジュール群です。以下のレイヤーを備えた設計になっています。

- データ収集（J-Quants API 経由の株価・財務データ、RSS ニュース）
- DuckDB によるデータスキーマと ETL パイプライン（差分取得、保存、品質チェック）
- 研究（research）で算出した生ファクターを用いた特徴量作成（feature engineering）
- シグナル生成（features + AI スコアを統合して BUY/SELL を決定）
- 発注／監視レイヤ（スキーマ・監査ログなど発注関連のテーブル定義、実行は execution 層）

設計方針として「ルックアヘッドバイアス回避」「冪等性（ON CONFLICT）」「ネットワーク／SSRF 対策」「ログ・監査性」を重視しています。

---

## 主な機能一覧

- 環境変数管理
  - プロジェクトルートの `.env` / `.env.local` を自動読み込み（無効化可能）
  - 必須値チェック（settings オブジェクト）

- データ取得・保存（J-Quants）
  - 日次株価（fetch + save）
  - 財務データ（fetch + save）
  - JPX カレンダー取得
  - API レート制御、リトライ、トークン自動リフレッシュ

- DuckDB スキーマ管理
  - raw / processed / feature / execution 層のテーブル DDL を一括作成（init_schema）

- ETL パイプライン
  - 差分更新（backfill 対応）、品質チェック、日次 ETL（run_daily_etl）

- 特徴量計算（strategy/research）
  - momentum / volatility / value 系ファクター計算
  - Zスコア正規化ユーティリティ
  - features テーブルへの日次アップサート（build_features）

- シグナル生成
  - features と ai_scores を統合して final_score を算出
  - Bear レジーム抑制、BUY/SELL 生成、signals テーブルへの日次置換（generate_signals）
  - エグジット条件（ストップロス等）対応

- ニュース収集
  - RSS フィード取得、前処理、raw_news 保存、銘柄コード抽出、紐付け（run_news_collection）
  - SSRF/サイズ/XML 攻撃対策を含む堅牢な実装

- カレンダー管理
  - 営業日判定、前後営業日の検索、カレンダー差分更新ジョブ（calendar_update_job）

- 監査ログ（audit）
  - signal → order_request → execution まで追跡可能な監査テーブル群

---

## 必要な環境（概略）

- Python 3.8+（ソースは型注釈で modern な仕様を利用）
- 推奨パッケージ（使用している主要ライブラリ）:
  - duckdb
  - defusedxml
- ネットワーク経路から API にアクセス可能な環境
- 環境変数（下記参照）

パッケージ管理ファイル（requirements.txt / pyproject.toml）はこのスナップショットに含まれていません。実行環境に合わせて依存を追加してください。

---

## 環境変数（.env）と設定

KabuSys は `.env` / `.env.local`（プロジェクトルート）または環境変数から設定を読み込みます。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。

主要な環境変数（例）:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack 送信先チャンネル ID（必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite モニタリング DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境（development / paper_trading / live; デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL; デフォルト INFO）

例 `.env`（テンプレート）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意: セキュリティ上の理由からシークレットはソース管理に置かないでください。

---

## セットアップ手順（ローカル開発向け）

1. 仮想環境作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール
   例:
   ```
   pip install duckdb defusedxml
   ```
   （実際のプロジェクトでは requirements.txt / pyproject.toml に依存を書くことを推奨します）

3. リポジトリルートに `.env` を作成し、必要な環境変数を設定

4. DuckDB スキーマ初期化（例: Python スクリプトまたは REPL）
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)  # data/kabusys.duckdb を作成してスキーマを作る
   ```

5. （オプション）監視 DB 初期化や外部サービスの設定を行ってください。

---

## 使い方（代表的な API と呼び出し例）

以下は最小限の利用フロー例です。各関数は詳細な例外処理やログ出力を行いますので、実運用ではハンドリングを追加してください。

- DuckDB スキーマの初期化
  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema

  conn = init_schema(settings.duckdb_path)
  ```

- 日次 ETL の実行（J-Quants から差分取得して保存）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 市場カレンダー更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print("saved", saved)
  ```

- 特徴量のビルド（features テーブル作成）
  ```python
  from datetime import date
  from kabusys.strategy import build_features
  count = build_features(conn, target_date=date.today())
  print("built features:", count)
  ```

- シグナル生成
  ```python
  from datetime import date
  from kabusys.strategy import generate_signals
  total = generate_signals(conn, target_date=date.today(), threshold=0.6)
  print("signals generated:", total)
  ```

- ニュース収集（RSS）
  ```python
  from kabusys.data.news_collector import run_news_collection
  # known_codes: 抽出する有効銘柄コードの集合（例: 全銘柄コードのセット）
  results = run_news_collection(conn, sources=None, known_codes=set(["7203","6758"]))
  print(results)
  ```

- 研究用ユーティリティ（forward returns / IC 等）
  ```python
  from kabusys.research import calc_forward_returns, calc_ic, factor_summary

  fwd = calc_forward_returns(conn, target_date=date.today(), horizons=[1,5,21])
  # factor_records は calc_momentum などの結果を渡す
  ```

---

## よく使うモジュール（短い説明）

- kabusys.config — 環境変数 / 設定読み込み（.env 自動ロード）
- kabusys.data.jquants_client — J-Quants API クライアント（取得・保存ユーティリティ含む）
- kabusys.data.schema — DuckDB スキーマ定義と init_schema
- kabusys.data.pipeline — ETL パイプライン（run_daily_etl 等）
- kabusys.data.news_collector — RSS ニュース収集・保存・銘柄抽出
- kabusys.data.calendar_management — JPX カレンダー管理（営業日ロジック）
- kabusys.data.stats — zscore_normalize 等の統計ユーティリティ
- kabusys.research — 研究用ファクター計算（calc_momentum 等）
- kabusys.strategy — build_features / generate_signals
- kabusys.execution — 発注層（パッケージ化のための名前空間、実装は別途）

---

## ディレクトリ構成（ソースツリーの要約）

以下は src/kabusys 以下の主なファイル/モジュール（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py                       — 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py             — J-Quants API クライアント & 保存関数
      - news_collector.py             — RSS 収集・保存・紐付け
      - schema.py                     — DuckDB スキーマ定義 / init_schema / get_connection
      - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
      - stats.py                      — 統計ユーティリティ（zscore_normalize）
      - features.py                   — features の公開ラッパ
      - calendar_management.py        — カレンダー管理/ジョブ
      - audit.py                      — 監査ログ用 DDL
      - (その他: quality, monitoring 等は別ファイルで存在する想定)
    - research/
      - __init__.py
      - factor_research.py            — momentum/volatility/value の計算
      - feature_exploration.py        — forward returns / IC / summary
    - strategy/
      - __init__.py
      - feature_engineering.py        — build_features（正規化・フィルタ・UPSERT）
      - signal_generator.py           — generate_signals（final_score 計算、BUY/SELL 作成）
    - execution/
      - __init__.py                   — 発注/実行層の名前空間（実装は別）
    - monitoring/                      — 監視系モジュール（外部監視・Slack通知など、実装想定）

（上記はソースの主要部分を抜粋したものです。リポジトリ全体のファイル数や細部は実際のツリーを参照してください）

---

## 運用上の注意・設計上のポイント

- 環境変数は .env に保存する際は権限管理に注意してください（機密情報を公開しない）。
- J-Quants API のレート制限やエラーハンドリングは jquants_client に組み込まれていますが、過剰な同時実行は避けること。
- DuckDB のファイル（DUCKDB_PATH）は定期バックアップを推奨します。監査ログは削除しない前提です。
- 本コードは発注 API（execution 層）への直接送信を分離しており、実運用時はブローカー API の実装・安全対策を追加してください（冪等制御・二重送信防止など）。
- テスト／CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使い、明示的に環境を注入してテスト可能です。

---

## 参考：簡単なトラブルシュート

- settings の必須 env が見つからない:
  - `.env` が正しいディレクトリ（プロジェクトルート、.git や pyproject.toml のある階層）に置かれているか確認
  - 自動ロードを無効にしている (KABUSYS_DISABLE_AUTO_ENV_LOAD) 場合は手動で環境変数を設定

- DuckDB のテーブルが作成されない:
  - init_schema を適切に呼び出しているか
  - ファイルパスの親ディレクトリに書き込み権限があるか

- RSS 取得で大量エラーが出る:
  - ネットワーク/リダイレクトでプライベートホストに飛ばされていないか
  - フィード側が gzip や巨大レスポンスで応答していないか（10MB 上限に達するとスキップ）

---

## さらに進めるために

- テストコード、CI 設定、依存リスト（requirements.txt / pyproject.toml）を整備してください。
- execution 層（ブローカー接続）の実装は別途安全設計に基づいて作成します（鍵管理・冪等制御・外部サービスのリトライ等）。
- モニタリングやアラート（Slack連携、Prometheus 等）を追加すると運用が安定します。

---

この README はソースコードのスナップショットに基づいて作成しています。実際の運用時はプロジェクトのドキュメント（DataPlatform.md / StrategyModel.md 等）や実装コメントも合わせて参照してください。