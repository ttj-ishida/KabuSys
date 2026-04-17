# KabuSys

日本株向けの自動売買システム骨組み。シグナル生成・ポートフォリオ構築・発注エンジン・監視・リサーチ・AI（ニュースセンチメント / レジーム判定）などの主要コンポーネント群を含みます。

このリポジトリはモジュール単位で実行可能なスクリプト群（設定ウィザード・設定検証・ExecutionEngine 起動・Monitoring 起動・レポート生成など）と、ポートフォリオ構築、ファクター計算、AI を用いたニューススコアリング等の実装を提供します。

---

## 主な機能

- 環境設定ウィザード（.env の対話式作成 / 更新）
- 起動前設定検証ツール（.env / config/*.yaml のチェック）
- ExecutionEngine 起動スクリプト（本番 / ペーパートレード切替対応）
- Monitoring ポーリング（システム状態、注文滞留・約定異常、リスク監視、Kill Switch）
- LINE によるアラート送信（AlertManager）
- Paper Trading 検証レポート生成ツール
- ポートフォリオ構築ユーティリティ（候補選定・重み計算・ポジションサイズ計算・セクター制限）
- リサーチ：ファクター計算（モメンタム / バリュー / ボラティリティ）および特徴量解析（forward returns / IC / summary）
- AI モジュール：ニュースの NLP スコアリング（OpenAI）・市場レジーム検出（OpenAI + MA200 合成）
- プラットフォームに依存しないプロセス優先度 & CPU affinity 設定ユーティリティ

---

## 必要な依存パッケージ（代表例）

主に次のパッケージを想定しています（プロジェクトの requirements.txt がない場合は手動でインストールしてください）:

- python >= 3.9
- duckdb
- psutil
- openai
- requests
- PyYAML（config.yaml のパース検証を行う場合に必要）

例:
pip install duckdb psutil openai requests pyyaml

標準ライブラリの sqlite3 は不要なインストールなしに使用できます。

---

## セットアップ手順

1. リポジトリをクローン / 展開する。

2. Python 仮想環境を作成（任意）:
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール:
   pip install duckdb psutil openai requests pyyaml

4. データディレクトリ作成（デフォルトの DB /フラグファイル場所）:
   mkdir -p data

5. .env を作成:
   - 対話式で作る場合:
     python -m kabusys.config_setup
   - もしくはプロジェクト直下に .env を置く。
   自動ロードの挙動:
     - OS 環境変数 > .env.local > .env の順で読み込まれます。
     - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

6. 設定を検証:
   python -m kabusys.validate_config
   --strict を付けると警告も失敗扱いになります:
   python -m kabusys.validate_config --strict

---

## 主な環境変数（抜粋）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードでの約定モード（instant / partial / never / reject、デフォルト: instant）
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE Push 通知（未設定時は送信せずログのみ）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）

注意: .env の自動ロードは config.Settings モジュールで行われます（プロジェクトルートが特定できない場合はスキップ）。

---

## 使い方（主要スクリプト）

- 環境設定ウィザード（対話式）:
  python -m kabusys.config_setup
  → 指示に従い .env を作成 / 更新します。

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ExecutionEngine を起動（本番/ペーパー自動判定）:
  環境変数 KABUSYS_ENV を設定してください。
  - ペーパートレード:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 本番:
    KABUSYS_ENV=live python -m kabusys.run_execution
  実行前に data ディレクトリや .env の設定を確認してください。
  run_execution は process 優先度を High に設定し、thread を使って Engine を実行します。停止は data/stop_requested.flag を作成することでトリガーできます。

- Monitoring を起動:
  MONITOR_POLL_INTERVAL でポーリング間隔を指定可能（秒、デフォルト 60）。
  python -m kabusys.run_monitoring
  停止は data/stop_requested.flag を作成するか、KeyboardInterrupt（Ctrl+C）。

- Paper Trading 検証レポート生成:
  python -m kabusys.tools.paper_verification_report
  オプション:
    --from YYYY-MM-DD  --to YYYY-MM-DD
    --db PATH  （PAPER_TRADING_SQLITE_PATH より優先）

- AI（ニューススコアリング / レジーム判定）:
  - OpenAI API キー（OPENAI_API_KEY）が必要。
  - プログラム API を直接呼ぶ形（例: kabusys.ai.score_news, kabusys.ai.regime_detector.score_regime）。
  - CLI ラッパーはありませんが、必要に応じて小さいスクリプトを作って呼び出せます。

- その他ユーティリティ:
  - 設定値読み取り: from kabusys.config import settings
  - ポートフォリオ関数等は kabusys.portfolio 配下を参照。

---

## 停止 / Kill Switch の仕組み

- run_execution / run_monitoring はプロジェクト直下 data/stop_requested.flag の存在を確認して安全にシャットダウンします。
- KillSwitch（監視コンポーネント）は data/kill.flag を書き込むことで ExecutionEngine 側に停止シグナルを送ります（Settings.kill_flag_path でパスを変更可能）。
- Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると kill.flag を自動的にクリアする挙動になります（本番では 0 推奨）。

---

## ディレクトリ構成（主要ファイルの説明）

- src/kabusys/
  - __init__.py: パッケージ情報（バージョン等）
  - config.py: 環境変数読み込み・Settings（.env 自動ロードロジック含む）
  - config_setup.py: .env 対話型ウィザード
  - validate_config.py: 起動前の設定検証ツール
  - run_execution.py: ExecutionEngine 起動スクリプト（本番 / ペーパー対応）
  - run_monitoring.py: Monitoring（SystemMonitor）ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py: ペーパートレード検証レポート生成スクリプト
  - portfolio/
    - portfolio_builder.py: 候補選定・重み計算
    - position_sizing.py: 発注株数計算・スケーリング・lot 単位処理
    - risk_adjustment.py: セクター制限・レジーム乗数
  - research/
    - factor_research.py: mom/value/volatility ファクター計算（DuckDB）
    - feature_exploration.py: forward returns / IC / summary
  - ai/
    - news_nlp.py: raw_news の LLM を使った銘柄別センチメント取得
    - regime_detector.py: MA200 と LLM を合成した市場レジーム判定
  - monitoring/
    - monitoring_db.py: SQLite ベースの永続化層（schema 初期化・操作）
    - system_monitor.py: CPU/メモリ/ディスク/データ鮮度/プロセス生存監視
    - trade_monitor.py: 注文滞留・約定異常検出
    - risk_monitor.py: ドローダウン・ポジション上限監視
    - kill_switch.py: kill.flag 書き込みロジック
    - alert_manager.py: LINE Push による通知（クールダウン管理）
    - monitoring_engine.py: 各 Monitor を束ねてポーリングするエンジン
  - execution/ (主なエンジン関連の実装ファイルはここに存在想定)
    - order_manager, order_repository, reconciler, execution_engine など（run_execution が組み立てて利用）
  - utils/
    - process_priority.py: プロセス優先度・CPU affinity 設定補助

（上記はこの README 作成時点の主要モジュールを抜粋した一覧です。実運用では execution 以下の各モジュール・データモデル等を確認してください。）

---

## 備考 / 運用上の注意

- ペーパートレードは production DB と分離されます（Settings.paper_sqlite_path を使用）。
- Monitoring は run_monitoring.py 実行時、KABUSYS_ENV の値にかかわらず本番 sqlite_path を使用する設計です（監視ログは共通の監視 DB に集める想定）。
- OpenAI 等外部 API 呼び出し機能はネットワーク上のコストやレート制限に注意してください。news_nlp などはリトライ / バックオフ機構を持ちますが、キー漏洩・コスト管理は運用者の責任です。
- .env（機密情報）は絶対にバージョン管理システムにコミットしないでください（config_setup.py のヘッダにも注意書きあり）。
- Windows / POSIX での優先度設定は psutil を通じて抽象化されていますが、権限不足で失敗する場合があります（警告が出ますが実行は継続します）。

---

## よく使うコマンドまとめ

- .env の対話作成:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Execution 起動:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Monitoring 起動:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  または
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

---

README に書かれている以外の詳細（ExecutionEngine の設定パラメータ、strategy やデータパイプラインの詳細等）はそれぞれのモジュールの docstring / コメントを参照してください。運用前に必ず validate_config で設定チェックを行い、テスト環境（paper_trading / development）で十分に検証してください。