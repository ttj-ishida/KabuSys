# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
ETL、ニュース NLP（LLM ベース）、リサーチ用ファクター計算、監査ログ、J-Quants クライアント、マーケットカレンダー管理などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータパイプラインとリサーチ・売買基盤を構築するためのライブラリ群です。主な役割は次の通りです。

- J-Quants API からの差分 ETL（株価・財務・カレンダー等）の実行と DuckDB への保存
- RSS ニュース収集と OpenAI（gpt-4o-mini）を用いたニュースセンチメントによる銘柄別 ai_score の生成
- マーケットレジーム判定（ETF 1321 の MA とニュースセンチメントの合成）
- ファクター計算（モメンタム / ボラティリティ / バリュー 等）と特徴量探索ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → executions のトレーサビリティ）用スキーマ初期化ユーティリティ
- 環境変数ベースの設定管理（.env 自動ロード、保護機構あり）

設計上の特徴:
- ルックアヘッドバイアス防止（内部処理で date.today()/datetime.today() を直接参照しない設計を徹底）
- DuckDB を中心としたローカル分析向けデータストア
- API 呼び出しは再試行・バックオフ・レートリミットに配慮
- 冪等性（DB 保存は ON CONFLICT / DO UPDATE 等で安全に上書き）

---

## 主な機能一覧

- data
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（fetch / save 関数）
  - カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / calendar_update_job）
  - ニュース収集（RSS → raw_news、SSRF 対策、トラッキングパラメータ除去）
  - データ品質チェック（missing_data, spike, duplicates, date_consistency）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - news_nlp.score_news: ニュースを LLM に投げ銘柄ごとの ai_score を作成
  - regime_detector.score_regime: ETF 1321 の MA とマクロニュースセンチメントを使った市場レジーム判定
- research
  - factor_research: calc_momentum, calc_volatility, calc_value
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- config
  - Settings（環境変数管理、自動 .env ロード）

---

## 必要条件 / 依存ライブラリ

最低限の依存例（環境や packaging により変動する可能性あり）:

- Python 3.10+
- duckdb
- openai
- defusedxml

インストール例（pip）:
```
pip install duckdb openai defusedxml
```

（プロジェクトをパッケージ化している場合は setup / pyproject に従ってインストールしてください）

---

## 環境変数 / 設定

Settings クラスで参照する主要な環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- KABUSYS_ENV — one of ("development", "paper_trading", "live"), default "development"
- LOG_LEVEL — one of ("DEBUG","INFO","WARNING","ERROR","CRITICAL"), default "INFO"
- OPENAI_API_KEY — OpenAI 呼び出しに利用（ai モジュールの api_key 引数でも上書き可）

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml の親ディレクトリ）にある `.env` と `.env.local` を自動で読み込みます（OS 環境変数が優先）。
- 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

注意:
- 必須の環境変数が未設定の場合、Settings のプロパティ参照時に ValueError が発生します。
- .env の書式はシェル互換（export KEY=val, クォート、コメント行など）をサポートします。

---

## セットアップ手順（例）

1. リポジトリをクローン / ダウンロード
2. 必要パッケージをインストール
   ```
   pip install -r requirements.txt
   ```
   あるいは個別に:
   ```
   pip install duckdb openai defusedxml
   ```
3. 環境変数を設定（.env を作成）
   - 例: `.env`（プロジェクトルート）
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-xxxx
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
4. DuckDB ファイル用ディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```
5. 監査ログ DB 初期化（オプション）
   - Python REPL で:
     ```py
     import duckdb
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - これにより監査用テーブルとインデックスが作成されます。

---

## 使い方（主要 API / 実行例）

以下はライブラリの主要機能を呼び出す簡単な例です。実行環境で settings に必要な環境変数を事前に設定してください。

- DuckDB 接続を作る:
  ```py
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する:
  ```py
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())
  ```

- ニュース NLP スコアを生成（指定日分）:
  ```py
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  written = score_news(conn, target_date=date(2026,3,20))
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定:
  ```py
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査スキーマを既存 DB に適用:
  ```py
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

- カレンダー更新ジョブ（夜間バッチ）:
  ```py
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"保存件数: {saved}")
  ```

- 研究用ファクター計算:
  ```py
  from kabusys.research.factor_research import calc_momentum
  from datetime import date
  factors = calc_momentum(conn, date(2026,3,20))
  ```

注意点:
- OpenAI 呼び出しが必要な関数（score_news, score_regime 等）は内部で `OPENAI_API_KEY` を参照します。API キーを引数で渡すことも可能です（テスト容易性のため）。
- 多くの DB 書き込みはトランザクションで保護されていますが、ETL は一部処理が独立して継続する設計です（部分失敗時に他処理を止めない）。

---

## ディレクトリ構成（主要ファイル）

（提供コードベースに基づく概観）

- src/kabusys/
  - __init__.py
  - config.py                             — 環境変数 / Settings 管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py                          — ニュースの LLM ベースセンチメント（score_news）
    - regime_detector.py                   — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py                    — J-Quants API クライアント（fetch/save）
    - pipeline.py                          — ETL パイプライン（run_daily_etl 等）
    - etl.py                               — ETL 便利インターフェース（ETLResult 再エクスポート）
    - news_collector.py                    — RSS 収集モジュール（SSRF 対策等）
    - quality.py                           — データ品質チェック
    - stats.py                             — 統計ユーティリティ（zscore_normalize）
    - calendar_management.py               — マーケットカレンダー管理（is_trading_day 等）
    - audit.py                             — 監査ログスキーマ定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py                   — ファクター計算（momentum, value, volatility）
    - feature_exploration.py               — 将来リターン, IC, 統計サマリー 等

---

## 運用上の注意 / 設計メモ

- Look-ahead bias prevention: 多くのモジュールは内部で現在時刻を直接参照しない／DB の date を厳格に扱うことで、バックテスト時の未来情報参照を防いでいます。
- 冪等性: J-Quants から取得したデータは save_* 関数で ON CONFLICT により上書き保存されます。ETL は差分更新とバックフィルを組み合わせて安全に運用できます。
- API 呼び出しはレート制限・再試行・指数バックオフに対応。OpenAI 呼び出しもリトライ・フォールバック（失敗時は中立値採用）を組み込んでいます。
- ニュース収集は SSRF／XML Bomb／巨大レスポンスなどへの対策が組み込まれています（_SSRFBlockRedirectHandler, defusedxml, MAX_RESPONSE_BYTES など）。
- テスト容易性: OpenAI 呼び出し部などは内部関数をパッチして差し替え可能に実装されています（unittest.mock.patch 等）。

---

## 参考 / トラブルシューティング

- 環境変数が足りない場合、Settings プロパティアクセスで ValueError が発生します。必要変数を .env に設定してください。
- DuckDB のクエリ実行時にスキーマやテーブルがない場合は pipeline/etl 側の初期化が必要です（スキーマ作成スクリプト等を用意してください）。
- OpenAI の利用は API 使用料が発生します。大量リクエストはコストとレート制限に注意してください。

---

この README はコードベースの主要機能と利用方法の要点をまとめたものです。より詳細な仕様や API の細かい動作は各モジュール（src/kabusys 以下）のドキュメント文字列とコードコメントを参照してください。