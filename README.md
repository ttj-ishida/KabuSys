# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
データの ETL、ニュースセンチメント解析（LLM）、市場レジーム判定、ファクター計算、品質チェック、監査ログ（トレーサビリティ）など、アルゴリズム取引の基盤機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は主に以下の目的で設計された Python パッケージです。

- J-Quants API から株価・財務・カレンダー等のデータを差分取得・保存（DuckDB）
- RSS ニュース収集と前処理、銘柄紐付け
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント解析（銘柄別およびマクロ）
- ETF を用いた市場レジーム判定（ma200 と マクロセンチメントの合成）
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレース用テーブルの作成・初期化）
- 設定は環境変数（.env 自動読み込み機能あり）で管理

設計上の重要点:
- ルックアヘッドバイアスを防ぐため、関数は内部で date.today() や datetime.today() を直接参照しない（呼び出し側が target_date を渡す）。
- API 呼び出しはリトライ・バックオフ・レートリミットを備え、フェイルセーフ（失敗時はスキップ or 中立値）を考慮。
- DuckDB をデータストアとして利用し、冪等保存（ON CONFLICT 等）を行う。

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（fetch_* / save_*）
  - 市場カレンダー管理（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job）
  - ニュース収集（RSS fetch_rss, 前処理、raw_news 保存、news_symbols 連携）
  - データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
  - 監査ログスキーマの初期化（init_audit_schema, init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai/
  - ニュース NLP（銘柄ごとの news スコア生成: score_news）
  - 市場レジーム判定（ETF ma200 とマクロセンチメントの合成: score_regime）
- research/
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索・評価（calc_forward_returns, calc_ic, factor_summary, rank）
- 設定管理
  - .env 自動読み込み（プロジェクトルートの .env / .env.local を優先順で読み込む。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - 環境変数参照用 Settings オブジェクト（kabusys.config.settings）

---

## 必要条件 / 依存関係（想定）

- Python 3.10+
- 必須パッケージ（抜粋）:
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ（urllib, json, logging 等）を使用

（実際の依存関係は pyproject.toml / requirements.txt を参照してください）

---

## 環境変数（主なもの）

少なくとも以下は設定する必要があります（用途に応じて追加設定あり）。

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL で ID トークン取得に使用）
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注などに利用する場合）
- SLACK_BOT_TOKEN: Slack 通知を行う場合の Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
- OPENAI_API_KEY: OpenAI API 呼び出しに必要（news_nlp, regime_detector）
- DUCKDB_PATH: デフォルトの DuckDB ファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite DB（例: data/monitoring.db）
- KABUSYS_ENV: 実行環境 ("development", "paper_trading", "live")
- LOG_LEVEL: ログレベル ("DEBUG", "INFO", ...)

.env ファイルをプロジェクトルートに置くと自動的に読み込まれます（.env.local は .env を上書き）。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン
   - git clone <リポジトリURL>

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. パッケージをインストール（編集可能インストール）
   - python -m pip install --upgrade pip
   - python -m pip install -e ".[dev]"   # pyproject の extras 名称に応じて変更

   依存が明示されていない場合は最低限:
   - python -m pip install duckdb openai defusedxml

4. 環境変数を設定
   - プロジェクトルートに .env を作成し必要な値を設定するか、CI/実行環境で環境変数を設定。

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=...
   OPENAI_API_KEY=...
   SLACK_BOT_TOKEN=...
   SLACK_CHANNEL_ID=...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

---

## 使い方（代表的な API / 実行例）

以下は Python スクリプトや対話型で利用する想定の例です。

- DuckDB 接続の作成（例: ファイル DB）
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL を実行（J-Quants からデータ取得 -> 保存 -> 品質チェック）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別）スコアを作成
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {n_written}")
  ```

- 市場レジーム判定（ETF 1321 の ma200 とマクロセンチメント合成）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB の初期化（監査専用 DuckDB）
  ```python
  from pathlib import Path
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db(Path("data/audit.duckdb"))
  ```

- ファクター計算例
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

ログやエラーは標準の logging を利用して出力されます。必要に応じて logging.basicConfig で設定してください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要ファイル構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                       # 環境変数 / .env 管理
  - ai/
    - __init__.py
    - news_nlp.py                    # 銘柄別ニューススコア（score_news）
    - regime_detector.py             # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py                    # ETL パイプライン（run_daily_etl 等）
    - jquants_client.py              # J-Quants API クライアント（fetch/save）
    - news_collector.py              # RSS 取得・前処理・保存
    - calendar_management.py         # 市場カレンダー管理
    - quality.py                     # データ品質チェック
    - stats.py                       # 統計ユーティリティ（zscore_normalize）
    - audit.py                       # 監査ログスキーマ初期化
    - etl.py                         # ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py             # モメンタム / ボラティリティ / バリュー
    - feature_exploration.py         # 将来リターン / IC / 統計サマリー
  - research/* その他
  - monitoring/                      # 監視・プロセス監視等（存在する場合）
  - strategy/                        # 戦略関連（存在する場合）
  - execution/                       # 発注実行層（存在する場合）

（実際のプロジェクトにはさらに補助モジュールやテストが含まれます）

---

## 実行上の注意 / ベストプラクティス

- OpenAI API キーや J-Quants のトークン等は安全に管理してください（CI の Secrets / Vault 等）。
- バックテストで利用する際は Look-ahead Bias を防ぐため、対象日以前のデータのみを DB にロードした状態で評価してください（jquants_client.fetch_listed_info 等は取得タイミングに注意）。
- ETL はネットワーク・API エラーに強い設計ですが、ログと quality.run_all_checks の結果を監視してデータ品質を常にチェックしてください。
- DuckDB のバージョン差異による SQL の挙動に注意（ex. executemany の空リスト挙動など）。パッケージは互換性を保つよう配慮されていますが、実環境ではテストを推奨します。

---

## 貢献 / 開発

- コードは PEP8 に準拠することを推奨します。
- テストは関数単位でのユニットテスト（特に API 呼び出し部分はモック化）を推奨。
- .env.example を用意して必要な環境変数を明記すると導入が容易になります。

---

不明点や README に追加してほしい内容があれば教えてください。環境別の実行例（paper_trading / live）、CI 設定、より詳細なテーブル定義なども追加できます。