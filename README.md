# KabuSys

日本株のデータ基盤・リサーチ・自動売買を想定したライブラリ群です。  
DuckDB をデータレイクとして用い、J-Quants / RSS / OpenAI（LLM）等と連携してデータ取得・品質管理・AIスコアリング・監査ログを提供します。

## プロジェクト概要
- ETL（J-Quants）で株価・財務・マーケットカレンダーを取得して DuckDB に保存
- ニュース収集（RSS）→ 銘柄紐付け → OpenAI による銘柄別センチメント算出（ai.news_nlp）
- マクロ＋テクニカル指標を組み合わせた市場レジーム判定（ai.regime_detector）
- 研究用ファクター計算、将来リターン・IC・統計サマリー（research）
- データ品質チェック（data.quality）
- 発注・約定のトレーサビリティを担う監査ログスキーマ（data.audit）
- 環境設定の一元管理（config）

## 主な機能一覧
- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（fetch / save / id_token 管理、レートリミット・リトライ対応）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / calendar_update_job）
  - ニュース収集（RSS の正規化・SSRF 対策・前処理・raw_news 保存）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLU による銘柄別センチメント（score_news）
  - マクロ + ETF MA200 乖離による市場レジーム判定（score_regime）
- research
  - ファクター計算（momentum / value / volatility など）
  - 特徴量探索（forward returns, IC, factor summary, rank）
- config
  - .env / 環境変数自動ロード、各種設定値のプロパティ（settings）

## 必要条件・依存関係
- Python 3.10+
- 必要パッケージ（主要なもの）
  - duckdb
  - openai
  - defusedxml
- その他 urllib / json / logging 等は標準ライブラリで利用

（pyproject.toml / requirements.txt がある場合はそれに従ってください）

## セットアップ手順（開発環境）
1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```
2. 仮想環境を作成・有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```
3. パッケージをインストール
   - editable install（src 配下パッケージを使う場合）
     ```
     pip install -e .
     ```
   - または必要パッケージのみ
     ```
     pip install duckdb openai defusedxml
     ```

4. 環境変数 / .env を用意する  
   パッケージはプロジェクトルート（.git または pyproject.toml がある場所）にある `.env` / `.env.local` を自動で読み込みます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   例（.env の最小例）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   主な環境変数一覧（よく使うもの）
   - JQUANTS_REFRESH_TOKEN (必須)：J-Quants 用リフレッシュトークン
   - OPENAI_API_KEY (AI 機能を使う場合必須)
   - KABU_API_PASSWORD, KABU_API_BASE_URL（kabuステーション連携）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（監視用 sqlite のパス）
   - PAPER_FILL_MODE（paper_trading 用挙動）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（通知用）
   - KABUSYS_ENV（development / paper_trading / live）
   - LOG_LEVEL（DEBUG/INFO/...）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD（自動 .env ロード無効化）

## 使い方（代表的な例）
- DuckDB 接続を作って ETL を実行する（日次 ETL）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを算出して ai_scores に書き込む
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env OPENAI_API_KEY を使う
  print(f"scored {count} codes")
  ```

- 市場レジームを算出して market_regime テーブルへ書込む
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB を初期化する
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/monitoring_audit.duckdb")
  ```

- research 用ファクター計算
  ```python
  from kabusys.research import calc_momentum, calc_value, calc_volatility
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  ```

注意点:
- LLM / 外部 API 呼び出し部分は API キー必須。キーは引数で渡すか環境変数 OPENAI_API_KEY を利用。
- 各処理はルックアヘッドバイアスに配慮して実装されており、関数は target_date を明示的に受け取ります（内部で date.today() を参照しないことが設計方針）。
- J-Quants API にはレートリミットとリトライロジックが実装されていますが、実際の使用時には利用規約・レートに注意してください。

## ディレクトリ構成（主なファイル）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env 自動ロードと settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に保存
    - regime_detector.py — ETF MA200 とマクロ記事センチメントから市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py — ETL パイプライン / run_daily_etl 等
    - calendar_management.py — 市場カレンダー関連ユーティリティ
    - news_collector.py — RSS 収集・正規化・保存（SSRF 対策等）
    - quality.py — データ品質チェック群
    - audit.py — 監査ログスキーマ初期化 / init_audit_db
    - stats.py — zscore_normalize 等の統計ユーティル
    - etl.py — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py — momentum / value / volatility 等のファクター計算
    - feature_exploration.py — forward returns / IC / summary / rank
  - ai, data, research のテスト補助や内部ユーティリティが含まれます

## ロギング・監視関連
- 環境変数 LOG_LEVEL によりログレベルを制御できます（デフォルト INFO）。
- 実行監視用に PID ファイルや kill フラグのパスを設定できる（settings.pid_file_path / settings.kill_flag_path）。

## 開発・テストに関するメモ
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）から行います。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って無効化可能。
- OpenAI 呼び出し部分は内部で再試行・フォールバックを行う設計ですが、ユニットテストでは該当関数をモックして外部通信を避けるべきです（モジュール内の _call_openai_api を patch 可能）。
- DuckDB のバージョン差異（executemany の挙動等）に配慮してコードが実装されています。

## ライセンス・貢献
- 本リポジトリのライセンス情報や貢献ガイドはプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（無ければ管理者へ問い合わせてください）。

---

この README はコードベースの主要機能と使い方の概要をまとめたものです。詳細な API/引数やスキーマ定義は各モジュールの docstring を参照してください。必要なら README にコード例や運用手順（cron、systemd、Docker 構成など）を追加しますので、用途を教えてください。