# KabuSys — 日本株自動売買システム

簡潔な説明書（README.md）

このリポジトリは日本株向けの自動売買・リサーチ基盤（KabuSys）です。戦略の研究・ファクター計算、ポートフォリオ構築、発注エンジン（実行/ペーパートレード）、監視・アラート、LLMを用いたニュースNLP / レジーム判定などを含みます。

---

## プロジェクト概要

- 目的: 日本株アルゴリズムの研究・バックテスト・実運用（発注）および運用監視を統合するツール群。
- 主な技術:
  - DuckDB（時系列・分析データ）
  - SQLite（監視ログ / ペーパートレード DB）
  - psutil（システム情報）
  - OpenAI（ニュースセンチメント・レジーム判定）
  - ロギング（コンソール + 日次ローテーション）
- 環境切替:
  - KABUSYS_ENV = development / paper_trading / live
  - paper_trading では MockBrokerClient を用い、ペーパートレード専用 DB（data/paper_trading.db）に記録されるため本番 DB と分離されます。

---

## 機能一覧

- execution（ExecutionEngine）
  - ブローカー接続（実口座 or モック）
  - オーダーマネージャ、リスクマネージャ、注文・約定ログの永続化
  - PID / stop フラグ（data/execution.pid, data/stop_requested.flag）対応

- monitoring（MonitoringEngine）
  - SystemMonitor: CPU/メモリ/ディスク、プロセス稼働、データ鮮度監視
  - TradeMonitor: 注文滞留・約定異常の検出（trade_logs 参照）
  - RiskMonitor: ドローダウン、ポジション数上限の監視（dashboard / positions）
  - KillSwitch: 条件に応じて data/kill.flag を書き込み ExecutionEngine を停止
  - AlertManager（アラート送信機能）と連携（LINE等）

- research
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計

- portfolio
  - 候補選定、重み付け（等金額 / スコア加重）、ポジションサイズ計算
  - セクター上限・レジーム乗数の適用

- ai
  - news_nlp: ニュース記事をOpenAIでスコアリングして ai_scores に格納
  - regime_detector: ETF（1321）MA とマクロニュースの LLM 評価を合成して日次レジーム判定

- tools
  - paper_verification_report: ペーパートレード DB を解析し期間ごとの PASS/FAIL レポートを生成

---

## セットアップ手順（開発環境・実行手順）

前提:
- Python 3.10+ を推奨（型注釈や近年のライブラリ互換性のため）
- 仮想環境の使用を推奨（venv / pyenv / conda 等）

1. リポジトリをクローンして作業ディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成・有効化（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール  
   （requirements.txt はリポジトリに無い場合があるため、主な依存を示します）
   ```
   pip install duckdb psutil openai PyYAML
   ```
   ※ 実行環境に応じて追加のパッケージが必要になる場合があります（例: sqlite3 は標準付属）。

4. .env の作成  
   対話式ウィザードで .env を生成できます：
   ```
   python -m kabusys.config_setup
   ```
   手動で作る場合の最小必須環境変数:
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   推奨のその他:
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
   - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH — デフォルト: data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
   - OPENAI_API_KEY — AI 機能を使う場合に必須
   - LOG_LEVEL — DEBUG/INFO/…

   自動で .env/.env.local を読み込む仕組みが Settings モジュールに実装されています（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

