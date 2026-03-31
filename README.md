# KabuSys

日本株向けのデータプラットフォーム & 自動売買・リサーチ基盤ライブラリです。  
J-Quants / kabuステーション / RSS / OpenAI 等を統合して、データ収集（ETL）・品質チェック・ファクター計算・ニュースNLP・市場レジーム判定・監査ログを提供します。

主な設計方針：
- ルックアヘッドバイアス対策（内部で datetime.today()/date.today() を直接参照しない設計）
- DuckDB を中心としたローカルデータストア（冪等保存、ON CONFLICT を多用）
- 外部 API 呼び出しに対して堅牢なリトライ／レート制御を実装
- ニュース収集での SSRF 対策、XML 攻撃対策（defusedxml）
- OpenAI 呼び出しは JSON mode を活用、テストのために差し替え可能な設計

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート探索）
  - 必須環境変数の検証（settings API）
- データ取得（J-Quants）
  - 株価日足（OHLCV）、財務諸表、上場銘柄情報、JPX マーケットカレンダー
  - レート制御（120 req/min）、トークン自動リフレッシュ、ページネーション対応
  - DuckDB へ冪等保存（save_* 関数）
- ETL パイプライン
  - 差分取得 / バックフィル / 品質チェック / 日次 ETL の統合（run_daily_etl）
  - 品質チェック（欠損、スパイク、重複、日付不整合）
- ニュース収集 / NLP
  - RSS 収集（SSRF 対策、トラッキングパラメータ除去）
  - OpenAI を用いた銘柄別ニュースセンチメント（score_news）
- 市場レジーム判定
  - ETF(1321) の MA200 乖離とマクロニュース（LLM）を重み合成して daily レジームを算出（score_regime）
- 研究支援
  - モメンタム / ボラティリティ / バリュー 等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクターの統計サマリ
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブル初期化・DB作成ユーティリティ（init_audit_schema, init_audit_db）
- ユーティリティ
  - 統計ユーティリティ（zscore_normalize 等）

---

## 要件（主要依存パッケージ）

最低限の主要依存（抜粋）：
- Python 3.10+
- duckdb
- openai
- defusedxml

（プロジェクトのセットアップ時に requirements.txt / Poetry 等で管理してください）

---

## セットアップ手順

1. リポジトリをクローン、仮想環境を作る
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （開発用）pip install -e . など

3. 環境変数を用意
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を作成すると自動読み込みされます。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

   主な必須キー（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注等を使う場合）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（通知機能を使う場合）
   - SLACK_CHANNEL_ID: Slack 送信先チャンネル ID
   - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 等で使用）

   任意 / デフォルト設定
   - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）

4. データベースディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## 使い方（基本例）

※ 各例では事前に environment（OPENAI_API_KEY など）と DuckDB ファイルが準備されていることを想定します。

- 設定へのアクセス
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)  # Path オブジェクト
  ```

- DuckDB 接続（デフォルトパスを利用）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの NLP スコアを生成（OpenAI 必須）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written scores: {written}")
  ```

- 市場レジームスコアを算出（OpenAI 必須）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DB を初期化する（専用ファイルを作る例）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

- ファクター/研究用ユーティリティ
  ```python
  from kabusys.research import calc_momentum, calc_volatility, calc_value, zscore_normalize

  momentum = calc_momentum(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  value = calc_value(conn, date(2026, 3, 20))
  normed = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])
  ```

注）OpenAI 呼び出し部分（news_nlp._call_openai_api / regime_detector._call_openai_api）はユニットテスト時にモック差し替えして利用できるよう設計されています。

---

## 重要な設計・安全上の注意点

- Look-ahead bias を避けるため、内部では target_date 未満／以前のみを参照するなどの工夫が随所にあります。バックテスト等で日付取り扱いに注意してください。
- J-Quants API はレート制限があるため、jq クライアントはレート制御とリトライを実装しています。過度な呼び出しを避けてください。
- ニュース収集は SSRF・XML攻撃・Gzip bomb 等を考慮した堅牢な実装になっていますが、RSS ソースの追加時は信頼性に注意してください。
- DuckDB に対する executemany の空リスト渡し等、バージョン依存で注意が必要な実装があります（コード内に注記あり）。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要モジュール / ファイル（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                       — 環境設定管理（.env 自動読み込み / Settings）
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュース NLP スコアリング（score_news）
    - regime_detector.py             — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（fetch/save 系）
    - pipeline.py                    — ETL パイプライン（run_daily_etl 他）
    - etl.py                         — ETLResult 再エクスポート
    - news_collector.py              — RSS ニュース収集（fetch_rss 等）
    - calendar_management.py         — 市場カレンダー管理（is_trading_day 等）
    - quality.py                     — データ品質チェック
    - stats.py                       — 統計ユーティリティ（zscore_normalize）
    - audit.py                       — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py             — モメンタム・バリュー・ボラティリティ等
    - feature_exploration.py         — 将来リターン・IC・統計サマリ etc.
  - monitoring/ (※コードに参照はある可能性があります)
  - その他（strategy/execution/monitoring といった公開モジュールのスタブ）

詳細は各モジュールの docstring を参照してください。コードには多くの設計上の注記（Look-ahead 対策、リトライ戦略、互換性注意点など）が含まれています。

---

もし README に含めたい追加の使用例（デプロイ手順、Dockerfile、CI 設定、requirements.txt の内容、サンプル .env.example など）があれば教えてください。それに合わせて追記・整形します。