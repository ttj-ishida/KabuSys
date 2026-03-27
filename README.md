# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースセンチメント（OpenAI）、市場レジーム判定、ファクター計算、監査ログなど、自動売買システムの基盤機能を提供します。

バージョン: 0.1.0

---

## 主な機能

- データ取得・ETL
  - J-Quants API から株価日足・財務データ・マーケットカレンダーを差分取得（ページネーション対応）。
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）。
  - 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）を提供。

- データ品質チェック
  - 欠損（OHLC）・スパイク（前日比）・重複・日付不整合の検出とサマリ（`quality` モジュール）。

- ニュース収集と NLP
  - RSS 取得（SSRF対策・サイズ制限・トラッキングパラメータ除去）。
  - OpenAI（gpt-4o-mini）を使った銘柄別ニュースセンチメント（`score_news`）。
  - レスポンス検証・バッチ処理・リトライ実装。

- 市場レジーム判定
  - ETF（1321）200日移動平均乖離とマクロニュースの LLM センチメントを合成して
    日次で `market_regime` に判定（`score_regime`）。

- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（`research` モジュール）。
  - 将来リターン計算、IC（Spearman）計算、Zスコア正規化など。

- 監査ログ（トレーサビリティ）
  - signal → order_request → execution の監査テーブル作成・初期化ユーティリティ（DuckDB）。

- 設定管理
  - .env または環境変数から設定を読み込み（プロジェクトルート自動検出、ロード順: OS > .env.local > .env）。
  - 自動ロードを無効化するフラグあり（テスト向け）。

---

## 必要環境

- Python 3.10 以上（| 型注釈 等を使用）
- 必要な主要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ: urllib, json, logging 等

（実プロジェクトでは requirements.txt / pyproject.toml に依存を定義してください）

---

## インストール（開発環境向け）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （開発時は pip install -e . が使えるように setuptools/poetry でパッケージ化してください）

---

## 環境変数（必須・推奨）

settings（`kabusys.config.Settings`）で参照される主な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL で利用）
- SLACK_BOT_TOKEN — Slack 通知に使う場合
- SLACK_CHANNEL_ID — Slack チャンネル ID

OpenAI 関連:
- OPENAI_API_KEY — ai モジュール（news_nlp / regime_detector）で使用

kabu ステーション:
- KABU_API_PASSWORD — kabu API のパスワード
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi

DB パス（デフォルトあり）:
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db

その他:
- KABUSYS_ENV — development / paper_trading / live （デフォルト development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

自動 .env ロード:
- パッケージはプロジェクトルート（.git または pyproject.toml を基準）で `.env` および `.env.local` を自動読み込みします。
- 自動ロードを無効化するには環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

注意: 必須変数が欠けると `Settings` のプロパティアクセス時に ValueError が発生します。

---

## 使い方（簡易例）

以下は代表的なユースケースの呼び出し例です（最低限のコード例）。

- DuckDB 接続
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する
  - from datetime import date
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- ニュースセンチメントをスコア化（OpenAI API キー必須）
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - count = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY または api_key 引数

- 市場レジームを判定（OpenAI API キー必須）
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ DB 初期化（専用 DB）
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")

- 研究用ファクター計算
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  - momentum = calc_momentum(conn, target_date=date(2026, 3, 20))

実際の運用では例外処理・ログ設定・API キー管理（安全な Vault 等）を必ず行ってください。

---

## 開発・テスト時の注意

- テストの際に自動 .env 読込を避けたい場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。

- OpenAI 呼び出しや外部 API 呼び出しはモック可能なように実装されています（モジュール内部の `_call_openai_api` 等を unittest.mock.patch で差し替え可能）。

- DuckDB の executemany に空リストを渡すとエラーになるため、モジュール内で注意してハンドリングされています。ユニットテストで DB に接続する際はインメモリ(":memory:") を利用できます。

---

## ディレクトリ構成

主要なファイル・モジュール構成（src/kabusys 配下）:

- __init__.py
- config.py — 環境変数 / 設定管理（.env 自動読み込み）
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント（score_news）
  - regime_detector.py — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存ロジック）
  - pipeline.py — ETL パイプライン（run_daily_etl 他）
  - etl.py — ETLResult のエクスポート
  - news_collector.py — RSS ニュース収集
  - calendar_management.py — マーケットカレンダー管理（営業日判定など）
  - quality.py — データ品質チェック
  - stats.py — 共通統計ユーティリティ（zscore_normalize）
  - audit.py — 監査ログ（DDL / 初期化）
- research/
  - __init__.py
  - factor_research.py — ファクター計算（momentum/value/volatility）
  - feature_exploration.py — 将来リターン / IC / 統計サマリー

---

## 付記・設計上のポイント

- Look-ahead bias 対策: モジュールの多くは `date` / `target_date` を明示的に受け取り、内部で `date.today()` を無暗に参照しません（バックテストでの再現性重視）。
- 冪等性: ETL と保存は基本的に冪等（ON CONFLICT DO UPDATE / INSERT … DO NOTHING）で実装されています。
- フェイルセーフ: 外部 API（OpenAI, J-Quants）失敗時は例外を表面化させないか、ロギングして安全側のデフォルト値を使用する設計が多く見られます（ただし重要な箇所ではエラーを伝播）。
- セキュリティ: news_collector では SSRF 対策や XML パーサーのハードニング（defusedxml）を行っています。

---

README はここまでです。実際の運用・デプロイの際は以下を推奨します:
- requirements.txt / pyproject.toml に依存を明示
- CI で DB / API 呼び出しをモックするテストを用意
- 機密情報は環境変数やシークレット管理により安全に保管

必要であれば、この README をベースにインストール手順や具体的なサンプルスクリプト（systemd / cron / Airflow 用）を追加で作成します。