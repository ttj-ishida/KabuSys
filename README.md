# KabuSys

日本株向け自動売買システムのコードベース（ライブラリ + 起動スクリプト群）。  
この README ではプロジェクト概要、主要機能、セットアップ手順、使い方例、ディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能群を集めたシステムです：

- シグナル生成・ポートフォリオ構築・ポジションサイズ計算（research / portfolio）
- ExecutionEngine による発注制御（実口座 / ペーパートレードの切替）
- 実行状況／システム状態／リスクの監視とアラート（monitoring）
- AI を用いたニュースのセンチメント評価・レジーム判定（ai）
- ペーパートレード検証レポート生成ツール（tools）
- 環境設定ウィザード・設定検証ツール（config_setup / validate_config）
- ログ・プロセス優先度・DB 周りのユーティリティ（utils / monitoring_db）

設計方針の一部：
- DuckDB を分析用、SQLite を監視・発注ログ用に利用（ペーパートレード時は専用 SQLite に分離）
- 起動スクリプトは .env で設定を行い、Settings クラスで一元管理
- OpenAI（ニュース分析など）は環境変数 `OPENAI_API_KEY` で指定（API 呼び出しはフェイルセーフ設計）

---

## 主な機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）
- 設定検証 CLI（python -m kabusys.validate_config）
- ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - `KABUSYS_ENV=paper_trading` 時は MockBrokerClient を使い、ペーパートレード用 DB（data/paper_trading.db）へ記録
- Monitoring（python -m kabusys.run_monitoring）
  - システム資源、データ鮮度、Execution 停止検知等を定期的にチェックして SQLite に記録
  - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
- リスク監視（ドローダウン・保有銘柄上限など）と Kill Switch（`data/kill.flag`）
- AI モジュール（ニュース NLP による銘柄スコア、レジーム判定）
- 研究用モジュール（ファクター計算、IC 計測、特徴量探索）
- ポートフォリオ構築ユーティリティ（候補選定、重みづけ、ポジションサイズ計算）
- Paper Trading 検証レポート生成ツール（python -m kabusys.tools.paper_verification_report）

---

## セットアップ手順

前提：
- Python 3.9+（Typing 機能を多用しているため）を推奨
- システムによってはネイティブ拡張を含むパッケージが必要（duckdb, psutil など）

1. リポジトリをクローン / チェックアウト
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows は .venv\Scripts\activate）
3. 依存パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 無ければ最低限以下を入れてください:
     - pip install duckdb psutil openai
     - 開発/検証用に PyYAML（設定ファイル検証）を使うなら: pip install pyyaml
4. 初回設定
   - 対話式に .env を生成する:
     - python -m kabusys.config_setup
   - あるいは .env.example を参考に手動作成
   - 自動読み込み: Settings モジュールはプロジェクトルートにある `.env` / `.env.local` を自動で読み込みします
     - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - `--strict` を付けると警告も失敗扱いになります
6. データディレクトリ作成（必要に応じて）
   - デフォルトでは `data/` 配下に DB / フラグファイル等が作られます
   - ログは `logs/`（環境変数 `LOG_DIR` で変更可）

必須環境変数（最低限、validate_config でもチェックされる）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要な環境変数（抜粋）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: 分析用 DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading モード時）
- LOG_LEVEL: ログ出力レベル（DEBUG / INFO / ...）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant / partial / never / reject）

---

## 使い方（起動例・操作）

基本的な起動/操作例を示します。

1. 環境ファイル作成
   - python -m kabusys.config_setup
   - 入力後、`.env` が生成される（Git にコミットしないでください）

2. 設定検証
   - python -m kabusys.validate_config
   - 問題があれば出力に従って修正してください

3. Monitoring の起動
   - 環境変数を設定したうえで:
     - python -m kabusys.run_monitoring
   - オプション:
     - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

   停止:
   - プロジェクトルートの `data/stop_requested.flag` を作成するとループが検知して安全終了します

4. ExecutionEngine の起動（実行エンジン）
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合、ペーパートレード専用 DB（`PAPER_TRADING_SQLITE_PATH`）に記録します
   - 実行中に `data/stop_requested.flag` を作成するとエンジン停止をトリガーします

5. Kill Switch
   - KillSwitch は `data/kill.flag` を書き込み、エンジン停止を促します（監視ルールに基づく）
   - `KillSwitch.clear()` により起動時にクリアする設定（環境変数 KILL_FLAG_CLEAR_ON_START=1 で挙動を変更）

6. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB は `--db` オプション、もしくは環境変数 `PAPER_TRADING_SQLITE_PATH`、デフォルト `data/paper_trading.db`

7. AI 機能
   - `OPENAI_API_KEY` を設定しておくことで、ニュース NLP（kabusys.ai.news_nlp.score_news）やレジーム判定（kabusys.ai.regime_detector.score_regime）が利用可能
   - API 呼び出しはリトライ・フェイルセーフ設計。API 欠如時は ValueError を送出する箇所あり（呼び出し側で捕捉してください）

ログ関連
- ロギング設定は `kabusys.utils.logging_setup.setup_logging(app_name=...)` で統一
- デフォルトログディレクトリ: logs/
- 環境変数 `LOG_LEVEL`, `LOG_DIR` で調整可

---

## 重要な挙動・設計上の注意

- Monitoring は常に本番の `Settings.sqlite_path` を使用して監視ログを残します（環境に依存せず監視 DB は本番パスを使う設計）
- ExecutionEngine は `KABUSYS_ENV=paper_trading` 時に発注 API をモック化し、DB を完全分離します（実口座と混ざらない）
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を探す）を基準に行われます。CWD に依存しません
- Kill / Stop フラグはファイルベース（data/kill.flag, data/stop_requested.flag）。ファイルを作成/削除してプロセスの挙動を制御します
- OpenAI を使う機能はネットワーク不安定時にリトライし、必要に応じて安全側のデフォルト（スコア 0.0 等）で継続します

---

## ディレクトリ構成

（主要ファイル・モジュールのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                      — Settings、.env の自動ロード
    - config_setup.py                — .env 対話式ウィザード
    - validate_config.py             — 起動前設定検証ツール
    - run_execution.py               — ExecutionEngine 起動スクリプト
    - run_monitoring.py              — Monitoring ポーリングループ起動スクリプト
    - utils/
      - logging_setup.py             — ログ初期化ユーティリティ
      - process_priority.py          — プロセス優先度 / CPU affinity 設定
    - monitoring/
      - monitoring_db.py             — SQLite 永続化層（schema 生成・読み書き）
      - monitoring_engine.py         — 各モニタの束ね
      - system_monitor.py            — システム状態 / データ鮮度監視
      - trade_monitor.py             — 発注ログ監視（該当ファイル内に詳細実装あり）
      - risk_monitor.py              — ドローダウン / ポジション数監視
      - kill_switch.py               — kill.flag 制御
      - alert_manager.py             — アラート送信（LINE 等）（実装ファイルが存在する場合）
    - execution/
      - execution_engine.py          — 発注エンジン本体（EngineConfig, ExecutionEngine）
      - order_manager.py             — 注文ロジック
      - order_repository.py          — 発注ログ保存・参照
      - broker_factory.py            — BrokerClient の生成（実口座 / mock 切替）
      - reconciler.py                — 注文の照合
      - risk_manager.py              — 実行時のリスク判定
    - portfolio/
      - portfolio_builder.py         — 候補選定 / 重み付け
      - position_sizing.py           — 株数・丸め・資金配分
      - risk_adjustment.py           — セクター上限 / レジーム乗数
    - research/
      - factor_research.py           — ファクター計算（momentum / value / volatility）
      - feature_exploration.py       — 将来リターン / IC / 統計サマリー
    - ai/
      - news_nlp.py                  — ニュース NLP による銘柄スコア
      - regime_detector.py           — レジーム判定（MA + マクロセンチメント）
    - tools/
      - paper_verification_report.py — Paper Trading 検証レポート生成
    - data/ (ランタイムで生成される)
      - monitoring.db (デフォルト)
      - paper_trading.db (ペーパートレード用デフォルト)
      - stop_requested.flag
      - kill.flag
      - execution.pid

---

## よく使うコマンドまとめ

- .env 対話式作成:
  - python -m kabusys.config_setup
- 設定の自動検証:
  - python -m kabusys.validate_config
- Monitoring の起動:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- ExecutionEngine の起動:
  - python -m kabusys.run_execution
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Python パッケージ化（開発時）:
  - pip install -e .

---

README はここまでです。必要であれば以下の追加ドキュメントを作成できます：
- 各モジュール（ExecutionEngine / OrderManager / RiskManager）の詳細設計ドキュメント
- デプロイ手順（systemd / Supervisor / cron での運用例）
- ローカルでの開発・テスト手順（モックの使い方、単体テストの実行方法）

どの補足が欲しいか教えてください。