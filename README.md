# KabuSys

KabuSys は日本株向けのデータプラットフォームと自動売買支援ライブラリです。  
ETL（J‑Quants からのデータ取得）→ データ品質チェック → ニュース NLP / レジーム判定 → ファクター研究 → 発注監査ログなど、トレーディングシステムに必要な共通処理を収めたモジュール群を提供します。

バージョン: 0.1.0

---

## 概要（Project overview）

KabuSys は以下の目的を想定した Python パッケージです。

- J‑Quants API から株価・財務・カレンダー等を差分取得して DuckDB に保存する ETL パイプライン
- 生データに対する品質チェック（欠損、スパイク、重複、日付整合性）
- ニュース（RSS）収集と OpenAI を用いたセンチメント分析（銘柄別 ai_score）
- 市場レジーム判定（ETF MA とマクロニュースの LLM スコアを合成）
- 研究用ファクター計算・特徴量解析ユーティリティ
- 発注・約定の監査ログスキーマ初期化（監査テーブル、インデックス）

設計上の主な配慮点：
- ルックアヘッドバイアスを防ぐため、内部で date.today() 等による暗黙参照を避ける設計
- DuckDB を中心としたローカル永続化（高速で軽量）
- API 呼び出しはリトライ・レート制御を備え、失敗時はフェイルセーフで継続する箇所もあり安全性を考慮
- 冪等性（ON CONFLICT / UUID / 記事IDハッシュ等）を意識したデータ保存

---

## 主な機能一覧（Features）

- ETL パイプライン
  - run_daily_etl/run_prices_etl/run_financials_etl/run_calendar_etl（kabusys.data.pipeline）
  - J‑Quants クライアント（kabusys.data.jquants_client）: 取得・保存・認証・ページネーション・レート制御
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク（急変）、重複、日付不整合 を検出
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、SSRF 対策、記事正規化、raw_news への保存フロー設計
- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメントスコアリング（ai_scores へ保存）
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の MA200 乖離とマクロニュース LLM スコアを合成して daily market_regime を算出
- 研究用ユーティリティ（kabusys.research）
  - calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank 等
- 統計ユーティリティ（kabusys.data.stats）
  - zscore_normalize 等
- 監査ログスキーマ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブルの初期化・インデックス、監査 DB 初期化ユーティリティ
- 環境変数管理（kabusys.config）
  - .env / .env.local 自動読み込み（プロジェクトルート検出）、必須 env チェック、便利プロパティ

---

## 前提（Requirements）

- Python 3.10 以上
- 必要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J‑Quants API、OpenAI、RSS ソース など）
- J‑Quants / OpenAI 等の API キー

（実際の依存管理はプロジェクトの requirements.txt / pyproject.toml に従ってください）

---

## セットアップ手順（Setup）

1. Python 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージのインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （プロジェクトが配布パッケージであれば）pip install -e .

3. 環境変数を用意
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動読み込みされます（kabusys.config が .git または pyproject.toml を基準にプロジェクトルートを探索）。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - KABU_API_PASSWORD=your_kabu_api_password
   - SLACK_BOT_TOKEN=your_slack_bot_token
   - SLACK_CHANNEL_ID=your_slack_channel_id
   - OPENAI_API_KEY=sk-...
   - （任意）DUCKDB_PATH=data/kabusys.duckdb
   - （任意）SQLITE_PATH=data/monitoring.db
   - （任意）KABUSYS_ENV=development|paper_trading|live
   - LOG_LEVEL=INFO

   .env のサンプル（.env.example として）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（Usage）

以下は代表的な利用例です。実行は適切に環境変数を設定した上で行ってください。

- DuckDB 接続の作成（ファイル DB）
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL 実行（J‑Quants から差分取得・保存・品質チェック）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（OpenAI を使って銘柄別 ai_scores を作成）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY は環境変数か api_key 引数で指定
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {n_written} codes")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査 DB 初期化（発注監査スキーマを作る）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

- RSS 取得（ニュース収集）
  ```python
  from kabusys.data.news_collector import fetch_rss

  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

- ファクター計算（研究用）
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  target = date(2026, 3, 20)
  mom = calc_momentum(conn, target)
  val = calc_value(conn, target)
  vol = calc_volatility(conn, target)
  ```

- 環境設定取得
  ```python
  from kabusys.config import settings

  print(settings.jquants_refresh_token)  # 必須
  print(settings.duckdb_path)            # デフォルト: data/kabusys.duckdb
  print(settings.is_live)
  ```

注意点：
- OpenAI 呼び出しを行う関数（news_nlp, regime_detector）は API キーを引数で渡すか、環境変数 OPENAI_API_KEY を使用します。
- ETL は外部 API（J‑Quants）へ多数のリクエストを行います。ID トークン／レート制御に注意してください。
- DuckDB の一部操作（executemany 等）に関する互換性に留意しています（空リストの処理など）。

---

## ディレクトリ構成（Directory structure）

主要なファイル・モジュールは以下のとおりです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                      — ニュース NLP（OpenAI）
    - regime_detector.py               — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py                — J‑Quants API クライアント（取得 + 保存）
    - pipeline.py                      — ETL パイプライン（run_daily_etl 等）
    - etl.py                           — ETL 結果型の再エクスポート
    - quality.py                       — データ品質チェック
    - news_collector.py                — RSS ニュース収集
    - calendar_management.py           — 市場カレンダー管理
    - stats.py                         — 統計ユーティリティ（zscore_normalize 等）
    - audit.py                         — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py               — モメンタム・バリュー・ボラティリティ計算
    - feature_exploration.py           — 将来リターン・IC・統計サマリ
  - ai/ (上記)
  - research/ (上記)
  - その他（strategy / execution / monitoring を想定するエントリが __all__ に含まれています）

各モジュールは docstring に設計意図と想定される DB テーブル（例: prices_daily, raw_news, ai_scores, market_regime 等）を明記しています。実行前に必要なテーブル（DDL）を準備してください（audit.init_audit_schema のようにスキーマ初期化ユーティリティが提供されています）。

---

## 運用上の注意（Notes）

- 環境依存の設定は `.env`/.env.local または OS 環境変数で管理してください。kabusys.config はプロジェクトルート（.git または pyproject.toml を基準）を探索して自動的に .env をロードします。
- OpenAI / J‑Quants 等の外部 API は課金・レート制限があるため、テスト時はモック化を推奨します。コード内にはテスト用に差し替え可能な内部呼び出し箇所（_call_openai_api 等）が設計されています。
- DuckDB は単一ファイル DB です。バックアップ／永続化ポリシーを運用ルールに合わせて決めてください。
- 本リポジトリのコードは「システム設計」の一部を実装したものであり、実際の売買執行（資金送金・本番発注）を行う場合は更に堅牢な検証・テストが必要です。

---

もし README に追加したいサンプルスクリプト（バッチ起動例や systemd / cron 用の実行例）や、要求される依存ファイル（requirements.txt、pyproject.toml、.env.example）を用意する場合はその内容を教えてください。必要に応じて README を拡張します。