# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。ETL、ニュースNLP、マーケットレジーム判定、ファクター算出、データ品質チェック、監査ログ機能などを備えた内部ユーティリティ群を提供します。

- パッケージ名: kabusys
- バージョン: 0.1.0（src/kabusys/__init__.py）

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群をまとめたライブラリです。

- J-Quants API からのデータ取得（株価日足、財務データ、JPX カレンダー）
- DuckDB ベースの ETL パイプライン（差分取得／バックフィル／品質チェック）
- ニュース収集・前処理・LLM を用いたニュースセンチメント算出（gpt-4o-mini）
- 市場レジーム判定（ETF 1321 の MA 乖離 + マクロニュースの LLM センチメント融合）
- 研究用途のファクター計算・特徴量探索（モメンタム、ボラティリティ、バリュー等）
- 監査ログ（signal → order_request → executions）を格納する監査用スキーマ初期化ユーティリティ
- Slack 通知や kabu ステーション等の外部連携設定を環境変数で管理

設計上の特徴：
- DuckDB をデータストアとして利用（高速な分析向け）
- OpenAI（gpt-4o-mini）を JSON mode で利用して安定的に構造化レスポンスを取得
- Look-ahead バイアス対策を重視（内部関数は date.today()/datetime.today() を直接参照しない設計）
- API 呼び出しはリトライ・バックオフ・レート制御を備える（J-Quants / OpenAI）

---

## 主な機能一覧

- data/
  - ETL: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント: fetch_* / save_*（ページネーション・認証・リトライ・レート制御）
  - カレンダー管理: is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - ニュース収集: RSS 取得・正規化・raw_news 保存支援
  - 品質チェック: 欠損・スパイク・重複・日付不整合チェック
  - 監査ログ初期化: init_audit_schema / init_audit_db
  - 統計ユーティリティ: zscore_normalize

- ai/
  - news_nlp.score_news(conn, target_date, api_key=None): ニュースを銘柄別に集約し LLM でセンチメント算出 → ai_scores テーブルへ保存
  - regime_detector.score_regime(conn, target_date, api_key=None): 1321 の MA200 乖離とマクロニュース LLM スコアを合成して market_regime テーブルへ保存

- research/
  - factor_research.calc_momentum / calc_volatility / calc_value
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize は data.stats モジュールから参照可能

- config.py
  - .env / .env.local の自動ロード（プロジェクトルート検出）
  - Settings クラスで環境変数を一元管理（例: settings.jquants_refresh_token）

---

## セットアップ手順（ローカル開発向け）

> 前提: Python 3.10+ を想定（型ヒントに Union 表記や型注釈を使用）

1. リポジトリを取得
   - Git でクローンする想定

2. 仮想環境作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   - 代表的な依存: duckdb, openai, defusedxml
   - 例:
     ```
     pip install duckdb openai defusedxml
     ```
   - （プロジェクトに pyproject.toml / requirements.txt があればそちらを利用してください）

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（config.py の自動ロード）。
   - 自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須環境変数（少なくとも ETL / AI を使う場合）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - OPENAI_API_KEY: OpenAI の API キー（score_news / score_regime にも利用可）
     - KABU_API_PASSWORD: kabuステーション API のパスワード（発注関連）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知を使う場合
   - 省略可能 / デフォルトあり:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
     - LOG_LEVEL: DEBUG | INFO | WARNING | ...
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（デフォルト）

   - .env のフォーマットは標準的な KEY=VALUE、コメントや export 形式にも対応します。

5. データディレクトリ作成
   ```
   mkdir -p data
   ```

---

## 使い方（代表的な例）

以下は DuckDB 接続を用いた主要 API の利用例です。実行は Python スクリプトやジョブランナーから行ってください。

- ETL（日次実行の例）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントのスコア生成（AI）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026,3,20))
  print(f"wrote {written} ai_scores")
  # OPENAI_API_KEY は環境変数に設定するか、api_key引数で渡します
  ```

- 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査ログ DB の初期化（独立した監査 DB を作成する場合）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/kabusys_audit.duckdb")
  # conn は監査用の DuckDB 接続
  ```

