# KabuSys

日本株向け自動売買システム（KabuSys）リポジトリの README。  
本プロジェクトは、戦略／ポートフォリオ構築、注文実行エンジン、監視・アラート、調査用モジュール、AI（ニュースセンチメント / レジーム判定）などを含む総合的な自動売買基盤です。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方
  - 環境設定ウィザード
  - 設定検証
  - 実行エンジン起動
  - 監視プロセス起動
  - Paper Trading 検証レポート生成
  - AI / リサーチ機能
- 重要な環境変数（抜粋）
- 停止・Kill スイッチの挙動
- ディレクトリ構成（主要ファイル）

---

プロジェクト概要
- KabuSys は日本株自動売買の基盤ライブラリ／アプリケーション群です。
- 戦略のためのファクター計算・特徴量解析モジュール、ポートフォリオ構築、ポジションサイジング、発注／リスク管理、監視・アラート、AI を用いたニューススコアリングや市場レジーム判定などを含みます。
- 設定は .env と config/*.yaml（オプション）で行います。Paper Trading モードでは実際の発注を行わず、専用の SQLite にログを残します。

主な機能一覧
- ExecutionEngine（発注エンジン）:
  - 本番（live） / ペーパートレード（paper_trading）対応
  - Broker クライアント抽象化（MockBrokerClient をペーパートレードで使用）
- Monitoring:
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、Execution プロセス生存監視
  - TradeMonitor: 滞留注文・約定価格異常検出
  - RiskMonitor: ドローダウン／ポジション上限検知、ダッシュボード更新、リスクログ記録
  - KillSwitch: 条件を満たすと data/kill.flag を書き込み ExecutionEngine 停止を要求
  - AlertManager（コードベースに準備。通知経路として LINE などを利用可能）
- Portfolio:
  - 銘柄選定、等配分／スコア加重配分、リスク制約（セクター制限、レジーム乗数）、単元株丸め、ポジションサイズ計算
- Research:
  - ファクター計算（モメンタム / ボラティリティ / バリュー等）
  - 将来リターン計算、Information Coefficient（IC）、統計サマリー
- AI:
  - news_nlp: OpenAI を用いたニュースセンチメントの銘柄別スコア付与（ai_scores）
  - regime_detector: ETF の MA とマクロニュースの LLM スコアを合成した市場レジーム判定
- Tools:
  - config_setup: 対話式で .env ファイルを作成・更新
  - validate_config: 環境変数・設定ファイルの事前検証 CLI
  - paper_verification_report: ペーパートレード履歴から検証レポートを生成

---

セットアップ手順（簡易）
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - 追加（オプション）: pyyaml（validate_config で YAML 検証を行う場合）
   - ※ requirements.txt があれば pip install -r requirements.txt を使用してください。

4. .env を作成
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（下記「重要な環境変数」参照）

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

6. データディレクトリを作る（必要なら）
   - mkdir -p data

7. （OpenAI を利用する機能を使う場合）OPENAI_API_KEY を設定

---

使い方（主要コマンド例）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- 実行エンジン起動（Engine）
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV に依存（development / paper_trading / live）
  - paper_trading の場合、MockBrokerClient を使用しデータは data/paper_trading.db（デフォルト）に記録され、本番 DB と分離されます。
  - 起動時に data/stop_requested.flag が存在すると起動を行わず終了します。
  - 実行中は data/execution.pid に PID を書きます（PID に基づくプロセス生存確認を行います）。

- 監視プロセス起動（監視ループ）
  - python -m kabusys.run_monitoring
  - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で秒数を変更可（1 以上の整数）。
    - MONITOR_POLL_INTERVAL が不正な値の場合はデフォルトにフォールバックします。
  - 監視は実際（production） sqlite_path を使用（KABUSYS_ENV に依らない）。
  - 監視ループはプロジェクトルート/data/stop_requested.flag を監視し、存在時に終了します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH でも可）
  - レポートは稼働率、注文成功率、送信率、レイテンシ等を集計して PASS/FAIL 判定を出力します。

- AI（ニューススコア、レジーム判定）
  - ニューススコア: kabusys.ai.score_news を呼ぶ（API キーは OPENAI_API_KEY）
    - 例: from kabusys.ai.news_nlp import score_news
  - レジーム判定: kabusys.ai.regime_detector.score_regime
  - 両機能は OpenAI API キーを必要とします。キーは環境変数 OPENAI_API_KEY で設定してください。
  - API 呼び出しはリトライ・フェイルセーフ実装あり。失敗時はスコアをフォールバックして処理継続します。

---

重要な環境変数（抜粋、デフォルト値を含む）
- 必須（実行には設定が必要）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- KABUSYS_ENV: 実行環境（development / paper_trading / live） デフォルト: development
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading の SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/…、デフォルト: INFO）
- OPENAI_API_KEY: OpenAI を利用する場合に必須
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知（任意）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動的な .env 読み込みを無効化

※ .env 自動ロード:
- プロジェクトルート（.git または pyproject.toml がある場所）を検出し、.env → .env.local の順で読み込みます（OS 環境変数は上書きされません）。テスト等で無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

停止・Kill スイッチの挙動
- Graceful stop フラグ:
  - run_monitoring / run_execution はプロジェクトルート/data/stop_requested.flag を監視し、存在するとループを終了します（これを使って外部から停止要求が出せます）。
- Kill Switch:
  - RiskMonitor / KillSwitch の組み合わせにより、ドローダウンやポジション上限等の致命的条件を検出すると data/kill.flag を書き込みます。
  - ExecutionEngine は起動時に kill.flag の存在を確認し、存在する場合は起動を行わない、または運用中に kill.flag が立てられると停止する設計になっています。
  - KILL_FLAG_CLEAR_ON_START=1 に設定すると Engine 起動時に自動で kill.flag をクリアしますが、本番では推奨されません（安全装置の自動解除となるため）。

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定読み込みロジック
  - config_setup.py               — .env 作成ウィザード（CLI）
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - execution/                     — 発注・注文管理関連（OrderManager 等）
  - monitoring/
    - monitoring_db.py            — SQLite 監視 DB 層（DDL / CRUD）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - utils/
    - process_priority.py
  - data/ (ランタイムで生成される／管理する)
    - execution.pid
    - kill.flag
    - stop_requested.flag
    - monitoring.db / paper_trading.db（デフォルトパスは data/ 以下）

---

運用上の注意
- 本プロジェクトは実際の発注を伴う可能性があるため、本番（KABUSYS_ENV=live）で実行する前に設定検証（validate_config）やペーパートレードでの十分な検証を行ってください。
- .env は機密情報（API トークン、パスワード）を含むため絶対に Git にコミットしないでください。
- OpenAI 等外部 API の利用はコストとレート制限に注意してください。AI モジュールは失敗時にフェイルセーフで処理を続行するよう設計されていますが、頻繁な呼出しは避けてください。
- プロセス優先度設定（psutil を利用）は OS によって挙動が異なります。アクセス権限の都合で設定に失敗することがあります（ログに警告が出ます）。

---

その他
- 本 README はコードベースに含まれるコメント・ドキュメントから要点をまとめたものです。各モジュールの詳細は該当ソース（src/kabusys/...）内の docstring／コメントを参照してください。
- ご不明点があれば、どの部分を詳しく説明してほしいかを教えてください（CLI の使い方、.env のサンプル、特定モジュールの API 仕様など）。

---