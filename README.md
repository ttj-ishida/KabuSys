# KabuSys

日本株向け自動売買システムの一部コンポーネント群（リサーチ、ポートフォリオ構築、実行エンジン、監視、AI補助機能など）。

このリポジトリには本番／ペーパートレードの運用を想定したモジュール群が含まれます。各モジュールは可能な限りフェイルセーフに設計されており、環境変数で挙動を切り替えられます。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要コマンド）
- 環境変数（主要）
- ファイル・ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株自動売買に関するロジックをモジュール化した Python パッケージ群です。
- 主なコンポーネント：
  - ExecutionEngine（発注・リスク管理・オーダーマネージャ）
  - Monitoring（システム稼働・注文状態・リスク監視）
  - Research（ファクター計算、特徴量解析）
  - Portfolio（候補選定・ウェイト計算・ポジションサイズ決定）
  - AI（ニュース NLP によるセンチメント評価、レジーム判定）
  - Tools（ペーパートレード検証レポート等）
- DB: DuckDB（分析向け）および SQLite（監視・ペーパートレード用）を使用。

---

機能一覧
- 設定管理
  - .env ファイル自動読み込み（.env / .env.local）
  - 対話式環境設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
- 実行エンジン
  - 実際のブローカー／Mock ブローカー（KABUSYS_ENV=paper_trading 時）を使い分け
  - RiskManager / OrderManager / Reconciler 等の組み立て
  - PID ファイル管理、停止フラグ検出による安全停止
- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク/プロセス稼働・データ鮮度確認
  - TradeMonitor: 滞留注文や約定異常の検出
  - RiskMonitor: ドローダウン・ポジション上限監視
  - Kill Switch: 条件に応じて停止フラグを書き込み ExecutionEngine を止める
  - 監視ログの永続化（SQLite）
- 研究・ポートフォリオ
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 特徴量探索・IC 計算・統計サマリ
  - ポートフォリオ構築（候補選定・等重量/スコア重み・リスクベースのポジションサイズ）
  - セクター上限適用・レジーム乗数
- AI（OpenAI）
  - ニュース集合を LLM（gpt-4o-mini 等）でセンチメント評価して ai_scores に書き込み
  - マクロニュースを用いた市場レジーム判定
  - API 呼び出しは冪等性・リトライ・フェイルセーフに配慮
- ツール
  - Paper Trading 検証レポート生成（成功率、稼働率、レイテンシ等の評価）

---

セットアップ手順（開発環境の一例）
1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - 必須と思われる主なパッケージ: duckdb, psutil, openai, PyYAML（検証用）

   ※ requirements.txt が無い場合は上記パッケージを個別にインストールしてください。

4. .env の準備
   - 対話式ウィザードで作成：
     - python -m kabusys.config_setup
   - または手動で .env を作成（リポジトリルート）。重要な環境変数は以下参照。

5. 設定検証
   - python -m kabusys.validate_config
   - 警告を厳格に扱う場合は --strict を付与

6. データディレクトリ作成（必要に応じて）
   - mkdir -p data

注意:
- 自動で .env を読み込む機能はデフォルトで有効です。自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

主要な環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN : J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD     : kabuステーション API パスワード
- 運用モード
  - KABUSYS_ENV : development | paper_trading | live  （デフォルト: development）
    - paper_trading 時は MockBrokerClient を使用し、data/paper_trading.db を使って完全に分離したペーパートレードを行います
- データパス
  - DUCKDB_PATH  : DuckDB ファイル（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH  : 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH : ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- AI (OpenAI)
  - OPENAI_API_KEY : OpenAI API キー（AI モジュールを利用する場合必須）
- 監視関連
  - MONITOR_POLL_INTERVAL : run_monitoring のポーリング間隔（秒、デフォルト 60）
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START（詳細は Settings 参照）
- その他
  - LOG_LEVEL : ログレベル（DEBUG/INFO/...）

---

使い方（主要コマンド例）
- 環境設定ウィザード
  - python -m kabusys.config_setup
    - --env-file で出力先を指定可能

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い data/paper_trading.db に記録します
    - エンジンは data/stop_requested.flag を検出すると安全に停止します
    - 実行中は data/execution.pid に PID を書きます

- 監視プロセス（SystemMonitor のシンプルループ）起動
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒、デフォルト 60）
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用します
    - 停止は data/stop_requested.flag を置くことで行います

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
    - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 関連（ニューススコア・レジーム判定）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime をアプリケーションから呼び出して使用
  - OpenAI API キー（OPENAI_API_KEY）または api_key 引数が必要

停止フラグの扱い
- stop/kill フラグ類:
  - data/stop_requested.flag : run_* スクリプトで監視する停止フラグ（存在でプロセスが停止）
  - data/kill.flag : KillSwitch が書き込むフラグ（ExecutionEngine に停止シグナルとして使用）
- KillSwitch は条件（ドローダウン超過・ポジション上限超過など）に応じて kill.flag を書き、ExecutionEngine を停止させます。

ログ出力とプロセス優先度
- 起動スクリプトは最初に set_process_priority("high") を試みます（psutil を使用）。
- LOG_LEVEL 環境変数でログレベルを指定可能。

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数/設定読み込みロジック（.env 自動ロード含む）
  - config_setup.py            — 対話式 .env ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
  - utils/
    - process_priority.py      — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py         — SQLite 永続化層（監視ログ）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py         — （未表示: アラート通知管理）
  - execution/
    - execution_engine.py      — ExecutionEngine（起動・セッション管理）
    - broker_factory.py        — ブローカークライアント生成（Mock/実装）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - order_record.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py              — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py      — マクロ＋価格でレジーム判定（OpenAI）
  - data/                      — 実行時生成される DB や PID/flag の置き場（例: data/*.db / data/*.flag）
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート生成

（上記は主要ファイルの抜粋です。詳細は該当モジュールの docstring を参照してください。）

---

開発上の注意
- LLM (OpenAI) を用いる機能は API キーが必要です。失敗時は多くの処理がデフォルト値（例: 0.0）でフォールバックする設計ですが、運用時は必ずキーを設定してください。
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください。
- 本番運用（KABUSYS_ENV=live）の場合は設定を慎重に確認してください（validate_config の live ガードを参照）。

---

トラブルシュート（よくある質問）
- 「.env が読み込まれない」
  - プロジェクトルートが自動検出されないと自動ロードはスキップされます。KABUSYS_DISABLE_AUTO_ENV_LOAD を設定していないか確認、または手動で .env を読み込んでください。
- 「監視ログが作成されない」
  - Settings.sqlite_path のパス先を確認し、parent ディレクトリが存在するか確認してください。validate_config でパスをチェックできます。
- 「OpenAI 呼び出しで失敗が多い」
  - ネットワーク・レート制限を確認。news_nlp/regime_detector は再試行ロジックを持ちますが、APIキーやネットワークの品質が重要です。

---

貢献・拡張
- 新しい戦略、ブローカー実装、ログのエクスポート、アラートの追加などを歓迎します。各機能は可能な限り純粋関数や小さなクラスに分割してあるため、差し替えやテストがしやすい設計になっています。

---

以上。必要であれば README に含めるサンプル .env テンプレートや追加の起動例（systemd / Docker / docker-compose 用のサンプル）を作成します。どの形式（plain text / Markdown）で欲しいか、また追記したい情報があれば教えてください。