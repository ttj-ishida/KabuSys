# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL によるデータ取得・品質チェック、ニュースの NLP スコアリング、マーケットレジーム判定、監査ログ（トレーサビリティ）など、取引・研究に必要な基盤処理を提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で date.today() を直接参照しない等）
- DuckDB を主データストアとして利用（冪等保存・トランザクション制御）
- 外部 API 呼び出しはリトライ / バックオフを備えた実装
- ETL や品質チェックはフェイルセーフ（部分失敗を許容してログ収集）

バージョン: 0.1.0

---

## 機能一覧

- データ取得・ETL
  - J-Quants から株価（OHLCV）、財務データ、上場銘柄情報、JPX カレンダーを差分取得して DuckDB に保存（jquants_client / pipeline）
  - ETL の結果を ETLResult で集約（成功・保存件数・品質問題など）
- データ品質チェック
  - 欠損（OHLC）検出、重複検出、スパイク検出、日付整合性チェック（quality）
- ニュース収集・前処理
  - RSS フィード取得、URL 正規化、トラッキングパラメータ除去、SSRF 対策、gzip 対応（news_collector）
- ニュース NLP（LLM）スコアリング
  - 銘柄ごとにニュースをまとめて OpenAI（gpt-4o-mini）でセンチメント評価し ai_scores に保存（news_nlp）
- 市場レジーム判定
  - ETF (1321) の 200 日 MA 乖離とマクロニュースの LLM センチメントを合成して日次レジーム判定（regime_detector）
- リサーチ / ファクター処理
  - Momentum / Volatility / Value 等のファクター計算、将来リターン計算、IC（Spearman）や統計サマリー（research）
- 統計ユーティリティ
  - Z スコア正規化等（data.stats）
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions のテーブル定義と初期化ヘルパー（data.audit）
- 設定管理
  - .env または環境変数から設定を自動ロード（config）

---

## セットアップ手順

前提
- Python 3.10+（typing の構文を使用）
- ネットワークアクセス（J-Quants, OpenAI 等）

1. リポジトリをクローン／作業ディレクトリへ移動

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. インストール（ローカル開発用）
   - 必要なパッケージ例（プロジェクトに requirements.txt があればそれを利用してください）
     ```
     pip install duckdb openai defusedxml
     ```
   - 開発インストール（パッケージ化されている場合）
     ```
     pip install -e .
     ```

4. 環境変数 / .env の準備
   - ルートに `.env` / `.env.local` を置くと自動ロードされます（config モジュールが .git または pyproject.toml からプロジェクトルートを検出して読み込み）。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   推奨される環境変数（例）:
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - OPENAI_API_KEY=your_openai_api_key
   - KABU_API_PASSWORD=your_kabu_api_password
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi
   - SLACK_BOT_TOKEN=your_slack_bot_token
   - SLACK_CHANNEL_ID=your_slack_channel_id
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - KABUSYS_ENV=development  # development | paper_trading | live
   - LOG_LEVEL=INFO

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

---

## 使い方（主要な例）

以下では DuckDB を使った接続例と主要 API の呼び出し例を示します。実行前に必要な環境変数（特に OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN）を設定してください。

- 共通準備
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する（市場カレンダー、株価、財務、品質チェックを順に実行）:
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコアリング（対象日の日次ウィンドウで raw_news / news_symbols を参照し ai_scores に書き込む）:
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定（ETF 1321 の MA 乖離 + マクロニュース）:
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DB を初期化する（監査専用の DuckDB を作成・スキーマ適用）:
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/kabusys_audit.duckdb")
  ```

- ファクター計算（例: momentum）:
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

- 設定値を参照する:
  ```python
  from kabusys.config import settings

  print(settings.duckdb_path)  # Path オブジェクト
  print(settings.is_live)
  ```

注意点:
- OpenAI 呼び出しを行う関数（score_news / score_regime）は API キーを引数で上書き可能（api_key="..."）。引数未指定時は環境変数 OPENAI_API_KEY を参照します。
- DuckDB に対する INSERT は多くの箇所で ON CONFLICT（冪等）を採用しています。ETL は冪等に設計されています。

---

## よく使うユーティリティ / API 一覧（抜粋）

- kabusys.config
  - settings: アプリケーション設定オブジェクト（環境変数ラッパー）
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, ...): 日次 ETL（ETLResult を返す）
  - run_prices_etl / run_financials_etl / run_calendar_etl: 個別 ETL
- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token(refresh_token=None)
- kabusys.data.quality
  - run_all_checks(conn, ...)
- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)
- kabusys.research
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary

---

## ディレクトリ構成

主要なファイルと簡単な説明：

- src/kabusys/
  - __init__.py — パッケージ初期化、バージョン定義
  - config.py — 環境変数・設定管理（.env 自動ロード・settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースを LLM に送って銘柄ごとのセンチメントを ai_scores に保存
    - regime_detector.py — ETF MA とマクロニュースを合成して市場レジームを判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得 + DuckDB 保存）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）および ETLResult 定義
    - etl.py — ETL の公開インターフェース（ETLResult の re-export）
    - calendar_management.py — 市場カレンダー管理・営業日判定ロジック
    - news_collector.py — RSS 取得・前処理と raw_news への保存ロジック
    - stats.py — 共通統計ユーティリティ（zscore_normalize）
    - quality.py — データ品質チェック（欠損・重複・スパイク・日付不整合）
    - audit.py — 監査ログスキーマ定義と初期化（signal_events / order_requests / executions）
  - research/
    - __init__.py
    - factor_research.py — Momentum/Volatility/Value 等のファクター計算
    - feature_exploration.py — forward return, IC, 統計サマリー等
  - monitoring / strategy / execution / ...（パッケージ初期化で __all__ に含まれるが、上の主要モジュールが中心）

---

## 開発／運用上の注意

- 環境変数管理
  - .env ファイルの自動ロードはプロジェクトルート（.git または pyproject.toml を探索）を基準に行われます。
  - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI / J-Quants
  - API 呼び出しはリトライ・バックオフを備えていますが、API キーの管理とレート制限には注意してください。
- DuckDB
  - ETL・監査テーブル初期化には適切なファイルパス（書き込み権限）を使用してください。
- テスト
  - LLM 呼び出しなど外部依存はユニットテストで差し替え（モック）できるよう設計されています（モジュール内の _call_openai_api を patch する等）。
- 本番環境
  - settings.env による挙動差（development / paper_trading / live）を利用して発注や通知の有効/無効を切り替えてください。

---

## ライセンス・貢献

この README はコードベース（提供されたモジュール）に基づく概要ドキュメントです。実際のプロジェクトにおけるライセンスやコントリビューション方法はリポジトリのルートにある LICENSE / CONTRIBUTING ドキュメントを参照してください。

---

何か追記してほしい項目（例：より詳細な .env.example、CI / テスト手順、具体的な DB スキーマ定義の一覧など）があれば教えてください。