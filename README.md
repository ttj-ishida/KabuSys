README.md

概要
---
KabuSys は日本株向けの自動売買・リサーチ・監視フレームワークです。  
主に以下の責務を持つモジュール群で構成されています。

- Execution: 発注エンジン（本番 / ペーパートレード対応）
- Monitoring: システム稼働監視、注文監視、リスク監視、Kill Switch
- Research: ファクター計算・特徴量探索
- Portfolio: 銘柄選定、重み付け、ポジションサイズ計算
- AI: ニュース NLP（OpenAI を利用したセンチメント評価）・市場レジーム判定
- Tools: レポート生成スクリプト等
- 設定ユーティリティ: .env ウィザード / 設定検証 CLI

主な機能
---
- ExecutionEngine の起動（本番 / paper_trading 切り替え）
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を利用して data/paper_trading.db に記録（本番 DB と分離）
- Monitoring（周期ポーリング）
  - システムリソース（CPU/メモリ/ディスク）、Execution プロセスの生存チェック
  - 注文滞留・約定異常価格検出
  - ドローダウン・ポジション上限の監視と Kill Switch の発動（data/kill.flag 書き込み）
  - 監視ログの永続化（SQLite）
- Research
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（Information Coefficient）等の解析ユーティリティ
- Portfolio construction
  - 候補選定、等配分・スコア重み・リスクベースのポジションサイズ計算
  - セクターキャップ適用、レジームに応じた資金乗数
- AI（OpenAI）
  - ニュース記事をまとめて LLM（gpt-4o-mini 等）に投げ、銘柄ごとのスコアを ai_scores テーブルへ書込み
  - マクロニュース + ETF MA200 を用いた市場レジーム判定
- ツール
  - Paper Trading の検証レポート生成（ツールは SQLite の paper_trading DB を解析）

準備 / セットアップ
---
1. リポジトリをクローンしプロジェクトルートへ移動

2. Python 仮想環境を作成して有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 必須（実行・監視・リサーチ・AI の主要依存）:
     - duckdb
     - psutil
     - openai
   - オプション:
     - PyYAML （config/*.yaml の検証に使用。未インストール時は検証をスキップ）
   - 例:
     - pip install duckdb psutil openai pyyaml

4. .env の作成
   - 対話式ウィザードを用意しています:
     - python -m kabusys.config_setup
   - あるいは .env を手動で作成（プロジェクトルートに配置）。主な環境変数:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH (例: data/kabusys.duckdb)
     - SQLITE_PATH (監視 DB: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB: data/paper_trading.db)
     - OPENAI_API_KEY (AI 機能を使う場合必須)
     - LOG_LEVEL (DEBUG|INFO|…)
     - KILL_FLAG_CLEAR_ON_START (0/1) — 本番では 0 推奨

5. 設定の検証（起動前推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit code=1）になります。

使い方（主要スクリプト）
---
- ExecutionEngine の起動
  - 本番/ペーパー切り替えは KABUSYS_ENV に依存
  - 起動:
    - python -m kabusys.run_execution
  - paper_trading 環境では MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）へ記録します。
  - 停止:
    - data/stop_requested.flag を作成すると実行中スレッドが検知して終了します。
    - monitoring の KillSwitch が data/kill.flag を書くと ExecutionEngine 側で検知して停止する実装（Kill Switch 動作フローを合わせて確認してください）。

- Monitoring の起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60）
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を参照します（monitoring は環境にかかわらず本番 DB を使用）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH

- 設定ウィザード / 検証
  - .env の作成: python -m kabusys.config_setup
  - 設定検証:    python -m kabusys.validate_config [--strict]

重要な環境変数（主な一覧）
---
- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API（必須）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）
- OPENAI_API_KEY — OpenAI API を使う場合に必須
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（1=クリア, 0=クリアしない）

停止 / Kill フラグ
---
- run_monitoring.py / run_execution.py は data/stop_requested.flag を監視して自ら終了します。
- KillSwitch（監視側）は data/kill.flag を書き込み、ExecutionEngine に対して停止シグナルを送ります。  
  - KillSwitch はドローダウンやポジション上限等の条件で発動します。
- ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動でクリアします（本番では 0 推奨）。

AI（OpenAI）に関する注意
---
- news_nlp / regime_detector は OpenAI（gpt-4o-mini 等）を使用します。OPENAI_API_KEY を設定してください。
- API 呼び出しは 429 / ネットワーク断 / タイムアウト / 5xx をエクスポネンシャルバックオフでリトライする仕組みを持っています。
- LLM レスポンスは JSON 検証とスコアのクリッピング（±1.0）を行い、失敗時はフェイルセーフ（スコア 0.0 など）で継続します。

ディレクトリ構成（抜粋）
---
src/kabusys/
- __init__.py
- config.py                — 環境変数 / Settings 管理（.env 自動ロード機能あり）
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 起動前設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor 起動スクリプト

- execution/                — 発注エンジン関連（Engine, OrderManager, BrokerFactory 等）
- monitoring/
  - monitoring_db.py        — SQLite テーブル初期化 / DB ラッパー
  - system_monitor.py       — システム状態監視
  - trade_monitor.py        — 注文滞留 / 約定異常監視
  - risk_monitor.py         — ドローダウン / ポジション数監視
  - kill_switch.py          — Kill Switch 実装
  - monitoring_engine.py    — 各 Monitor を束ねる実行ループ
  - alert_manager.py        — アラート通知（LINE など、実装箇所）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py      — momentum / volatility / value 等
  - feature_exploration.py  — forward returns / IC / summary
- ai/
  - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py      — レジーム判定（MA200 + マクロ NLP）
- tools/
  - paper_verification_report.py — Paper Trading レポート生成
- utils/
  - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ

補足 / 参考
---
- Settings はプロジェクトルートの .env / .env.local を自動読込します（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可能）。
- monitoring_db.init_monitoring_db() は既存 DB へのマイグレーション（カラム追加）を試みます（冗長実行可能）。
- run_execution / run_monitoring はそれぞれ data/stop_requested.flag により安全に終了できます。監視側は監視 DB を用いてログとリスクイベントを管理します。

トラブルシュート
---
- PyYAML がないと config/*.yaml の内容チェックがスキップされますが、実行自体には直接影響しません。
- OpenAI 呼び出しで APIKey がない場合、AI 機能は ValueError を出します。AI を使わない場合は APIKey を設定しなくても他機能は動きます（ただし regime_detector など一部機能は使えません）。
- psutil によるプロセス優先度設定は権限に依存するため失敗する場合があります（警告ログのみ）。

ライセンス等
---
README では言及していません。プロジェクトのライセンスはリポジトリのルートにある LICENSE を参照してください（もし無い場合は運用チームに確認してください）。

最後に
---
まずは .env を作成 → python -m kabusys.validate_config で設定を検証 → python -m kabusys.run_monitoring と python -m kabusys.run_execution を適切な順で起動して動作を確認してください。ご不明点があれば、具体的なエラーメッセージやログを添えて質問してください。