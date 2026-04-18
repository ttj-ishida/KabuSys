# KabuSys

日本株自動売買システムのコアライブラリ群（実行エンジン、監視、ポートフォリオ構築、リサーチ、AI 補助機能など）。

この README はリポジトリ内の主要スクリプト / モジュール（run_execution, run_monitoring, config_setup, validate_config, tools 等）を使い始めるための手引きです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォームの骨組みを提供します。主な目的は次の通りです。

- 発注エンジン（ExecutionEngine）による注文管理・実行（本番 / ペーパートレード対応）
- システム稼働監視（SystemMonitor / MonitoringEngine）
- リスク監視（ドローダウン・ポジション上限など）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ計算）
- ファクター計算・特徴量探索（DuckDB を用いたリサーチ用モジュール）
- ニュース NLP を用いた銘柄センチメント評価、レジーム判定（OpenAI API 利用）
- 運用支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート生成）

設計上の特徴:
- 設定は .env / 環境変数中心（自動ロード機構あり、テスト時に無効化可）
- DuckDB / SQLite を分析・監視 DB に使用
- OpenAI を用いた LLM 呼び出しはフェイルセーフ（API 失敗時は安全にフォールバック）
- 起動スクリプト群で一貫したログ設定・プロセス優先度設定を行う

---

## 機能一覧

- ExecutionEngine
  - 本番（kabuステーション）とペーパートレード（MockBrokerClient）に対応
  - RiskManager / OrderManager / Reconciler を組み合わせた発注ワークフロー
  - ペーパートレード時は専用 SQLite（data/paper_trading.db）に記録して本番 DB と分離

- Monitoring
  - SystemMonitor: CPU/Mem/Disk、Execution プロセス監視、データ鮮度チェック
  - TradeMonitor, RiskMonitor: 注文の滞留・異常約定・ドローダウン・ポジション上限監視
  - MonitoringEngine: 各モニタをまとめて定期ポーリングし、Kill Switch やアラートに連携

- Portfolio（純粋関数）
  - 候補選定、等金額/スコア加重、セクターキャップ、レジーム乗数、ポジションサイズ計算

- Research
  - DuckDB ベースでファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC（情報係数）計算、統計サマリー

- AI
  - news_nlp: raw_news をまとめて OpenAI に送ることで銘柄ごとのセンチメントを ai_scores に保存
  - regime_detector: ETF（1321）MA200 とマクロニュースの LLM センチメントで市場レジーム判定

