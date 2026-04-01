# KabuSys

日本株向けのデータプラットフォームと自動売買支援ライブラリ。  
ETL（J-Quants からの株価/財務/カレンダー取得）、ニュース収集と AI によるセンチメント評価、研究（ファクター計算・特徴量解析）、監査ログ（発注トレーサビリティ）、市場カレンダー管理などを提供します。

主な利用対象：
- データパイプライン実行（daily ETL）
- ニュースセンチメントによる銘柄スコアリング（LLM）
- 市場レジーム判定（MA + マクロニュース）
- 研究用ファクター計算・IC/統計集計
- 監査用 DuckDB スキーマ初期化（発注・約定トレース）

バージョン: 0.1.0

---

## 機能一覧

- 環境変数管理（.env 自動読み込み、上書き制御）
- J-Quants API クライアント
  - 日次株価（OHLCV）取得・保存（pagination / リトライ / レート制御）
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存
- ETL パイプライン（差分更新、バックフィル、品質チェックの統合）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS、SSRF/サイズ/トラッキング除去対策）
- ニュース NLP（OpenAI を用いた銘柄別センチメント -> ai_scores 保存）
- 市場レジーム判定（ETF 1321 の MA200 乖離と LLM マクロセンチメントを合成）
- 研究モジュール
  - モメンタム / ボラティリティ / バリュー ファクター計算
  - 将来リターン計算、IC（Spearman rank）、ファクター統計サマリ
  - Zスコア正規化ユーティリティ
- 監査ログスキーマ（signal_events / order_requests / executions）および初期化ユーティリティ
- 市場カレンダー管理（営業日判定 / next/prev / bulk update job）

---

## 前提条件（依存ライブラリ）

最低限想定される主要依存：
- Python 3.9+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- （標準ライブラリ・urllib 他を多用）

実際のプロジェクト配布では requirements.txt / pyproject.toml を参照してください。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone ...

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （必要に応じて他のパッケージを追加）

4. 環境変数の設定
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（起動時）。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数（README 用の抜粋）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時に必須）
- KABU_API_PASSWORD: kabu API パスワード（実行/発注コンポーネント利用時）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: デフォルト DuckDB ファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite パス
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視設定
- KABUSYS_ENV: 環境（development, paper_trading, live）
- LOG_LEVEL: ログレベル（DEBUG, INFO, ...）

（.env.example をプロジェクトに用意しておくことを推奨）

---

## 使い方（代表的な利用例）

以下は Python REPL / スクリプトでの簡単な利用例です。各関数は DuckDB の接続オブジェクト（duckdb.connect(...) が返すもの）を受け取ります。

- DuckDB 接続を作る
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL 実行
  - from datetime import date
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- 個別 ETL（株価 / 財務 / カレンダー）
  - from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
  - run_prices_etl(conn, target_date=date(2026,3,20))
  - run_financials_etl(conn, target_date=date(2026,3,20))
  - run_calendar_etl(conn, target_date=date(2026,3,20))

- ニュースセンチメント（LLM）で銘柄スコアを作る
  - from datetime import date
  - import duckdb
  - from kabusys.ai.news_nlp import score_news
  - conn = duckdb.connect("data/kabusys.duckdb")
  - n = score_news(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY が必要
  - print(f"scored {n} codes")

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY が必要

- 監査ログ DB 初期化（発注トレース用）
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")

- カレンダー参照ユーティリティ
  - from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days
  - is_trading_day(conn, date(2026,3,20))
  - next_trading_day(conn, date(2026,3,20))
  - get_trading_days(conn, date(2026,3,1), date(2026,3,31))

注意点 / テスト時のヒント
- OpenAI 呼び出しは内部でリトライを実装していますが、ユニットテストでは各モジュールが提供する _call_openai_api を patch/モックして応答を差し替えられます（score_news/_score_macro 等の説明参照）。
- J-Quants API クライアントは内部でトークンキャッシュ・自動リフレッシュとレート制御を行います。テストでは get_id_token や _request をモックすることを推奨します。
- DuckDB の executemany は空リストを受け付けないバージョン制約があるため、ライブラリ内でもチェック済みです。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py  — 環境変数・設定管理（.env 自動ロード、Settings クラス）
- ai/
  - __init__.py
  - news_nlp.py         — ニュース NLP（銘柄別スコア生成）
  - regime_detector.py  — 市場レジーム判定（MA200 + LLM）
- data/
  - __init__.py
  - jquants_client.py       — J-Quants API クライアント（取得・保存）
  - pipeline.py            — ETL パイプライン（run_daily_etl 等）
  - etl.py                 — ETLResult 再エクスポート
  - news_collector.py      — RSS ニュース収集（SSRF/サイズ対策）
  - quality.py             — データ品質チェック
  - stats.py               — 汎用統計ユーティリティ（Zスコア）
  - calendar_management.py — 市場カレンダー管理（営業日ロジック）
  - audit.py               — 監査ログスキーマ定義 & 初期化
- research/
  - __init__.py
  - factor_research.py     — Momentum / Volatility / Value 等のファクター計算
  - feature_exploration.py — 将来リターン計算、IC、ファクター統計
- ai/、data/、research/ 以下には更に詳細なユーティリティ関数・定義があります。

---

## 運用上の注意

- 環境変数は OS 環境変数が最優先。プロジェクトルート（.git や pyproject.toml を基準）にある `.env.local`（上書き）→ `.env` を自動で読み込みます。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI / J-Quants の API キーは外部に漏れないよう管理し、.env をリポジトリに含めないでください。
- DuckDB スキーマ作成や DDL 実行は idempotent（冪等）に設計されていますが、実行前にバックアップを取ることを推奨します。
- リアル口座での発注や自動売買を行う場合は、十分な検証とリスク管理を実施してください（本ライブラリは補助的ツールです）。

---

もし README に追加したい具体的な例（.env.example の雛形、requirements の正確なリスト、実行スクリプト例など）があれば教えてください。必要に応じて追記します。