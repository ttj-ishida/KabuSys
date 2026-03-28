# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
株価・財務・ニュースの ETL、ニュースの NLP スコアリング、マーケットレジーム判定、監査ログ（トレーサビリティ）など、売買システム全般で必要となる機能群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買プラットフォームやリサーチ環境で使う共通コンポーネント群をまとめたライブラリです。主な目的は以下の通りです：

- J-Quants API からの差分取得（株価、財務、上場情報、カレンダー）と DuckDB への保存（ETL）
- RSS によるニュース収集と前処理（SSRF 対策、トラッキングパラメータ除去、記事IDの冪等化）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント／市場レジームの評価（JSON Mode を利用）
- ファクター計算・特徴量探索（モメンタム・バリュー・ボラティリティ等）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（信号 → 発注 → 約定）を保存する監査用 DB スキーマの初期化ユーティリティ

設計上の特徴として、ルックアヘッドバイアスの排除、冪等性、API リトライ／レートリミット制御、安全な外部入力処理（RSS の SSRF 対策、XML の安全パース）などを重視しています。

---

## 主な機能一覧

- data
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 系関数、認証トークン管理、レート制限）
  - カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job）
  - ニュース収集（RSS 取得、前処理、raw_news への保存準備）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore 正規化）
- ai
  - ニュース NLP（score_news: 銘柄ごとのニュースセンチメントを ai_scores に書き込む）
  - レジーム判定（score_regime: ETF 1321 の MA200 乖離とマクロニュースを合成して market_regime に書き込む）
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量解析（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - 環境変数読み込みユーティリティ（.env / .env.local を自動ロードする仕組み）
  - settings オブジェクトで各種設定値を取得

---

## 必須 / 推奨環境

- Python 3.10 以上（型注釈の | 演算子、from __future__ annotations 等を使用）
- 依存パッケージ（少なくとも以下が必要）
  - duckdb
  - openai
  - defusedxml

（他に標準ライブラリのみで実装された部分が多いですが、実行用途によって追加パッケージが必要な場合があります）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .\.venv\Scripts\activate   # Windows
   ```

3. 必要パッケージをインストール
   - 簡易例:
     ```
     pip install duckdb openai defusedxml
     ```
   - パッケージ化されている場合:
     ```
     pip install -e .
     ```

4. 環境変数の設定
   - プロジェクトルートの `.env` / `.env.local`（なければ作成）または OS 環境変数で下記を設定してください。

必須環境変数（実行する機能に応じて必要）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL）
- OPENAI_API_KEY: OpenAI API キー（AI 評価）
- KABU_API_PASSWORD: kabuステーション API のパスワード（注文連携を行う場合）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知を行う場合

任意（デフォルト値あり）
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: デフォルト data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化（テスト時に便利）

5. データディレクトリ作成（必要なら）
   ```
   mkdir -p data
   ```

---

## 基本的な使い方（例）

Python スクリプトや REPL から以下のように利用します。下記は代表的な例です。

- DuckDB 接続と settings の取得
  ```python
  import duckdb
  from kabusys.config import settings

  db_path = settings.duckdb_path  # Path オブジェクト
  conn = duckdb.connect(str(db_path))
  ```

- 日次 ETL を実行（株価・財務・カレンダー取得 + 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn)  # target_date を指定しなければ今日が対象
  print(result.to_dict())
  ```

- ニュースの NLP スコアリング（score_news）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {n_written} codes")
  ```

- 市場レジーム判定（score_regime）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査用 DB の初期化（独立した監査 DB を作る）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- ファクター計算・研究系
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  target = date(2026, 3, 20)
  mom = calc_momentum(conn, target)
  val = calc_value(conn, target)
  vol = calc_volatility(conn, target)
  ```

注意点:
- OpenAI 連携関数（score_news / regime_detector）は api_key を引数で渡すか、環境変数 OPENAI_API_KEY を参照します。未設定だと ValueError を送出します。
- J-Quants 呼び出しは settings.jquants_refresh_token を用います（get_id_token が自動でリフレッシュを行います）。
- ETL / AI 呼び出しはルックアヘッドバイアスを避ける実装になっています（内部で date.today() を不用意に参照しない等）。

---

## 環境変数の自動ロードについて

`kabusys.config` はパッケージ読み込み時にプロジェクトルート（.git または pyproject.toml を基準）を探索し、見つかった場合は `.env` → `.env.local` の順で読み込みます（OS 環境変数を上書きしない / .env.local は上書き可能）。テストなどで自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主なファイル）

```
src/kabusys/
├── __init__.py               # パッケージ定義（version 等）
├── config.py                 # 設定・環境変数ロード
├── ai/
│   ├── __init__.py
│   ├── news_nlp.py           # news -> ai_scores（OpenAI）
│   └── regime_detector.py    # 市場レジーム判定（MA200 + マクロニュース）
├── data/
│   ├── __init__.py
│   ├── calendar_management.py
│   ├── pipeline.py           # ETL パイプライン（run_daily_etl 等）
│   ├── jquants_client.py     # J-Quants API クライアント（fetch/save）
│   ├── news_collector.py     # RSS 収集・前処理
│   ├── quality.py            # データ品質チェック
│   ├── stats.py              # zscore_normalize 等
│   ├── audit.py              # 監査ログスキーマ初期化
│   └── etl.py                # ETLResult の再エクスポート
├── research/
│   ├── __init__.py
│   ├── factor_research.py    # momentum/value/volatility 等
│   └── feature_exploration.py
└── research/...              # その他リサーチユーティリティ
```

---

## ロギング / 実行モード

- KABUSYS_ENV（development / paper_trading / live）により実行モードを区別できます（settings.env）。
- LOG_LEVEL 環境変数でログレベルを制御できます（デフォルト INFO）。
- 各モジュールは標準 logging を利用しているため、アプリ側でハンドラを設定してください。

---

## テスト / 開発メモ

- OpenAI 呼び出しや外部ネットワークを含む処理は、モジュール内で外部呼び出し箇所を関数化しているため、unittest.mock で差し替えやすく設計されています（例: kabusys.ai.news_nlp._call_openai_api を mock する）。
- .env の自動ロードはプロジェクトルート探索に依存するため、テスト実行時は KABUSYS_DISABLE_AUTO_ENV_LOAD を有効化して環境を制御することを推奨します。

---

## 注意事項 / ライセンス

- 本 README はコードベースに基づく利用説明書です。実運用にあたっては、API キーの管理、レート制御、発注ロジックの検証・サンドボックスでの十分なテストを必ず行ってください。
- ライセンス情報・貢献規約等はリポジトリのトップレベルにある LICENSE / CONTRIBUTING 等のファイルを参照してください（存在する場合）。

---

必要であれば、セットアップ手順の具体的な .env.example（期待するキーのテンプレート）や、CI／Docker での起動例、より詳細な API 使用例を追加で作成します。どの情報を優先して追加しますか？