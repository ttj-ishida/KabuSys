KabuSys — 日本株自動売買プラットフォーム（README）
概要
- KabuSys は日本株向けのデータプラットフォーム／リサーチ／簡易自動売買のためのライブラリ群です。
- DuckDB を中心にデータを蓄積・品質チェック・ETL を行い、ニュースNLP（OpenAI）や市場レジーム判定、ファクター算出、監査ログ（約定トレーサビリティ）などを提供します。
- 設計方針として「ルックアヘッドバイアス防止」「冪等性」「フェイルセーフ（API失敗時の継続）」を重視しています。

主な機能
- データ ETL（J-Quants API から株価・財務・カレンダーの差分取得および DuckDB への保存）
  - 差分更新、ページネーション、トークン自動リフレッシュ、レート制御、指数バックオフ
- データ品質チェック（欠損・スパイク・重複・日付不整合の検出）
- ニュース収集（RSS）とニュースNLP（OpenAI を利用した銘柄ごとのセンチメント）
  - gpt-4o-mini の JSON mode を利用し結果を ai_scores に保存
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースセンチメントを合成）
- 研究用ユーティリティ（ファクター計算／将来リターン／IC／Z-score 正規化）
- 監査ログ（signal_events / order_requests / executions）スキーマ定義と初期化ユーティリティ
- JPX カレンダー管理（market_calendar と営業日判定ユーティリティ）

セットアップ（開発環境）
1. Python 環境の準備
   - Python 3.10+ を推奨
2. リポジトリをクローンして editable インストール
   - 例:
     - git clone <repo>
     - cd <repo>
     - python -m pip install -e ".[dev]"  # requirements ファイルがある想定
   - 必須パッケージ（主要なもの）
     - duckdb
     - openai
     - defusedxml
     - （その他 urllib / 標準ライブラリを利用）
3. 環境変数 / .env
   - プロジェクトルートに .env / .env.local を配置すると自動で読み込みます（os 環境変数が優先）。
   - 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
   - 必須（実行する機能に応じて）:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
     - KABU_API_PASSWORD — kabu API パスワード（実運用で使用するとき）
     - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID — Slack 通知（運用時）
     - OPENAI_API_KEY — OpenAI 呼び出し（news_nlp / regime_detector を使う場合）
   - 省略可能:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト development）
     - LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視用 DB デフォルト data/monitoring.db）
   - .env の読み書きルールは kabusys.config モジュールがサポートします。

使い方（簡単なコード例）
- 共通準備（DuckDB 接続、settings）
  - from kabusys.config import settings
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))
- 日次 ETL を実行（株価・財務・カレンダー取得 + 品質チェック）
  - from datetime import date
  - from kabusys.data.pipeline import run_daily_etl
  - res = run_daily_etl(conn, target_date=date(2026,3,20))
  - print(res.to_dict())
- ニュースセンチメントをスコアリングして ai_scores に書き込む
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key 省略時は OPENAI_API_KEY を参照
- 市場レジーム判定（1321 MA200 とマクロ記事の合成）
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - score_regime(conn, target_date=date(2026,3,20), api_key=None)
- 監査ログ用 DB 初期化（監査ログ専用ファイルを作る）
  - from kabusys.data.audit import init_audit_db
  - conn_audit = init_audit_db("data/audit.duckdb")
  - これにより signal_events/order_requests/executions テーブルが作成されます
- 研究ユーティリティ例（モメンタム）
  - from kabusys.research.factor_research import calc_momentum
  - result = calc_momentum(conn, target_date=date(2026,3,20))

重要な設計上の注意点
- ルックアヘッドバイアスの回避:
  - 各モジュールは内部で datetime.today() を直接参照せず、必ず target_date を明示して処理します（バックテスト時の再現性確保）。
- 冪等性:
  - ETL の保存操作は ON CONFLICT（UPSERT）やユニーク制約により冪等になるよう実装しています。
- フェイルセーフ:
  - LLM や外部 API が失敗した場合は、可能な限りスキップして処理を継続する設計です（ログに警告を残します）。
- OpenAI とのやり取り:
  - gpt-4o-mini を用いた JSON mode を利用し、結果を厳密な JSON として期待しています。
  - レート制限・リトライ処理を実装していますが、APIキーやコスト管理に注意してください。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py (パッケージ定義)
  - config.py — 環境変数/設定読み込み（.env 自動読み込みロジック含む）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント算出（ai_scores へ保存）
    - regime_detector.py — 市場レジーム判定（market_regime へ保存）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント & DuckDB 保存処理
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult のエクスポート
    - calendar_management.py — JPX カレンダー管理・営業日判定
    - stats.py — 汎用統計（zscore_normalize）
    - quality.py — データ品質チェック群
    - audit.py — 監査ログスキーマ初期化 / DB 初期化
    - news_collector.py — RSS 収集と前処理
  - research/
    - __init__.py
    - factor_research.py — Momentum/Value/Volatility 等のファクター計算
    - feature_exploration.py — 将来リターン計算 / IC / 統計サマリー
  - monitoring / strategy / execution / その他（パッケージ公開対象として __all__ に含めるが、本 README のコードベースでは一部は空または別実装）
- README.md（このファイル）
- .env.example（プロジェクトルートに置くことを推奨: 必須環境変数のサンプル）

運用時のヒント
- 本番実行時は KABUSYS_ENV を live、あるいは paper_trading を指定して副作用（実際の発注）制御を行ってください。
- ログレベルは LOG_LEVEL 環境変数で制御できます。デバッグ時は DEBUG を指定。
- OpenAI API を多用する処理（news_nlp / regime_detector）はコストとレート制限に注意。テスト時は内部の _call_openai_api をモックして負荷を避けてください。
- J-Quants の API レートはモジュール内で制御されていますが、大量のページネーションや並列化は避ける設計にしてください。

貢献 / テスト
- テストや CI を導入する場合、環境変数自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用の環境設定をプログラム内で注入しやすくなります）。
- OpenAI 呼び出しやネットワーク関連は単体テストではモックすることを推奨します（コード中にモックポイントが用意されています）。

ライセンス / 表示
- この README ではライセンス表記は含めていません。実際のリポジトリでは適切な LICENSE ファイルを置いてください。

問い合わせ
- 実装上の不明点・改善提案があればコードコメントや Issue を通じてフィードバックしてください。

以上。必要であれば、.env.example のテンプレートや具体的な実行スクリプト（cron / systemd / Airflow 用）サンプルを追記します。どの情報を優先して追加しますか？