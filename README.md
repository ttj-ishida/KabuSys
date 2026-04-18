# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買・研究・監視ツール群を収めた Python パッケージです。エンジン（ExecutionEngine）、監視（Monitoring）、ファクター計算 / リサーチ、ポートフォリオ構築、AI を使ったニュースセンチメント評価などを含みます。

注意: .env は機密情報（API トークンやパスワード）を含むため、決して Git にコミットしないでください。

---

## プロジェクト概要

- 実行スクリプト
  - run_execution.py: 発注実行エンジン（ExecutionEngine）を起動
  - run_monitoring.py: 監視ループ（SystemMonitor）を起動
- 設定管理
  - config_setup.py: 対話式に .env を生成／更新
  - validate_config.py: 起動前の設定検証 CLI
  - config.py: 環境変数 / 設定アクセス用の Settings クラス
- モジュール群
  - execution: 発注関連ロジック（ブローカー抽象、OrderManager 等）
  - monitoring: システム監視、リスク監視、アラート、Kill Switch 等
  - portfolio: 銘柄選定・重み付け・ポジションサイズ決定
  - research: DuckDB を用いたファクター計算・特徴量解析
  - ai: OpenAI を使ったニュース NLP / レジーム判定
  - utils: ログ設定・プロセス優先度設定 など
- DB
  - DuckDB: 分析用（デフォルト data/kabusys.duckdb）
  - SQLite: 監視・注文ログ用（デフォルト data/monitoring.db）、ペーパートレード用に分離可能（data/paper_trading.db）

---

## 機能一覧

- 実行エンジン
  - live / paper_trading の切り替え（KABUSYS_ENV）
  - RiskManager/OrderManager/Reconciler と連携
- 監視
  - CPU/メモリ/ディスク・Execution プロセス生存確認
  - データ鮮度チェック（prices_daily 参照）
  - リスク監視（ドローダウン・ポジション上限）
  - Kill Switch（data/kill.flag）によるエンジン停止
  - 監視結果の永続化（SQLite）
- ポートフォリオ構築
  - 候補選定、等分配・スコア加重、リスクベースのポジションサイズ計算
  - セクター上限チェック、レジーム乗数
- 研究・ファクター計算
  - モメンタム、ボラティリティ、バリュー指標の DuckDB ベース計算
  - 将来リターン（forward returns）、IC 計算、統計サマリー
- AI (OpenAI)
  - ニュースの銘柄別センチメントスコア算出（ai_scores テーブル）
  - マクロニュース + ETF MA による市場レジーム判定
  - API 呼び出し時のエクスポネンシャルバックオフ、レスポンス検証、書き込みは冪等処理
- ツール
  - paper_verification_report: ペーパートレード DB から検証レポート生成（稼働率・注文成功率・レイテンシ等）

---

## 前提 / 必要環境

- Python 3.9+
- 推奨追加パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML の検証を行う場合）
- システム上のファイルパス（デフォルト）
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring): data/monitoring.db
  - SQLite (paper trading): data/paper_trading.db
  - ログディレクトリ: logs/
  - フラグファイル: data/kill.flag, data/stop_requested.flag
  - PID ファイル: data/execution.pid

インストール例（仮の requirements を想定）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

必要なパッケージはプロジェクトで管理される requirements.txt があればそちらを使用してください。

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリに移動
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して依存パッケージをインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb psutil openai PyYAML
   ```

3. .env を作成（対話式ウィザード）
   ```bash
   python -m kabusys.config_setup
   ```
   - 対話で J-Quants トークン、kabu API パスワード、KABUSYS_ENV 等を設定します。
   - .env は絶対にリポジトリにコミットしないでください。

4. 設定検証（起動前チェック）
   ```bash
   python -m kabusys.validate_config
   # 警告をエラー扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

5. 初期 DB / ディレクトリの作成
   - 多くの起動スクリプトは必要に応じてログディレクトリや data ディレクトリを自動作成しますが、事前に手動作成して権限を確認しておくと安全です。
   ```bash
   mkdir -p data logs
   ```

---

## 使い方

基本はモジュールを直接実行します。

