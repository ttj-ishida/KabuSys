# KabuSys

日本株向け自動売買 / データ基盤ライブラリ群。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI）、リサーチ用ファクター計算、監査ログ（発注→約定トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株のデータ取得・品質管理・特徴量計算・AI によるニュースセンチメント評価・市場レジーム判定・監査ログ生成など、自動売買システムを構成する主要コンポーネントをまとめた Python パッケージです。  
設計上の特徴として、バックテストでのルックアヘッドバイアスを避ける設計、DuckDB を用いたローカル DB 管理、外部 API 呼び出しの堅牢なリトライ/レート制御、冪等性重視の保存ロジックなどが盛り込まれています。

---

## 主な機能一覧

- データ ETL
  - J-Quants からの株価日足（OHLCV）、財務データ、JPX カレンダー取得（差分更新・バックフィル）
  - 品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集 / 前処理
  - RSS フィード収集（SSRF 対策、トラッキングパラメータ除去、前処理）
- AI ベース NLP
  - 銘柄別ニュースセンチメント算出（OpenAI gpt-4o-mini、JSON Mode）
  - マクロニュース + ETF MA 乖離から市場レジーム判定（bull/neutral/bear）
- リサーチ / ファクター
  - Momentum / Value / Volatility 等のファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリー
  - Z-score 正規化ユーティリティ
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブルによる完全トレース
  - 監査スキーマ初期化ユーティリティ
- 設定管理
  - .env / .env.local / 環境変数からの設定読み込み（自動ロード、無効化オプションあり）

---

## 動作要件

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - openai (OpenAI の新 SDK)
  - defusedxml
- ネットワークアクセス（J-Quants API, RSS ソース, OpenAI API）

（実際の依存関係はプロジェクトの pyproject.toml / requirements ファイルを参照してください）

---

## セットアップ手順

1. リポジトリをクローン・チェックアウト

2. 仮想環境を作成して有効化（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール（例）
   ```bash
   pip install duckdb openai defusedxml
   ```

4. 環境変数 / .env を用意する  
   プロジェクトルート（.git か pyproject.toml があるディレクトリ）に `.env` および任意で `.env.local` を作成すると、自動で読み込まれます。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必要となる主な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: 通知用 Slack 設定（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / regime で使用）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
   - PID_FILE_PATH: 実行プロセスの PID ファイルパス
   - KABUSYS_ENV: 開発環境設定（development / paper_trading / live）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/...）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（クイックスタート）

以下はパッケージ API の簡単な使い方例です。実行前に環境変数を正しく設定してください。

- DuckDB 接続準備（例）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行（株価・財務・カレンダー取得・品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別）をスコアして ai_scores に保存
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を設定する
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print("written:", n_written)
  ```

- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュース）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ（audit）スキーマ初期化
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")  # 必要に応じてパスを変更
  ```

- ファクター計算（例: モメンタム）
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  records = calc_momentum(conn, target_date=date(2026,3,20))
  ```

- マーケットカレンダー関連ユーティリティ
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  from datetime import date

  is_trade = is_trading_day(conn, date(2026,3,20))
  nxt = next_trading_day(conn, date(2026,3,20))
  ```

注意:
- score_news / score_regime は OpenAI API を呼び出します。api_key を関数引数で渡すか、環境変数 OPENAI_API_KEY を設定してください。API 呼び出しは冗長なリトライやフェイルセーフ（失敗時はスコアを 0 として継続等）を備えています。
- ETL は J-Quants API を呼び出します。J-Quants の認証情報（JQUANTS_REFRESH_TOKEN）が必要です。

---

## 設定の自動読み込み

- 起動時、以下の優先順位で読み込みされます:
  1. OS 環境変数
  2. .env.local（存在すれば上書き）
  3. .env

- 自動ロードを無効にするには:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

- 必須設定が未設定の場合、Settings のプロパティアクセスで ValueError が発生します（例: settings.jquants_refresh_token）。

---

## ディレクトリ構成

主要なモジュール構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py          # 銘柄ニュースセンチメント算出
    - regime_detector.py   # マクロ + ETF MA で市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py
    - pipeline.py          # ETL パイプライン（run_daily_etl 等）
    - etl.py               # ETLResult 再エクスポート
    - stats.py             # zscore_normalize 等
    - quality.py           # データ品質チェック
    - audit.py             # 監査ログスキーマ / 初期化
    - jquants_client.py    # J-Quants API クライアント / 保存処理
    - news_collector.py    # RSS 取得 & 前処理
  - research/
    - __init__.py
    - factor_research.py   # Momentum / Value / Volatility 等
    - feature_exploration.py   # 将来リターン / IC / rank / summary
  - ai/ (上記)
  - その他: strategy/ execution/ monitoring パッケージは __all__ に含まれる（実装は別ファイル群に存在）

（プロジェクト全体のツリーは実際のリポジトリを参照してください）

---

## 開発・テスト時の注意

- DuckDB を使ったユニットテストは ":memory:" 接続や一時ファイルを利用して実行できます。
- OpenAI / J-Quants の外部呼び出しはモック化してテストしてください。レート制御やリトライロジックがあるため、実ネットワーク呼び出しはテストの安定性を損ないます。
- 環境による自動 .env 読み込みを無効化したいテストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- news_collector には SSRF 対策やレスポンスサイズ制限等の保護実装が含まれていますが、運用時は RSS ソースの信頼性を監視してください。

---

## おわりに

この README はコードベースの主要コンポーネントと基本的な利用方法をまとめたものです。各モジュールには詳細な docstring が埋め込まれており、内部設計や振る舞い（例: リトライ条件、フェイルセーフ、ルックアヘッドバイアス対策など）が明記されています。実運用では、設定ファイルの管理、API キーの安全な保管、ログ監視、バックテストでのデータ整合性確認を必ず行ってください。