# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
このリポジトリはデータ取得（J-Quants）、ETL、データ品質チェック、ニュースの自然言語処理（LLM を用いたセンチメント評価）、市場レジーム判定、監査ログ（発注→約定のトレーサビリティ）などを一貫して提供します。

主な設計方針
- バックテストでのルックアヘッドバイアスを避ける（日時参照やデータ取得範囲に注意）
- DuckDB を用いたオンディスク/インメモリのデータ管理
- J-Quants API のレート制御・リトライ・トークン自動リフレッシュ対応
- OpenAI（gpt-4o-mini 等）を利用した JSON Mode による堅牢な NLP 呼び出し
- 冪等性のある DB 書き込み（ON CONFLICT / DELETE→INSERT 等）
- フェイルセーフ（API失敗時はスキップまたは中立値で継続）

---

## 機能一覧

- データ取得
  - J-Quants API クライアント（株価日足 / 財務 / 上場銘柄 / 市場カレンダー）
  - RSS ベースのニュース収集（SSRF 対策、トラッキングパラメータ除去）
- ETL パイプライン
  - 差分取得、バックフィル、保存（DuckDB）、品質チェックの一括実行
  - run_daily_etl で日次パイプラインを実行可能
- データ品質チェック
  - 欠損、重複、スパイク（急変）、将来日付／非営業日の検出
- ニュース NLP
  - 銘柄ごとのニュースをまとめて LLM に投げ、センチメント（ai_scores）を生成
  - レート制限/429/ネットワーク/5xx に対するリトライとバリデーション
- 市場レジーム判定
  - ETF (1321) の 200 日 MA 乖離とマクロニュース LLM スコアの重み付けで日次レジーム判定
- カレンダー管理
  - JPX マーケットカレンダー取得・営業日判定・前後営業日取得
- 監査ログ（Audit）
  - signal_events / order_requests / executions といった監査テーブルの初期化・管理
- リサーチ支援
  - モメンタム・バリュー・ボラティリティ等のファクター計算、将来リターン、IC 計算、Z スコア正規化など

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈の | 演算子等を使用）
- git が利用可能

1. リポジトリをクローン
   ```bash
   git clone <this-repo-url>
   cd <repo>
   ```

2. 仮想環境を作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate    # macOS / Linux
   .venv\Scripts\activate.bat   # Windows
   ```

3. 必要パッケージをインストール  
   （このコードベースで利用している主なライブラリ）
   ```bash
   pip install duckdb openai defusedxml
   ```
   - 他に logging 等は標準ライブラリを使用しています。
   - プロジェクト化されている場合は `pip install -e .` で editable install してください。

4. 環境変数設定（.env）
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - サンプル（.env）:
     ```
     # J-Quants
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

     # OpenAI（news_nlp / regime_detector が使用）
     OPENAI_API_KEY=your_openai_api_key

     # kabu API（注文実行等がある場合）
     KABU_API_PASSWORD=your_kabu_password
     KABU_API_BASE_URL=http://localhost:18080/kabusapi

     # ローカル DB パス等
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db

     # 環境モード: development | paper_trading | live
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - .env のパースはシェル風（`export KEY=val` / クォート / コメント）に対応しています。

5. データディレクトリ作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

---

## 使い方（主な API と実行例）

以下は Python REPL やスクリプト内での利用例です。各関数は DuckDB 接続（duckdb.connect）を受け取ります。

- 設定読み取り
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)  # Path オブジェクト
  ```

- DuckDB 接続
  ```python
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- ETL（日次パイプライン）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  # target_date を None にすると今日が使われます
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- 個別 ETL ジョブ
  ```python
  from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
  run_prices_etl(conn, target_date=date(2026,3,20))
  ```

- ニュースセンチメント（ai_scores への書込み）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  count = score_news(conn, target_date=date(2026,3,20))
  print(f"scored {count} codes")
  ```
  - OpenAI API キーを明示的に渡すことも可能: `score_news(conn, date, api_key="...")`

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査ログの初期化（別 DB で監査用に分ける場合）
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  # テーブルが作成され TimeZone が UTC に設定されます
  ```

- ファクター計算（Research）
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  momentum = calc_momentum(conn, date(2026,3,20))
  volatility = calc_volatility(conn, date(2026,3,20))
  ```

- カレンダー管理ユーティリティ
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  from datetime import date

  is_trading_day(conn, date(2026,3,20))
  next_trading_day(conn, date(2026,3,20))
  ```

注意点
- OpenAI を呼び出す機能は API キー（環境変数 OPENAI_API_KEY または関数引数）を必要とします。
- J-Quants へのリクエストは内部でレート制御・リトライを行います。JQUANTS_REFRESH_TOKEN を設定してください。
- News/NLP モジュールは LLM の応答を厳密な JSON として期待しており、レスポンスパースに失敗した場合は安全側でスキップまたは中立値を採ります。

---

## ディレクトリ構成

（src/kabusys 以下の主なファイルと説明）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定の読み込みとバリデーション（自動 .env ロード機能あり）
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュース記事を集約し OpenAI で銘柄ごとのセンチメントを算出、ai_scores に書き込み
    - regime_detector.py
      - ETF(1321) の MA200 乖離とマクロニュース LLM スコアを組合せて market_regime を更新
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント、fetch/save 関数（差分・ページネーション・リトライ・レート制御）
    - pipeline.py
      - ETL パイプラインと run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl 等
    - etl.py
      - ETLResult の公開エイリアス
    - news_collector.py
      - RSS フィード取得と raw_news への保存ロジック（SSRF 対策・XML 安全）
    - quality.py
      - データ品質チェック（欠損・重複・スパイク・日付不整合）
    - calendar_management.py
      - 市場カレンダー取得・営業日判定・next/prev/get_trading_days 等
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - audit.py
      - 監査ログ（signal_events / order_requests / executions）DDL と初期化ヘルパー
  - research/
    - __init__.py
    - factor_research.py
      - モメンタム / バリュー / ボラティリティ等のファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリー等
  - (その他)
    - strategy, execution, monitoring 等のパッケージ名が __all__ に含まれますが、実装は本スニペット中に含まれていません（プロジェクト全体で別ファイルがあるか確認してください）。

---

## 実運用上の注意・運用ヒント

- 環境モード:
  - settings.env は "development" / "paper_trading" / "live" のいずれかを指定します。live では特に注意を。
- 自動 .env ロード:
  - デフォルトでプロジェクトルート（.git または pyproject.toml を基準）にある .env / .env.local を読み込みます。無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- ロギング:
  - settings.log_level によりログレベルを制御します（DEBUG, INFO, ...）。
- セキュリティ:
  - news_collector は SSRF/ XML Bomb 対策を組み込んでいますが、運用環境でのネットワーク制限・WAF 等の併用を推奨します。
- テスト:
  - OpenAI やネットワーク呼び出しはモック可能な設計（内部の _call_openai_api などを patch）になっています。ユニットテストでは外部呼び出しをモックしてください。

---

もし README に追加したい内容（例: CI の設定、具体的な .env.example、デプロイ手順、サンプルワークフロー等）があれば教えてください。必要に応じて実行コマンドやサンプルスクリプトを追記します。