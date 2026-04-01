KabuSys — 日本株向けデータプラットフォーム & 自動売買補助ライブラリ
================================================================================

このリポジトリは日本株のデータ収集・品質管理・特徴量計算・AIによるニュース評価・市場レジーム判定・監査ログの基盤機能を提供する Python パッケージです。ETL → 品質チェック → 研究・リサーチ → 戦略／執行 の上流部分を中心に実装しています。

主な目的
- J-Quants API からの差分 ETL（株価・財務・カレンダー）
- ニュース収集（RSS）と LLM を用いた銘柄センチメント算出（ai_score）
- 市場レジーム判定（ETF + マクロニュースを統合）
- ファクター計算・特徴量探索・IC 計算
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（信号→発注→約定のトレース可能なテーブル群）初期化ユーティリティ

機能一覧
- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（認証・取得・保存・ページネーション・レート制御・リトライ）
  - market カレンダー管理（営業日判定・next/prev_trading_day 等）
  - ニュース収集（RSS 取得、前処理、SSRF 対策）
  - データ品質チェック（欠損・スパイク・重複・日付整合性）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（news_nlp.score_news: 銘柄ごとのセンチメントを ai_scores テーブルへ書き込み）
  - 市場レジーム判定（regime_detector.score_regime: ETF 1321 の MA200 とマクロニュースを統合）
- research
  - ファクター計算（momentum / volatility / value）
  - 特徴量探索（forward returns / IC / summary / rank）
- config
  - 環境変数管理（.env 自動ロード、必須鍵の取得用 Settings オブジェクト）

セットアップ手順（ローカル開発向け）
1. Python 環境
   - Python 3.10+ を推奨（typing|annotations を利用）
2. パッケージのインストール
   - 最小依存例:
     pip install duckdb openai defusedxml
   - 開発インストール（リポジトリルートに setup / pyproject がある前提）:
     pip install -e .
   ※ requirements.txt / pyproject.toml がある場合はそちらを利用してください。
3. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml を探索）から .env と .env.local を自動で読み込みます。
   - 自動読み込みを無効にするには:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
4. 必須外部サービス
   - J-Quants API（取得用リフレッシュトークン）
   - OpenAI（LLM 呼び出し。news_nlp / regime_detector が使用）
   - Slack（一部通知で使用する場合）

主な環境変数（settings で参照）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY        : OpenAI API キー（ai 機能を使う場合は必須）
- KABU_API_PASSWORD     : kabuステーション API パスワード（発注系の統合に使用）
- KABU_API_BASE_URL     : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID : Slack 通知用
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : sqlite 用パス（監視用など）
- PID_FILE_PATH / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT : 監視用
- KABUSYS_ENV           : development / paper_trading / live（デフォルト development）
- LOG_LEVEL             : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

簡単な使い方（コード例）
- DuckDB 接続と日次 ETL 実行
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニューススコアリング（AI）
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"wrote {n_written} ai_scores")

  ※ OPENAI_API_KEY が環境変数に設定されていることを確認してください。
  ※ score_news は raw_news / news_symbols / ai_scores テーブルを参照・更新します。

- 市場レジーム判定
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ DB 初期化
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn を使って以降の監査テーブル操作が可能

実行上の注意・設計方針（要点）
- Look-ahead bias 回避: 多くの処理は datetime.today()/date.today() を直接参照せず、target_date を明示して呼ぶことを想定しています。
- API 呼び出し: J-Quants はレート制御・リトライを内蔵。OpenAI 呼び出しはリトライとフェイルセーフ（失敗時は 0.0）。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                        : .env 自動読み込み / Settings
  - ai/
    - __init__.py
    - news_nlp.py                     : ニュースの LLM スコアリング（score_news）
    - regime_detector.py              : 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py               : J-Quants API クライアント（fetch / save）
    - pipeline.py                     : ETL パイプライン（run_daily_etl 等）
    - etl.py                          : ETL インターフェース（ETLResult 再エクスポート）
    - calendar_management.py          : マーケットカレンダー管理
    - news_collector.py               : RSS 収集・前処理・保存
    - quality.py                      : データ品質チェック（QualityIssue, run_all_checks）
    - stats.py                        : zscore_normalize 等の統計ユーティリティ
    - audit.py                        : 監査テーブル初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py              : momentum/value/volatility 等
    - feature_exploration.py          : forward returns / IC / summary / rank
  - research/... (ファイル群)

開発・デバッグのヒント
- .env 自動ロード:
  - プロジェクトルートを .git または pyproject.toml から探索して .env と .env.local を読み込みます。
  - 優先順: OS 環境変数 > .env.local > .env
  - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に便利）。
- OpenAI 呼び出しのモック:
  - unit テストでは kabusys.ai.news_nlp._call_openai_api や kabusys.ai.regime_detector._call_openai_api を patch して応答を返すことで API 呼び出しをシミュレートできます。
- DuckDB compat:
  - 一部の executemany が空リストを受け付けないバージョン（例: DuckDB 0.10）を考慮したガードが入っています。空の書き込みは避けるように実装されています。

.env.example（例）
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- OPENAI_API_KEY=sk-...
- KABU_API_PASSWORD=your_kabu_password
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C12345678
- DUCKDB_PATH=data/kabusys.duckdb
- LOG_LEVEL=INFO
- KABUSYS_ENV=development

ライセンス / コントリビューション
- 本 README にはライセンス情報は含まれていません。実際のリポジトリに LICENSE を追加してください。
- バグ報告や機能提案は issue を作成してください。

補足
- 実行には外部 API の認証情報（J-Quants, OpenAI）が必要です。テストやローカル動作確認時はこれらをモックするか、KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して環境を分離してください。
- コード中に多くのログ出力・警告処理・フェイルセーフが実装されています。運用環境では LOG_LEVEL と KABUSYS_ENV を適切に設定してください。

以上です。README に加えたい具体的なコマンド例や .env.example の完全版、あるいは CI / Docker 用の指示が必要であれば教えてください。