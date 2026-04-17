# KabuSys — README

概要
- KabuSys は日本株向けの自動売買・リサーチ基盤のサンプル実装です。
- 発注エンジン（ExecutionEngine）、監視コンポーネント（Monitoring）、ポートフォリオ構築、ファクター計算、ニュースの NLP 評価、ペーパートレード向け検証ツールなどを含みます。
- 設定は環境変数（.env）で管理され、DuckDB / SQLite を利用して時系列データやログを保管します。

主な機能（抜粋）
- ExecutionEngine：ブローカークライアントを介した注文発行の実行（本番 / ペーパートレード切替）
- Monitoring：プロセス・リソース・データ鮮度・注文の監視、Kill Switch による安全停止
- Portfolio モジュール：候補選定、重み計算、ポジションサイジング、セクター制約、レジーム倍率
- Research：ファクター計算（Momentum / Value / Volatility 等）、特徴量探索、IC 計算
- AI モジュール：ニュース記事の NLP スコアリング（OpenAI）、市場レジーム判定のためのマクロセンチメント集約
- Tools：Paper Trading 検証レポート生成スクリプト
- 設定関連 CLI：対話式 .env 作成ウィザード（config_setup）、設定検証 CLI（validate_config）

前提（依存）
- Python 3.10+
- 必要なパッケージ（代表例、プロジェクトに requirements.txt がなければ手動でインストール）
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML — validate_config の YAML 検証に使用
- SQLite（標準ライブラリに含まれるため別インストール不要）

セットアップ手順（ローカル開発）
1. リポジトリをクローン
   - git clone ...

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML

4. 環境変数の初期作成（対話ウィザード）
   - python -m kabusys.config_setup
     - .env ファイルを生成します（.env は絶対に Git にコミットしないでください）。
   - 自動ロードは既定で .env/.env.local をプロジェクトルートから読み込みます。自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

主要な環境変数（必須・代表）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）

主要なオプション（代表）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルト: development
  - paper_trading の場合、MockBrokerClient が使用され、data/paper_trading.db に記録されます（本番 DB と分離）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI を使う機能（news_nlp / regime_detector）で必須
- LOG_LEVEL: ログレベル（INFO 等）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動でクリアする（0/1, デフォルト 0）
- PAPER_FILL_MODE: ペーパートレードでの約定振る舞い（instant / partial / never / reject）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

よく使うコマンド（実行方法）
- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- ExecutionEngine 起動
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading にすると MockBrokerClient と paper_trading DB を使用します。
    - 実行中に data/stop_requested.flag を作成するとエンジンが停止します。
    - 実行時に data/execution.pid に PID を書きます。
- Monitoring 起動（監視ループ）
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更できます（例: MONITOR_POLL_INTERVAL=30）
    - 監視は環境に関わらず本番 sqlite_path を使用します（monitoring 用 DB）
    - 監視ループは data/stop_requested.flag 検知または Ctrl+C で停止します。
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
    - デフォルト DB パスは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

停止・Kill Switch について
- Kill Switch:
  - KillSwitch は監視結果に応じて data/kill.flag（デフォルト）を作成し、ExecutionEngine に停止シグナルを送ります。
  - Settings.kill_flag_clear_on_start が 1 の場合、起動時に kill.flag を自動でクリアします（本番では 0 を推奨）。
- stop_requested.flag:
  - run_execution/run_monitoring は data/stop_requested.flag の存在を監視して、発見時に安全停止します（運用者による手動停止など）。

OpenAI 関連
- news_nlp（ニュース NLP）や regime_detector（市場レジーム判定）は OpenAI API（gpt-4o-mini など）を利用します。
- API キーは OPENAI_API_KEY に設定するか、score_news / score_regime の引数で渡します。
- OpenAI 呼び出しはリトライ・バックオフや応答バリデーションを行っており、失敗時はフェイルセーフで継続する設計です。

注意事項 / 運用上のヒント
- .env は機密情報を含むため Git に含めないでください（config_setup に注釈あり）。
- 本番環境（KABUSYS_ENV=live）での設定は慎重に行ってください（validate_config はライブ用のガードをいくつか警告します）。
- PID ファイルやフラグファイルは data/ ディレクトリ配下に置かれます。起動前に適切な権限／ディレクトリの存在を確認してください。
- Monitoring は設定に関わらず本番 sqlite_path を参照する点に注意してください（監視用ログは共通の監視 DB に記録されます）。
- PAPER_FILL_MODE：ペーパートレードでの約定挙動を制御します（instant / partial / never / reject）。

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env 自動読み込み / Settings
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリング起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - execution/ — 発注関連（OrderManager, ExecutionEngine, BrokerFactory 等）
  - monitoring/
    - monitoring_db.py — SQLite の永続化層
    - system_monitor.py — プロセス/データ鮮度監視
    - trade_monitor.py — 注文滞留 / 約定異常監視
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — フラグファイルによる停止シグナル
    - monitoring_engine.py — 各モニタとアラートを束ねる
    - alert_manager.py — （アラート送信管理、実装参照）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・投下資金調整
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum/Volatility/Value 等のファクター計算
    - feature_exploration.py — 将来リターン計算 / IC / 統計サマリ
  - ai/
    - news_nlp.py — ニュースの NLP スコアリング（OpenAI）
    - regime_detector.py — マクロ + MA によるレジーム判定（OpenAI）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート

開発・テスト時のヒント
- Settings（kabusys.config.Settings）経由で環境変数へアクセスする設計になっており、テスト時は環境変数をモック／上書きして挙動を切り替えられます。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を起点）で行われます。CI / テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を推奨します。
- OpenAI 呼び出し部分は内部でラップされており、unittest.mock で _call_openai_api を差し替えてテスト可能です。

ライセンス・貢献
- （この README にはライセンス情報が含まれていません。実プロジェクトでは LICENSE を追加してください）

以上。プロジェクトの具体的な実装や各モジュールの詳細はソースコード内の docstring / コメントを参照してください。追加で README に盛り込みたい「運用手順」や「デプロイ手順（systemd / コンテナ化）」があれば指示してください。