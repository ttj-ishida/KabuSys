# KabuSys

日本株向けのデータプラットフォームおよび自動売買／リサーチ基盤ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP スコアリング（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（発注／約定トレース）などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - `.env` / `.env.local` の自動読み込み（プロジェクトルート検出）
  - 必須設定を容易に取得する Settings API

- データ取得（J-Quants）
  - 株価日足（OHLCV）取得・保存（ページネーション / 冪等保存）
  - 財務データ（四半期）取得・保存
  - JPX マーケットカレンダー取得・保存
  - レート制御・リトライ・トークン自動リフレッシュ対応

- ETL パイプライン
  - 差分取得 / バックフィル / 品質チェックを含む日次 ETL（run_daily_etl）
  - 個別ジョブ：run_prices_etl / run_financials_etl / run_calendar_etl

- ニュース収集
  - RSS から記事収集（URL 正規化・記事 ID の SHA-256 ハッシュ化）
  - SSRF 対策・受信サイズ制限・XML 安全パーサ（defusedxml）

- ニュース NLP（OpenAI）
  - ニュースを銘柄ごとに集計して LLM（gpt-4o-mini）でセンチメントを評価（score_news）
  - チャンク・バッチ呼び出し、パース検証、クリップ、部分失敗保護

- 市場レジーム判定（Regime）
  - ETF 1321 の 200 日移動平均乖離とマクロニュース LLM センチメントを合成して日次レジーム判定（score_regime）

- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計サマリー、Zスコア正規化ユーティリティ

- データ品質チェック
  - 欠損、重複、スパイク（大幅変動）、日付不整合チェック（run_all_checks）

- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定 のトレーサビリティ用テーブル生成と初期化（init_audit_schema / init_audit_db）
  - UUID ベースの冪等・トレーサビリティ設計

---

## 必要な環境・依存ライブラリ（代表例）

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml

（実際のプロジェクトでは pyproject.toml / requirements.txt を参照してください）

---

## 環境変数

主に以下の環境変数を使用します（必須は明記）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（ETL／jquants_client）
- SLACK_BOT_TOKEN — Slack 通知用（利用する機能がある場合）
- SLACK_CHANNEL_ID — Slack チャンネル ID（利用する機能がある場合）
- KABU_API_PASSWORD — kabu ステーション API パスワード（注文連携機能利用時）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime を使用する場合）

オプション（デフォルトあり）:
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) — default: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — default: INFO

自動 .env ロード:
- プロジェクトルートにある `.env` / `.env.local` を自動で読み込みます（OS 環境変数が優先）。
- 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

注意:
- Settings API（kabusys.config.settings）は不足する必須変数で ValueError を送出します。
- `.env.example` を参考に `.env` を作成してください（プロジェクトに .env.example を置くことを想定）。

---

## セットアップ手順（ローカル開発用）

1. Python と仮想環境の準備
   - 推奨: Python 3.10+
   - 仮想環境を作成/有効化:
     - python -m venv .venv
     - source .venv/bin/activate  (Unix/macOS)
     - .venv\Scripts\activate     (Windows)

2. 依存ライブラリのインストール
   - 実際のプロジェクトでは pyproject.toml / requirements.txt を使用してください。代表例:
     - pip install duckdb openai defusedxml

3. 環境変数の設定
   - プロジェクトルートに `.env` を作成して必要なキーを設定するか、環境に直接設定します。
   - 例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-xxxx...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=CXXXXXXXX
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=DEBUG
     ```

4. データベース用ディレクトリを作る（必要に応じて）
   - mkdir -p data

5. （推奨）プロジェクトを editable install
   - pip install -e .

---

## 使い方（主要 API と実行例）

以下は代表的な利用シナリオと簡単なコード例です。実行時には適切な環境変数・APIキーを設定してください。

- 日次 ETL を実行する（DuckDB 接続が既に存在すると想定）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュースセンチメント（LLM）でスコアを生成する:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  score_count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {score_count} codes")
  ```

- 市場レジーム判定（1321 MA200 とマクロニュース合成）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB を初期化して接続を取得する:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # テーブル群が作成され、UTC TimeZone が設定されます
  ```

- 研究用: モメンタム計算・IC・Zスコア正規化:
  ```python
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_forward_returns, calc_ic, zscore_normalize

  conn = duckdb.connect("data/kabusys.duckdb")
  target = date(2026, 3, 20)
  factors = calc_momentum(conn, target)
  fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
  ic = calc_ic(factors, fwd, "mom_1m", "fwd_1d")
  print("IC:", ic)
  ```

注意点:
- score_news / score_regime は OpenAI API を呼ぶため API キーとコスト制約に注意してください。テストではモック可能な設計です（内部の _call_openai_api を patch）。
- run_daily_etl は J-Quants API を呼びます。J-Quants のトークンと利用規約に従ってください。
- KABUSYS_ENV を `live` にすると本番発注等と連携する機能を有効化する想定です。まず `development` または `paper_trading` で十分に検証してください。

---

## ディレクトリ構成（主要ファイル）

パッケージルート: src/kabusys

- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - calendar_management.py
  - etl.py
  - pipeline.py
  - stats.py
  - quality.py
  - audit.py
  - jquants_client.py
  - news_collector.py
  - (その他ETL/jquants補助モジュールを想定)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- monitoring, strategy, execution, など（パッケージの __all__ に含まれる想定モジュール）

（上記はこのコードベースで提供されている主要モジュールの一覧です。実際のプロジェクトでは更にテスト、CLI、Web/監視連携等がある可能性があります。）

---

## 運用上の注意 / ベストプラクティス

- ローカルでの初期動作確認は development モードで行い、外部発注や実際のブローカー接続を行う前に多層の検証を実施してください。
- OpenAI の呼び出しはレート・コストが発生します。バッチサイズや頻度を運用に合わせて調整してください。
- J-Quants API のレート制限を守るため、jquants_client は内部でレート制御とリトライを行います。トークンの管理を適切に行ってください。
- データ品質チェック（quality.run_all_checks）を ETL 後に必ず実行し、問題がある場合は運用担当者が調査・対処するワークフローを用意してください。
- `.env.local` はローカル上で上書きしたい機密設定（例: 開発用OAuthトークン）を置くのに便利です。ただし git 管理しないよう .gitignore へ登録してください。

---

もし README に加えたい具体的な使用例（CLI スクリプト、Dockerfile、CI 設定など）があれば、その要件を教えてください。README をそれに合わせて拡張します。