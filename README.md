# KabuSys

日本株向け自動売買システムのリポジトリ（骨格実装）。  
この README はコードベース（src/kabusys 以下）を参照して作成しています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株自動売買・検証・監視のためのモジュール群を提供するプロジェクトです。主な関心領域は以下です。

- 発注エンジン（ExecutionEngine）とブローカー接続（本番 / ペーパートレード切替）
- 監視（System / Trade / Risk）とアラート、Kill Switch による安全停止
- ポートフォリオ構築（候補選定、重み算出、ポジションサイズ計算、セクター制約）
- リサーチ（ファクター計算、特徴量探索、IC 計算など）
- AI を使ったニュース NLP（OpenAI）によるセンチメント評価とレジーム判定
- ペーパートレード検証レポート生成ツール

設計方針の一部:
- 環境（KABUSYS_ENV）による挙動切替（development / paper_trading / live）
- Paper trading は本番 DB と分離（`data/paper_trading.db` 等）
- ルックアヘッドバイアスに注意した時系列処理設計
- フェイルセーフ: API 失敗やデータ不足時は部分継続する設計

---

## 機能一覧

- 環境設定ウィザード（`.env` 作成支援）: `kabusys.config_setup`
- 設定検証 CLI（必須環境変数・config YAML・パス等の事前チェック）: `kabusys.validate_config`
- Execution 起動スクリプト（本番 / ペーパートレード切替）: `kabusys.run_execution`
  - ペーパートレードなら MockBrokerClient を使用しデータは `data/paper_trading.db` に保存
- Monitoring 起動スクリプト（SystemMonitor ポーリング）: `kabusys.run_monitoring`
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト: 60秒）
- MonitoringEngine：System / Trade / Risk を束ねてポーリング、Kill Switch 評価、アラート発行
- MonitoringDB（SQLite）による監視ログの永続化（system_status, trade_logs, positions, risk_logs, dashboard）
- RiskMonitor：ドローダウン・ポジション上限のチェックとリスクログ
- KillSwitch：条件を満たした場合に `data/kill.flag` を作成して ExecutionEngine に停止シグナル送出
- ポートフォリオモジュール（候補選定、等配分/スコア加重、ポジションサイズ計算、セクター制約、レジーム乗数）
- Research モジュール（モメンタム、バリュー、ボラティリティファクター、将来リターン、IC 計算、統計サマリ等）
- AI モジュール
  - `kabusys.ai.news_nlp`: OpenAI を使ったニュースセンチメントスコアリング（ai_scores 書込）
  - `kabusys.ai.regime_detector`: MA とマクロニュースを合わせた日次レジーム判定（market_regime 書込）
- ツール: Paper Trading 検証レポート生成スクリプト

---

## 必要条件（概略）

- Python 3.10+
- 必要と思われる主要パッケージ（プロジェクトに requirements.txt がない場合は手動で準備してください）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検証のため、任意）
- SQLite（標準ライブラリで使用）
- ローカルで kabuステーション API を使う場合はその環境

（実際の運用では requirements.txt / pyproject.toml を用意して pip/Poetry 等で依存解決してください）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール（例）
   ```
   pip install duckdb psutil openai pyyaml
   ```

4. 環境変数ファイル（.env）の作成
   - 対話式ウィザードを利用:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは手動で .env を作成（例）:
     ```
     # .env (例)
     KABUSYS_ENV=development
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
     KABU_API_PASSWORD=your_kabu_password_here
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     KILL_FLAG_CLEAR_ON_START=0
     ```

   注意: `.env` は絶対にリポジトリにコミットしないでください。

