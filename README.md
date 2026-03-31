# KabuSys

日本株向けの自動売買・データプラットフォーム（ライブラリ）。  
データ取得（J-Quants）、ETL、ニュースNLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（DuckDB）などをまとめたモジュール群を提供します。

---

## 主な概要

- データ取得 / ETL：J-Quants API から株価／財務／カレンダーを差分取得して DuckDB に保存するパイプラインを提供します（jquants_client / pipeline）。
- ニュース NLP：RSS を収集して raw_news に保存し、OpenAI（gpt-4o-mini 等）を使って銘柄ごとのセンチメントを算出して ai_scores に保存します（news_collector / news_nlp）。
- 市場レジーム判定：ETF（1321）200日移動平均乖離とマクロニュースの LLM センチメントを合成して日次の市場レジーム（bull/neutral/bear）を算出します（regime_detector）。
- 研究（Research）：モメンタム / バリュー / ボラティリティ等のファクター計算、将来リターンやIC・統計サマリーを行うユーティリティ（research）。
- 監査ログ（Audit）：シグナル→発注→約定までのトレーサビリティ用テーブルを DuckDB に初期化・管理する仕組み（audit）。
- データ品質チェック：欠損・スパイク・重複・日付不整合を検出するチェック群（data.quality）。

---

## 機能一覧

- 環境設定管理（.env 自動読み込み・settings）
- J-Quants API クライアント（取得・保存・レート制限・リトライ・トークン自動リフレッシュ）
- 日次 ETL パイプライン（run_daily_etl）
- RSS ニュース収集（SSRF対策・gzip制限・トラッキング除去）
- OpenAI を用いたニュースセンチメント算出（バッチ・JSON Mode・リトライ）
- 市場レジーム判定（ETF MA200 とマクロセンチメントの合成）
- ファクター計算（momentum, volatility, value）と正規化ユーティリティ
- データ品質チェック（missing, spike, duplicates, date_consistency）
- 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
- 各種ユーティリティ（日付処理、統計、DBヘルパー等）

---

## 必須環境・依存パッケージ

最低限の依存パッケージ（例）:
- Python 3.10+
- duckdb
- openai
- defusedxml

（プロジェクト側で requirements.txt を用意している場合はそれを使用してください。ここに示したのはコードから推定される主要依存です。）

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. パッケージのインストール
   - 開発中にローカル編集して利用する場合:
     ```
     pip install -e .
     ```
   - 必要な依存パッケージを個別にインストールする例:
     ```
     pip install duckdb openai defusedxml
     ```

4. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと自動読み込みされます（自動読み込みはデフォルトで有効）。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   代表的な環境変数（必須のもの）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で利用）
   - KABU_API_PASSWORD: kabuステーション接続パスワード（発注等で使用する場合）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack チャネル ID
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: env（development/paper_trading/live のいずれか）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/...）

   例 `.env`（テンプレートを作ってください）:
   ```
   JQUANTS_REFRESH_TOKEN=...
   OPENAI_API_KEY=...
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=...
   SLACK_CHANNEL_ID=...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（サンプル）

以下は Python REPL またはスクリプト内での基本的な使い方例です。

- 設定（settings）の読み出し
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  ```

- DuckDB 接続を作成して日次 ETL を実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを算出して ai_scores へ書き込む
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY は環境変数で
  print(f"wrote {written} scores")
  ```

- 市場レジーム判定を実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))  # 結果は market_regime テーブルに保存
  ```

- 監査ログ DB を初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # ディレクトリは自動作成
  ```

- J-Quants からの生データ取得（直接呼び出し）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を利用
  records = fetch_daily_quotes(id_token=token, date_from=date(2026,3,1), date_to=date(2026,3,20))
  ```

注意点:
- OpenAI に関する呼び出しは API 使用料金が発生します。テスト時はモック化（unittest.mock.patch）を推奨します。
- run_daily_etl 等は内部で date.today() を用いる箇所もありますが、主要な関数はルックアヘッドバイアス防止を考慮して設計されています。テストやバッチ実行では明示的に target_date を渡すことを推奨します。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要な Python モジュール構成（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースセンチメント算出（OpenAI）
    - regime_detector.py            — 市場レジーム判定（MA200 + macro LLM）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得・保存）
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETL インターフェース再エクスポート
    - news_collector.py             — RSS 収集・raw_news 保存
    - calendar_management.py        — 市場カレンダー管理・営業日判定
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - quality.py                    — データ品質チェック群
    - audit.py                      — 監査ログスキーマ初期化 / audit DB ユーティリティ
  - research/
    - __init__.py
    - factor_research.py            — momentum / value / volatility 等
    - feature_exploration.py        — forward returns / IC / summaries

各モジュールは概ね以下の目的で分割されています:
- data.* : データ取得・ETL・保存・品質管理
- ai.* : ニュース NLP と LLM を用いた分析
- research.* : 研究・因子計算・評価指標
- audit : 監査ログ（取引フローの完全トレーサビリティ）

---

## 実運用向け注意事項

- KABUSYS_ENV によるモード:
  - development, paper_trading, live をサポート。is_live / is_paper / is_dev のプロパティで判定可能。
  - 実発注を行う機能を有効化する前に paper_trading（検証）で十分にテストしてください。
- セキュリティ:
  - API キーやトークンは必ず安全に管理し、公開リポジトリに含めないでください。
  - news_collector は SSRF 対策・応答サイズ制限・XML デフューズを実装していますが、運用環境ではネットワークポリシーを厳格にしてください。
- テスト:
  - OpenAI コールやネットワーク依存処理はモック化してユニットテストを実施してください（コード内にモック可能なポイントがあります）。
- トランザクション:
  - DuckDB に対する複数の操作は BEGIN/COMMIT を利用して冪等性・原子性を確保していますが、呼び出し元でトランザクションを扱う際は注意してください（audit.init_audit_schema は transactional フラグあり）。

---

## 追加情報 / 開発者向けヒント

- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。CI/CD やテストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると良いです。
- OpenAI 呼び出しに関しては JSON Mode を使用し、厳密な JSON の返却を期待する設計になっています。レスポンスのバリデーションとリトライロジックが組み込まれています。
- jquants_client は内部で固定間隔の RateLimiter（120 req/min）とリトライ/トークン再取得を行います。大量取得時の間隔調整は _MIN_INTERVAL_SEC を変更してください（ただし API ルールを守ってください）。

---

この README はコードベースの主要点をまとめたものです。詳細な API 仕様・スキーマ・運用手順は各モジュールの docstring（ソース内コメント）を参照してください。追加で README に追記してほしいトピック（例: 実行スクリプト、CI 設定、サンプル .env.example）などがあれば教えてください。