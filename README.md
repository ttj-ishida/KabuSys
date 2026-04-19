# KabuSys

日本株自動売買システムのライブラリ／実行スクリプト群。  
このリポジトリはトレードエンジン（Execution）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株自動売買に必要なコンポーネントを集めたコードベースです。主な役割は次のとおりです。

- ExecutionEngine: ブローカーとのやり取り／注文管理／リスク管理を行う本体（paper_trading モードあり）。
- Monitoring: システム状態、注文状態、リスク条件を定期チェックし、必要に応じてアラート発行や Kill Switch を発動。
- Portfolio construction: 候補選定・重み付け・ポジションサイズ計算など、ポートフォリオ構築ロジック（純粋関数群）。
- Research: DuckDB 上の時系列データからファクター計算・将来リターン・IC 等を算出。
- AI 補助: ニュース記事を LLM（OpenAI）でスコアリングし、銘柄スコアやマクロセンチメントを算出。
- ユーティリティ: ロギング設定、プロセス優先度設定、設定ウィザード・検証ツールなど。

設計上の特徴:
- 環境変数／.env を利用した設定管理（自動ロード機能あり）。
- paper_trading モードは本番 DB と分離（専用 SQLite）。
- DuckDB を分析用 DB として利用。
- フェイルセーフ（LLM失敗時のフォールバック、部分的な書き込み保護等）。

---

## 機能一覧（主要）

- 実行関連
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い data/paper_trading.db に記録。
  - 注文管理、リスク管理、リコンサイル処理等（Engine 側の実装に依存）。

- 監視関連
  - run_monitoring.py: SystemMonitor のポーリングループを起動。デフォルト 60 秒間隔（環境変数で変更可）。
  - MonitoringEngine: SystemMonitor / TradeMonitor / RiskMonitor を束ね、KillSwitch と AlertManager を用いて自動対応。
  - MonitoringDB: system_status, trade_logs, positions, risk_logs, dashboard 等の永続化。
  - RiskMonitor / KillSwitch: ドローダウン・ポジション数等に基づく停止判定。

- ポートフォリオ構築
  - 候補選定（スコア降順）、等加重・スコア重み配分、リスクベースのポジションサイズ計算。
  - セクターキャップ適用、レジーム乗数計算。

- リサーチ
  - ファクター計算（モメンタム / ボラティリティ / バリュー）。
  - 将来リターン計算、IC（Spearman）計算、統計サマリ。

- AI（OpenAI）
  - news_nlp.score_news: raw_news をまとめて LLM に送信し銘柄ごとの ai_score を ai_scores テーブルに書き込む。
  - regime_detector.score_regime: ETF の MA 乖離と LLM によるマクロセンチメントを合成して market_regime を更新。

