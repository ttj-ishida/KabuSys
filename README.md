プロジェクト: KabuSys — 日本株自動売買 / データ基盤ライブラリ
概要
- KabuSys は日本株のデータ取得、品質管理、特徴量計算、ニュースNLP、LLM を用いた市場レジーム判定、監査ログ管理などを含むライブラリ群です。
- 主に以下の用途を想定しています：
  - J-Quants → DuckDB への ETL（株価・財務・市場カレンダー）
  - RSS ニュース収集と銘柄別センチメントスコアリング（OpenAI を利用）
  - マーケットレジーム判定（ETF MA とマクロニュースの合成）
  - 研究用ファクター計算・特徴量探索（Momentum / Value / Volatility 等）
  - 発注/約定までの監査ログスキーマ（監査DB初期化ユーティリティ）
  - データ品質チェックと運用用設定管理

主な機能一覧
- 環境設定管理
  - .env / .env.local または OS 環境変数から設定を読み込む（自動ロード可）
  - 必須設定の取得と検証（settings オブジェクト）
- データ ETL（kabusys.data.pipeline）
  - run_daily_etl を中心に calendar/prices/financials の差分取得・保存・品質チェック
  - J-Quants API クライアント（jquants_client）: レート制御、リトライ、トークン自動リフレッシュ
- ニュース収集（news_collector）
  - RSS フィード取得、前処理、SSRF 対策、raw_news への冪等保存サポート
- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を使った銘柄別ニュースセンチメント算出と ai_scores への書き込み
  - バッチ化、トリミング、リトライ、レスポンス検証
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF(1321) の 200 日移動平均乖離とマクロニュース LLM センチメントを合成して daily なレジーム判定
- 研究ユーティリティ（kabusys.research）
  - ファクター計算（momentum, value, volatility）・将来リターン・IC 計算・統計サマリー
  - zscore_normalize（data.stats）など共通統計関数
- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、将来日付 / 非営業日データの検出
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions の DDL 定義と初期化ユーティリティ（init_audit_db）

セットアップ手順（開発環境向け）
1) Python 仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2) 必要パッケージをインストール
   - 主要依存想定例: duckdb, openai, defusedxml
   - 例: pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそれに従ってください）

3) 環境変数 / .env ファイルを用意
   - 自動でプロジェクトルート（.git または pyproject.toml 基準）から .env/.env.local を読み込みます。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   - 主な必須環境変数（settings で参照されるもの）
     - JQUANTS_REFRESH_TOKEN   （J-Quants 用リフレッシュトークン）
     - KABU_API_PASSWORD       （kabuステーション API パスワード）
     - SLACK_BOT_TOKEN         （Slack 通知に使用する Bot トークン）
     - SLACK_CHANNEL_ID        （通知先チャネル ID）
     - OPENAI_API_KEY          （AI モジュールで使用。関数呼出し時に api_key 引数でも渡せます）
   - その他オプション:
     - KABU_API_BASE_URL (デフォルト http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
     - SQLITE_PATH, PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV (development | paper_trading | live)
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)

   .env の簡易例:
     JQUANTS_REFRESH_TOKEN=xxxxx
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_kabu_pass
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb

使い方（代表的な API 例）
- DuckDB 接続（監査DB初期化）
  - from kabusys.data.audit import init_audit_db
  - conn = init_audit_db("data/audit.duckdb")

- 日次 ETL 実行（prices / financials / calendar の差分取得）
  - from kabusys.data.pipeline import run_daily_etl
  - from datetime import date
  - conn = duckdb.connect("data/kabusys.duckdb")
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - result.to_dict() で詳細を取得

- ニュースセンチメントスコアの算出
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - conn = duckdb.connect("data/kabusys.duckdb")
  - n = score_news(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")
  - 戻り値: 書き込み済み銘柄数

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - conn = duckdb.connect("data/kabusys.duckdb")
  - score_regime(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")
  - market_regime テーブルに結果を書き込む

- 研究用ファクター計算
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  - records = calc_momentum(conn, target_date=date(2026,3,20))

- 設定値参照
  - from kabusys.config import settings
  - settings.duckdb_path などで Path オブジェクトが取得できます
  - 自動 .env ロードの仕組みは .env/.env.local をプロジェクトルート（.git か pyproject.toml）から探します

運用上の注意・設計方針（抜粋）
- ルックアヘッドバイアス防止:
  - モジュールの多くは date や target_date を明示的に受け取り、datetime.today()/date.today() を直接参照しない設計です（バックテスト利用時に重要）。
- 冪等性:
  - ETL の保存処理（save_*）や監査テーブル初期化は冪等性を考慮（ON CONFLICT DO UPDATE 等）。
- フェイルセーフ:
  - LLM 呼び出しや外部 API の失敗は基本的に局所でハンドルして処理継続する設計（必要に応じてログ・WARN を出力）。
- セキュリティ:
  - secrets（API キーなど）は .env やシークレット管理で保持し、リポジトリへコミットしないこと。
  - news_collector では SSRF／サイズ制限／XML の脆弱性対策を実装済み（defusedxml・ホスト検査・受信サイズ制限など）。

主要なディレクトリ構成（src/kabusys 以下、代表）
- __init__.py
- config.py                            — 環境変数 / 設定管理（settings）
- ai/
  - __init__.py                         — AI ユーティリティの公開
  - news_nlp.py                         — ニュースセンチメントのバッチ処理
  - regime_detector.py                  — 市場レジーム判定ロジック
- data/
  - __init__.py
  - jquants_client.py                   — J-Quants API クライアント（取得/保存）
  - pipeline.py                         — ETL パイプライン（run_daily_etl 等）
  - etl.py                              — ETLResult の再エクスポート
  - news_collector.py                   — RSS ニュース収集
  - quality.py                          — データ品質チェック
  - stats.py                            — 共通統計ユーティリティ（zscore_normalize 等）
  - calendar_management.py              — 市場カレンダー管理・営業日ロジック
  - audit.py                            — 監査ログスキーマ定義と初期化ユーティリティ
- research/
  - __init__.py
  - factor_research.py                  — モメンタム/バリュー/ボラティリティ等
  - feature_exploration.py              — 将来リターン/IC/統計サマリー等

補足（開発／デバッグ）
- テスト時に自動 .env 読み込みを無効化:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- OpenAI 呼び出しは各モジュール内部で分離され、unit test では _call_openai_api をモックして差し替え可能
- DuckDB バージョンや executemany の挙動に注意（コード内に互換性対策あり）

ライセンス・貢献
- この README はコードベースの概要と利用手順を示すためのドキュメントです。実運用前に各モジュールの詳細な動作（テーブルスキーマ、期待される DB テーブルの事前準備、権限など）を確認してください。
- 貢献方法やライセンス情報はプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

必要ならば、具体的な実行例（完全スクリプト）、想定スキーマ定義、requirements.txt の候補、.env.example ファイルの完全版なども作成します。どれを優先しましょうか？