- ツール
  - config_setup: .env の対話式ウィザード生成
  - validate_config: 環境変数・config/*.yaml の事前検証 CLI
  - paper_verification_report: ペーパートレード DB の指標レポート生成

- ユーティリティ
  - logging_setup: 統一的なログ設定（stdout + 日次ローテートファイル）
  - process_priority: プラットフォーム差を吸収したプロセス優先度 / CPU affinity 設定

---

## セットアップ手順

前提
- Python 3.10 以上（typing の | 演算子等を使用）
- SQLite は標準ライブラリ、その他は pip でインストール

推奨パッケージ（例）
- duckdb
- psutil
- openai
- PyYAML（config 検証を行う場合に必要）

例: 仮想環境作成と依存インストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb psutil openai pyyaml
```

.env の準備（対話式）
```bash
python -m kabusys.config_setup
# ウィザードに従って .env を作成
```

設定検証
```bash
python -m kabusys.validate_config        # 警告は許容
python -m kabusys.validate_config --strict   # 警告も FAIL 扱い
```

注意点
- 自動で .env をプロジェクトルートから読み込みます（.env.local が優先で上書き）。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須環境変数（一部）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development | paper_trading | live）
- OPENAI_API_KEY（AI 機能を使用する場合）
- その他: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH（必要に応じて）

---

## 使い方

主なコマンド（プロジェクトルートから実行）

- ExecutionEngine を起動
  - 本番 / ペーパーを切り替えるのは KABUSYS_ENV 環境変数で制御
  - ペーパートレード時は MockBrokerClient が選ばれ、data/paper_trading.db を使用する
```bash
# 例: ペーパートレード起動
export KABUSYS_ENV=paper_trading
python -m kabusys.run_execution
```

- Monitoring を起動
  - 環境に関係なく monitoring は Settings.sqlite_path（デフォルト data/monitoring.db）を使用します
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で秒単位に変更可能（デフォルト 60）
```bash
python -m kabusys.run_monitoring
# 例: 30秒間隔
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring
```

停止制御（Kill Switch / Stop Flag）
- 監視ループや実行エンジンの停止はフラグファイルで制御します
  - stop_requested.flag（data/stop_requested.flag）: 監視プロセスや実行スレッドを終了させるための停止フラグ（run_monitoring/run_execution が参照）
  - kill.flag（Settings.kill_flag_path, デフォルト data/kill.flag）: KillSwitch が書き込み、ExecutionEngine に停止を促す（Risk 条件等）
- ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 推奨）

ツール
- 設定ウィザード
```bash
python -m kabusys.config_setup
```

- 設定検証
```bash
python -m kabusys.validate_config
```

- ペーパートレード検証レポート生成
```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB を指定する場合:
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```

AI 機能（プログラムから呼ぶ）
- news_nlp.score_news(conn, target_date, api_key=None)
  - DuckDB 接続オブジェクト（kabusys が使う DuckDB 接続）と target_date を渡して実行
  - api_key を None にすると環境変数 `OPENAI_API_KEY` を参照
- regime_detector.score_regime(conn, target_date, api_key=None)
  - 同様に DuckDB 接続と target_date を渡して実行

ログ
- デフォルトで logs/ ディレクトリに日次ローテートのログファイルを出力します（logs/<app_name>.log）
- ログレベルは環境変数 `LOG_LEVEL` または setup_logging の引数で設定可能

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: execution 環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリア（"1" で有効）

---

## ディレクトリ構成（主要ファイル）

（プロジェクトルート直下の src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数設定の読み込み/Settings クラス
  - config_setup.py              — .env 対話ウィザード
  - validate_config.py           — 起動前設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト

- src/kabusys/execution/
  - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py
    — 発注系の主要コンポーネント（Engine / Broker 抽象 / リスク管理など）

- src/kabusys/monitoring/
  - monitoring_db.py             — SQLite を使った永続化 API（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py            — システム状態・データ鮮度監視
  - trade_monitor.py             — 注文滞留・約定異常監視（詳細実装ファイルあり）
  - risk_monitor.py              — ドローダウン・ポジション上限監視
  - kill_switch.py               — kill.flag 書き込み等
  - monitoring_engine.py         — 各 Monitor を束ねるポーリングエンジン
  - alert_manager.py             — アラート送信管理（LINE など）

- src/kabusys/portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py

- src/kabusys/research/
  - factor_research.py           — momentum/value/volatility 等の計算
  - feature_exploration.py       — 将来リターン・IC・統計サマリー

- src/kabusys/ai/
  - news_nlp.py                  — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py           — レジーム判定（MA200 + マクロセンチメント）

- src/kabusys/tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成

- src/kabusys/utils/
  - logging_setup.py             — ログ設定ユーティリティ
  - process_priority.py          — プロセス優先度 / CPU affinity 設定

- config/
  - system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml
    — 各種 YAML 設定（存在しない場合は警告）。generate スクリプトで生成することを想定

- data/
  - *.db, *.pid, stop_requested.flag, kill.flag
    — デフォルトでデータ・フラグを配置するディレクトリ（自動作成されることが多い）

---

## 運用上の注意・ベストプラクティス

- 本番運用時は KABUSYS_ENV=live を必ず確認し、設定ファイル・LINE 通知設定などを十分に検証してください。
- kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は開発時のみ使用することを推奨します。本番では 0（クリアしない）が安全です。
- OpenAI など外部 API を使う処理はレート制限や一時エラーに対してリトライロジックが組まれていますが、コスト・レート制限には注意してください。
- DuckDB / SQLite のパスやログディレクトリは適切な永続領域（ディスク容量）に設定してください。
- .env は絶対に Git にコミットしないでください（config_setup のヘッダにも明記）。

---

必要であれば README に「インストール用 requirements.txt」や具体的な systemd / supervisor 用の起動ユニット例、より詳細な設定サンプル（.env.example）などを追加できます。どの情報を補足したいか教えてください。