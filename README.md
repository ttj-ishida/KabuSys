# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
データ収集（J-Quants）、品質チェック、特徴量生成、ニュースのLLM解析、監査ログ（発注〜約定追跡）などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的として設計された Python モジュール群です。

- J-Quants API からの株価・財務・カレンダー取得（レート制御・リトライ付き）
- DuckDB を用いた ETL パイプライン（差分取得・冪等保存・品質チェック）
- ニュース本文の収集・前処理・LLM による銘柄センチメント算出（gpt-4o-mini / JSON Mode）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースセンチメントを合成）
- リサーチ用ファクター計算（モメンタム、バリュー、ボラティリティ）と統計ユーティリティ
- 発注・約定の監査ログスキーマ（監査テーブルの初期化・専用 DB 作成）
- ニュース収集での SSRF 対策や RSS 正規化・トラッキング除去等の堅牢な実装

設計方針として、ルックアヘッドバイアス回避（date.today()/datetime.today() の直接参照を避ける等）、冪等性、フォールバックロジック、外部 API の堅牢なリトライを重視しています。

---

## 主な機能一覧

- data
  - jquants_client: J-Quants API からの取得と DuckDB への保存（raw_prices, raw_financials, market_calendar 等）
  - pipeline / etl: 日次 ETL フロー（差分取得、backfill、品質チェック）
  - news_collector: RSS フィード取得・前処理・raw_news 保存（SSRF 対策・トラッキング除去）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management: 営業日判定・next/prev_trading_day 等のユーティリティ
  - audit: 発注〜約定の監査スキーマ定義と初期化ユーティリティ
  - stats: z-score 正規化など統計ユーティリティ
- ai
  - news_nlp.score_news: ニュースを銘柄ごとに集約して LLM でセンチメントを算出し ai_scores に書き込む
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロニュース LLM を合成して market_regime に書き込む
- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## 要件

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml

（プロジェクトの実行時に必要な追加パッケージがある可能性があります。requirements.txt を作成している場合はそれに従ってください。）

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境の作成（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージのインストール（例）
   ```bash
   pip install duckdb openai defusedxml
   ```

   - 実運用や CI 用には requirements.txt / pyproject.toml に依存関係を明記してください。

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml を含むディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます（注意: 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
     - KABU_API_PASSWORD: kabu API のパスワード（発注関連）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_FILL_MODE: paper trading の埋め合わせ挙動（instant|partial|never|reject）
     - KABUSYS_ENV: development | paper_trading | live
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   KABU_API_PASSWORD=your_kabu_password
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡単な例）

以下はいくつかの主要機能の呼び出し例です。実際にはログ設定やエラーハンドリングを適切に行ってください。

- DuckDB 接続を作成して ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを算出して ai_scores に保存する
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"written {written} stocks")
  ```

- 市場レジーム判定を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査用 DuckDB を初期化する
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # conn は初期化済みの DuckDB 接続
  ```

- カレンダー・営業日ユーティリティ
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  conn = duckdb.connect("data/kabusys.duckdb")
  print(is_trading_day(conn, date(2026, 3, 20)))
  print(next_trading_day(conn, date(2026, 3, 20)))
  ```

注意点:
- score_news / score_regime は OpenAI API を使用します。API キーを渡すか環境変数 OPENAI_API_KEY を設定してください。
- ETL/API 呼び出しはネットワークや API レート制限の影響を受けます。ログを確認しながら運用してください。

---

## よく使う API (抜粋)

- kabusys.config.settings
  - 環境変数を参照する Settings インスタンス。例: settings.jquants_refresh_token
- kabusys.data.pipeline.run_daily_etl(conn, target_date, ...)
  - 日次 ETL のメインエントリポイント
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - ニュースから銘柄ごとスコアを生成して ai_scores に書き込む
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 市場レジームを算出して market_regime に書き込む
- kabusys.data.jquants_client.fetch_daily_quotes / save_daily_quotes
  - J-Quants API からのデータ取得と保存
- kabusys.data.audit.init_audit_db / init_audit_schema
  - 監査ログテーブルの初期化

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
      - jquants_client.py
      - pipeline.py
      - etl.py
      - news_collector.py
      - calendar_management.py
      - quality.py
      - stats.py
      - audit.py
      - etl.py (再エクスポート用)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/（その他ユーティリティ）
    - monitoring/（モニタリング系モジュール、パッケージに含まれる想定）
    - execution/（発注・ブローカーラッパー等、パッケージに含まれる想定）
    - strategy/（ストラテジ関連モジュール、パッケージに含まれる想定）
- pyproject.toml / setup.cfg / README.md（本ファイル）

---

## 運用上の注意

- 自動環境変数ロード:
  - config.py はプロジェクトルート（.git または pyproject.toml を探索）から .env / .env.local を自動ロードします。テストなどで自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Look-ahead バイアス:
  - ライブラリ内部ではバックテスト向けに「未来データを参照しない」実装方針が採られています。target_date を明示的に渡す API を使うことで、バックテスト時の正しい再現が可能です。
- リトライ / フェイルセーフ:
  - OpenAI / J-Quants 呼び出しはリトライとフォールバック（スコア 0.0 等）を行うため、API 側の一時的障害に対して堅牢ですが、完全な可用性は保証されません。ログを必ず監視してください。

---

## テスト / 開発

- ユニットテストでは外部 API 呼び出しをモックすることを想定して実装されています（例: news_nlp._call_openai_api をパッチする等）。
- DuckDB の ":memory:" を使えばインメモリ DB で高速にテストできます。

---

## ライセンス / 貢献

この README はコードベースからの要約ドキュメントです。実際のライセンス・貢献ルールはリポジトリルートの LICENSE / CONTRIBUTING を参照してください（存在しない場合は管理者に問い合わせてください）。

---

README に不足している具体的な使用例や追加のセットアップ手順（CI 用、運用用 systemd ユニット、コンテナ化等）が必要であれば、利用シナリオを教えてください。環境変数テンプレート（.env.example）や requirements.txt の例も作成できます。