5. 設定検証（起動前チェック）
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict  # 警告も失敗扱い
   ```

6. データディレクトリ・ログディレクトリの作成  
   実行時に自動作成されますが、権限やパスが問題になる場合は手動作成してください。
   - data/ (各種 DB・PID/flag)
   - logs/ (ログファイル)

---

## 使い方（主要コマンド・実行例）

- ExecutionEngine を起動（本番/ペーパートレードは KABUSYS_ENV に従う）
  ```
  python -m kabusys.run_execution
  ```
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中は data/execution.pid に PID を書きます。
  - paper_trading 環境では MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）に記録します。
  - プロセス優先度は起動時に "high" に設定されます（platform に依存、失敗時は警告）。

- Monitoring（監視ループ）を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能。デフォルトは 60 秒。
    例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - Monitoring は KABUSYS_ENV にかかわらず sqlite_path（監視 DB）を本番のパスから接続します（監視ログは共通に取る想定）。
  - 終了は data/stop_requested.flag を作成するか KeyboardInterrupt（Ctrl+C）。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db --from 2026-04-01 --to 2026-04-11
  ```
  または環境変数で DB を指定:
  ```
  export PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

- AI 機能（ニューススコア／レジーム判定）  
  - OPENAI_API_KEY を .env に設定し、呼び出し元のスクリプトまたはジョブから該当関数を呼び出します。
  - 例（ライブラリAPI使用）:
    - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)  # api_key 省略時は環境変数参照
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

- 設定の自動ロードを無効化したいテスト等:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## 運用に関する注意点

- Kill Switch:
  - KillSwitch は RiskMonitor 等の結果に応じて data/kill.flag を書き込みます。ExecutionEngine は起動時にこのフラグや起動中にフラグ出現を検知して終了します。
  - 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にすることを推奨します（誤って自動クリアされると安全機構が無効化されるため）。

- DB 分離:
  - paper_trading 環境は paper_sqlite_path を用いて発注ログを本番 DB と分離します。
  - DuckDB は分析用に共通で使用（パスは DUCKDB_PATH）。

- ログ:
  - ログは stdout に出力され、また logs/<app_name>.log に日次ローテーションで保存されます（デフォルト: logs/）。
  - ログディレクトリ作成に失敗した場合はコンソール出力のみになります。

- プロセス優先度と CPU affinity:
  - run_* 起動時に set_process_priority("high") が呼ばれます（OSにより未対応で警告が出る可能性あり）。
  - CPU affinity の設定関数も用意されています（必要に応じて呼び出してください）。

---

## ディレクトリ構成（抜粋）

プロジェクトルートに src/kabusys パッケージが存在します。主要ファイル・ディレクトリ:

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数管理・自動ロード
  - config_setup.py             — .env 対話式ウィザード
  - validate_config.py          — 設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート
  - utils/
    - logging_setup.py          — ロギング初期化ユーティリティ
    - process_priority.py       — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py          — 監視ログ用 SQLite ラッパー（テーブル作成・CRUD）
    - system_monitor.py         — システム状態 & データ鮮度監視
    - trade_monitor.py          — 注文／約定監視（trade_logs）
    - risk_monitor.py           — ドローダウン・ポジション上限監視
    - monitoring_engine.py      — 各 Monitor を束ねる
    - kill_switch.py            — kill.flag 書き込みユーティリティ
    - alert_manager.py          — （アラート送信管理: LINE など）
  - execution/
    - execution_engine.py       — 発注エンジン本体
    - broker_factory.py         — BrokerClient の生成（実口座 / モック）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py               — ニュース NLP（OpenAI呼び出し）
    - regime_detector.py        — レジーム判定（LLM + MA200）
  - data/                       — （実行時生成）DB / PID / flag 等配置（例: data/monitoring.db, data/paper_trading.db, data/execution.pid）
  - logs/                       — ログ出力先（デフォルト）

---

## よく使う環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (AI 機能使用時に必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- LOG_LEVEL (default: INFO)
- KILL_FLAG_CLEAR_ON_START (0/1) — 起動時に kill.flag を自動クリアするか
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）

---

## 開発者向けメモ

- .env の自動読み込みは Settings モジュールで実装されています。テスト時に自動ロードを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB 接続オブジェクトを関数に渡して操作する設計により、分析ロジックは DB を直接参照できます（look-ahead バイアス防止に注意）。
- LLM 呼び出しは耐障害（リトライ、フォールバック）を考慮して実装されています。API キーやモデル変更時は対応が必要です。
- DB マイグレーションは monitoring_db.init_monitoring_db で一部対応（例: カラム追加）していますが、本格的なマイグレーションは別ツールを検討してください。

---

## サポート / 貢献

- バグや改善提案は Issues で報告してください。
- 大きな変更を加える際は事前に設計方針を議論してください（LLM 使用部分や発注ロジックは特に慎重に）。

---

READMEは以上です。必要であれば以下を追加できます：
- 依存関係の正確な requirements.txt
- systemd / supervisor 用の起動スクリプト例
- CI / テストコマンド
- API の詳細ドキュメント（各モジュールの入出力仕様）