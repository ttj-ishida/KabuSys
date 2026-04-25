KabuSys
======

日本株自動売買システム（簡易ドキュメント）

概要
---
KabuSys は日本株の自動売買・研究・監視を支援する Python ベースのシステムです。本リポジトリは以下の主要機能を持ちます。

- 発注エンジン（ExecutionEngine）: ブローカークライアント経由で発注・注文管理を行う。
- 監視（Monitoring）: システム状態・注文状況・リスク指標を定期ポーリングしてログ/アラート化。Kill Switch 機能で異常時に発注を停止可能。
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ計算、セクター制限など。
- リサーチ: ファクター計算（モメンタム、バリュー、ボラティリティ）や特徴量探索（IC計算等）。
- AI モジュール: ニュースのセンチメント評価（OpenAI を利用）や市場レジーム判定。
- ツール: ペーパートレード検証レポート生成、環境設定ウィザード、設定検証 CLI 等。

主な機能一覧
---
- 実行環境分離:
  - KABUSYS_ENV により development / paper_trading / live を切替。paper_trading 時は MockBroker を利用し、ペーパートレード用 DB に記録。
- 監視:
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせた MonitoringEngine。監視データは SQLite に永続化。
  - KillSwitch による自動停止（kill.flag）。
- ポートフォリオ構築:
  - 候補選定（score/equal）、重み算出、ポジションサイズ計算（単元株丸め・リスク制約・aggregate cap）。
  - セクター集中制限、レジーム乗数。
- リサーチ:
  - DuckDB を用いたファクター計算（prices_daily / raw_financials 参照）。
  - 将来リターン・IC・統計サマリ等。
- AI / NLP:
  - OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント集計（ai_scores への書込み）。
  - マクロ記事を用いた市場レジーム判定（market_regime テーブル）。
- 運用支援:
  - 対話式 .env ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ペーパートレード検証レポート（tools/paper_verification_report）

前提（Prerequisites）
---
- Python 3.10+（typing | list|dict の表記から推奨）
- 必要パッケージ（主なもの）:
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（validate_config が YAML ファイルのパース検証を行う場合）
- SQLite は標準ライブラリで使用
- システムでのファイル作成権限（data/, logs/ 等）

セットアップ手順
---
1. リポジトリをクローンして venv を作成:
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール（例）:
   - pip install duckdb psutil openai
   - （開発時）pip install PyYAML

3. .env の準備:
   - 対話式ウィザード: python -m kabusys.config_setup
     - これにより .env を生成できます（.env は絶対に Git にコミットしないでください）。
   - あるいは .env を手動作成。主要な環境変数（デフォルトや意味は次節参照）。

4. 設定検証:
   - python -m kabusys.validate_config
   - 厳密モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

主要な環境変数（抜粋）
---
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABUSYS_ENV — execution/監視の挙動を切替（development / paper_trading / live。デフォルト: development）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LOG_DIR — ログ保存ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY — OpenAI API キー（AI 機能利用時必須）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

使い方（コマンド）
---
- 環境設定ウィザード（.env 作成）:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）:
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
    - 起動時に data/execution.pid が作成されます。
    - 停止要求はプロジェクトルートの data/stop_requested.flag を作成するとスレッドを止めて終了します。
    - kill.flag（Settings.kill_flag_path にデフォルト data/kill.flag）は発注停止シグナル（Kill Switch）です。KillSwitch が発動すると ExecutionEngine を止める仕組みになっています。

- 監視ループ起動（Monitoring）:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（秒、デフォルト 60）。
  - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用して監視ログを記録します。

- ペーパートレード検証レポート生成:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定（デフォルトは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

- プログラム的に各機能を利用:
  - AI スコアリング: from kabusys.ai import score_news
  - リサーチ関数群: from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary

停止方法
---
- 優雅な停止（監視が検出して停止するパターン）:
  - KillSwitch が条件を満たすと data/kill.flag に理由を書き込み、ExecutionEngine に停止指示を出します。
- 強制停止（外部から）:
  - data/stop_requested.flag を作成すると run_execution/run_monitoring のループが終了します（両スクリプトともこのフラグを監視）。
  - またはプロセスに SIGINT/Ctrl-C。

ログ
---
- デフォルトで stdout（コンソール）と日次ローテートのファイルログ（logs/<app_name>.log）を出力します。
- ログ設定: kabusys.utils.logging_setup.setup_logging に従う。LOG_DIR 環境変数でログディレクトリを変更可能。

ディレクトリ構成（主なファイル）
---
以下はソースツリー（src/kabusys 内）の主要ファイル / モジュール一覧（抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py              — ニュース NLP → ai_scores 書込み
    - regime_detector.py       — 市場レジーム判定
    - __init__.py
  - monitoring/
    - monitoring_db.py         — SQLite 永続化層
    - system_monitor.py        — システム状態・データ鮮度監視
    - trade_monitor.py         — 注文関連監視（コメント参照）
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - monitoring_engine.py     — 複数モニタの統合ループ
    - kill_switch.py           — kill.flag 管理
    - alert_manager.py         — （アラート送信管理: LINE 等） ※実装参照
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み計算
    - position_sizing.py       — 発注株数計算
    - risk_adjustment.py       — セクター制限・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py       — ファクター計算（Momentum/Value/Volatility）
    - feature_exploration.py   — 将来リターン / IC / 統計サマリ
    - __init__.py
  - utils/
    - logging_setup.py         — ログ初期化ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity 設定
    - __init__.py
  - execution/                 — Execution に関するコンポーネント群（Engine, BrokerFactory, OrderManager...
  - data/                      — データパイプライン / DB 周りのモジュール（prices_daily など）

運用上の注意
---
- paper_trading モードは本番 DB と完全分離することを想定しています。PAPER_TRADING_SQLITE_PATH を確認してください。
- OpenAI を利用する機能（news_nlp / regime_detector）は API キー（OPENAI_API_KEY）が必要です。API 失敗時は安全側のフォールバック設計（0.0 等）になっていますが、API コストやレート制限に注意してください。
- validate_config は PyYAML がない場合に YAML の内容検証をスキップします。config/*.yaml を使う場合は PyYAML をインストールしてください。
- ログディレクトリの作成に失敗した場合はファイルログ出力が無効化され、代わりに stdout のみになります。

トラブルシューティング
---
- DB ファイルが見つからない:
  - デフォルトでは data/kabusys.duckdb と data/monitoring.db（および paper_trading.db）が使用されます。適切なパスを .env で設定するか、--db オプションを使用してください。
- OpenAI 呼び出しでエラーが出る:
  - OPENAI_API_KEY が設定されているか、ネットワーク/レート制限を確認してください。モジュールはリトライとフェイルセーフを実装しています。

最後に
---
この README はコードベース内のドキュメントと実装コメントを元に作成しています。実運用前に python -m kabusys.validate_config を実行し、設定やファイルパス、環境変数を必ず確認してください。追加の実装や詳細は各モジュール内の docstring やコメントを参照してください。