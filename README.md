KabuSys
======

日本株向けのデータプラットフォーム & 自動売買補助ライブラリです。  
ETL（J-Quants → DuckDB）、ニュースセンチメント解析（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログなど、運用に必要な基盤機能をまとめて提供します。

主な特徴
--------
- ETL（J-Quants API 経由）
  - 日次株価（OHLCV）、財務データ、JPXカレンダーの差分取得と DuckDB への冪等保存
  - レートリミット・リトライ・トークン自動更新対応
- ニュース NLP（OpenAI）
  - RSS 収集・前処理（SSRF対策、トラッキング除去）
  - 銘柄単位のニュース統合センチメント（gpt-4o-mini / JSON Mode、バッチ・リトライ）
  - 市場マクロセンチメントを利用した市場レジーム判定
- 研究（Research）ユーティリティ
  - モメンタム・バリュー・ボラティリティ等のファクター計算
  - 将来リターン計算、IC（スピアマン）や統計サマリー
  - Z スコア正規化
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合などの自動検出
- 監査（Audit / Tracing）
  - signal → order_request → execution まで追跡可能な監査テーブル生成ユーティリティ
- 設計方針
  - ルックアヘッドバイアス回避（内部で datetime.today()/date.today() を不用意に参照しない）
  - 冪等性を重視（ON CONFLICT / UUID 等）
  - 外部依存は必要最小限（DuckDB、OpenAI、defusedxml 等）

必須（および主要）環境変数
-------------------------
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD      : kabuステーション API パスワード（必須）
- OPENAI_API_KEY         : OpenAI API キー（score_news / score_regime 実行時に必要）
- SLACK_BOT_TOKEN        : Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID       : Slack 通知チャンネル ID（必須）
- DUCKDB_PATH            : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH            : 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV            : 環境 ("development", "paper_trading", "live")（デフォルト "development"）
- LOG_LEVEL              : ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")（デフォルト "INFO"）

.env の自動読み込み
-------------------
パッケージ起点で .env / .env.local を自動で読み込みます（OS 環境変数より下位）。  
自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

セットアップ手順
---------------
前提: Python 3.10 以上、pip が利用可能であること（typing の | を使用しているため）。

1. リポジトリをクローン（またはソースを配置）
2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （開発用）pip install -e . などプロジェクトに合わせて
   - 実際の運用では requests 等の追加依存がある場合は適宜導入してください
4. .env を作成
   - .env.example（存在する場合）を参照して必須値を設定
   - 例:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=your_openai_api_key
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
5. データベースの準備
   - duckdb を使用するので、ETL 実行時に必要テーブルが自動作成されるか、スキーマ初期化関数（本ライブラリにスキーマ初期化がある場合）を実行してください。
   - 監査用 DB を個別に初期化する例は下記参照。

使い方（例）
------------

- 共通：DuckDB 接続作成
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行（J-Quants から差分取得して保存 + 品質チェック）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（単日・銘柄ごと）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY が環境変数に設定されていること
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込み銘柄数:", n_written)
  ```

- 市場レジーム判定（1321 MA200 とマクロニュース合成）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査テーブル初期化（監査専用 DB を作る）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions テーブルが作成されます
  ```

- 研究用ファクター計算
  ```python
  from datetime import date
  from kabusys.research import calc_momentum, calc_value, calc_volatility

  momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
  value = calc_value(conn, target_date=date(2026, 3, 20))
  volatility = calc_volatility(conn, target_date=date(2026, 3, 20))
  ```

- データ品質チェックを個別に実行
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i)
  ```

注意点 / 運用上のヒント
-----------------------
- OpenAI 呼び出しには API 制限やコストが発生します。テスト時は score_news / score_regime の _call_openai_api をモックして下さい（各モジュールで差し替え可能）。
- ETL は差分更新・バックフィルロジックを内蔵しています。スケジュール実行（cron / Airflow 等）で日次運用する想定です。
- market_calendar が未取得の場合は自動で曜日ベースのフォールバックが行われますが、正確な営業日判定のために calendar ETL を優先して実行してください。
- DuckDB の executemany に空リストを渡すと問題になるバージョンがあるため、コード中で空チェックを行っています。ライブラリ更新時は互換性に注意してください。
- KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかで設定してください。is_live/is_paper/is_dev により動作を分岐できます。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                        : 環境変数・設定管理（.env 自動ロード）
- ai/
  - __init__.py
  - news_nlp.py                     : ニュースセンチメント処理（score_news 等）
  - regime_detector.py              : 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py               : J-Quants API クライアント + DuckDB 保存ロジック
  - pipeline.py                     : ETL パイプライン（run_daily_etl 等）
  - etl.py                          : ETL インターフェース再エクスポート（ETLResult）
  - news_collector.py               : RSS 取得と前処理
  - calendar_management.py          : マーケットカレンダー管理（営業日判定等）
  - quality.py                      : データ品質チェック
  - stats.py                        : 統計ユーティリティ（zscore_normalize）
  - audit.py                        : 監査ログテーブル初期化ユーティリティ
- research/
  - __init__.py
  - factor_research.py              : momentum/value/volatility 等
  - feature_exploration.py          : 将来リターン・IC・統計サマリー
- monitoring/ (監視関連モジュールがここに入る想定)
- execution/ (発注/ブローカー連携モジュールがここに入る想定)
- strategy/ (戦略実装層がここに入る想定)

開発 / テスト
-------------
- OpenAI 呼び出しは外部 API なのでユニットテストでは _call_openai_api を patch/mocking してテストすることを推奨します（news_nlp と regime_detector はそれぞれ独立した private wrapper を持っています）。
- RSS フェッチ等ネットワーク I/O 部分もモック可能な設計になっています（_urlopen 等）。
- .env の自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定するとよいです。

ライセンスや貢献方法
--------------------
（このテンプレートではライセンスファイルが含まれていません。実プロジェクトでは LICENSE を追加し、貢献ガイドを CONTRIBUTING.md 等にまとめてください。）

お問い合わせ
------------
実運用や拡張（ブローカー連携、戦略化、自動化スケジューリング等）についてのご相談があれば、README の連絡先情報（Slack 等）を .env に設定し、運用通知を組み込んでください。

以上。必要であれば README にサンプル .env.example、cron 例、より詳細な DB スキーマ初期化手順、よくあるトラブルシュートを追加します。どの情報を追記しますか？