- 研究用ファクター計算
  ```python
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026,3,20))
  volatility = calc_volatility(conn, date(2026,3,20))
  value = calc_value(conn, date(2026,3,20))
  normalized = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])
  ```

注意点：
- score_news / score_regime は OpenAI API キーが必要です。api_key 引数を省略した場合、環境変数 OPENAI_API_KEY を参照します。
- J-Quants API は認証（refresh token -> id token）を行います。JQUANTS_REFRESH_TOKEN を必ず設定してください。
- ETL の保存先テーブルはスキーマが前提として存在する想定です（ETL 実行前にスキーマ初期化を行う運用を想定）。監査スキーマは data.audit.init_audit_schema / init_audit_db で作成できます。

---

## ディレクトリ構成（主要ファイル）

リポジトリ内の src/kabusys 以下の主要モジュールを抜粋します。

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings
  - ai/
    - __init__.py
    - news_nlp.py                — ニュースNLP, score_news
    - regime_detector.py         — レジーム判定, score_regime
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（fetch/save）
    - pipeline.py                — ETL パイプライン / run_daily_etl 等
    - etl.py                     — ETLResult の公開
    - news_collector.py          — RSS 収集・正規化
    - calendar_management.py     — マーケットカレンダー管理
    - quality.py                 — データ品質チェック
    - stats.py                   — zscore_normalize 等
    - audit.py                   — 監査ログテーブル定義 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py         — calc_momentum, calc_value, calc_volatility
    - feature_exploration.py     — forward returns, IC, summary, rank

---

## 環境変数一覧（代表）

- JQUANTS_REFRESH_TOKEN — 必須（J-Quants のリフレッシュトークン）
- OPENAI_API_KEY         — 必須（AI スコアリングを使う場合）
- KABU_API_PASSWORD      — kabuステーション API 用パスワード
- KABU_API_BASE_URL      — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN        — Slack 通知用
- SLACK_CHANNEL_ID       — Slack 通知先チャンネル
- DUCKDB_PATH            — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH            — SQLite 監視 DB 等（デフォルト data/monitoring.db）
- KABUSYS_ENV            — development | paper_trading | live（デフォルト development）
- LOG_LEVEL              — ログレベル（INFO 等）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効にする（1 等の真値）

config.Settings クラスを通じてこれらの値にアクセスできます（例: from kabusys.config import settings; settings.jquants_refresh_token）。

---

## トラブルシューティング（よくある問題）

- OpenAI / J-Quants のキーが見つからない
  - score_news / score_regime / jquants_client.get_id_token はキーが未設定だと ValueError を送出します。環境変数を確認してください。

- DuckDB テーブルがない
  - ETL / save_* 系は既定のテーブルスキーマを前提とします。運用ではスキーマ初期化スクリプトを用意しておくことを推奨します。監査スキーマは init_audit_db で作成できます。

- RSS フィード取得で SSRF やプライベートアドレス検出
  - news_collector はリダイレクト先やホストがプライベートアドレスの場合にアクセスを拒否します（安全的挙動）。外部公開 RSS のみを指定してください。

- レート制限 / ネットワークエラー
  - J-Quants クライアントはレート制御とリトライを行いますが、429 などで遅延が発生します。ログを確認してリトライ状況を把握してください。

---

## 開発／テストのヒント

- config.py はプロジェクトルート（.git または pyproject.toml）を起点に .env/.env.local を自動ロードします。テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを抑止できます。
- ai モジュール内の _call_openai_api は unittest.mock.patch() で差し替え可能に実装されています。テストで API 呼び出しをモックするために便利です。
- news_collector._urlopen / jquants_client._request 等の低レイヤーもテスト用にモックしやすく設計されています。

---

ライセンスや貢献方法、CI 設定、詳細なスキーマ定義やマイグレーション手順はプロジェクトのルートにある別ドキュメント（例: DataPlatform.md, StrategyModel.md）に従ってください。

何か特定の機能の使い方（例: ETL のカスタム引数、監査スキーマのカスタマイズ、OpenAI プロンプトの調整）についてさらに詳しく知りたい場合は教えてください。