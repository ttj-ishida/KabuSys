# KabuSys

日本株向けの自動売買システムのライブラリ群・ユーティリティ群です。  
本リポジトリは戦略・ポートフォリオ構築、発注/約定管理、監視、リサーチ、AI（ニュースセンチメント）などのコンポーネントで構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次を目的としたモジュール群です。

- 戦略/ポートフォリオ構築（候補選定、重み付け、ポジションサイズ決定、セクター制約など）
- 発注エンジン（ExecutionEngine）およびフェイルセーフな Paper Trading の分離
- システム監視（リソース/プロセス/データ鮮度）、リスク監視（ドローダウン・保有数制限）、アラート発行
- リサーチ用ユーティリティ（ファクター計算・特徴量探索）
- AI を用いたニュースセンチメント/レジーム判定（OpenAI API を利用）
- 各種 CLI ユーティリティ（環境設定ウィザード、設定検証、Paper Trading 検証レポート生成）

設計方針の一部:
- 本番/ペーパートレード DB を分離（Paper Trading は専用 SQLite）
- ルックアヘッドバイアスを避けるため日時参照は明示的に行う設計
- フェイルセーフ（API 失敗や DB エラー時は安全策で継続）を重視

---

## 主な機能一覧

- 環境設定
  - 対話式ウィザードで `.env` を生成/更新（kabusys.config_setup）
  - 起動前設定検証（kabusys.validate_config）

- 実行・監視
  - ExecutionEngine 起動スクリプト（kabusys.run_execution）
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB に記録
  - SystemMonitor のポーリング（kabusys.run_monitoring）
    - MONITOR_POLL_INTERVAL で間隔設定（デフォルト 60 秒）
    - stop_requested.flag によりループ停止
  - Kill Switch（data/kill.flag）による外部停止シグナル

- モニタリング/アラート
  - system_status, trade_logs, positions, risk_logs, dashboard の永続化（SQLite）
  - RiskMonitor: ドローダウンやポジション上限の検知
  - MonitoringEngine: 各 Monitor を束ねてアラート/Kill Switch を判定

- ポートフォリオ構築
  - 候補選定、等金額/スコア加重、リスクベースのサイズ算出
  - セクター集中制限、レジームに応じた投下資金乗数

- 研究（Research）
  - ファクター計算（モメンタム、バリュー、ボラティリティ）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリ

- AI（OpenAI）
  - ニュース記事の銘柄別センチメント集約とスコア保存
  - マクロニュースを用いた市場レジーム判定（'bull'/'neutral'/'bear'）

- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## 必要な依存パッケージ（主なもの）

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config YAML の検証時に必要）
※ 実行環境に合わせて requirements.txt を作成してください。

例:
pip install duckdb psutil openai PyYAML

---

## セットアップ手順

1. リポジトリをクローン / 展開
2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb psutil openai PyYAML
   - 追加で使用する場合は他パッケージをインストールしてください
4. 環境変数の準備
   - 対話式ウィザードを使う: python -m kabusys.config_setup
   - もしくは `.env` を手動で作成（.env.example を参照）
   - 重要: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須
5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります
6. データディレクトリの作成（必要に応じて）
   - デフォルトの SQLite/DuckDB/ログディレクトリは `data/` `logs/`

---

## 環境変数（代表的なもの）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: execution 環境（development / paper_trading / live）（デフォルト: development）
- OPENAI_API_KEY: OpenAI 利用時に必要
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用 DB, デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 SQLite、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（paper_trading の約定挙動: instant / partial / never / reject、デフォルト: instant）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR（ログ保存ディレクトリ、デフォルト: logs/）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START（本番環境で危険なのでデフォルト 0 推奨）
- KILL_FLAG_PATH / PID_FILE_PATH（必要に応じて上書き可能）

---

## 使い方（代表的なコマンド・ワークフロー）

- 環境を対話式に作成
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- ExecutionEngine の起動（実際の注文処理）
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB（デフォルト data/paper_trading.db）に記録します
    - 実行中は data/execution.pid が作成されます
    - 外部停止は data/stop_requested.flag または data/kill.flag により行えます（Kill Switch は monitoring 側で生成）

- Monitoring（SystemMonitor）起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL でオーバーライド可能（秒、デフォルト 60）
  - 監視ログは SQLITE_PATH（デフォルト data/monitoring.db）に永続化されます
  - 停止は data/stop_requested.flag による

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 簡易的に稼働率、注文成功率、レイテンシ等をレポートします

- Kill Switch の操作
  - KillSwitch は監視で危険な状態を検出すると `data/kill.flag` を書き込み、ExecutionEngine の停止を促します
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動でクリアされますが、本番では推奨されません

ログ:
- ログはデフォルトで stdout（コンソール）とファイル（logs/<app_name>.log）に出力されます
- ログ保存先は LOG_DIR で変更可能

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数/設定管理（.env 自動ロード）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py        — 統一的ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
  - execution/                — 発注/注文管理関連（Engine, OrderManager 等）
  - monitoring/
    - monitoring_db.py        — 監視用 SQLite 永続化レイヤ
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py
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
    - news_nlp.py             — ニュースセンチメント（OpenAI）
    - regime_detector.py      — マクロ + MA200 によるレジーム判定
  - tools/
    - paper_verification_report.py

その他:
- data/                     — データファイル置き場所（SQLite、PID、flag など）
- logs/                     — ログファイル出力先（デフォルト）

---

## 運用上の注意点

- 本番（KABUSYS_ENV=live）では LINE の通知設定（LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID）を必ず確認してください。validate_config は本番向けの警告を出します。
- Kill Switch（data/kill.flag）は本番で自動クリアしない設定を強く推奨します（KILL_FLAG_CLEAR_ON_START=0）。
- Paper Trading は本番 DB と完全分離されるよう設計されています。ペーパートレード用 DB パスは PAPER_TRADING_SQLITE_PATH で指定できます。
- OpenAI を使う機能（news_nlp, regime_detector）は API キー（OPENAI_API_KEY）が必要です。API 呼び出しはリトライ/フェイルセーフの実装がありますが、API 利用料に注意してください。
- ログディレクトリの作成に失敗した場合、ファイル出力はスキップされコンソールのみの出力になります。

---

## 開発・テストのヒント

- モジュールは可能な限り純粋関数（副作用を持たない）または DB 接続を引数に取る設計になっています。ユニットテストではモック接続や一時 DB を使って検証できます。
- OpenAI 呼び出し箇所は内部で `_call_openai_api` といった関数を経由しているため、テスト時にパッチして擬似応答を返すことが容易です。
- Monitoring/Execution の起動スクリプトは `if __name__ == "__main__": main()` を持つため、モジュール単体で実行可能です。daemon スレッドや flag ファイルにより安全に停止できます。

---

必要に応じて README を拡張します。特定のセットアップ（Docker、systemd ユニット、CI 設定）や各モジュールの詳細ドキュメントを追加したい場合は教えてください。