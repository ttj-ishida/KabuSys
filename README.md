# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
ETL（J-Quants からの株価/財務/カレンダー取得）、ニュース収集・NLP（OpenAI を用いたセンチメント）、ファクター計算、監査ログ（トレース可能な発注・約定記録）などをモジュール化して提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- 前提条件 / 依存関係
- セットアップ手順
- 環境変数 (.env) / 設定
- 使い方（主要な API の例）
- ディレクトリ構成
- よくある質問 / トラブルシューティング

---

プロジェクト概要
- KabuSys は日本株の自動売買やリサーチ用の内部ライブラリ群です。  
  データ取得（J-Quants）、ETL、品質チェック、ニュース収集・NLP、AI による市場レジーム判定、研究用ファクター計算、監査ログ（発注〜約定のトレーサビリティ）などを提供します。
- バックテストや実運用の前段（データ基盤・信号生成・監査）を主目的に設計されています。

---

機能一覧
- データ取得 / ETL
  - J-Quants からの株価日足（raw_prices）、財務データ（raw_financials）、市場カレンダー（market_calendar）の差分取得と DuckDB への冪等保存
  - run_daily_etl 等のパイプライン API
- データ品質チェック
  - 欠損、スパイク、重複、将来日付・非営業日データ検出
  - QualityIssue オブジェクトによる詳細報告
- ニュース収集
  - RSS フィード取得、前処理、raw_news への冪等保存、news_symbols による銘柄紐付け（news_collector）
  - SSRF 対策、XML パースの安全化（defusedxml）
- ニュース NLP / AI
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント算出（ai.news_nlp.score_news）
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースセンチメントの合成）(ai.regime_detector.score_regime)
  - バッチ・チャンク・リトライ等の堅牢な設計
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（research パッケージ）
  - Z-score 正規化、将来リターン・IC 計算、統計サマリー
- 監査ログ（audit）
  - signal_events / order_requests / executions といった監査テーブルの DDL、初期化 API（init_audit_schema / init_audit_db）
  - トレーサビリティの維持（UUID 連鎖）、UTC タイムスタンプ

---

前提条件 / 依存関係
- Python >= 3.10（Union 型 annotation（X | None）を使用）
- 主要依存パッケージ（抜粋）
  - duckdb
  - openai
  - defusedxml
- その他標準ライブラリを広く使用

（実際の requirements.txt がある場合はそちらを利用してください）

例:
pip install duckdb openai defusedxml

---

セットアップ手順（ローカル開発想定）
1. リポジトリをクローン
   - git clone <repo-url>
2. Python 仮想環境を作成し有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Unix/macOS)
   - .venv\Scripts\activate     (Windows)
3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （追加でテスト・開発用のライブラリがあればインストール）
4. パッケージを編集モードでインストール（任意）
   - pip install -e .

---

環境変数 / .env の管理
- 自動読み込み
  - パッケージ import 時にプロジェクトルート（.git または pyproject.toml を検出）を起点として .env を自動ロードします。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に便利）。
- 主要な環境変数（config.Settings 参照）
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
  - KABU_API_PASSWORD: kabu API のパスワード（発注関連）
  - KABU_API_BASE_URL: kabu ステーション API の base URL（デフォルト: http://localhost:18080/kabusapi）
  - OPENAI_API_KEY: OpenAI API キー（ai モジュールで使用）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知（任意）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: SQLite（監視用）パス（デフォルト data/monitoring.db）
  - PAPER_FILL_MODE: Paper Trading の模擬約定挙動（instant/partial/never/reject）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
  - PID_FILE_PATH / KILL_FLAG_PATH など監視用設定
  - KABUSYS_ENV: development / paper_trading / live
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

例 .env（最小）
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxx
KABU_API_PASSWORD=your_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

使い方（主要 API サンプル）

- DuckDB 接続を用意して ETL を実行する
  - ETL は duckdb 接続を受け取り、差分取得→保存→品質チェックを実行します。

  Python 例:
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントのスコア算出
  - OpenAI API キー（OPENAI_API_KEY）が必要です。

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {n_written} codes")

- 市場レジームの判定
  - ETF 1321 の MA200 乖離とマクロニュースの LLM スコアを合成して market_regime テーブルに書き込みます。

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ DB の初期化
  - 監査テーブル（signal_events, order_requests, executions）を初期化します。

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn は初期化済みの DuckDB 接続

- カレンダー更新ジョブ（JPX カレンダーを J-Quants から取得）
  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import calendar_update_job

  conn = duckdb.connect("data/kabusys.duckdb")
  saved = calendar_update_job(conn, lookahead_days=90)

- 設定参照（コード内での利用例）
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                      — ニュースの LLM スコアリング
    - regime_detector.py               — 市場レジーム判定
  - data/
    - __init__.py
    - pipeline.py                      — ETL のメインロジック（run_daily_etl 等）
    - etl.py (再エクスポート)
    - jquants_client.py                — J-Quants API クライアント（取得 & 保存）
    - news_collector.py                — RSS ニュース収集
    - calendar_management.py           — 市場カレンダー管理（is_trading_day 等）
    - quality.py                       — データ品質チェック
    - stats.py                         — 統計ユーティリティ（zscore_normalize）
    - audit.py                         — 監査ログ定義と初期化
  - research/
    - __init__.py
    - factor_research.py               — Momentum/Value/Volatility 等の計算
    - feature_exploration.py           — 将来リターン / IC / summary 等

（上記以外に strategy / execution / monitoring などの名前が __all__ に示されていますが、今回のコードベースでは上のモジュール群が中心です）

---

よくある質問 / トラブルシューティング
- OpenAI API 呼び出しで失敗する
  - OPENAI_API_KEY が正しいことを確認してください。ネットワークやレート制限に対しては内部でリトライが組まれています。
  - レスポンスの JSON パース失敗時はフェイルセーフでスコア 0.0 を返す設計の箇所があります（ログを確認してください）。
- J-Quants 関連エラー
  - JQUANTS_REFRESH_TOKEN を .env に設定してください。get_id_token は 401 時に自動リフレッシュを試みます。
  - API レート制限（120 req/min）に従うため内部でスロットリングしています。大量の連続リクエストは時間がかかります。
- DuckDB のスキーマ・テーブルがない
  - 初回はテーブルを作成するスクリプトや DDL を実行してください。audit.init_audit_db は監査スキーマを作成します。ETL は想定するテーブル群が存在することを前提としています。
- 自動 env ロードを無効化したい
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください（テスト用途等）。
- Python バージョン
  - 本コードは Python 3.10 以上を想定しています（X | None の型ヒント等）。

---

貢献 / 開発
- 新機能やバグ修正はプルリクエストでお願いします。テスト・型チェック・静的解析（好ましくは）を含めるとマージがスムーズです。

---

ライセンス
- 本リポジトリにライセンスファイルがあればそれに従ってください（README 自体には特に記載がなければ追記してください）。

---

質問や追加のドキュメント（例: API 詳細、DB スキーマ、運用手順）を作成する必要があればお知らせください。README に追記して反映します。