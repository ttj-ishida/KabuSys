# KabuSys

日本株向けの自動売買・データプラットフォーム実装（ライブラリ）です。  
データ ETL、ニュース収集・NLP（LLM）によるセンチメント評価、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（トレーサビリティ）などの機能を含みます。

主な特徴
- J-Quants API からの差分取得および DuckDB への冪等保存（ETL パイプライン）
- RSS によるニュース収集と前処理（SSRF 対策・サイズ制限・トラッキング除去）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価（銘柄単位／マクロ）
- ETF とマクロニュースを統合した市場レジーム判定（bull / neutral / bear）
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と研究ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- 監査ログ用テーブル群の初期化／監査 DB（order/signals/executions 等）
- 自動で .env / .env.local を読み込む設定ローダ（プロジェクトルート検出）

以下はリポジトリ（コード）を利用・開発するための README です。

目次
- プロジェクト概要
- 機能一覧
- 前提・依存関係
- セットアップ手順
- 環境変数（主なキー）
- 使い方（簡易例）
- ディレクトリ構成 / 主なモジュール

---

## プロジェクト概要

KabuSys は日本株（JPX）向けのデータプラットフォームおよびリサーチ／自動売買支援ライブラリです。  
データ取得（J-Quants）、保存（DuckDB）、品質チェック、ニュース NLP（OpenAI）によるスコアリング、ファクター計算、監査ログなどを提供します。バックテスト・本番発注部分は別レイヤで実装しますが、本ライブラリはデータ基盤と戦略・研究の共通ユーティリティを提供します。

---

## 機能一覧

- 環境設定管理（.env / .env.local の自動ロード、Settings オブジェクト）
- J-Quants API クライアント
  - 日次株価（OHLCV）のページネーション取得
  - 財務データ取得
  - JPX マーケットカレンダー取得
  - 保存（DuckDB への冪等 INSERT / UPDATE）
- ETL パイプライン（run_daily_etl）
  - カレンダー / 株価 / 財務 の差分取得・保存
  - 品質チェックの実行（データの欠損・スパイク等）
- ニュース収集（RSS）と前処理（news_collector.fetch_rss, preprocess_text 等）
  - SSRF 対策・トラッキングパラメータ除去・サイズ制限
- ニュース NLP（OpenAI）
  - 銘柄ごとの ai_score を計算して ai_scores に保存する処理（score_news）
  - マクロ記事を用いた市場センチメント推定（regime_detector.score_regime）
- 研究ユーティリティ
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
  - zscore_normalize（クロスセクション正規化）
- データ品質チェック（quality.run_all_checks）
- マーケットカレンダー管理（is_trading_day, next_trading_day 等、calendar_update_job）
- 監査ログ（audit.init_audit_db / init_audit_schema）: signal_events / order_requests / executions の DDL とインデックス

---

## 前提・依存関係

必須（最低限）
- Python 3.10+
- duckdb
- openai (OpenAI の公式 Python SDK)
- defusedxml

テスト／追加機能で使用される（推奨）
- urllib / 標準ライブラリ群（requests は使用していません）
- その他、logging 等の標準モジュール

（実際の requirements.txt / pyproject.toml があればそちらを優先してください。）

---

## セットアップ手順

1. リポジトリをチェックアウト／クローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   - 最低限の例:
     ```
     pip install duckdb openai defusedxml
     ```
   - 開発用にパッケージや pyproject.toml があれば:
     ```
     pip install -e .
     ```

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml がある階層）を自動検出し、
     自動で .env → .env.local を読み込みます（優先度: OS 環境変数 > .env.local > .env）。
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. DuckDB・監査 DB 用ディレクトリの準備
   - デフォルトでは data/kabusys.duckdb を使用します（settings.duckdb_path）。
   - 監査用 DB 初期化はコードから行います（例は下記）。

---

## 環境変数（主なキー）

必須（使用する機能による）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（fetch API 用）
- OPENAI_API_KEY : OpenAI API を使う場合に必要（score_news / score_regime）
- KABU_API_PASSWORD : kabuステーション API を使う場合
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID : Slack 通知を使う場合

