KabuSys — 日本株自動売買プラットフォーム
=================================

概要
----
KabuSys は日本株のデータ収集・ETL・品質チェック・ファクター算出・AIベースのニュースセンチメント評価・市場レジーム判定・監査ログ管理などを含む、研究／運用向けの自動売買基盤コンポーネント群です。主に DuckDB をデータストアとして想定し、J-Quants API から価格・財務・カレンダー等を取得して ETL を行い、AI（OpenAI）を用いたニュースのセンチメントや市場レジーム判定で研究・戦略化を支援します。

主な機能
--------
- データ取得／ETL
  - J-Quants から株価日足（OHLCV）、財務データ、JPX カレンダーを差分取得・保存（ページネーション・レート制御・再試行対応）
  - 差分更新、バックフィル、品質チェックの一貫実行（run_daily_etl）
- データ品質管理
  - 欠損、重複、未来日付、スパイク（前日比）などの検出（quality モジュール）
- ニュース収集
  - RSS フィード収集と前処理、raw_news / news_symbols への冪等保存（SSRF対策・サイズ制限・トラッキングパラメータ除去）
- AI（LLM）による解析
  - ニュースごとの銘柄センチメント算出（news_nlp.score_news）
  - マクロニュースとETF（1321）の200日MA乖離を組み合わせた市場レジーム判定（regime_detector.score_regime）
  - 両モジュールは OpenAI（gpt-4o-mini 等）を JSON Mode で利用し、リトライやフェイルセーフを備える
- 研究系ユーティリティ
  - ファクター計算（モメンタム・バリュー・ボラティリティ等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions などの監査テーブル定義と初期化ユーティリティ（init_audit_db / init_audit_schema）
- 設定管理
  - .env / 環境変数読み込みと Settings オブジェクト経由での安全な参照

動作要件（推奨）
---------------
- Python 3.10+
- 必要な Python パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
- インターネット接続（J-Quants API、OpenAI、RSS フィードなど）

セットアップ手順
----------------

1. リポジトリ取得
   - git clone してチェックアウトしてください。

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   ※ プロジェクトに requirements.txt / pyproject.toml があればそれを使ってください:
   - pip install -r requirements.txt
   - または: pip install -e . （パッケージ化されている場合）

4. 環境変数 / .env の準備
   - プロジェクトルートに .env または .env.local を置くと自動でロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能）。

   主要な環境変数（最低限設定が必要なもの）
   - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
   - KABU_API_PASSWORD=<kabu_station_api_password>        # kabuステーション周りで必要
   - SLACK_BOT_TOKEN=<slack_bot_token>
   - SLACK_CHANNEL_ID=<slack_channel_id>
   - OPENAI_API_KEY=<openai_api_key>                       # news_nlp / regime_detector 実行時に必要
   - DUCKDB_PATH=data/kabusys.duckdb                       # 省略時デフォルト
   - SQLITE_PATH=data/monitoring.db                        # 省略時デフォルト
   - KABUSYS_ENV=development|paper_trading|live            # デフォルト: development
   - LOG_LEVEL=INFO|DEBUG|...                              # デフォルト: INFO

   例（.env）
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

5. データベース初期化（監査用）
   - 監査テーブルを初期化するには Python コンソールから:
     ```
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")  # or ":memory:"
     ```
   - または既存の DuckDB 接続に対して init_audit_schema を呼ぶこともできます。

使い方（例）
------------

- DuckDB 接続を作成
  ```
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行（run_daily_etl）
  ```
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  # target_date を指定しない場合は今日が対象
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントのスコア化（OpenAI API キーが環境変数に設定されていること）
  ```
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  n = score_news(conn, target_date=date(2026,3,20))
  print(f"scored {n} codes")
  ```

- 市場レジーム判定
  ```
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026,3,20))
  ```

- ファクター計算（Research）
  ```
  from kabusys.research import calc_momentum, calc_value
  from datetime import date

  mom = calc_momentum(conn, target_date=date(2026,3,20))
  val = calc_value(conn, target_date=date(2026,3,20))
  ```

- ニュース収集（RSS）
  ```
  from kabusys.data.news_collector import fetch_rss

  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  ```

注意点・運用上の留意事項
-----------------------
- API キーやシークレットは .env / 環境変数で管理してください。誤ってリポジトリに含めないでください。
- OpenAI・J-Quants API 呼び出しにはレート制限／課金が伴います。開発・テスト時は小さいバッチや paper_trading 環境で試してください。
- LLM 呼び出しは外部サービス依存のため、失敗時はフェイルセーフ（スコアを 0.0 にフォールバック）する実装です。ログを確認してください。
- ETL 実行時は品質チェック結果（ETLResult.quality_issues）を監視し、重大な issue が検出された場合は手動確認を推奨します。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py — パッケージ定義（バージョン等）
- config.py — 環境変数・設定管理（Settings オブジェクト）
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメントスコアの生成（OpenAI）
  - regime_detector.py — ETF MA とマクロニュースを合成した市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch / save / auth / rate limit）
  - pipeline.py — 日次 ETL パイプライン（run_daily_etl 等）
  - etl.py — ETLResult の再エクスポート
  - news_collector.py — RSS 収集・前処理・保存ヘルパー
  - calendar_management.py — 市場カレンダー管理（営業日判定等）
  - quality.py — データ品質チェックモジュール
  - stats.py — 統計ユーティリティ（zscore_normalize 等）
  - audit.py — 監査ログテーブル定義・初期化
- research/
  - __init__.py
  - factor_research.py — Momentum/Value/Volatility 等のファクター計算
  - feature_exploration.py — 将来リターン、IC、統計サマリー等

API キー・設定一覧（Settings プロパティ）
-----------------------------------------
settings オブジェクトでアクセス可能な代表的な設定:
- settings.jquants_refresh_token
- settings.kabu_api_password
- settings.kabu_api_base_url
- settings.slack_bot_token
- settings.slack_channel_id
- settings.duckdb_path
- settings.sqlite_path
- settings.env (development / paper_trading / live)
- settings.log_level
- settings.is_live / is_paper / is_dev

テスト・デバッグ
----------------
- OpenAI や外部 API 呼び出しはテスト時にモックできます（各モジュール内で _call_openai_api などが分離されています）。
- 自動環境変数読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ライセンス・貢献
----------------
この README はコードベースの説明ドキュメントです。実際のライセンス表記や貢献ガイドライン（CONTRIBUTING.md）がある場合はリポジトリのルートを参照してください。

お問い合わせ
------------
不明点や実運用での導入支援が必要な場合は、リポジトリの issue やチーム内で共有してください。README の補足・改善提案も歓迎します。