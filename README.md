# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。J-Quants / kabuステーション 等からデータを取得・保存し、ニュース NLP / 市場レジーム判定、ファクター計算、ETL、データ品質チェック、監査ログ（トレーサビリティ）等のユーティリティを提供します。

---

## プロジェクト概要

KabuSys は日本株の研究・自動売買向けに設計された内部ライブラリ群です。主な目的は：

- J-Quants API からの株価・財務・カレンダー等の差分 ETL
- RSS ニュース収集と LLM を用いた銘柄センチメント評価（OpenAI）
- 市場レジーム判定（ETF + マクロニュースの組合せ）
- ファクター（モメンタム・バリュー・ボラティリティ等）計算・探索
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用 DuckDB スキーマ

設計方針として「ルックアヘッドバイアス回避」「冪等保存」「フォールトトレランス（APIエラー時のフェイルセーフ）」が貫かれています。

---

## 主な機能一覧

- data
  - J-Quants クライアント (fetch / save): prices, financials, market calendar, listed info
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - ニュース収集（RSS → raw_news、news_symbols との紐付け）
  - データ品質チェック（missing, spike, duplicates, date consistency）
  - マーケットカレンダー管理（is_trading_day / next_trading_day 等）
  - 監査ログ（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（Zスコア正規化）
- ai
  - ニュース NLP スコアリング（score_news: 銘柄ごとの ai_score を ai_scores に保存）
  - 市場レジーム判定（score_regime: ETF 1321 の MA とマクロセンチメントを合成）
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量解析（forward returns, IC, summary, rank）
- 設定管理（kabusys.config.Settings）
  - .env 自動読み込み・環境変数管理（.env / .env.local 優先度、テスト用に無効化可）

---

## 前提・必須ソフトウェア

- Python 3.10+（型注釈や新しい構文を使用）
- 推奨パッケージ（実行に必要な主要なライブラリ）
  - duckdb
  - openai (OpenAI の最新 SDK)
  - defusedxml
- ネットワーク接続（J-Quants API / OpenAI / RSS フィード へのアクセス）

（実際の requirements.txt はリポジトリに合わせて用意してください）

---

## 環境変数

主要な環境変数（デフォルトや用途）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: デフォルト DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- OPENAI_API_KEY: OpenAI API キー（ai.score_news / score_regime を使う場合）
- KABUSYS_ENV: 環境（development / paper_trading / live）（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）（デフォルト: INFO）

自動 .env ロード:
- パッケージインポート時にプロジェクトルート（.git または pyproject.toml の所在）を探索し、.env → .env.local の順で自動読み込みします（OS 環境変数優先）。
- 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

.env のパーサは `export KEY=val`、クォート、インラインコメント等に対応しています。

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール（例）
   ```
   pip install duckdb openai defusedxml
   # または開発用 requirements があればそれを使用
   ```

4. パッケージを開発モードでインストール
   ```
   pip install -e .
   ```

5. .env を作成（.env.example を参考に）
   - 必須トークン: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
   - OpenAI を使う場合は OPENAI_API_KEY を設定

6. DuckDB のデータディレクトリ作成（必要なら）
   ```
   mkdir -p data
   ```

---

## 使い方（主要なユースケース）

以下は最小限のコードスニペット例です。実運用前に安全性・テストを十分行ってください。

- DuckDB 接続を作る
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 監査ログ DB を初期化（専用 DB）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # あるいは既存 conn にスキーマだけ追加する:
  # from kabusys.data.audit import init_audit_schema
  # init_audit_schema(conn)
  ```

- 日次 ETL の実行（J-Quants から差分取得して保存）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # id_token を明示的に渡すことも可能（get_id_token で取得済みであれば不要）
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース NLP（OpenAI）でスコア付けして ai_scores テーブルへ保存
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-xxxx")
  print(f"written {written} codes")
  ```

- 市場レジーム判定（ETF 1321 の MA + マクロニュース）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-xxxx")
  ```

- ファクター計算例
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  momentum = calc_momentum(conn, date(2026, 3, 20))
  value = calc_value(conn, date(2026, 3, 20))
  volatility = calc_volatility(conn, date(2026, 3, 20))
  ```

- データ品質チェック
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026, 3, 20))
  for iss in issues:
      print(iss)
  ```

注意:
- OpenAI 呼び出しや J-Quants 呼び出しは外部 API を使います。API キー・レート制限・コストに注意してください。
- ETL / DB 書き込みは冪等性を意識して設計されていますが、本番運用前にローカルで動作確認してください。

---

## ディレクトリ構成（主要ファイル・モジュールの簡易説明）

（リポジトリの src/kabusys を想定）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数・.env 自動読み込み、Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py        — RSS ニュースの LLM による銘柄別スコアリング（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（fetch / save / auth / rate limiter）
    - pipeline.py        — ETL パイプライン（run_daily_etl 等）と ETLResult
    - etl.py             — ETLResult 再エクスポート
    - calendar_management.py — 市場カレンダー管理 / 営業日判定
    - news_collector.py  — RSS フィード取得と raw_news 保存ロジック
    - quality.py         — データ品質チェック
    - stats.py           — 統計ユーティリティ（zscore_normalize）
    - audit.py           — 監査ログスキーマ定義・初期化（signal / order_request / executions）
  - research/
    - __init__.py
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — forward returns / IC / summary / rank
  - research/ ほかモジュール群...

各モジュールは docstring と設計方針を含んでおり、関数の振る舞い（ルックアヘッド防止、リトライ、冪等性、フェイルセーフ）や引数・戻り値が明記されています。

---

## 運用上の注意点

- 本ライブラリは実際の売買や金銭的結果に繋がるコードの基礎を提供します。実運用前に必ず総合テスト・リスク管理（発注の冪等性、二重発注防止、ポジション管理）を実装してください。
- OpenAI / J-Quants 等の外部 API を利用するため、キー管理とコスト・レート制限に注意してください。J-Quants は 120 req/min の想定で RateLimiter を実装しています。
- DuckDB のバージョンや SQL 機能（executemany の空リスト挙動等）に依存する箇所があるため、実行環境の互換性を確認してください。
- .env 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト向け）。

---

## サポート / 貢献

- バグ報告や機能要望は Issue にて提出してください。
- コード貢献は PR を歓迎します。既存の設計方針（ルックアヘッド回避・冪等性等）に沿うよう留意してください。

---

README 内の例は最小限の利用イメージです。詳しい API の戻り値仕様やテーブルスキーマは各モジュールの docstring を参照してください。