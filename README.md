# KabuSys — 日本株自動売買プラットフォーム

KabuSys は日本株のデータパイプライン、特徴量計算、ニュース NLP、マーケットレジーム判定、監査ログなどを含む自動売買システムのライブラリ群です。本リポジトリはバックテスト／リサーチ／運用を想定した共通ユーティリティを提供します。

- 対象言語: Python 3.10+
- 主要依存: duckdb, openai, defusedxml（詳しい依存はプロジェクトの requirements/pyproject を参照してください）

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要 API と簡単な例）
- ディレクトリ構成
- 注意事項 / 補足

---

## プロジェクト概要

KabuSys は以下を目的としたコンポーネント群をまとめたライブラリです。

- J-Quants API からのデータ取得（株価、財務、マーケットカレンダー）
- DuckDB を用いた差分 ETL パイプライン（日次実行を想定）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- RSS ニュース収集・前処理・銘柄紐付け
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント解析（銘柄別 ai_score）とマクロセンチメントを用いた市場レジーム判定
- ファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ、IC 等）
- 監査ログ（signal → order_request → execution のトレーサビリティ）スキーマの初期化・管理

設計上、ルックアヘッドバイアスを避ける実装方針や冪等性、API リトライ・バックオフ、SSRF 防止などの実運用向けの考慮が施されています。

---

## 機能一覧（抜粋）

- 環境設定管理
  - .env/.env.local の自動読み込み（プロジェクトルート検出）
  - 必須設定の明示的取得（settings オブジェクト）

- データ取得 / ETL
  - J-Quants クライアント（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar 等）
  - DuckDB への保存（save_daily_quotes / save_financial_statements / save_market_calendar）
  - 日次 ETL: run_daily_etl（差分取得・保存・品質チェックを一括実行）

- データ品質チェック
  - 欠損、重複、スパイク、日付不整合などを検出し QualityIssue を返却

- ニュース収集 / NLP
  - RSS 取得（SSRF 対策・受信サイズ制限・トラッキングパラメータ除去）
  - ニュース前処理、銘柄ごとのまとめ
  - OpenAI を用いた銘柄別センチメント（score_news）
  - マクロセンチメント + ETF MA 乖離を用いた市場レジーム判定（score_regime）

- リサーチ / ファクター
  - calc_momentum / calc_value / calc_volatility
  - calc_forward_returns / calc_ic / factor_summary / zscore_normalize

- 監査ログ（audit）
  - 監査テーブル DDL とインデックス定義
  - init_audit_schema / init_audit_db による初期化

---

## セットアップ手順

前提: Python 3.10 以上を推奨。

1. リポジトリをクローンしてワークディレクトリへ移動

   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成と有効化（任意）

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール

   依存関係は pyproject.toml / requirements.txt を参照してください。主要なものの例:

   ```bash
   pip install duckdb openai defusedxml
   # またはプロジェクトで提供されているセットアップ方法に従ってください
   pip install -e .
   ```

4. 環境変数 / .env の準備

   プロジェクトルートに `.env`（必要な場合 `.env.local`）を用意してください。自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセット。

   必要な主要環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
   - OPENAI_API_KEY: OpenAI 利用時に必要（score_news / score_regime）
   - その他（任意）:
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - KABUSYS_ENV (development | paper_trading | live)（デフォルト: development）
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用 DB 等）

   例 .env の最小例:

   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   ```

---

## 使い方（主要 API と簡単な例）

以下は主要ワークフローの利用例です。DuckDB 接続には `duckdb` パッケージを使用します。

- DuckDB 接続オブジェクトの作成（設定値を使う例）:

  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行

  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコア生成（OpenAI API キーが環境変数にセットされていること）

  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} symbols")
  ```

- 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメントを合成）

  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- ファクター計算（モメンタム / ボラティリティ / バリュー）

  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value

  momentum = calc_momentum(conn, date(2026,3,20))
  volatility = calc_volatility(conn, date(2026,3,20))
  value = calc_value(conn, date(2026,3,20))
  ```

- 監査ログスキーマ初期化

  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # または既存 conn に対して init_audit_schema(conn)
  ```

注意点（AI/外部 API に関する挙動）
- OpenAI 呼び出しでエラーやレート制限が発生した場合、多くの箇所でフォールバック（0.0 にする等）し、安全側に倒す設計になっています。ログを必ず確認してください。
- J-Quants API 呼び出しは内部でレート制御・リトライ・401 のトークン自動リフレッシュを行います。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要なモジュール構成は以下のとおりです（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py            — 環境変数 / 設定管理（settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースを集約し OpenAI で銘柄別センチメントを算出
    - regime_detector.py — ETF MA とマクロセンチメントを合成して市場レジームを判定
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py        — ETL パイプライン（run_daily_etl 等）
    - etl.py             — ETLResult の再エクスポート
    - quality.py         — データ品質チェック
    - news_collector.py  — RSS 収集 / 前処理 / 保存
    - calendar_management.py — 市場カレンダー管理（営業日判定等）
    - stats.py           — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py           — 監査ログスキーマ / 初期化
  - research/
    - __init__.py
    - factor_research.py — Momentum / Volatility / Value の計算
    - feature_exploration.py — forward returns / IC / 統計サマリー

---

## 注意事項 / 補足

- Python バージョン: typing の "X | Y" 構文を使用しているため Python 3.10 以上が必要です。
- .env 自動読み込み: パッケージはインポート時にプロジェクトルート（.git または pyproject.toml を起点）を探索して `.env` / `.env.local` を自動読み込みします。テストや特殊ケースで自動読み込みを止めたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- セキュリティ: news_collector では SSRF 対策や XML 安全対策（defusedxml）・受信サイズ制限などを実装していますが、実運用時は外部向け設定（User-Agent、タイムアウト、ソースのホワイトリスト等）を適切に行ってください。
- ロギング: 多くの関数は詳細なログを出すので、運用時は LOG_LEVEL を調整してください。
- テスト: 各モジュールは外部 API 呼び出しやネットワークを伴う箇所に差し替え可能な内部関数を用意しており、ユニットテストでモックしやすい設計になっています。

---

不明点や README に追加したいサンプル・ワークフロー（CI 実行、cron ジョブ化、Slack 通知の例など）があれば教えてください。必要に応じて README を拡張します。