オプション / 設定
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 自動 .env ロードを無効化（値が存在すれば無効）
- KABUSYS_ENV : environment mode ("development" | "paper_trading" | "live")。既定 "development"
- LOG_LEVEL : "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"
- KABU_API_BASE_URL : kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : SQLite path（監視用、デフォルト: data/monitoring.db）

注意: Settings クラス経由で取得するため、コード中では settings.jquants_refresh_token などで参照します。必須項目が未設定だと ValueError を送出します。

---

## 使い方（簡易例）

以下は典型的な利用例です。必要に応じて import 文やパスを調整してください。

- DuckDB 接続準備
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントスコア（銘柄ごと）を生成する
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None -> env OPENAI_API_KEY を使用
  print(f"written scores: {written}")
  ```

- 市場レジーム（ETF 1321 の MA200 乖離 + マクロニュース）を算出する
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査用 DuckDB を初期化する（監査ログ向け DB）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions テーブルが作成されます
  ```

- RSS を取得する（ニュース収集の一部）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles[:5]:
      print(a["id"], a["datetime"], a["title"])
  ```
  ※ raw_news テーブルへ保存するユーティリティはプロジェクト内別実装（ETL での保存やカスタム処理）で行ってください。

- 研究用ファクター計算
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
  from datetime import date

  momentum = calc_momentum(conn, target_date=date(2026,3,20))
  volatility = calc_volatility(conn, target_date=date(2026,3,20))
  value = calc_value(conn, target_date=date(2026,3,20))
  ```

テストや開発時のヒント
- OpenAI API 呼び出しは内部で _call_openai_api を呼んでいます。ユニットテストではこの関数をモックして応答を差し替えることが想定されています。
- 自動 .env ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## ディレクトリ構成（主要ファイル）

下記は src/kabusys 配下の主要モジュールと役割の概略です。

- src/kabusys/__init__.py
  - パッケージ初期化、export 定義

- src/kabusys/config.py
  - 環境変数と Settings クラス、自動 .env ロードの実装

- src/kabusys/ai/
  - __init__.py
  - news_nlp.py : 銘柄単位ニュースセンチメント（score_news、calc_news_window 等）
  - regime_detector.py : 市場レジーム判定（score_regime）

- src/kabusys/data/
  - __init__.py
  - calendar_management.py : 市場カレンダー判定（is_trading_day, next_trading_day...）と calendar_update_job
  - etl.py : ETL の公開インターフェース（ETLResult の再エクスポート）
  - pipeline.py : ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - stats.py : zscore_normalize 等の統計ユーティリティ
  - quality.py : データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
  - audit.py : 監査ログ DDL / init_audit_schema / init_audit_db
  - jquants_client.py : J-Quants API クライアント + 保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）
  - news_collector.py : RSS 取得・前処理・SSRF 対策

- src/kabusys/research/
  - __init__.py
  - factor_research.py : calc_momentum / calc_value / calc_volatility
  - feature_exploration.py : calc_forward_returns / calc_ic / factor_summary / rank

その他
- 設定やサンプルファイル（.env.example など）はルートに置くことを想定（config._find_project_root が .git または pyproject.toml を探します）。

---

## 補足・設計上の注意点

- Look-ahead バイアス対策: 日付計算・データ取得は基本的に target_date を明示的に渡し、内部で datetime.today() / date.today() を不用意に参照しない設計になっています（一部 ETL のデフォルトで date.today() を使う箇所あり）。
- 冪等性: DuckDB へは ON CONFLICT 句で冪等保存を行い、再実行可能な ETL を目指しています。
- フェイルセーフ: LLM/API が失敗した場合はデフォルト値（例: macro_sentiment=0.0）で継続する実装が随所にあります。
- テスト容易性: OpenAI 呼び出しや外部ネットワーク呼び出しは差し替え（モック）しやすい設計です。
- 自動 .env ロード: プロジェクトルート基準で .env / .env.local を読み込み、OS 環境変数を上書きしない（ただし .env.local は override=True で上書き）仕組みです。テスト時に無効化可能。

---

## ライセンス・貢献

（リポジトリのライセンス情報や貢献手順があればここに追記してください）

---

README に掲載して欲しい追加情報（例: 実運用の注意点、CI ワークフロー、より詳しい API リファレンスなど）があれば教えてください。必要に応じて README を拡張します。