# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集・NLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（約定トレーサビリティ）などを組織化したモジュールセットです。

---

## 主な特徴（機能一覧）
- データ取得・ETL
  - J-Quants API から株価（OHLCV）、財務データ、マーケットカレンダーの差分取得／保存（DuckDB向け、冪等保存）
  - 日次 ETL パイプライン（calendar → prices → financials → 品質チェック）
- データ品質チェック
  - 欠損、重複、スパイク（前日比）、日付不整合の検出と QualityIssue レポート
- ニュース収集
  - RSS 取得、前処理、SSRF/プライベートホスト対策、raw_news への冪等登録
- ニュースNLP（OpenAI）
  - 銘柄別ニュース統合によるセンチメントスコア算出（JSON Mode、バッチ/リトライ実装）
- 市場レジーム判定
  - ETF(1321) の 200日MA乖離とマクロニュースの LLM センチメントを合成し日次で 'bull'/'neutral'/'bear' を判定・保存
- 研究（Research）
  - モメンタム、ボラティリティ、バリュー等のファクター計算、将来リターン、IC・統計サマリー
- 監査ログ（Audit）
  - signal → order_request → executions の監査テーブル DDL と初期化ユーティリティ（DuckDB）
- 環境設定
  - .env / .env.local の自動読み込み（プロジェクトルート検出）、Settings 経由で安全に環境変数を参照

---

## セットアップ手順

前提:
- Python 3.9+（本リポジトリの型ヒント・標準ライブラリ使用を考慮）
- DuckDB、OpenAI クライアント、defusedxml などが必要

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化（任意だが推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. インストール（開発モード推奨）
   - setup.py / pyproject.toml がある場合:
     ```bash
     pip install -e .
     ```
   - 必要な外部ライブラリを個別にインストール:
     ```bash
     pip install duckdb openai defusedxml
     ```

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env` および（必要なら）`.env.local` を配置すると自動で読み込まれます。
   - 自動読み込みを無効化する場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須、発注系で使用）
     - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
     - DUCKDB_PATH: デフォルト DB パス（例: data/kabusys.duckdb）
     - PAPER_FILL_MODE: paper trading のシミュレーション挙動（instant/partial/never/reject）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用（任意）

   - README 用の簡易 `.env` 例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
     OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
     KABU_API_PASSWORD=your_kabu_password
     DUCKDB_PATH=data/kabusys.duckdb
     ```

---

## 使い方（簡単なサンプル）

以下は代表的な関数の使い方例です。各モジュールは DuckDB の接続を受け取る設計です。

- 日次 ETL 実行（run_daily_etl）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（score_news）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY が使われる
  print(f"scored {n_written} codes")
  ```

- 市場レジーム判定（score_regime）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログスキーマの初期化（init_audit_db / init_audit_schema）
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/monitoring_audit.duckdb")
  # これで監査用テーブルが作成されます
  ```

- 研究用ファクター計算（例: calc_momentum）
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  print(len(records), "records")
  ```

---

## 環境変数 / 設定（主なもの）
Settings クラスは `kabusys.config.settings` から参照します。主なプロパティ：

- jquants_refresh_token -> JQUANTS_REFRESH_TOKEN（必須）
- kabu_api_password -> KABU_API_PASSWORD（発注系で使用）
- kabu_api_base_url -> KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- line_channel_access_token, line_user_id -> LINE 関連（任意）
- duckdb_path -> DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- sqlite_path -> SQLITE_PATH（監視用 DB デフォルト: data/monitoring.db）
- paper_fill_mode -> PAPER_FILL_MODE（instant|partial|never|reject）
- paper_sqlite_path -> PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- pid_file_path / kill_flag_path 他、監視設定
- KABUSYS_ENV -> KABUSYS_ENV 値 (development|paper_trading|live)
- LOG_LEVEL -> LOG_LEVEL (DEBUG/INFO/...)

自動 .env 読み込みの挙動:
- プロジェクトルート（.git または pyproject.toml）を基準に `.env` → `.env.local` を読み込みます。
- OS 環境変数が優先され、`.env.local` は `.env` を上書きします（ただし OS 環境変数は保護）。
- 無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成（主要ファイル）
（src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py                — 環境設定・自動 .env ロード
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント（OpenAI）
    - regime_detector.py     — 市場レジーム判定（ma200 + macro sentiment）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存・認証・レート制御）
    - pipeline.py            — ETL パイプライン & run_daily_etl
    - etl.py                 — ETL の公開インターフェース（ETLResult 再エクスポート）
    - news_collector.py      — RSS 取得・前処理・保存（SSRF対策）
    - calendar_management.py — 市場カレンダー（営業日判定等）
    - quality.py             — データ品質チェック
    - stats.py               — zscore_normalize 等の統計ユーティリティ
    - audit.py               — 監査ログ DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py     — モメンタム・ボラティリティ・バリュー
    - feature_exploration.py — 将来リターン・IC・統計サマリー

---

## 運用上の注意点 / 設計上のポイント
- Look-ahead バイアス防止設計
  - AI モジュールや ETL、研究モジュールは内部で現在時刻を直接参照しないよう配慮されています。関数は target_date を明示的に受け取ります。
- 冪等性
  - J-Quants からの保存は ON CONFLICT / DO UPDATE 等で冪等に行います。
  - ニュースは URL 正規化＋SHA-256 ハッシュで冪等キーを生成します。
- フォールバック
  - market_calendar が未取得時は曜日ベースで営業日判定を行うなど、DB が未整備でも動くように設計されています。
- OpenAI 呼び出し
  - JSON Mode を利用した厳格なレスポンス検証とリトライ・バックオフ実装が含まれます。
- セキュリティ / ネットワーク
  - RSS 収集は SSRF 対策（リダイレクト検査、プライベートホスト拒否）を実装しています。

---

## よくある操作（考慮すべき点）
- テスト時に .env 自動ロードを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。
- OpenAI 呼び出しをテストでモックしたい場合、モジュール内の _call_openai_api 等を patch してください（コード内コメント参照）。
- DuckDB executemany に空リストを渡すと失敗するバージョンがあるため、空時のガード処理があります（pipeline/news_nlp 等）。

---

この README はコードベースの主要機能と基本的な使い方をまとめたものです。各モジュールの詳細な API やスキーマについてはソースコード中の docstring を参照してください。必要であればサンプルスクリプトやユースケース別の運用手順（ETL スケジュール、監視、発注フロー）も追記します。