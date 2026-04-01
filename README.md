# KabuSys

日本株向けのデータプラットフォーム兼自動売買補助ライブラリ。  
J-Quants / JPX のデータを取得・保存・品質チェックし、ニュースNLP や市場レジーム判定、ファクター計算、監査ログなどの機能を提供します。

主な設計方針：
- ルックアヘッドバイアスを防ぐ（内部で date.today()/datetime.today() を直接参照しない）
- DuckDB を中心としたローカルデータストア（冪等な保存）
- 外部API呼び出しに対する堅牢なリトライ・レート制御
- LLM 呼び出しは JSON Mode + バリデーションで安全に処理
- ニュース収集は SSRF / XML攻撃対策済み

---

## 機能一覧

- データ取得 / ETL
  - J-Quants から株価日足（OHLCV）、財務データ、上場銘柄情報、JPX カレンダーを差分取得
  - 差分更新・バックフィル対応、取得後は DuckDB に冪等保存
  - ETL 実行の監査・結果集計（ETLResult）
- データ品質チェック
  - 欠損、スパイク（前日比）、重複、日付不整合の検出（QualityIssue）
- ニュース収集 / 前処理
  - RSS 取得（SSRF対策、受信サイズ制限、トラッキングパラメータ除去）
  - raw_news / news_symbols へ冪等保存
- ニュース NLP（LLM）
  - 銘柄別ニュースを結合して LLM（gpt-4o-mini 等）でセンチメントを算出し ai_scores テーブルへ保存
  - レスポンスバリデーション、バッチ処理、リトライ
- 市場レジーム判定
  - ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを合成して日次レジーム（bull/neutral/bear）を判定
  - LLM 呼び出しのフェイルセーフやリトライ実装
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマンランク相関）、Zスコア正規化等
- 監査（audit）
  - signal / order_request / execution を記録する監査スキーマの作成ユーティリティ
  - 監査専用 DuckDB 初期化関数

---

## 必要要件（推奨）

- Python 3.10+
- DuckDB
- openai パッケージ（OpenAI SDK）
- defusedxml
- （ネットワーク経由で J-Quants / OpenAI を使用するため、各種 API キーが必要）

必要な Python パッケージ例（requirements.txt を用意している場合はそちらを利用）:
- duckdb
- openai
- defusedxml

---

## セットアップ

1. リポジトリをクローンして仮想環境を作成・有効化:
   ```bash
   git clone <repo-url>
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. 必要なパッケージをインストール:
   ```bash
   pip install duckdb openai defusedxml
   # または開発用: pip install -e .
   ```

3. 環境変数の設定:
   プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（読み込み順: OS > .env.local > .env）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主要な環境変数（必須なもの）:
   - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token 内で利用）
   - KABU_API_PASSWORD: kabuステーション API 用パスワード（必要に応じて）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知に使用する場合

   任意 / デフォルト設定:
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/…（デフォルト: INFO）
   - DUCKDB_PATH: データベースパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視（monitoring）DB（デフォルト: data/monitoring.db）
   - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など

4. データディレクトリの作成（必要に応じて）:
   ```bash
   mkdir -p data
   ```

---

## 使い方（基本例）

以下は主要ユースケースの最小例です。実行は仮想環境内で行ってください。

- DuckDB に接続して日次 ETL を実行する:
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（ai_scores への書き込み）を実行:
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"wrote scores for {count} codes")
  ```

- 市場レジーム判定を実行:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査用 DB 初期化:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

注意:
- 上記関数は内部で環境変数（例えば OPENAI_API_KEY や JQUANTS_REFRESH_TOKEN）を参照します。無ければ ValueError が発生します。
- DuckDB テーブルスキーマ（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, market_regime, etc.）は本リポジトリにはDDLが一部含まれていますが、実運用では初期スキーマ作成ルーチンを呼ぶか、マイグレーションで用意してください。

---

## 主要モジュール概要 / ディレクトリ構成

(src 配下のパッケージ構成)

- kabusys/
  - __init__.py
  - config.py
    - .env 自動読み込み、設定アクセス用の Settings オブジェクト（settings）
  - ai/
    - __init__.py
    - news_nlp.py         : ニュースを LLM でスコアリングして ai_scores に保存する
    - regime_detector.py  : マクロニュース + ETF MA200 乖離で市場レジームを判定
  - data/
    - __init__.py
    - calendar_management.py : JPX カレンダー管理（is_trading_day, next_trading_day 等）
    - pipeline.py            : ETL パイプライン（run_daily_etl 等）
    - jquants_client.py      : J-Quants API クライアント（取得 & DuckDB 保存関数）
    - news_collector.py      : RSS 取得・前処理・raw_news 保存（SSRF/サイズ/XML対策）
    - quality.py             : データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py               : 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py               : 監査ログスキーマ初期化 / init_audit_db
    - etl.py                 : ETLResult の公開再エクスポート
  - research/
    - __init__.py
    - factor_research.py     : モメンタム / バリュー / ボラティリティの計算
    - feature_exploration.py : 将来リターン / IC / 統計サマリー 等
  - ai、data など内部の細かなユーティリティ・実装は各モジュール内の docstring を参照

---

## 設計上の注記（運用 / 開発者向け）

- 環境変数の自動ロード:
  - プロジェクトルート（.git または pyproject.toml の存在）を基準に .env / .env.local を自動読込します。
  - OS 環境変数優先。`.env.local` は `.env` をオーバーライドします。
  - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

- 冪等性:
  - J-Quants からの保存は ON CONFLICT DO UPDATE を使用して冪等性を確保。
  - ETL の各ステップは独立してエラーハンドリングされ、1ステップ失敗でも他は継続します（結果は ETLResult.errors に収集）。

- LLM 呼び出し:
  - news_nlp / regime_detector ともに JSON Mode を使い、レスポンスのバリデーションを厳密に行っています。
  - API の一時的な失敗（429, timeout, 5xx）はリトライし、最終失敗はフェイルセーフ（スコア = 0.0 等）で継続する設計。

- セキュリティ:
  - news_collector は SSRF 対策（リダイレクト先の検査、プライベート IP のブロック）、受信サイズ制限、defusedxml による XML 攻撃防止を実装。

---

## トラブルシューティング

- ValueError: OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN が未設定
  - .env にキーを追加するか環境変数を設定してください。

- DuckDB のテーブルが無い・スキーマ不整合
  - 初期スキーマ作成ルーチン（プロジェクト内のスキーマ定義やマイグレーション）を適用してください。
  - audit 用は `kabusys.data.audit.init_audit_db()` を参照。

- J-Quants API が 401 を返す
  - リフレッシュトークンが正しいか、`JQUANTS_REFRESH_TOKEN` を確認。`jquants_client.get_id_token()` がトークンを取得します。

- RSS フィードで XML パースエラー
  - フィードの形式が壊れている可能性があります。ログに警告が出ます。フィード URL を確認してください。

---

この README はコード内の docstring を基に要点をまとめた概要です。各モジュールには詳細な docstring とエラーハンドリングの挙動がコメントで記載されていますので、実装や拡張を行う際は該当モジュールのソースを参照してください。