- ツール
  - config_setup.py: .env の対話的生成／更新ウィザード。
  - validate_config.py: 環境変数や config/*.yaml を起動前に検証。
  - tools/paper_verification_report.py: ペーパートレード DB を集計し PASS/FAIL 判定（稼働率、約定率、レイテンシ等）。

- ユーティリティ
  - logging_setup.setup_logging: 統一的なログ設定（コンソール + 日次ローテートファイル）。
  - process_priority.set_process_priority / set_cpu_affinity: プロセス優先度 / CPU affinity の設定。

---

## セットアップ手順

1. Python を用意
   - 推奨: Python 3.10+（コードはタイプヒントで新しい構文を使用）

2. 依存パッケージをインストール
   - 必要な主なパッケージ:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証を行う場合に推奨）
   - 例:
     - pip install duckdb psutil openai PyYAML

   > 注: requirements.txt が存在する場合は `pip install -r requirements.txt` を使用してください。

3. プロジェクトルートにデータ・ログディレクトリを作成（通常は自動作成されますが手動作成して権限を確認してください）
   - data/
   - logs/

4. .env を作成
   - 対話的に作る: python -m kabusys.config_setup
   - 生成後、必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）を設定してください。
   - 自動ロードはデフォルトで有効。無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - 警告を厳格に扱いたい場合: python -m kabusys.validate_config --strict

6. （OpenAI を使う機能を利用する場合）OPENAI_API_KEY を環境変数に設定

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB; デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE: instant | partial | never | reject (paper_trading のフィルモード)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- OPENAI_API_KEY (AI 機能を使う場合)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔秒; デフォルト 60)
- KILL_FLAG_CLEAR_ON_START (起動時に kill.flag を自動クリアするか: 0/1)

.env 例は config_setup の出力を参照してください（.env は絶対に Git にコミットしないでください）。

---

## 使い方（コマンド例）

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading のとき、MockBrokerClient を使い paper_trading.db に記録（本番 DB とは分離）
    - 起動時に data/stop_requested.flag が存在すると起動しない
    - 実行中に data/stop_requested.flag が作成されるとエンジンに停止を通知
    - 実行中は data/execution.pid に PID が書かれます

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は本番 sqlite_path（Settings.sqlite_path）を常に使用します（環境に依らず）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH

- AI 関連関数（プログラム内 API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## シグナル / フラグファイル

- 停止要求（run_execution / run_monitoring が参照）
  - data/stop_requested.flag を作成すると両スクリプトは検知して終了動作を行います。

- Kill Switch（Execution を停止させる重大アラート）
  - KillSwitch は data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では推奨されません）。

注意: flag を手動で消す / 作る場合は適切な理由と手順を確認してください。

---

## ロギング

- ログはデフォルトで logs/ ディレクトリに日次ローテートファイルとして出力されます（例: logs/execution.log, logs/monitoring.log）。
- コンソール出力は stdout に行われます。
- ログレベルは LOG_LEVEL 環境変数または setup_logging の level 引数で制御可能。

---

## トラブルシューティングと注意点

- process priority 設定:
  - set_process_priority はプラットフォーム依存の操作を行います。権限不足で警告が出る場合があります（sudo が必要なケースあり）。
- DuckDB / SQLite:
  - DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、コード内で空リストを回避する配慮があります。
- OpenAI 呼び出し:
  - API エラーやレート制限は指数バックオフでリトライしますが、最終的に失敗した場合はフェイルセーフ（スコア = 0 など）で継続します。
- .env 自動読み込み:
  - 自動的にプロジェクトルートの .env / .env.local を読み込みます（CWD に依存せず __file__ を基準に探索）。無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1。

---

## ディレクトリ構成（主要ファイル抜粋）

src/kabusys/
- __init__.py
- config.py                      — 環境変数／設定管理（自動 .env ロード）
- config_setup.py                — .env 対話ウィザード
- validate_config.py             — 設定検証 CLI
- run_execution.py               — ExecutionEngine 起動スクリプト
- run_monitoring.py              — SystemMonitor 起動スクリプト

src/kabusys/utils/
- logging_setup.py               — ログ設定ユーティリティ
- process_priority.py            — プロセス優先度 / CPU affinity

src/kabusys/monitoring/
- monitoring_db.py               — SQLite テーブル定義・永続化レイヤ
- system_monitor.py              — システム状態・データ鮮度監視
- risk_monitor.py                — ドローダウン・ポジション上限監視
- trade_monitor.py               — 注文状態監視（実装参照）
- kill_switch.py                 — kill.flag 書き込みロジック
- monitoring_engine.py           — 各 Monitor を束ねる

src/kabusys/execution/
- (ExecutionEngine・OrderManager 等の実装ファイル群)

src/kabusys/portfolio/
- portfolio_builder.py           — 候補選定・重み計算
- position_sizing.py             — 株数決定・スケーリング
- risk_adjustment.py             — セクターキャップ・レジーム乗数

src/kabusys/research/
- factor_research.py             — ファクター計算（momentum/value/volatility）
- feature_exploration.py         — 将来リターン・IC・統計サマリ

src/kabusys/ai/
- news_nlp.py                    — ニュースを LLM に投げて銘柄スコアを生成
- regime_detector.py             — MA 乖離 + LLM で市場レジーム判定

src/kabusys/tools/
- paper_verification_report.py   — Paper Trading の検証レポート生成ツール

その他:
- data/                          — DB / PID / flag 等（実行時に使用）
- logs/                          — ログファイル

---

## 開発メモ・設計上の留意点

- 多くのモジュールは「外部副作用を持たない純粋関数」と「DB への読み書きのみを行う永続化層」に分離されています。ユニットテストが書きやすい設計です。
- LLM 周りは失敗許容で実装され、API キー未設定時は例外を投げる設計（呼び出し側で対処）。
- 時刻の扱いはルックアヘッドバイアス回避に配慮され、target_date を引数に取り内部で datetime.today() を直接参照しないようになっています。

---

README の内容で不明点や、特定のモジュール（ExecutionEngine の起動方法や OrderManager の使い方、AI 部分のテスト方法など）について詳細が必要であれば、どの項目を深掘りしたいか教えてください。