- 監視ループの起動
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
  - 停止はプロジェクトルートの data/stop_requested.flag ファイルを作成すると、ループが検知して終了します。
  ```bash
  python -m kabusys.run_monitoring
  # 例: ポーリングを30秒にする
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- 実行エンジンの起動（ExecutionEngine）
  - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使い、データベースは data/paper_trading.db に記録されます（本番 DB と完全分離）。
  - 起動前に kill.flag（data/kill.flag）が存在すると起動せずに終了します。強制停止には data/stop_requested.flag を使用できます。
  ```bash
  python -m kabusys.run_execution
  # paper_trading モードで起動する例:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report
  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを指定
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- .env 関連環境変数（主なもの）
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - OPENAI_API_KEY: OpenAI API を使う機能で必要
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
  - LOG_LEVEL（デフォルト: INFO）
  - MONITOR_POLL_INTERVAL（run_monitoring で使用）
  - PAPER_FILL_MODE（paper_trading の注文約定モード: instant|partial|never|reject）

- ロギング
  - 共通の logging 設定ユーティリティ (kabusys.utils.logging_setup.setup_logging) により、
    - stdout (コンソール) 出力
    - 日次ローテーションファイルログ: logs/<app_name>.log（30 日保持）
  - ログレベルは LOG_LEVEL 環境変数または引数で制御可。

- Kill Switch / 停止フラグ
  - Kill Switch（監視側）により data/kill.flag が書き込まれると、実行エンジンは停止信号を受けます。
  - 実行プロセスの停止リクエスト（外部停止）には data/stop_requested.flag を利用します（run_monitoring/run_execution が検出）。

- ライブラリ API 例
  - 研究用関数（DuckDB 接続を渡して使用）
    - kabusys.research.calc_momentum(conn, date)
    - kabusys.research.calc_volatility(conn, date)
    - kabusys.research.calc_value(conn, date)
    - kabusys.research.calc_forward_returns(...)
  - AI スコアリング
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## ディレクトリ構成

以下は主要ファイル・ディレクトリの概要（src/kabusys 配下）です。追加のサブモジュールやファイルがある場合がありますが、主要なものを列挙します。

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数 / Settings クラス、自動 .env ロード
    - config_setup.py           — 対話式 .env 作成ウィザード
    - validate_config.py        — 起動前設定検証 CLI
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — Monitoring ポーリング起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py  — ペーパートレード検証レポート出力
    - ai/
      - __init__.py
      - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
      - regime_detector.py      — マクロ＋ETF MA によるレジーム判定
    - data/                      — （実運用時に DB・データを置く想定）
    - portfolio/
      - __init__.py
      - portfolio_builder.py    — 候補選定 / 等重・スコア重み
      - position_sizing.py      — 株数決定・スケーリング・単元丸め
      - risk_adjustment.py      — セクターキャップ / レジーム乗数
    - research/
      - __init__.py
      - factor_research.py      — モメンタム / ボラティリティ / バリュー計算
      - feature_exploration.py  — forward returns, IC, summary
    - monitoring/
      - monitoring_db.py        — SQLite スキーマ + 永続化ラッパー
      - monitoring_engine.py    — 各 Monitor を束ねるループ
      - system_monitor.py       — システム状態・データ鮮度監視
      - trade_monitor.py        — 発注ログ監視（存在）
      - risk_monitor.py         — ドローダウン・位置数監視
      - kill_switch.py          — kill.flag 管理
      - alert_manager.py        — 通知（LINE など想定）
    - execution/
      - （発注関連モジュール群: BrokerClientFactory, ExecutionEngine, OrderManager, Reconciler, RiskManager 等）
    - utils/
      - __init__.py
      - logging_setup.py       — 共通ログ設定
      - process_priority.py    — プロセス優先度 / CPU affinity
    - monitoring/               — （上で説明した監視関連）
    - research/                 — （上で説明した研究関連）

---

## 運用上の注意

- 本番環境（KABUSYS_ENV=live）では設定を慎重に確認してください。validate_config に本番向けの警告チェックがあります。
- .env の JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / OPENAI_API_KEY は機微情報です。適切に秘匿してください。
- データベースファイル（特に本番用 SQLite）は適切なバックアップとアクセス制御を行ってください。
- OpenAI API 利用には料金が発生します。rate-limit やエラー時の挙動はコード側で一定のフォローがありますが、呼び出し頻度・コストは設計時に考慮してください。
- run_monitoring / run_execution はプロセス優先度を "high" に設定しようとしますが、権限不足で失敗する場合があります（警告が出ます）。

---

必要に応じて README に追記します。たとえば具体的な設定例（.env.example）、requirements.txt、Dockerfile、systemd ユニットのサンプルなどを追加できます。どの情報を追加したいか教えてください。