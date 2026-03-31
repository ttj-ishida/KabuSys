# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP スコアリング（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（発注 → 約定のトレーサビリティ）などの機能を内包しています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムおよびデータ基盤向けの共通ライブラリです。主な目的は以下です。

- J-Quants API からの差分 ETL（株価日足、財務、JPX カレンダー）
- ニュース収集（RSS）と LLM を用いた銘柄レベルのニュースセンチメント算出
- ETF（1321）やニュースを用いた市場レジーム判定（bull / neutral / bear）
- リサーチ用ファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量解析ユーティリティ
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログテーブル（シグナル・発注・約定のトレーサビリティ）初期化ユーティリティ

設計方針として、ルックアヘッドバイアス回避（内部で date.today() を盲目的に参照しない等）、冪等性、フォールバックロジック、外部 API の堅牢なリトライ処理を重視しています。

---

## 機能一覧（概略）

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch_*, save_*）
  - market_calendar 管理（is_trading_day / next_trading_day / get_trading_days）
  - ニュース収集（RSS）と保存
  - データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency）
  - 監査ログのスキーマ初期化・専用 DB 初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（score_news）: 銘柄ごとのセンチメントを ai_scores テーブルへ書き込む
  - レジーム判定（score_regime）: ETF MA とマクロニュースセンチメントを合成して market_regime に書き込む
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - 環境変数読み込み・設定管理（Settings オブジェクト）

---

## セットアップ手順

前提
- Python 3.10 以上（typing の新構文や Literal を使用しているため）
- ネットワークアクセス（J-Quants / OpenAI / 各 RSS）

1. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 必要パッケージをインストール
   基本的に以下のライブラリが必要です（プロジェクトに requirements.txt があればそちらを使用してください）。
   ```
   pip install duckdb openai defusedxml
   ```
   - duckdb: 組み込みデータベース（ETL / 解析に使用）
   - openai: LLM 呼び出し（gpt-4o-mini 等）
   - defusedxml: 安全な XML パース（RSS 収集）

   開発時は linters / test フレームワークを追加してください。

3. パッケージをインストール（ローカル開発向け）
   プロジェクトルートに pyproject.toml / setup.cfg 等があれば editable install：
   ```
   pip install -e .
   ```

4. 環境変数の設定
   プロジェクトは .env / .env.local を自動で読み込みます（os 環境変数を優先）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須環境変数（少なくとも ETL / AI を実行する際に必要）:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
   - SLACK_BOT_TOKEN: Slack 通知が必要な場合
   - SLACK_CHANNEL_ID: Slack チャンネル ID
   - KABU_API_PASSWORD: kabuステーション API を使う場合（注文実行など）
   - OPENAI_API_KEY: OpenAI API キー（score_news／score_regime にも使用可）

   任意 / デフォルト:
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（監視用）等（デフォルト: data/monitoring.db）

   サンプル .env:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（主要な使用例）

以下は Python REPL / スクリプトでの基本的な利用例です。

- Settings の利用（環境変数読み込み）
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)  # Path オブジェクト
  ```

- DuckDB 接続を作って日次 ETL を実行
  ```python
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn)  # target_date を明示することも可能
  print(result.to_dict())
  ```

- ニュース NLP でスコアを算出（ai_scores に書き込む）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # 明示的に API キーを渡すことも可能（None なら環境変数 OPENAI_API_KEY を参照）
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（専用 DB にする場合）
  ```python
  from kabusys.data.audit import init_audit_db
  from kabusys.config import settings

  audit_conn = init_audit_db(settings.duckdb_path)  # ":memory:" も可
  ```

- 研究用ファクター計算例
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  res = calc_momentum(conn, target_date=date(2026, 3, 20))
  # res は [{'date':..., 'code':..., 'mom_1m':..., ...}, ...]
  ```

注意点:
- OpenAI を呼ぶ関数（score_news, score_regime）は api_key 引数を受け取り、None の場合は環境変数 OPENAI_API_KEY を参照します。
- 各 ETL / 保存関数は冪等（ON CONFLICT DO UPDATE / DO NOTHING）を基本としています。
- ルックアヘッドバイアス防止のため、target_date を明示的に与えることを推奨します（テストやバックテストで特に重要）。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要なファイル・モジュール構成の概観です（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数 / Settings
  - ai/
    - __init__.py
    - news_nlp.py                   -- ニュース NLP スコアリング（score_news）
    - regime_detector.py            -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             -- J-Quants API クライアント（fetch / save）
    - pipeline.py                   -- ETL パイプライン（run_daily_etl 等）
    - etl.py                        -- ETLResult の再エクスポート
    - calendar_management.py        -- market_calendar の管理、営業日判定等
    - news_collector.py             -- RSS 収集・正規化・保存
    - quality.py                    -- データ品質チェック
    - stats.py                      -- 汎用統計（zscore_normalize）
    - audit.py                      -- 監査ログテーブル定義／初期化
  - research/
    - __init__.py
    - factor_research.py            -- モメンタム / ボラティリティ / バリュー
    - feature_exploration.py        -- 前方リターン / IC / 統計サマリー
  - ai, data, research 配下にテストに差し替え可能な内部関数や注釈あり

リポジトリルートには pyproject.toml や .env.example を置く想定です（config.py 内でプロジェクトルート検出に .git / pyproject.toml を使用）。

---

## 注意事項・運用メモ

- 環境変数の自動ロード
  - .env / .env.local を自動読み込み（ただし OS 環境変数を保護）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI / J-Quants の API 呼び出しはリトライやバックオフ戦略を備えていますが、課金やレート制限に注意してください。
- DuckDB の executemany などのバージョン差分に依存する処理があるため、DuckDB のバージョン互換性に注意してください（README に含める `requirements` にバージョンを固定することを検討してください）。
- 本ライブラリは研究・ツール群を含むため、本番で自動売買を行う場合は十分なテスト・リスク管理を行ってください（kabu API 呼び出しや実際の発注は別モジュールで統制される想定です）。

---

## 貢献・開発

バグ報告や機能提案は Issue を通じてお願いします。ローカルでの開発には仮想環境と上記依存関係のインストールの後、editable install を行ってください。

---

必要であれば README に以下を追加できます：
- 詳細な .env.example
- CI / テスト実行手順
- よくあるトラブルシュート（OpenAI レスポンスパースエラー、J-Quants 認証失敗など）
- API 使用上限やレート制御の詳しい説明

追加希望があれば教えてください。