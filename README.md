# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。J-Quants からのデータ ETL、ニュース収集と LLM によるセンチメント評価、ファクター計算、監査ログ（トレーサビリティ）などを提供します。

主な設計方針は「バックテスト時のルックアヘッドバイアス防止」「DuckDB によるローカル永続化」「外部 API の呼び出しはリトライ＆フェイルセーフ」「モジュール分離によるテスト容易性」です。

---

## 機能一覧

- ETL（data.pipeline）
  - J-Quants から株価（日足）・財務・市場カレンダーを差分取得し DuckDB に保存
  - 品質チェック（欠損・重複・スパイク・日付不整合）
  - 日次 ETL の統合エントリポイント `run_daily_etl`

- データ基盤ユーティリティ（data/*）
  - market_calendar の管理（営業日判定・next/prev trading day 等）
  - J-Quants API クライアント（認証リフレッシュ、レート制御、リトライ）
  - ニュース収集（RSS -> raw_news、SSRF 対策・前処理）
  - 監査ログ（signal / order_requests / executions）スキーマ初期化

- AI（ai/*）
  - ニュースの銘柄別センチメント評価 `score_news`（OpenAI Chat API 使用、JSON Mode）
  - マクロセンチメントと ETF MA を組み合わせた市場レジーム判定 `score_regime`（gpt-4o-mini 想定）

- リサーチ（research/*）
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン計算、IC（Information Coefficient）計測、統計サマリー
  - Z スコア正規化ユーティリティ（data.stats から）

- セキュリティ・堅牢性
  - RSS の SSRF 対策、defusedxml による XML パース、安全な URL 正規化
  - API 呼び出しのリトライ・バックオフ、認証トークンの自動リフレッシュ
  - ETL・DB 書き込みは冪等設計（ON CONFLICT / DELETE→INSERT 等）

---

## 前提 / 要件

- Python 3.10 以上（標準ライブラリの型記法・| 演算子を使用）
- 主な依存パッケージ（一例）
  - duckdb
  - openai
  - defusedxml

requirements.txt がある場合はそちらを参照してください。無ければ上記をインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン（あるいは適切な配置にする）

2. 仮想環境を作成・有効化（例）:
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. パッケージと依存をインストール（開発用 editable インストール想定）:
   ```
   pip install -e .
   pip install duckdb openai defusedxml
   ```

4. 環境変数を設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（自動読み込みは CWD に依存せずパッケージファイル位置からプロジェクトルートを探索します）。
   - 自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. データディレクトリ作成（必要に応じて）:
   ```
   mkdir -p data
   ```

---

## 必須 / 推奨 環境変数

Settings（kabusys.config.Settings）で使用される主な環境変数と説明：

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン。fetch_* 系 API の認証に使用。

- KABU_API_PASSWORD (必須)
  - kabuステーション API のパスワード（発注系モジュールで使用）。

- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
  - kabuステーション API のベース URL。

- OPENAI_API_KEY (必須 for AI 機能)
  - OpenAI API キー。`score_news` / `score_regime` 実行時に必要。関数引数で上書き可能。

- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (任意)
  - LINE 通知連携用（存在していれば通知に利用）。

- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
  - DuckDB ファイルのパス。":memory:" も可能。

- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
  - 監視用 SQLite のパス（監視モジュールが利用）。

- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
  - 実行監視・停止フラグ関連の設定。

- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
  - 監視のしきい値（%）。

- KABUSYS_ENV (任意, デフォルト: development)
  - 有効値: development / paper_trading / live
  - live の場合は実際の発注など本番挙動となる設定確認に注意。

- LOG_LEVEL (任意, デフォルト: INFO)
  - DEBUG / INFO / WARNING / ERROR / CRITICAL

.env.example を参考に .env を用意してください。

---

## 使い方（簡易例）

以下は Python REPL やスクリプトから利用する例です。詳細は各モジュールの docstring を参照してください。

- DuckDB 接続の作成（デフォルトパスを利用）:
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（市場カレンダー→株価→財務→品質チェック）:
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントをスコア（OpenAI API キーは環境変数 OPENAI_API_KEY から読み込まれる）:
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  count = score_news(conn, target_date=date(2026,3,20))
  print(f"scored {count} codes")
  ```

- 市場レジーム判定（ETF 1321 の MA + マクロセンチメント合成）:
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査用 DB 初期化（監査ログ専用 DB を別ファイルで作る）:
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- カレンダー・営業日判定ユーティリティ:
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  from datetime import date

  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

- RSS フェッチ（ニュース収集の一部）:
  ```python
  from kabusys.data.news_collector import fetch_rss

  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
  ```

注）AI を使う機能は OpenAI の API 使用料が発生します。`OPENAI_API_KEY` を環境変数に設定するか、関数の `api_key` 引数で渡してください。API 呼び出しはリトライ・フェイルセーフを備えていますが、ネットワーク・キー設定の確認をお願いします。

---

## 主要モジュール / ディレクトリ構成

以下はパッケージ内の主要なファイルと役割（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数管理 / Settings クラス（J-Quants / kabu / LINE / DB パス等）
  - ai/
    - news_nlp.py        — ニュースを LLM で銘柄別スコア化する（score_news）
    - regime_detector.py — マクロセンチメント + ETF MA で市場レジーム判定（score_regime）
  - data/
    - jquants_client.py      — J-Quants API クライアント（認証・レート制御・保存関数）
    - pipeline.py            — ETL パイプライン / run_daily_etl 等
    - etl.py                 — ETLResult の公開
    - calendar_management.py — 市場カレンダー管理・営業日判定
    - news_collector.py      — RSS 取得・前処理・記事ID生成
    - quality.py             — データ品質チェック群
    - stats.py               — zscore_normalize 等の統計ユーティリティ
    - audit.py               — 監査ログスキーマ初期化（signal/order_requests/executions）
  - research/
    - factor_research.py    — ファクター計算（momentum/value/volatility）
    - feature_exploration.py— 将来リターン計算、IC、統計サマリー
    - __init__.py
  - ai/__init__.py, research/__init__.py などで関数を公開

（上記は主要ファイルの抜粋です。細かい実装や追加モジュールはソースを参照してください。）

---

## テスト・デバッグのヒント

- 自動で .env を読み込む仕組みはプロジェクトルート（.git または pyproject.toml を基準）を探索しているため、テスト時に現在のディレクトリ構成に注意してください。
- 自動 `.env` 読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
- OpenAI 呼び出し系は内部で `_call_openai_api` をラップしているため、ユニットテストでは該当関数を patch してモックできます（module path: `kabusys.ai.news_nlp._call_openai_api` / `kabusys.ai.regime_detector._call_openai_api`）。
- J-Quants クライアントの HTTP 呼び出しは `_request` を介しているため、モックしやすくなっています。ID トークン自動リフレッシュの挙動は `get_id_token` 周りで制御されています。

---

## 貢献・ライセンス

この README はコードベースの抜粋に基づいて作成しています。実際の運用では更に README 内のセクション（開発フロー、テスト、CI、ライセンス等）を追加してください。

何か追記やドキュメントの改善点があればお知らせください。