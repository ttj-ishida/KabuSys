# KabuSys

日本株向けの自動売買・データ基盤ライブラリ群です。  
ETL（J-Quants からの差分取得）、ニュース収集・NLP（OpenAI を利用したセンチメント解析）、ファクター計算、監査ログ（トレーサビリティ）、マーケットカレンダー管理などを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム／リサーチ基盤のための共通ユーティリティ群を提供します。主な役割は以下です。

- J-Quants API を利用した株価・財務・上場情報・カレンダーの差分 ETL
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI を用いたニュースセンチメント（銘柄別 ai_score / マクロセンチメント）
- 市場レジーム判定（ETF MA と LLM の合成）
- ファクター計算（Momentum / Value / Volatility 等）と研究用ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- 環境変数管理（.env 自動読み込み / オーバーライド制御）

設計上のポイント:
- ルックアヘッドバイアス対策（内部で date.today() を直接参照しない関数設計）
- 冪等性（DB 保存は INSERT … ON CONFLICT / DELETE+INSERT で整合を保つ）
- フェイルセーフ（外部 API 失敗時は部分スキップや安全側の既定値で継続）
- DuckDB を主要なオンディスク DB として利用

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch/save の実装、レート制御、トークン自動リフレッシュ）
  - market_calendar 管理・営業日判定ユーティリティ
  - news_collector（RSS 取得・前処理・SSRF 対策）
  - quality（データ品質チェック）
  - audit（監査ログテーブル作成・初期化ユーティリティ）
  - stats（z-score 正規化など）
- ai/
  - news_nlp.score_news（銘柄別ニュースセンチメントを ai_scores テーブルへ書込）
  - regime_detector.score_regime（ETF MA と LLM による市場レジーム判定）
- research/
  - factor_research（momentum / value / volatility 等のファクター計算）
  - feature_exploration（forward returns, IC, summary, rank 等）
- config.py
  - .env 自動ロード（プロジェクトルート判定）と Settings オブジェクト（環境変数アクセス）

---

## セットアップ手順

前提
- Python 3.10 以上（typing の | や型注釈を使用しているため）
- Git（プロジェクトルート判定に .git を使用）

1. リポジトリをクローン / 取得

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -U pip
   - 主要依存（例）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトで requirements.txt / pyproject.toml があればそちらを利用してください）

4. 環境変数設定
   - プロジェクトルートの `.env` と `.env.local`（任意）に環境変数を設定できます。自動ロード順は:
     1. OS 環境変数（優先）
     2. .env.local（存在すれば上書き）
     3. .env

   - 自動ロードを無効化したいテスト等では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   - 最低限必要な環境変数（機能により必須/任意）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ETL）
     - OPENAI_API_KEY : OpenAI を使う場合（score_news/score_regime, もしくは関数に api_key を渡す）
     - KABU_API_PASSWORD : kabu ステーション API（約定等を利用する場合）
     - KABU_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID : 通知を行う場合
     - DUCKDB_PATH : DuckDB の保存先（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH : 監視用 SQLite（デフォルト: data/monitoring.db）
     - KABUSYS_ENV : development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL : DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）

   - サンプル .env（簡易例）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

5. 初期 DB 準備（監査DB など）
   - 監査 DB 初期化例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - ETL 用の DuckDB はデフォルトで `data/kabusys.duckdb` を参照します（settings.duckdb_path）。

---

## 使い方（主なユースケース）

以下はライブラリ内の関数を直接利用する Python 例です。スクリプトやジョブから呼び出して使います。

1. DuckDB 接続を作成して日次 ETL を実行する
   ```python
   import duckdb
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl

   conn = duckdb.connect(str("data/kabusys.duckdb"))
   result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(result.to_dict())
   ```

2. ニュースのセンチメント（銘柄別）を計算して ai_scores に書き込む
   ```python
   import duckdb
   from datetime import date
   from kabusys.ai.news_nlp import score_news

   conn = duckdb.connect("data/kabusys.duckdb")
   written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None で環境変数 OPENAI_API_KEY を利用
   print(f"wrote {written} scores")
   ```

