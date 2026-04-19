# KabuSys

日本株向け自動売買システムのリポジトリ（モジュール抜粋）。  
このREADMEはリポジトリ内の主要スクリプト・モジュールを基に作成した簡易ドキュメントです。

---

## プロジェクト概要

KabuSys は日本株の自動売買パイプライン／監視／研究ユーティリティ群を集めたパッケージです。  
主な責務は以下のとおりです：

- 実行エンジン（ExecutionEngine）による発注処理（実運用・ペーパートレード対応）
- 監視（System / Trade / Risk）と Kill Switch による安全停止
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- 研究用のファクター計算・特徴量解析（DuckDB を使用）
- ニュース NLP / レジーム判定（OpenAI を利用したセンチメント評価）
- 各種 CLI（.env ウィザード、設定検証、ペーパートレード検証レポート）

設計方針としては、DB を使った永続化（SQLite / DuckDB）、外部 API は明示的に分離、フェイルセーフ（API失敗時のフォールバック）を重視しています。

---

## 機能一覧

- 環境設定ウィザード（.env 生成・更新）: python -m kabusys.config_setup
- 設定検証 CLI（.env / config/*.yaml 検査）: python -m kabusys.validate_config
- 実行エンジン起動スクリプト（paper_trading モードあり）: python -m kabusys.run_execution
- 監視ループ起動スクリプト: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL によるポーリング間隔変更可能（デフォルト 60 秒）
- 監視永続化（SQLite）と DB マイグレーション（monitoring_db）
- RiskMonitor / TradeMonitor / SystemMonitor によるアラート・Kill Switch 判定
- KillSwitch による安全停止ファイル (data/kill.flag) の生成
- ポートフォリオ構築: 候補選択、重み計算、リスク調整、ポジションサイズ計算
- 研究モジュール: momentum / volatility / value などのファクター計算、IC 計算、統計サマリー
- AI モジュール: ニュースを LLM（OpenAI）でスコアリング、日次レジーム判定
- ツール: Paper Trading 用の検証レポート生成スクリプト

---

## セットアップ手順（開発環境向け）

※ requirements.txt がリポジトリに含まれていない場合は下記パッケージを個別にインストールしてください。

1. リポジトリをクローンして作業ディレクトリに移動します。
   - 例: git clone <repo> && cd <repo>

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール
   - 例（代表的な依存）:
     - pip install duckdb psutil openai
   - 実際にはプロジェクトで使用するライブラリを requirements.txt にまとめている場合は
     - pip install -r requirements.txt

4. .env の作成（推奨: ウィザードを利用）
   - python -m kabusys.config_setup
   - ウィザードで入力後、.env が生成されます。

5. 設定検証
   - python -m kabusys.validate_config
   - 必須環境変数や config/*.yaml の存在／パースをチェックできます。
   - --strict を付けると警告も失敗（exit 1）扱いになります。

6. データディレクトリの準備
   - デフォルトでは `data/`、ログは `logs/` に出力されます。必要に応じて作成してください（自動生成もされます）。

---

## 主要な環境変数（まとめ）

- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）（デフォルト: development）
  - paper_trading: MockBrokerClient を使用し、Paper Trading 専用 DB を使用
  - live: 本番（注意喚起あり）
- PAPER_FILL_MODE: paper_trading 時の約定モード（instant / partial / never / reject）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで必要）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1=有効、本番では推奨しない）

---

## 使い方（起動・運用メモ）

1. .env を作成して設定を行う（または環境変数を直接設定）。
   - 推奨: python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config
   - 問題がある場合は表示される ERROR/WARNING を修正してください。

3. 実行エンジン（ExecutionEngine）を起動
   - 開発・テスト（paper_trading）:
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   - 本番:
     - KABUSYS_ENV=live python -m kabusys.run_execution
   - 動作:
     - paper_trading の場合は MockBrokerClient を使い、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。
     - 起動時に data/stop_requested.flag が存在する場合は起動せずに終了します。
     - 実行中に stop_requested.flag を作成するとエンジンを停止します。

4. 監視ループを起動
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き可能（例: export MONITOR_POLL_INTERVAL=30）
   - 監視は Settings.sqlite_path（監視 DB）へ書き込みを行います（環境にかかわらず本番 sqlite_path を使用）。

5. Safety / Kill Switch
   - RiskMonitor が閾値を超えた場合、KillSwitch が `data/kill.flag` を書き込みます。これが検出されると実運用側で安全停止するフローが想定されています（ExecutionEngine の実装部分と合わせて使用）。

6. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - オプション:
     - --db PATH で SQLite DB を直接指定可能（デフォルトは PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db）

7. AI（ニュース NLP / レジーム判定）
   - OpenAI API キー（OPENAI_API_KEY）が必要。
   - ライブラリ関数として利用可能:
     - from kabusys.ai import score_news
     - from kabusys.ai.regime_detector import score_regime

---

## ログ・プロセス管理

- ログ設定: kabusys.utils.logging_setup.setup_logging を各スクリプトで呼び出して統一的にログ出力（コンソール + 日次ローテーションファイル）を行います。
- プロセス優先度: 起動スクリプトは set_process_priority("high") を呼び出します（可能な場合）。
- 停止フラグ:
  - run_execution / run_monitoring が参照する停止フラグ: data/stop_requested.flag
  - KillSwitch が書き込む: data/kill.flag
  - pid ファイル: data/execution.pid（実行エンジンが使用）

---

## ディレクトリ構成（抜粋）

以下は主要モジュールのツリー概観（src/kabusys 以下）です。実際のファイル数は他にも存在する可能性があります。

- src/
  - kabusys/
    - __init__.py
    - config.py                   — 環境変数・.env 自動ロード、Settings クラス
    - config_setup.py             — .env 対話式ウィザード
    - validate_config.py          — 起動前検証 CLI
    - run_execution.py            — ExecutionEngine 起動スクリプト
    - run_monitoring.py           — SystemMonitor ポーリングループ起動スクリプト
    - utils/
      - logging_setup.py          — ログ初期化ユーティリティ
      - process_priority.py       — プロセス優先度 / CPU affinity 設定
    - monitoring/
      - monitoring_db.py          — SQLite テーブル作成 / 永続化層
      - system_monitor.py         — システム・データ鮮度監視
      - risk_monitor.py           — ドローダウン / ポジション上限監視
      - trade_monitor.py          — (取引監視: ファイル内で参照あり)
      - kill_switch.py            — kill.flag 制御
      - alert_manager.py          — アラート送信（LINE 等） ※実装参照
      - monitoring_engine.py      — 監視のオーケストレーション
    - execution/
      - execution_engine.py       — 実行エンジン本体（EngineConfig 等）
      - broker_factory.py         — BrokerClient の生成（Mock/Live 切替）
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - portfolio_builder.py      — 候補選定・重み計算
      - position_sizing.py        — 株数決定・資金配分ロジック
      - risk_adjustment.py        — セクター上限・レジーム乗数
    - research/
      - factor_research.py       — Momentum/Value/Volatility 計算（DuckDB）
      - feature_exploration.py   — forward returns / IC / 統計
    - ai/
      - news_nlp.py               — ニュースを LLM でスコアリング
      - regime_detector.py        — 市場レジーム判定
    - tools/
      - paper_verification_report.py — ペーパートレード検証レポート生成

---

## 開発上の注意・設計上のポイント

- .env 自動読み込み:
  - config.py はプロジェクトルート（.git または pyproject.toml）を探索して .env を自動ロードします。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- DB 関連:
  - 監視ログは SQLite（デフォルト data/monitoring.db）へ永続化されます。
  - 分析向けデータは DuckDB（data/kabusys.duckdb）を使用します。
- Paper Trading:
  - KABUSYS_ENV=paper_trading の場合、発注は仮想ブローカーに対して行われ、本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH を使用）。
- AI 呼び出し:
  - OpenAI の呼び出しはリトライやバックオフ制御、レスポンス検証が組み込まれています。APIキーの管理には注意してください（.env に設定）。
- フェイルセーフ:
  - AI の失敗時やデータ不足時にはフォールバック値を使い、致命的な例外でサービス全体を停止させない設計になっています。

---

## よく使うコマンド例

- .env ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動
  - python -m kabusys.run_execution
- 監視起動（ポーリング間隔 30 秒にする例）
  - export MONITOR_POLL_INTERVAL=30
  - python -m kabusys.run_monitoring
- Paper Trading レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

---

## 最後に

この README はリポジトリ内の主要なモジュール群から自動生成的にまとめた概要です。実際に運用・カスタマイズする際は各モジュールのドキュメント（関数 docstring）と config ディレクトリ内の設定ファイル（存在する場合）を必ず確認してください。質問や追加で記載してほしい点があれば教えてください。