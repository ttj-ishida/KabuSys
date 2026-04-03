KabuSys — 日本株自動売買プラットフォーム（README）
===================================

概要
----
KabuSys は日本株のデータ収集（ETL）・データ品質チェック・ファクター計算・ニュースNLP・市場レジーム判定・監査ログ管理を行うための Python モジュール群です。J-Quants や OpenAI（gpt-4o-mini）等の外部 API を利用して、研究（Research）・運用（Execution）双方の基盤機能を提供します。

主な設計方針
- ルックアヘッドバイアスを避ける（内部で date.today() を不用意に参照しない）
- DuckDB を主要なオンプレミス DB として利用
- ETL/保存は冪等（ON CONFLICT / UPDATE）を意識
- OpenAI 呼び出しはリトライ／バックオフ処理あり
- RSS 収集は SSRF 対策やサイズ制限を実装

機能一覧
---------
- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - settings オブジェクトで各種設定を参照可能

- データ ETL（kabusys.data.pipeline / jquants_client）
  - J-Quants から株価（日足）、財務、上場情報、JPX カレンダーの差分取得＆保存
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl を提供
  - 保存時は冪等化（ON CONFLICT DO UPDATE）

- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、日付不整合などを検出
  - QualityIssue オブジェクト群で詳細を返す

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、前処理、raw_news への冪等保存
  - SSRF、XML attack、レスポンスサイズなどの防御を実装

- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI を用いた銘柄別ニュースセンチメント評価（JSON mode）
  - score_news(conn, target_date, api_key=None) で ai_scores に書き込み

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（70%）とマクロニュースセンチメント（30%）を合成してレジームを判定
  - score_regime(conn, target_date, api_key=None)

- 研究支援（kabusys.research）
  - ファクター計算（momentum/value/volatility）
  - 将来リターン計算、IC（Spearman）計算、統計サマリ、Z スコア正規化

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査テーブル定義および初期化
  - init_audit_db(db_path) で監査専用 DuckDB を初期化

セットアップ手順
----------------
前提
- Python 3.10 以上（本コードは | 型注釈等を使用しているため 3.10+ が必要）
- DuckDB を使用するためネイティブモジュールのインストールが必要

1) リポジトリをクローン
   git clone <repo-url>
   cd <repo-root>

2) 仮想環境と依存ライブラリのインストール（例）
   python -m venv .venv
   source .venv/bin/activate  # Windows では .venv\Scripts\activate
   pip install --upgrade pip
   pip install duckdb openai defusedxml

   ※ 必要に応じて他パッケージ（requests 等）を追加してください。

3) 環境変数設定
   プロジェクトルートに .env または .env.local を置くと、自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可能）。

   主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
   - OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime 用）
   - KABU_API_PASSWORD     : kabu ステーション API パスワード（発注系）
   - KABU_API_BASE_URL     : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID : 通知用（省略可）
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH           : 監視用 SQLite（デフォルト data/monitoring.db）
   - KABUSYS_ENV           : development / paper_trading / live
   - LOG_LEVEL             : DEBUG / INFO / WARNING / ERROR / CRITICAL

   .env の書き方の注意:
   - export KEY=val 形式を許容
   - シングル/ダブルクォートのエスケープをサポート
   - コメント（#）はスペース区切りで認識される場合は除外

使い方（簡単な例）
-----------------

- 設定値の参照
  from kabusys.config import settings
  print(settings.duckdb_path)

- DuckDB 接続
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=None)  # target_date=None だと今日を基準に実行
  print(result.to_dict())

- ニューススコアリング（OpenAI API キーが環境変数 OPENAI_API_KEY に設定されていること）
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  n = score_news(conn, target_date=date(2026,3,20))
  print(f"書き込み銘柄数: {n}")

- 市場レジーム判定
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026,3,20))

- 監査 DB 初期化（監査専用 DB ファイルを作成）
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")

- ファクター / リサーチ系の呼び出し（研究用途）
  from kabusys.research import calc_momentum, calc_value, calc_volatility
  res = calc_momentum(conn, target_date=date(2026,3,20))
  print(len(res))

運用上の注意
-------------
- OpenAI/API キーは安全に管理してください。プロダクション環境では環境変数も OS レベルで保護してください。
- .env 自動読み込みはプロジェクトルートの .git または pyproject.toml を起点に行います。パッケージ配布後も安全に動作するよう設計されていますが、CI やテスト環境で自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ETL・API 呼び出しはリトライ・バックオフを備えていますが、API レート制限やコストに注意してください（J-Quants、OpenAI）。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                 — 環境設定 / .env 自動読み込み / settings
- ai/
  - __init__.py
  - news_nlp.py             — ニュースのセンチメントスコアリング（OpenAI）
  - regime_detector.py      — 市場レジーム判定（1321 MA200 + マクロニュース）
- data/
  - __init__.py
  - jquants_client.py       — J-Quants API クライアント（fetch / save）
  - pipeline.py             — ETL パイプライン（run_daily_etl 等）
  - quality.py              — データ品質チェック
  - news_collector.py       — RSS 収集
  - calendar_management.py  — マーケットカレンダー管理（is_trading_day 等）
  - audit.py                — 監査ログテーブル定義 / 初期化
  - etl.py                  — ETL の公開インターフェース（ETLResult 再エクスポート）
  - stats.py                — 共通統計ユーティリティ（zscore_normalize 等）
- research/
  - __init__.py
  - factor_research.py      — Momentum / Value / Volatility 等
  - feature_exploration.py  — 将来リターン, IC, 統計サマリ, rank 等
- ai/, research/, data/ 以下はさらに多数の内部関数・定数を含みます（詳細は各ファイルを参照）

よくある質問（FAQ）
-------------------
Q: テストを実行する方法は？
A: テストコードは本コードベースには含まれていません。ユニットテストを書く場合は、OpenAI 呼び出しやネットワーク依存部分をモック（unittest.mock.patch）してください。score_news/regime_detector には _call_openai_api を差し替え可能な設計があります。

Q: ログレベルを変更したい
A: 環境変数 LOG_LEVEL を設定してください（例: LOG_LEVEL=DEBUG）。

Q: OpenAI 呼び出しの課金やレートに気をつけたい
A: バッチサイズや頻度を調整し、API キーの使用量を監視してください。score_news は最大 20 銘柄ごとのバッチを行います（定数 _BATCH_SIZE）。

ライセンス、貢献
----------------
- ライセンスやコントリビュート方法はリポジトリのルートに別途記載してください（この README には含まれていません）。

問い合わせ
-----------
不明点やバグ報告、機能要望はリポジトリの Issue をご利用ください。

以上。