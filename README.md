# KabuSys

日本株向け自動売買・リサーチ基盤の一部を実装したコードベースの README です。本リポジトリは、注文実行エンジン・監視（Monitoring）・ポートフォリオ構築・リサーチ・AI によるニュース解析などを含みます。

## プロジェクト概要
KabuSys は日本株の自動売買システムのコンポーネント群です。本コードベースには、次のような機能群が実装されています。

- ExecutionEngine（注文発行・状態管理・リコンシリエーション）
- Monitoring（システム状態・注文滞留・ドローダウン監視、LINE アラート、ダッシュボード）
- Portfolio construction（候補選定・重み付け・ポジションサイズ計算・セクター制限）
- Research（ファクター計算、将来リターン、IC 計算、統計サマリー）
- AI モジュール（ニュースセンチメント、レジーム判定：OpenAI を利用）
- ツール（Paper Trading 検証レポート生成など）

設計方針として、DB（SQLite / DuckDB）や外部 API へのアクセスを分離し、フェイルセーフや冪等性を考慮した実装になっています。

## 主な機能一覧
- システム監視（CPU / メモリ / ディスク、Execution プロセスの生存チェック、データ鮮度チェック）
- 注文監視（滞留注文、約定異常の検出）とリスクログ保存
- ドローダウン監視、ポジション上限監視 → kill.flag 書き込み（Execution 停止シグナル）
- LINE へのアラート（AlertManager）とクールダウン管理
- Streamlit ベースの監視ダッシュボード（読み取り専用）
- Paper Trading 用検証レポート生成ツール（paper_verification_report）
- ニュース NLP（OpenAI）を使った銘柄別センチメントの収集と ai_scores 書き込み
- 市場レジーム判定（ETF MA とマクロセンチメントの合成）
- ポートフォリオ構築関数群（候補選定、等重・スコア重み、リスクベースの株数計算）
- DuckDB / SQLite を用いたデータ/ログ管理

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - 例: git clone <リポジトリURL>

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存ライブラリをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 目安（本コードで使用している主なパッケージ）:
     - pip install duckdb psutil requests openai streamlit

   （配布方法により pip install -e . などでもインストール可能）

4. データディレクトリ作成
   - mkdir -p data

5. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 推奨する環境変数（例）
     - KABUSYS_ENV=development | paper_trading | live
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - MONITOR_POLL_INTERVAL=60
     - OPENAI_API_KEY=（OpenAI APIキー、AI 機能を使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN、LINE_USER_ID（LINE 通知を使う場合）
     - JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD（外部 API 用）
     - PAPER_FILL_MODE=instant | partial | never | reject

   - .env.example がある想定のメッセージをコード内で参照するため、必要に応じて .env を用意してください。

6. DB 初期化
   - 実行スクリプトが起動時に monitoring DB のテーブルを作成します（init_monitoring_db は冪等実行）。特別な手順は不要です。

## 使い方（主なエントリポイント）
下記はプロジェクトルートで実行する想定です。

- 監視ループ（Monitoring）
  - python -m kabusys.run_monitoring
  - 説明:
    - SystemMonitor を定期ポーリングして system_status / risk_logs / trade_logs / dashboard 等を更新します。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト: 60）。
    - 監視は常に本番の sqlite_path（Settings.sqlite_path）を使用します（KABUSYS_ENV に依らず）。
    - 停止: プロジェクトルートの data/stop_requested.flag が検出されるとループを終了します。

- 注文実行エンジン（ExecutionEngine）
  - python -m kabusys.run_execution
  - 説明:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。本番 DB と分離されます。
    - 起動時に data/execution.pid を使ってプロセス生存チェックを行います。data/stop_requested.flag があれば起動しません。
    - 停止方法: data/stop_requested.flag を作成するか、KillSwitch が data/kill.flag を書き込むと ExecutionEngine は停止します。

- Streamlit ダッシュボード（監視ビュー）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 説明: 監視用 SQLite DB を読み取り専用で開き、Overview / Positions / Orders / System などを表示します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH より優先）
  - 検証指標: 稼働率、注文成功率、送信率、P95 レイテンシ など。基準値はコード内コメントで定義されています。

