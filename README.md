# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants）、ニュース収集／NLP（OpenAI）、リサーチ（ファクター計算）、監査ログ（発注追跡）などを含む一連の機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とした内部ライブラリです。

- J-Quants API を用いた株価・財務・カレンダー等の差分 ETL（DuckDB 保存、冪等）
- RSS によるニュース収集と article → 銘柄紐付け
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄単位）とマクロセンチメントによる市場レジーム判定
- 研究用のファクター計算、将来リターン・IC・統計サマリ機能
- 監査ログ用スキーマ（signal → order_request → executions）と初期化ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）

設計方針の一部:
- ルックアヘッドバイアス防止のため、内部関数は明示的な target_date を受け取り、`date.today()` に頼らない。
- DuckDB をストレージとして利用。DB 書き込みは冪等（ON CONFLICT）を基本。
- 外部 API 呼び出しはリトライ・バックオフ・レート制御を備える。
- OpenAI 呼び出しは JSON モードを使い、失敗時はフェイルセーフ（0 相当）で継続する。

---

## 機能一覧（ハイレベル）

- 環境設定
  - `kabusys.config.settings`: .env / .env.local / OS 環境変数から設定を読み込み（自動ロードは無効化可能）
- データ/ETL（kabusys.data）
  - J-Quants クライアント（取得・保存・認証・レート制御）：`jquants_client.py`
  - ETL パイプライン（`run_daily_etl`、`run_prices_etl`、`run_financials_etl`、`run_calendar_etl`）
  - 市場カレンダー管理（営業日判定、next/prev/get_trading_days、calendar_update_job）
  - ニュース収集（RSS 取得、安全対策、前処理、raw_news 保存）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ初期化（`init_audit_db` / `init_audit_schema`）
  - 汎用統計ユーティリティ（Zスコア正規化）
- AI（kabusys.ai）
  - ニュース NLP（`score_news`）: 銘柄ごとにニュースをまとめて LLM に投げ、ai_scores テーブルへ保存
  - 市場レジーム判定（`score_regime`）: ETF(1321) の MA とマクロニュースセンチメントを合成してレジーム判定
- Research（kabusys.research）
  - ファクター計算（momentum/value/volatility）、将来リターン計算、IC, 統計サマリー 等

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の union 型表記などを使用）
- DuckDB を使用するので native ビルドに問題ない環境

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存関係をインストール  
   必要最低限の外部ライブラリ:
   - duckdb
   - openai
   - defusedxml
   - （標準ライブラリ以外が追加されている場合は requirements.txt を用意している想定）
   例:
   ```
   pip install duckdb openai defusedxml
   ```
   またはパッケージ化されている場合:
   ```
   pip install -e .
   ```

4. 環境変数の設定  
   プロジェクトルートの `.env` / `.env.local` を用意できます（自動ロードが有効な場合）。主要な環境変数:

   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
   - KABU_API_PASSWORD: kabu ステーション API のパスワード（発注連携がある場合）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite path
   - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env ロードを無効化

   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxx
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（主要な API と実行例）

以下はライブラリをインポートしてスクリプトから呼ぶ基本例です。実行前に DuckDB のスキーマ（raw_prices など）が用意されていることを前提にしています。

- 設定参照
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  ```

- DuckDB 接続準備
  ```python
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- ETL（日次パイプライン）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（OpenAI が必要）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # api_key を引数に渡すか、環境変数 OPENAI_API_KEY を設定
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print("written:", written)
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026,3,20), api_key=None)
  ```

- 監査ログ DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions テーブルが作成されます
  ```

- リサーチ（ファクター計算）
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from kabusys.data.stats import zscore_normalize

  d = date(2026, 3, 20)
  mom = calc_momentum(conn, d)
  val = calc_value(conn, d)
  vol = calc_volatility(conn, d)

  # 複数ファクターの Z スコア正規化例
  records = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
  ```

- RSS 取得（ニュースコレクタの低レベル関数）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  ```

注意点:
- OpenAI 呼び出しはネットワーク・レート制限で失敗することがあるため、関数はリトライ・フォールバックを備えていますが、API キーは必ず設定してください。
- ETL・保存処理は多くの SQL スキーマ（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, ai_scores など）を前提とします。初期スキーマはプロジェクトの別スクリプトで用意することが想定されています。

---

## 実行上の注意 / 運用メモ

- .env の自動読み込みはプロジェクトルートの検出 (.git または pyproject.toml) に基づいて行われます。テスト時など自動化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API はレート制限（120 req/min）に合わせてモジュール内でスロットリングしています。長時間のページネーションや大量取得では時間がかかる点に注意。
- OpenAI の JSON Mode を利用しています。レスポンスのパース失敗や API の一時エラーはフェイルセーフ（0相当）にフォールバックしますが、結果の完全性は保証されません。運用ではログ監視を強く推奨します。
- DuckDB に対する executemany の空引数問題（バージョン依存）を考慮して実装されていますが、DuckDB のバージョン差に留意してください。
- 監査ログは削除しない前提の運用を想定しています。サイズ管理・アーカイブ方針は運用側で設計してください。

---

## ディレクトリ構成（抜粋）

以下は主要ファイル／モジュールの構成です（src/kabusys 以下）。

- kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   — 銘柄別ニューススコアリング（score_news）
    - regime_detector.py            — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（fetch/save）
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETLResult の再エクスポート
    - calendar_management.py        — 市場カレンダー管理（is_trading_day など）
    - news_collector.py             — RSS 取得と前処理
    - quality.py                    — データ品質チェック
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - audit.py                      — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py            — モメンタム/バリュー/ボラティリティ
    - feature_exploration.py        — 将来リターン/IC/統計サマリ
  - execution/ (存在が示唆されるパッケージ名)
  - monitoring/ (存在が示唆されるパッケージ名)
  - その他（strategy 等のモジュール群は __all__ に含まれる）

---

## ロギング / モニタリング

- 各モジュールは標準 logging を使用して情報・警告・エラーを出力します。`LOG_LEVEL` 環境変数でログレベルを制御できます。
- 監視用の設定は `settings` から参照できます（CPU/MEM/DISK 閾値、PID ファイル、KILL フラグ等）。

---

## よくある質問（FAQ）

Q: OpenAI キーはどこに設定する？  
A: 環境変数 `OPENAI_API_KEY`、または `score_news` / `score_regime` に `api_key` 引数で直接渡せます。

Q: .env ファイルの読み込み順は？  
A: OS 環境変数 > .env.local > .env の順で優先されます。

Q: Look-ahead bias はどう扱われている？  
A: スコア生成や ETL の多くの関数は `target_date` を明示的に受け取り、データ選択で `date < target_date` やウィンドウの半開区間を使うなど、未来データ参照を防ぐ実装になっています。

---

README は主にライブラリ利用者向けの概要と基本例をまとめたものです。運用やスキーマ初期化、バックテスト用のデータ準備など、より詳細な手順はプロジェクト内のドキュメント（DataPlatform.md / StrategyModel.md 等）を参照してください。必要であれば README にサンプルスキーマ作成やスクリプト例を追加します。