# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP による銘柄センチメント、ファクター計算・リサーチユーティリティ、監査ログ（発注・約定トレース）などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株のアルゴリズムトレーディング／データ基盤向けに設計されたモジュール群です。主な目的は以下です。

- J-Quants API を用いた市場データ（株価・財務・カレンダー）の差分取得と DuckDB への永続化（ETL）
- RSS ニュース収集と前処理（SSRF 対策、トラッキングパラメータ除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（銘柄ごと、マクロ判定）
- ファクター計算（モメンタム・バリュー・ボラティリティ等）および研究用ユーティリティ（将来リターン、IC、統計）
- 監査ログ（signal → order_request → executions）テーブルの初期化・管理
- データ品質チェック（欠損・スパイク・重複・日付不整合検出）

設計上の特徴:
- DuckDB を用いた軽量で高速な分析向けストレージ
- Look-ahead bias を避ける実装（内部で date.today()/datetime.today() を直接参照しない設計の箇所が多くあります）
- 冪等性を考慮した保存ロジック（ON CONFLICT / INSERT/DELETE ロジック）
- 外部 API 呼び出しにはリトライ・レート制限・フェイルセーフを備える

---

## 機能一覧（主な箇所）

- kabusys.config: .env / 環境変数読み込み・設定管理
- kabusys.data
  - etl / pipeline: 日次 ETL（run_daily_etl）・個別 ETL ジョブ（prices/financials/calendar）
  - jquants_client: J-Quants API クライアント（認証、取得、DuckDB 保存関数）
  - news_collector: RSS 取得・前処理・raw_news 保存補助
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management: JPX カレンダー管理・営業日判定ユーティリティ
  - audit: 監査ログ（signal/order_requests/executions）テーブル定義・初期化
  - stats: zscore 正規化などの共通統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: 銘柄別ニュースセンチメントを ai_scores テーブルへ書き込む
  - regime_detector.score_regime: ETF 1321 の MA とマクロニュース（LLM）を合成して市場レジーム判定を行う
- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

（strategy / execution / monitoring パッケージはパブリック API として __all__ に含まれますが、このリポジトリの抜粋では詳細実装が含まれていません。）

---

## 動作環境 / 依存

- Python >= 3.10（PEP 604 の型記法や構文を使用）
- 推奨パッケージ（主要依存、最新バージョンを使用してください）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- ネットワークアクセス: J-Quants API, RSS ソース, OpenAI API へアクセス可能であること

（実際のプロジェクトでは requirements.txt / pyproject.toml を用意して下さい。）

---

## セットアップ手順

1. Python 仮想環境を作成・有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール（例）
   ```
   pip install duckdb openai defusedxml
   ```

3. 環境変数を設定
   - .env ファイル（プロジェクトルート）に設定するか、OS 環境変数として設定します。
   - 自動読み込みの順序: OS環境変数 > .env.local > .env
   - 自動読み込みを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

   推奨/使用される主要な環境変数（最低限）:
   - JQUANTS_REFRESH_TOKEN   : J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY          : OpenAI API キー（score_news / regime_detector で使用）
   - KABU_API_PASSWORD       : kabu ステーション API パスワード（発注系を使う場合）
   - KABU_API_BASE_URL       : kabu API のベース URL（省略時デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH             : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH             : 監視用 SQLite（デフォルト: data/monitoring.db）
   - その他監視閾値や PID ファイルなど（README 内の config モジュール参照）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   ```

4. データベース初期化（監査ログを使う場合）
   - 監査テーブルを初期化する例:
     ```python
     from kabusys.data.audit import init_audit_db
     from kabusys.config import settings

     conn = init_audit_db(settings.duckdb_path)  # ファイルがなければ作成されます
     ```

---

## 使い方（基本例）

以下はライブラリの代表的な利用例です。実運用ではログ設定や例外処理を適切に行ってください。

- DuckDB 接続の準備（設定のパスを使う）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行（run_daily_etl）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントをスコアリングして ai_scores に書き込む
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # api_key を省略すると環境変数 OPENAI_API_KEY を参照します
  written_count = score_news(conn, target_date=date(2026,3,20))
  print(f"wrote {written_count} scores")
  ```

- 市場レジーム判定（regime_detector）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026,3,20))
  ```

- ファクター計算（research）
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  target = date(2026,3,20)
  mom = calc_momentum(conn, target)
  val = calc_value(conn, target)
  vol = calc_volatility(conn, target)
  ```

- カレンダー・営業日ユーティリティ
  ```python
  from datetime import date
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  d = date(2026,3,20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

- データ品質チェック
  ```python
  from kabusys.data.quality import run_all_checks

  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i)
  ```

---

## 環境変数の挙動（重要）

- 自動読み込み:
  - モジュール import 時にプロジェクトルート（.git または pyproject.toml を探索）を基準に .env/.env.local を自動ロードします。
  - 優先順位: OS 環境変数 > .env.local > .env
  - OS 環境変数は保護され、.env による上書きを防ぎます（.env.local は override=True で上書き可能）。
- 自動読み込みを無効化する:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると .env 自動ロードを無効化します（テスト向け）。

---

## ディレクトリ構成（抜粋）

以下はこのリポジトリ内の主要ファイル群（src/kabusys 以下）の抜粋です:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - calendar_management.py
    - pipeline.py
    - etl.py
    - jquants_client.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/__init__.py

各モジュールの概要は上記「機能一覧」を参照してください。README での抜粋以外にも詳細な docstring が各関数・モジュールに付与されています。

---

## 注意事項 / ベストプラクティス

- API キーやトークンは必ず安全に管理してください（.env を用いる場合はリポジトリにコミットしない）。
- ETL / LLM 呼び出しはコスト（API クレジット）とレート制限に注意して実行してください。
- DuckDB のスキーマ（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, market_regime など）は ETL/保存関数が期待する形に合わせる必要があります。プロジェクトのスキーマ初期化手順が別途ある場合はそれに従ってください。
- OpenAI の JSON mode でのレスポンスを前提としているため、モデル・API 仕様の変更に注意が必要です。レスポンスのパースは堅牢に実装していますが、将来の SDK 変更に備えてテスト／モックを用いた検証を推奨します。

---

## 開発・テスト

- 各種外部 API 呼び出し箇所（OpenAI、J-Quants、RSS）のネットワーク呼び出しはモック可能な設計にしています。ユニットテストではこれらを patch/mock してテストを行ってください。
- 環境変数の自動ロードはテストで邪魔になる場合があるため `KABUSYS_DISABLE_AUTO_ENV_LOAD` を利用できます。

---

必要であれば、README に以下を追加します：
- 具体的なスキーマ（DuckDB テーブル定義）の一覧と CREATE 文
- requirements.txt / pyproject.toml のサンプル
- より詳しい実行フロー（Cron / Airflow / Runner の例）
- strategy / execution / monitoring の実装ガイド

追加希望があれば教えてください。