- AI / 研究系（プログラム呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - OpenAI の API キーは api_key 引数または環境変数 OPENAI_API_KEY で指定。
    - モデル: gpt-4o-mini（コード内で指定）
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

## 環境変数（主要）
- KABUSYS_ENV: development | paper_trading | live（必須ではないが許容値に制約あり）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）。1 以上の整数。デフォルト 60。
- SQLITE_PATH: 監視ログ用 SQLite（デフォルト data/monitoring.db）
- DUCKDB_PATH: 時系列データ格納用 DuckDB（デフォルト data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定振る舞い（instant | partial | never | reject）
- PID_FILE_PATH: ExecutionEngine が利用する PID ファイルパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH: KillSwitch のフラグファイルパス（デフォルト data/kill.flag）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知を有効にする場合に設定
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など外部 API 用トークン

※ Settings クラスにより、環境変数の検証やデフォルト値の解決が行われます。未設定の必須キーを参照すると例外が発生します。

## フラグファイル / 制御ファイルについて
- data/stop_requested.flag
  - run_monitoring.py / run_execution.py はこのファイルが存在することを検知するとループを終了またはエンジンを停止します（停止指示用）。
- data/kill.flag
  - KillSwitch（リスクトリガ）が書き込むと ExecutionEngine 停止をユーザ側にシグナルする目的で使われます。KillSwitch は冪等にファイルを書きます。
- data/execution.pid
  - ExecutionEngine が起動時に PID を書き、SystemMonitor がプロセス生存判定に使用します。stale PID は自動削除されリスクイベントとしてログに残ります。

## ディレクトリ構成
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数/設定読み込みロジック（.env 自動読み込みを含む）
  - run_monitoring.py — SystemMonitor の常駐ポーリング起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成ツール
  - monitoring/
    - monitoring_db.py — SQLite を使った監視ログ永続化層（テーブル作成・CRUD）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の管理
    - alert_manager.py — LINE 通知クライアント
    - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
    - streamlit_dashboard.py — Streamlit 版監視ダッシュボード
  - execution/
    - order_manager.py, order_repository.py, reconciler.py, execution_engine.py, ...（発注関連）
  - portfolio/
    - portfolio_builder.py — 候補選定・スコアソート・等重/スコア重み
    - position_sizing.py — 株数計算・集約キャップ処理
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — Momentum/Volatility/Value ファクター計算（DuckDB SQL）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py — ニュース記事の LLM ベースセンチメント処理（DuckDB 入出力）
    - regime_detector.py — ETF MA と LLM を合成した市場レジーム判定
  - data/ （実行時に作成）
    - monitoring.db（SQLite、デフォルト）
    - kabusys.duckdb（DuckDB、デフォルト）
    - paper_trading.db（Paper Trading 用 SQLite）
    - stop_requested.flag / kill.flag / execution.pid など制御用ファイル

## 運用上の注意
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と完全分離されています。テストや検証時は必ず PAPER_TRADING_SQLITE_PATH を確認してください。
- OpenAI を使用する機能は API キーが必須です（OPENAI_API_KEY）。API 呼び出し失敗時はフェイルセーフ（スコア 0 やスキップ）を行う設計ですが、ログを確認してください。
- Monitoring はデフォルトで本番 sqlite_path を参照します。テスト環境で別 DB を使いたい場合は設定を調整してください。
- プロセス優先度の設定や CPU affinity 設定はプラットフォーム依存のため権限不足等で警告が出ることがあります（set_process_priority が起動時に呼ばれます）。
- DB マイグレーションは簡易に実装されています（init_monitoring_db は既存テーブルへのカラム追加を行う箇所を含む）。

## 開発・貢献
- コードはモジュール単位に分かれており、ユニットテストが書きやすい設計を意図しています（純粋関数・副作用のある層の分離）。
- 外部 API 呼び出しや時刻取得は注入やモックで差し替え可能な設計を心がけてあります（例: _call_openai_api を patch してテスト可能）。

---

この README はコード内の docstring / コメントを元に作成しています。実際の実行環境や依存関係はプロジェクトの配布パッケージ（pyproject.toml / requirements.txt）を確認してください。必要であれば README をプロジェクト固有のコマンドや例（systemd unit、Docker Compose、CI 設定など）に合わせて拡張できます。