# KabuSys

日本株自動売買プラットフォームのライブラリ群（データ ETL / ニュース NLP / リサーチ / 監査ログ / 市場カレンダー 等）。  
このリポジトリは、J-Quants や RSS、OpenAI（LLM）を用いたデータ収集・品質管理・AI スコアリング・市場レジーム判定・ファクター計算などを行うモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株にフォーカスしたデータプラットフォーム兼研究 / 自動売買支援ライブラリです。主に以下を目的とします。

- J-Quants API からの株価・財務・カレンダー取得（差分 ETL、ページネーション、リトライ、レートリミット制御）
- RSS ニュース収集と前処理（SSRF 対策、トラッキングパラメータ除去、冪等保存）
- OpenAI を使ったニュースセンチメント解析（銘柄毎 / マクロ）
- 市場レジーム判定（ETF の MA とマクロセンチメントの合成）
- ファクター計算・特徴探索（モメンタム、ボラティリティ、バリュー、IC 等）
- データ品質チェック（欠損/スパイク/重複/日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティを維持）とその初期化ユーティリティ

設計上、バックテストでのルックアヘッドバイアスを避けるため、
datetime.now()/today() による暗黙的な時刻参照を極力避け、関数引数で日付を与える設計が多用されています。

---

## 主な機能一覧

- data/
  - ETL Pipeline（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（認証・ページング・保存関数）
  - カレンダー管理（営業日判定、next/prev_trading_day、calendar_update_job）
  - ニュース収集（RSS -> raw_news、SSRF/サイズ/トラッキング対策）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 統計ユーティリティ（zscore 正規化）
  - 監査ログ初期化（init_audit_db / init_audit_schema）
- ai/
  - news_nlp.score_news: 銘柄毎ニュースセンチメントを ai_scores に書き込み
  - regime_detector.score_regime: ETF MA とマクロセンチメントで market_regime を算出
  - OpenAI 呼び出しは適切なリトライ/フェイルセーフを実装
- research/
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン・IC・統計サマリー等の探索ユーティリティ

---

## セットアップ手順

前提
- Python 3.10+（typing | union types を使用）
- ネットワークアクセス（J-Quants / RSS / OpenAI）

1. リポジトリをクローンして仮想環境を作成（例: venv）
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール（最低限）
   ```bash
   pip install duckdb openai defusedxml
   ```
   実際のプロジェクトでは requirements.txt / pyproject.toml を参照して依存を揃えてください。

3. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を配置することで自動読み込みされます。
   - 自動読み込みを無効にする場合：
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   推奨する必須環境変数（README 用抜粋）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD : kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN : Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID : Slack チャネル ID（必須）
   - OPENAI_API_KEY : OpenAI API キー（AI モジュール利用時）
   オプション:
   - KABUSYS_ENV : development | paper_trading | live（デフォルト development）
   - LOG_LEVEL : DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
   - DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH : 監視用 SQLite パス（デフォルト data/monitoring.db）
   - PID_FILE_PATH : 実行プロセス PID ファイル（デフォルト data/execution.pid）
   - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT : 監視しきい値

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

4. データベース準備（監査ログ用 DuckDB を初期化する例）
   ```python
   from kabusys.config import settings
   from kabusys.data.audit import init_audit_db

   conn = init_audit_db(settings.duckdb_path)
   # conn をアプリケーション内部で利用
   ```

---

## 使い方（主なユースケース）

※ すべての関数は date 型の日付引数を受け取るものが多く、ルックアヘッドバイアス防止のため内部での現在時刻参照は避けられています。

1. DuckDB 接続を作る（共通）
   ```python
   import duckdb
   from kabusys.config import settings

   conn = duckdb.connect(str(settings.duckdb_path))
   ```

2. 日次 ETL を実行する
   ```python
   from kabusys.data.pipeline import run_daily_etl
   from datetime import date

   result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(result.to_dict())
   ```

3. ニュースセンチメント（銘柄毎）をスコアリングして ai_scores に書き込む
   ```python
   from kabusys.ai.news_nlp import score_news
   from datetime import date

   n_written = score_news(conn, target_date=date(2026, 3, 20))
   print("書き込み銘柄数:", n_written)
   ```

4. 市場レジーム判定（ETF 1321 の MA とマクロセンチメントの合成）
   ```python
   from kabusys.ai.regime_detector import score_regime
   from datetime import date

   score_regime(conn, target_date=date(2026, 3, 20))
   ```

5. 監査データベースの初期化（別 DB を使用したい場合）
   ```python
   from kabusys.data.audit import init_audit_db
   conn_audit = init_audit_db("data/audit.duckdb")
   ```

6. ニュース RSS をフェッチ（単体ユーティリティ）
   ```python
   from kabusys.data.news_collector import fetch_rss

   articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
   for a in articles:
       print(a["id"], a["title"], a["datetime"])
   ```

注意事項:
- OpenAI や J-Quants を用いる機能は API キー / トークンが必須です。無ければ ValueError が発生します。
- 外部 API 呼び出しはリトライやフェイルセーフ設計を持ちますが、料金や利用制限に注意してください。
- DuckDB の executemany はバージョン差で空リストが受け付けられないため、各モジュールで保護されて実装されています。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数・設定管理（.env 自動読み込み含む）
  - ai/
    - __init__.py
    - news_nlp.py                     — ニュース NLP スコアリング（score_news）
    - regime_detector.py              — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント + 保存関数
    - pipeline.py                     — ETL パイプライン（run_daily_etl 等）
    - etl.py                          — ETL インターフェース再エクスポート
    - news_collector.py               — RSS 収集・前処理
    - calendar_management.py          — 市場カレンダー管理（営業日判定等）
    - stats.py                        — 統計ユーティリティ（zscore_normalize）
    - quality.py                      — データ品質チェック
    - audit.py                        — 監査ログスキーマ初期化（init_audit_db 等）
  - research/
    - __init__.py
    - factor_research.py              — モメンタム/バリュー/ボラティリティ算出
    - feature_exploration.py          — 将来リターン/IC/統計サマリー
  - ai/、data/、research/ の各種補助モジュールが含まれます。

---

## 設定と動作に関する補足

- .env の自動ロード
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に `.env`、`.env.local` の順で自動読み込みします。
  - OS 環境変数が優先され、`.env.local` は `.env` を上書きします。
  - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 環境の区別
  - KABUSYS_ENV によって動作モードを切り替えます（development / paper_trading / live）。
- ロギングとしきい値
  - LOG_LEVEL、CPU_THRESHOLD_PCT 等の値は config.Settings 経由で取得できます。

---

## 開発・テストに関して

- モジュール設計はテスト容易性を考慮しており、OpenAI / HTTP 呼び出し等は差し替え可能（関数をモック可能）です。
- DuckDB を :memory: で使えば単体テスト用の軽量 DB を用意できます。

---

この README はコードベースの主要ポイントを抜粋してまとめたものです。より詳しい設計思想や API の振る舞いは各モジュール（src/kabusys 以下の .py ファイル）ドキュメント文字列を参照してください。必要であれば、README にチュートリアル（初回フル ETL 実行例、監査ログ活用例、戦略接続例）を追加できます。どのトピックを深掘りしますか？