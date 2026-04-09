# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース/NLP による銘柄スコアリング、マーケットレジーム判定、監査ログ（注文→約定のトレース）、リサーチ用ファクター計算などを含みます。

---

## 主な機能

- データ取得（J-Quants API）
  - 日次株価（OHLCV）、財務データ、上場銘柄情報、JPXマーケットカレンダー
  - レートリミット管理、リトライ、トークン自動リフレッシュ
- ETL パイプライン
  - 差分取得、バックフィル、品質チェックの統合実行（run_daily_etl）
  - 品質チェック（欠損/重複/スパイク/日付不整合）
- ニュース収集・NLP
  - RSS 取得、安全対策（SSRF/リダイレクト検証、XML 防御、受信サイズ制限）
  - OpenAI（gpt-4o-mini）を利用したニュースセンチメント集約（ai/news_nlp.score_news）
- 市場レジーム判定
  - ETF（1321）200日MA乖離とマクロニュースのLLMセンチメントを合成（ai/regime_detector.score_regime）
- リサーチ（ファクター計算）
  - Momentum / Volatility / Value 等の定量ファクター計算、Forward returns、IC、統計サマリー
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブル、冪等性・トレーサビリティの確保
- ユーティリティ
  - カレンダー管理（営業日判定、next/prev/get_trading_days 等）
  - データ保存ユーティリティ（duckdb への保存関数）
  - 共通統計関数（zscore 正規化）

---

## 要件

- Python 3.10+
- 主要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI 等）

（実プロジェクトでは requirements.txt を用意し pip でインストールしてください）

---

## セットアップ手順

1. Python 仮想環境の作成と有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（例）
   - pip install duckdb openai defusedxml

   ※ 実際はプロジェクトの requirements.txt / pyproject.toml に従ってください。

3. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=（必須: J-Quants リフレッシュトークン）
     - KABU_API_PASSWORD=（必須: kabuステーション API パスワード）
     - OPENAI_API_KEY=（LLM 呼び出し用; score_news / score_regime 等で利用）
     - LINE_CHANNEL_ACCESS_TOKEN=（任意: 通知用）
     - LINE_USER_ID=（任意）
     - DUCKDB_PATH=data/kabusys.duckdb (既定)
     - SQLITE_PATH=data/monitoring.db (既定)
     - PAPER_FILL_MODE=instant|partial|never|reject (Paper Trading の動作)
     - KABUSYS_ENV=development|paper_trading|live (既定: development)
     - LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL (既定: INFO)

   - 例 .env（最小）
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - OPENAI_API_KEY=your_openai_api_key
     - KABU_API_PASSWORD=your_kabu_api_password
     - KABUSYS_ENV=development
     - LOG_LEVEL=INFO

4. ディレクトリ（data 等）を作成
   - mkdir -p data

---

## 使い方（主要な API 例）

以下はライブラリを直接インポートして使う例です。実行は仮想環境と環境変数が設定されている前提です。

- ETL（デイリー ETL を実行）
  - Python 例:
    - from datetime import date
      import duckdb
      from kabusys.config import settings
      from kabusys.data.pipeline import run_daily_etl
      conn = duckdb.connect(str(settings.duckdb_path))
      result = run_daily_etl(conn, target_date=date(2026, 3, 20))
      print(result.to_dict())

- ニューススコアリング（OpenAI を使用）
  - from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    n = score_news(conn, target_date=date(2026, 3, 20))
    print(f"scored {n} codes")

  - 注意: OPENAI_API_KEY が必要。API 失敗時はフェイルセーフで継続します（多くはスキップ・0 return）。

- 市場レジーム判定
  - from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,3,20))

- 監査ログ DB 初期化
  - from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")

- ファクター計算 / リサーチ
  - from datetime import date
    import duckdb
    from kabusys.research import calc_momentum, calc_value, calc_volatility
    conn = duckdb.connect("data/kabusys.duckdb")
    momentum = calc_momentum(conn, date(2026,3,20))
    volatility = calc_volatility(conn, date(2026,3,20))
    value = calc_value(conn, date(2026,3,20))

- カレンダー操作（営業日判定など）
  - from datetime import date
    import duckdb
    from kabusys.data.calendar_management import is_trading_day, next_trading_day
    conn = duckdb.connect("data/kabusys.duckdb")
    d = date(2026,3,20)
    print(is_trading_day(conn, d))
    print(next_trading_day(conn, d))

備考:
- 多くの関数は DuckDB の接続（duckdb.DuckDBPyConnection）を受け取ります。settings.duckdb_path を利用して接続を作成してください。
- LLM 呼び出しや外部 API はネットワーク依存でエラーやレート制限が発生するため、各モジュールはリトライ・フェイルセーフを備えています。

---

## 設定の自動読み込みについて

- kabusys.config モジュールはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に `.env` と `.env.local` を自動読み込みします。
  - 読み込み優先度: OS 環境変数 > .env.local > .env
  - テスト等で自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 必須の環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は settings のプロパティ参照時にチェックされ、未設定なら ValueError が発生します。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py (ETLResult re-export)
    - stats.py
    - quality.py
    - news_collector.py
    - calendar_management.py
    - audit.py
    - (その他: pipeline / audit の補助モジュール)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research package は data.stats の zscore 正規化等を再利用

（上記は主要モジュールの抜粋です。実際のツリーは src/kabusys 以下にさらに細分化されたモジュールが存在します。）

---

## 追加の注意点 / 開発メモ

- Python の型アノテーションで `X | None` 等を使用しているため Python 3.10 以上を想定しています。
- DuckDB を用いる設計のため、大量データ処理はローカルの DuckDB ファイルを用いて実行してください（デフォルト: data/kabusys.duckdb）。
- OpenAI 呼び出しは JSON Mode（厳密な JSON を返すようプロンプト指定）を利用し、レスポンスのバリデーションや冗長なテキストの切り出し処理を行っています。API レスポンスの変化に注意してください。
- news_collector では SSRF・XML 注入・大容量レスポンスに対する対策が組み込まれています。

---

この README はコードベースにあるドキュメント文字列と設計ノートに基づいて作成しています。より詳細な設計ドキュメント（StrategyModel.md / DataPlatform.md 等）がある場合はそれらも参照してください。README の改善や追加したい実行例があれば内容を追記します。