5. 設定検証を実行
   ```
   python -m kabusys.validate_config
   # 警告も失敗扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

6. 初回は必要に応じて data/ や logs/ ディレクトリを作成（多くのコードは自動作成しますが権限に注意）
   ```
   mkdir -p data logs
   ```

---

## 使い方（主要スクリプト）

- ExecutionEngine を起動（本番 / paper_trading は KABUSYS_ENV に依存）
  ```
  python -m kabusys.run_execution
  ```

  動作ポイント:
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、Paper DB（PAPER_TRADING_SQLITE_PATH）に記録します。
  - 起動前に `data/stop_requested.flag` が存在すると起動をスキップします。
  - 実行中に `data/stop_requested.flag` が作成されるとエンジン停止を開始します。
  - Execution 用 PID ファイル: `data/execution.pid`（デフォルト）

- Monitoring を起動（SystemMonitor をポーリング）
  ```
  python -m kabusys.run_monitoring
  ```

  オプション:
  - ポーリング間隔を秒で上書き:
    ```
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```
    デフォルトは 60 秒。0 以下や不正値は 60 秒にフォールバックします。

  動作ポイント:
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依存せず本番 DB を参照）。
  - stop フラグファイル: `data/stop_requested.flag`（存在すると監視ループ終了）

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  デフォルト DB: `data/paper_trading.db`。`--db` で明示指定可能。

- 環境変数の自動読み込みを無効化（テスト用）
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## 重要な環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

- DB / ファイルパス
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
  - PID_FILE_PATH（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（Kill Switch が書き込むパス、デフォルト: data/kill.flag）

- Monitoring
  - MONITOR_POLL_INTERVAL（秒、デフォルト 60）

- AI 関連
  - OPENAI_API_KEY（news_nlp / regime_detector の API 呼出し用）

- その他
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動クリア（本番では推奨しない）

---

## ディレクトリ構成（主要ファイルの要約）

src/kabusys/
- __init__.py — パッケージ定義（バージョン等）
- config.py — 環境変数管理・自動 .env ロード・Settings クラス
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor 起動スクリプト

サブパッケージ（機能別）
- execution/ — 発注エンジン、OrderManager、RiskManager 等（詳細実装ファイルはリポジトリにあります）
- monitoring/
  - monitoring_db.py — SQLite 永続化層（テーブル作成 / マイグレーション / CRUD）
  - system_monitor.py — CPU/メモリ/ディスク/プロセス・データ鮮度のチェック
  - trade_monitor.py — 発注 / 約定の監視（ファイル内に存在）
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — kill.flag 書込・評価ロジック
  - monitoring_engine.py — 各 Monitor を束ねる
  - alert_manager.py — （アラート送信ラッパー、LINE などを利用）
- portfolio/
  - portfolio_builder.py — 候補選定 / 重み計算
  - position_sizing.py — 株数決定・制約、lot 単位処理
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — モメンタム・バリュー・ボラティリティ等
  - feature_exploration.py — 将来リターン・IC・統計サマリ
- ai/
  - news_nlp.py — ニュースセンチメント scoring（OpenAI 利用）
  - regime_detector.py — MA とマクロニュースで市場レジーム判定
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成
- utils/
  - logging_setup.py — 統一的なログ設定（コンソール + 日次ローテーション）
  - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ

その他
- data/ — デフォルト DB / フラグファイル / pid を格納する想定ディレクトリ
  - stop_requested.flag — 外部からプロセス停止を要求するフラグ（run_* スクリプトで監視）
  - kill.flag — Kill Switch による強制停止トリガー
  - monitoring.db / paper_trading.db / kabusys.duckdb（デフォルトパス）
- logs/ — デフォルトのログ出力先（`setup_logging` が作成）

---

## 運用上の注意

- .env をリポジトリにコミットしないこと（機密情報含む）。
- 本番環境では KABUSYS_ENV=live を設定する前に validate_config を必ず実行し、LINE 通知等の設定を確認してください。
- Kill Switch (data/kill.flag) の自動クリアを本番で有効にするのは危険です（KILL_FLAG_CLEAR_ON_START=0 を推奨）。
- OpenAI API を利用する機能は API コスト・レートリミットに注意してください。API キーは安全に保管してください。
- プロセス優先度の変更や CPU affinity 設定は権限・OS に依存します。設定に失敗した場合は警告が出ますが処理は継続します。

---

## トラブルシュート（簡易）

- ログが出力されない / ログファイルが作成されない:
  - `logs/` ディレクトリの作成権限を確認（logging_setup はフォルダ作成を試みますが失敗する場合はコンソールのみ）。
- .env が読み込まれない:
  - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行います。テストで無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Monitoring / Execution がすぐ終了する:
  - `data/stop_requested.flag` が存在しないか確認してください。
- AI 機能で「API キーが未設定」エラー:
  - 環境変数 OPENAI_API_KEY を設定するか、関数呼出し時に api_key を渡してください。

---

## 参考コマンドまとめ

- .env ウィザード:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  ```

- Execution 起動:
  ```
  python -m kabusys.run_execution
  ```

- Monitoring 起動:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- Paper Trading レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

この README はコードベースに基づく概要ドキュメントです。詳細な挙動・実装は各モジュール（src/kabusys 以下のファイル）を参照してください。補足やドキュメント追加の希望があれば教えてください。