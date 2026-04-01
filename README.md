# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォームのライブラリです。J-Quants API を用いたデータ ETL、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（監査テーブル初期化）などを含みます。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- データ取得 / ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、JPX カレンダーを差分取得・保存
  - 差分取得・バックフィル対応、ページネーション、リトライ・レート制御
  - 品質チェック（欠損、スパイク、重複、日付整合性）

- ニュース収集 / NLP
  - RSS フィード収集（SSRF 対策、トラッキングパラメータ除去、前処理）
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（銘柄単位の ai_score）
  - 市場マクロニュースを用いた市場レジーム判定（ETF 1321 の MA200 と LLM を合成）

- リサーチ / ファクター計算
  - モメンタム、ボラティリティ、バリュー等の定量ファクター計算
  - 将来リターン計算、IC（スピアマンランク相関）、統計サマリー、Zスコア正規化ユーティリティ

- 監査 / トレーサビリティ
  - シグナル → 発注 → 約定の監査テーブル定義と初期化ユーティリティ（DuckDB 用）
  - 冪等性・時刻(UTC)ポリシーを保持

- 設定管理
  - .env / 環境変数の自動ロード（プロジェクトルート検出）と Settings API

---

## 要件

- Python 3.10 以上（型ヒントに | 記法を使用）
- 推奨 Python パッケージ（一例）
  - duckdb
  - openai
  - defusedxml
  - その他標準ライブラリを使用

（実際の requirements.txt / pyproject.toml に従ってインストールしてください）

---

## セットアップ手順

1. リポジトリをクローン / コピー
   - 例: git clone ...

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存関係のインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトに pyproject.toml / requirements.txt がある場合はそれに従ってください）
   - pip install -e . なども想定

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（モジュール起動時）。
   - 自動ロードを無効化する場合:
     - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

5. DuckDB の準備
   - デフォルトでは data/kabusys.duckdb（settings.duckdb_path）を使用します。必要に応じて `DUCKDB_PATH` を .env に設定してください。

---

## 必要な環境変数（主なもの）

以下は代表的な必須 / 主要な環境変数です。実運用では .env.example を参照して設定してください。

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack 送信先チャンネルID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: environment（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化（値が存在すれば無効化）

設定は kabusys.config.settings 経由でアクセスできます。

---

## 使い方（基本例）

以下はライブラリを Python から直接利用する簡単な例です。DuckDB 接続は duckdb.connect() を用います。

- 日次 ETL の実行（株価・財務・カレンダー取得 + 品質チェック）
  - 例:
    ```
    from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())
    ```

- ニュースの NLP スコアリング（ai_scores へ書き込み）
  - 例:
    ```
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-xxxxx")
    print("written:", n_written)
    ```

- 市場レジーム判定（market_regime へ書き込み）
  - 例:
    ```
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-xxxxx")
    ```

- 監査 DB の初期化（監査用 DuckDB を作成）
  - 例:
    ```
    import duckdb
    from kabusys.data.audit import init_audit_db

    conn = init_audit_db("data/audit.duckdb")
    # conn を使って以降の監査テーブル操作を行う
    ```

- ファクター計算・リサーチユーティリティ
  - calc_momentum / calc_volatility / calc_value などを呼んで (date, code) ベースの dict リストを取得できます。
    ```
    from datetime import date
    import duckdb
    from kabusys.research import calc_momentum

    conn = duckdb.connect("data/kabusys.duckdb")
    recs = calc_momentum(conn, date(2026, 3, 20))
    ```

- 設定へのアクセス
  - kabusys.config.settings 経由で設定を取得できます。
    ```
    from kabusys.config import settings
    print(settings.duckdb_path)
    print(settings.is_live)
    ```

注意点:
- 各メソッドは基本的に Look-ahead バイアスに配慮し、内部で date.today() を無差別に参照しない設計です。
- OpenAI の呼び出しを行う関数は api_key 引数で明示的にキーを渡せます。指定がなければ環境変数 OPENAI_API_KEY が使われます。
- ETL や保存処理は冪等化（ON CONFLICT DO UPDATE）されます。

---

## よく使う関数 / エントリポイント一覧

- kabusys.data.pipeline
  - run_daily_etl(...) : 日次 ETL 実行
  - run_prices_etl(...) / run_financials_etl(...) / run_calendar_etl(...)

- kabusys.data.jquants_client
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - save_daily_quotes(...)
  - save_financial_statements(...)

- kabusys.data.news_collector
  - fetch_rss(url, source) : RSS を取得して記事リストを返す

- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)

- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(path)

- kabusys.research
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/
      - __init__.py
      - pipeline.py
      - etl.py
      - jquants_client.py
      - news_collector.py
      - calendar_management.py
      - quality.py
      - stats.py
      - audit.py
      - etl.py
      - ...（その他モジュール）
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - monitoring/（実装がある場合）
    - strategy/（戦略層がある場合）
    - execution/（実行 / ブローカー連携用がある場合）
    - monitoring/（監視用モジュール）

このリポジトリはモジュール単位で機能が分離されており、ETL / データ品質 / リサーチ / AI スコアリング / 監査ログが各サブパッケージにまとまっています。

---

## 運用上の注意

- OpenAI や J-Quants のクレデンシャルは厳格に管理してください。`.env` をバージョン管理しないでください。
- 自動ロードされる .env はプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に検出されます。挙動を変えたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD` を使えます。
- DuckDB の executemany 周りや SQL の互換性についてコメントがソースにあるため、DuckDB バージョンに依存する挙動に注意してください（特に古い/新しいバージョンでの挙動差）。
- ニュース取得は外部 URL にアクセスするため SSRF 保護やタイムアウト等の制御が必要です。本実装では複数の保護を実装済みです。

---

必要に応じて README にサンプル .env.example、より詳細な運用手順、テスト方法（ユニットテストのモックの利用方法）等を追加できます。追加して欲しい項目があれば教えてください。