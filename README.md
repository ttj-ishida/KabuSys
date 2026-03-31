# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ（KabuSys）。  
データ収集（J-Quants / RSS）、品質チェック、ファクター計算、AI を用いたニュースセンチメント、監査ログ／約定管理、ETL パイプラインなどを提供します。

---

## プロジェクト概要

KabuSys は以下の目的を持つコンポーネント群をまとめた Python パッケージです。

- J-Quants API からの株価・財務データ取得と DuckDB への差分保存（ETL）
- RSS ベースのニュース収集と記事 → 銘柄紐付け
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント & 市場レジーム判定
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ）と特徴量評価ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（signal / order_request / execution テーブル）用スキーマ初期化ユーティリティ
- 環境変数管理（.env 自動ロード機能）と設定ラッパー

設計上、バックテストでの「ルックアヘッドバイアス」を避けるために現在日時参照を最小限に抑え、DuckDB と SQL を活用した実装になっています。

---

## 主な機能一覧

- 環境設定
  - .env 自動読み込み（プロジェクトルート判定：.git / pyproject.toml）
  - 必須環境変数のラップ（settings オブジェクト）

- データ（kabusys.data）
  - J-Quants クライアント：差分取得・レート制御・再試行・トークン自動リフレッシュ
  - ETL パイプライン（日次 ETL, 個別 ETL ジョブ）
  - 市場カレンダー管理（営業日判定、next/prev 等）
  - ニュース収集（RSS、SSRF対策、トラッキングパラメータ除去）
  - データ品質チェック（missing / spike / duplicates / date consistency）
  - 監査ログスキーマの初期化・専用 DB 作成ユーティリティ

- AI（kabusys.ai）
  - ニュース NLP（銘柄ごとのセンチメント → ai_scores に保存）
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースセンチメントの合成）

- 研究（kabusys.research）
  - ファクター計算（momentum/value/volatility）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ、Zスコア正規化

---

## セットアップ手順

1. リポジトリをクローンしてインストール（編集可能インストール推奨）

   ```bash
   git clone <this-repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"   # 依存関係は pyproject.toml/setup.cfg に依存
   ```

   ※ 実際の依存パッケージ（例）: duckdb, openai, defusedxml

2. 環境変数設定

   プロジェクトルートに `.env`（および `.env.local`）を置くと自動で読み込まれます（デフォルト）。  
   自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   必須環境変数（最低限）:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
   - KABU_API_PASSWORD: kabu ステーション API パスワード（必要に応じて）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必要に応じて）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必要に応じて）
   - OPENAI_API_KEY: OpenAI を使う機能で必要

   また、DB パスは環境変数で上書き可能（デフォルト値は下記）:
   - DUCKDB_PATH: data/kabusys.duckdb
   - SQLITE_PATH: data/monitoring.db

3. 初期 DB スキーマ（監査ログ等）の作成

   例: 監査ログ専用 DB を初期化する

   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（主要なユースケース例）

以下は最小限の使用例です。実運用ではログ設定や例外処理を追加してください。

- DuckDB 接続（設定からパスを取得）

  ```python
  import duckdb
  from kabusys.config import settings

  db_path = str(settings.duckdb_path)
  conn = duckdb.connect(db_path)
  ```

- 日次 ETL 実行（株価 / 財務 / カレンダー取得 + 品質チェック）

  ```python
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=None)  # None -> 今日 (内部で営業日調整あり)
  print(result.to_dict())
  ```

- ニュースセンチメントのスコアリング（ai_scores テーブルへ書き込み）

  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written: {n_written}")
  ```

- 市場レジーム判定（market_regime テーブルへ書き込み）

  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 研究用ファクター取得

  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  d = date(2026, 3, 20)
  mom = calc_momentum(conn, d)
  val = calc_value(conn, d)
  vol = calc_volatility(conn, d)
  ```

- 監査スキーマの初期化（既存接続へ）

  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

- .env 自動ロードの挙動

  パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml を探索）を検出できれば、自動で `.env` → `.env.local` を読み込みます。OS 環境変数が優先され、`.env.local` は `.env` を上書きします。テスト等で無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成

以下は主要なファイル／モジュールの一覧と簡単な説明です（src/kabusys 配下）。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数と設定を管理。.env 自動読み込み機能あり。
  - ai/
    - __init__.py
    - news_nlp.py
      - 銘柄ごとのニュースセンチメントを OpenAI で評価し ai_scores に書き込む。
    - regime_detector.py
      - ETF 1321 の MA200 とマクロニュースのセンチメントを合成して market_regime に記録する。
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（レート制御・リトライ・保存処理）。
    - pipeline.py
      - ETL パイプライン（run_daily_etl 等）。
    - etl.py
      - ETLResult の再エクスポート。
    - news_collector.py
      - RSS 収集（SSRF対策・XML 防御・前処理）。
    - calendar_management.py
      - 市場カレンダー管理（営業日判定 / 更新ジョブ）。
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）。
    - stats.py
      - zscore_normalize などの統計ユーティリティ。
    - audit.py
      - 監査ログスキーマと初期化ユーティリティ。
  - research/
    - __init__.py
    - factor_research.py
      - momentum/value/volatility のファクター計算。
    - feature_exploration.py
      - 将来リターン、IC、統計サマリ、ランク変換など。

---

## 注意事項 / 運用上のポイント

- OpenAI 利用
  - OPENAI_API_KEY を設定してください。API 失敗時はフェイルセーフとして 0.0 を返す設計の箇所があります（スコアの欠如を防ぐため）。
  - レスポンスの JSON 検証やリトライを実装していますが、モデルの挙動変更に備えたエラーハンドリングが必要です。

- J-Quants API
  - rate limit（120 req/min）を内部で調整していますが、並列化や大量リクエスト時は注意してください。
  - 401 を受けた場合はリフレッシュトークンで自動更新するロジックがあります。

- DuckDB
  - 一部の操作で `executemany` の空リストが問題となる箇所を考慮した実装になっています（DuckDB のバージョン互換性対策）。

- セキュリティ
  - RSS 取得時の SSRF 対策、defusedxml による XML 攻撃対策、受信サイズ制限などの防御が組み込まれています。

---

## 開発 / テスト

- 自動 .env ロードを無効にしてテストを実行する場合:

  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  pytest
  ```

- モジュール内部の外部 API 呼び出しはモック可能な設計になっています（例: kabusys.ai.news_nlp._call_openai_api を patch してテスト）。

---

この README はコードベースの主な機能と使い方・構成をまとめたものです。さらに詳しい内部設計やデータスキーマ（テーブル定義）は各モジュールの docstring を参照してください。質問や追加で README に入れたい具体的な例があれば知らせてください。