3. 市場レジーム判定（ETF 1321 の MA とマクロ記事センチメントの合成）
   ```python
   import duckdb
   from datetime import date
   from kabusys.ai.regime_detector import score_regime

   conn = duckdb.connect("data/kabusys.duckdb")
   score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY 環境変数を使用
   ```

4. 監査スキーマ初期化（既存接続へ追加）
   ```python
   import duckdb
   from kabusys.data.audit import init_audit_schema

   conn = duckdb.connect("data/kabusys.duckdb")
   init_audit_schema(conn, transactional=True)
   ```

5. ファクター計算 / リサーチ用ユーティリティ
   ```python
   from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
   from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

   # conn と target_date を用意してそれぞれ呼ぶ
   ```

6. 設定・環境変数の読み方
   ```python
   from kabusys.config import settings
   print(settings.duckdb_path, settings.is_live, settings.log_level)
   ```

注意点:
- OpenAI 呼び出しはモデル gpt-4o-mini を想定し、JSON mode（response_format）で厳密な JSON を期待します。API エラー時はフェイルセーフとしてスコア 0.0 などの既定値で継続する設計です。
- J-Quants API 呼び出しはモジュールレベルのレートリミッタを採用しています。
- DuckDB の executemany で空リストを渡せない（互換性問題）箇所があるため、関数内でチェック済みです。

---

## ディレクトリ構成

以下は主要なファイル/パッケージ構成（src/kabusys 以下の抜粋）です。

- src/
  - kabusys/
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
      - pipeline.py
      - etl.py
      - audit.py
      - jquants_client.py
      - ...
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
      - ...
    - research/
    - monitoring/ (モニタリング関連モジュールは __all__ に含まれる想定)
    - execution/ (発注関連モジュールは __all__ に含まれる想定)

（実際のリポジトリでは上記に加えて tests、docs、pyproject.toml / setup.cfg 等がある想定）

---

## 開発・運用メモ

- .env 自動ロード:
  - config.py はプロジェクトルート（.git または pyproject.toml を探索）を起点に `.env` と `.env.local` を読み込みます。OS 環境変数が優先され、`.env.local` が `.env` を上書きできます。
  - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト用）。

- テスト容易性:
  - OpenAI 呼び出しやネットワーク I/O 部分は関数レベルで差し替え可能（テスト用に patch しやすい設計）。
  - news_collector._urlopen や ai モジュール中の _call_openai_api 等を mocking してテストできます。

- ロギング:
  - settings.log_level を参照してアプリ側で logging.basicConfig() 等を設定してください。

- セキュリティ:
  - news_collector は SSRF や XML 攻撃対策（defusedxml）・レスポンスサイズ制限・トラッキング除去等を実施しています。
  - J-Quants トークンは .env で管理し、不要な露出を避けてください。

---

## よくある Q&A

Q: OpenAI のキーがないと関数はどうなる？  
A: score_news / score_regime は api_key 引数が None の場合に環境変数 OPENAI_API_KEY を参照し、両方未設定だと ValueError を送出します。ただし設計上 API エラーやパースエラー時は 0.0 を返すなどフェイルセーフが組まれています。

Q: DuckDB が無いデータベースでも動きますか？  
A: 現状は DuckDB を主要な永続ストレージとして想定しています。軽い解析やテストではインメモリ DuckDB(":memory:") を使えます。

Q: ETL の差分更新はどう管理されますか？  
A: run_*_etl 系はテーブル内の最終日付を参照して差分取得します。バックフィル日数を与えることで直近数日の再取得で API 側の修正を吸収します。

---

必要に応じて README を拡張して、具体的なデプロイ手順（Systemd / Airflow / Cron ジョブ例）、CI / CD、詳細な環境変数ドキュメント、サンプル .env.example を追加できます。どの情報を追記したいか教えてください。