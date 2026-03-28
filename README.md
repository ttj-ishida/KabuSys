KabuSys — 日本株自動売買プラットフォーム (README)
======================================

概要
----
KabuSys は日本株向けのデータプラットフォームと研究／自動売買基盤のライブラリ群です。  
主に以下の機能を組み合わせて、データ取得（ETL）→ 品質チェック → 特徴量計算 → ニュース/マクロの NLP 評価 → 戦略評価 → 監査（オーダー／約定ログ）といったワークフローを実現します。

目的:
- J-Quants API を用いた株価・財務・カレンダーの差分 ETL
- RSS ニュース収集と OpenAI を使った銘柄別/マクロセンチメント評価
- DuckDB を中心としたオフラインデータ管理と品質チェック
- 研究用ファクター計算（モメンタム／バリュー／ボラティリティ等）
- 発注フローの監査テーブル（トレーサビリティ）管理

主要な設計方針:
- ルックアヘッドバイアス回避（API 呼び出し・日付参照の設計に配慮）
- 冪等性を意識した DB 保存（ON CONFLICT / upsert）
- フェイルセーフ（外部 API 失敗時は局所的にフォールバック）
- DuckDB を利用した軽量で高速なクエリ基盤

主な機能一覧
----------------
- 環境変数 / .env 自動読み込みと設定管理（kabusys.config）
- J-Quants API クライアント（取得・保存・トークン管理／レート制御）
  - 株価日足、財務、マーケットカレンダー、上場銘柄情報等
- ETL パイプライン（差分取得、バックフィル、品質チェック）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS → raw_news、SSRF / Gzip / トラッキング除去対策）
- ニュース NLP（OpenAI を用いた銘柄別センチメント、バッチ処理）
  - score_news（銘柄別 ai_scores へ書込）
- マクロレジーム判定（ETF の MA200乖離 + マクロニュース LLM）
  - score_regime（market_regime テーブルへ書込）
- 研究用ファクター計算（momentum, value, volatility 等）
  - calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, zscore_normalize
- 監査ログ（signal_events / order_requests / executions）の初期化ユーティリティ
  - init_audit_schema / init_audit_db

セットアップ手順
----------------

前提
- Python 3.10 以上（型注釈で | 演算子などを使用）
- DuckDB が動作する環境
- OpenAI API キー（ニュース/マクロ NLP を使う場合）
- J-Quants リフレッシュトークン（データ ETL を行う場合）

1. リポジトリ／パッケージをクローン & インストール
   - 編集・開発する場合:
     ```
     git clone <repo-url>
     cd <repo-root>
     pip install -e .
     ```
   - 依存パッケージ（最低限の例）:
     ```
     pip install duckdb openai defusedxml
     ```
     ※ 実際のプロジェクトでは requirements.txt / poetry 等で依存管理してください。

2. 環境変数 / .env
   - プロジェクトルートに .env を置くと自動で読み込まれます（優先度: OS 環境 > .env.local > .env）。  
   - 自動ロードを無効化したい場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API パスワード（発注統合する場合）
     - SLACK_BOT_TOKEN: Slack 通知等で使用するトークン
     - SLACK_CHANNEL_ID: 通知先チャンネル ID
     - OPENAI_API_KEY: OpenAI を使う場合（score_news / score_regime）
   - 任意 / デフォルト値あり:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG/INFO/...
     - KABU_API_BASE_URL: kabu API のベース URL（default: http://localhost:18080/kabusapi）
     - DUCKDB_PATH: デフォルト data/kabusys.duckdb
     - SQLITE_PATH: 監視用 SQLite のパス（default: data/monitoring.db）

   例 (.env.example):
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

3. DuckDB データベースの準備
   - デフォルトでは DUCKDB_PATH (data/kabusys.duckdb) を使用します。ファイル/ディレクトリは自動作成されます（一部初期化関数で親ディレクトリを作成します）。
   - 監査ログ専用 DB を別に用意する場合:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")  # 監査用 DB を初期化して接続を返す
     ```

使い方（基本例）
----------------

Python API を直接利用する際の簡単な例を示します。各関数は DuckDB の接続（duckdb.connect(...) が返す接続）を受け取ります。

1. DuckDB 接続を用意
   ```python
   import duckdb
   conn = duckdb.connect("data/kabusys.duckdb")
   ```

2. 日次 ETL を実行（J-Quants からデータ取得 → 保存 → 品質チェック）
   ```python
   from kabusys.data.pipeline import run_daily_etl
   from datetime import date

   result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(result.to_dict())
   ```

3. ニュースセンチメントを計算して ai_scores に書き込む
   - OpenAI API キーは環境変数 OPENAI_API_KEY、または api_key 引数で渡せます。
   ```python
   from kabusys.ai.news_nlp import score_news
   from datetime import date

   written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # env OPENAI_API_KEY を使用
   print(f"書込銘柄数: {written}")
   ```

4. マクロレジーム判定
   ```python
   from kabusys.ai.regime_detector import score_regime
   from datetime import date

   score_regime(conn, target_date=date(2026,3,20))
   ```

5. 研究用ファクター計算例
   ```python
   from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
   from datetime import date

   mom = calc_momentum(conn, date(2026,3,20))
   vol = calc_volatility(conn, date(2026,3,20))
   val = calc_value(conn, date(2026,3,20))
   ```

6. 監査テーブル初期化
   ```python
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn, transactional=True)
   ```

主要モジュール / ディレクトリ構成
------------------------------
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数/設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP / OpenAI 呼び出し / ai_scores 書込
    - regime_detector.py           — マクロ + MA200 を使った市場レジーム判定
  - data/
    - __init__.py
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - jquants_client.py            — J-Quants API クライアント（fetch / save）
    - calendar_management.py       — 市場カレンダーの管理（is_trading_day 等）
    - news_collector.py            — RSS ニュース収集・前処理・保存
    - quality.py                   — データ品質チェック
    - stats.py                     — zscore_normalize 等
    - audit.py                     — 監査テーブル DDL と初期化
    - etl.py                       — ETL ユーティリティの公開（ETLResult）
  - research/
    - __init__.py
    - factor_research.py           — momentum/value/volatility 等
    - feature_exploration.py       — forward returns / IC / stats summary
  - ai, research, data の詳細機能は docstring に設計方針・処理フローの説明あり

運用上の注意
------------
- OpenAI の呼び出しは API エラー・レート制限に対してリトライやフォールバックが組まれているものの、コストと応答時間を考慮してください（バッチサイズやモデル選択の調整を推奨）。
- J-Quants のレート制限（例: 120 req/min）に合わせた RateLimiter 実装が含まれていますが、運用負荷によっては追加のスロットリングが必要かもしれません。
- DuckDB のバージョン差異により executemany の挙動等で影響を受けることがあるため、運用時は使用する DuckDB バージョンを固定してください。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を起点に行います。CI やテスト環境で自動ロードをオフにするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

開発・テスト
-------------
- 単体テストやモックについては、OpenAI 呼び出しや外部ネットワーク関連の関数は patch/mocking しやすい設計（内部 _call_openai_api を差し替え可能）になっています。
- news_collector の外部 HTTP 呼び出しや jquants_client の HTTP はモックしてテストを作成してください。

最後に
------
この README はコード内の docstring と設計コメントに基づき作成しています。細かな使用方法や追加のユーティリティは各モジュールの docstring を参照してください（例: kabusys/data/pipeline.py, kabusys/ai/news_nlp.py）。必要であればサンプルスクリプトや運用手順（cron/ジョブ定義、監視・アラートの設定）を別ファイルで追加できます。