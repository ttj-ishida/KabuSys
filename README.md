# KabuSys

日本株自動売買システム（ライブラリ / 実行スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・発注・監視・AI ベースのニューススコアリング等を含む自動売買基盤の一部を提供します。モジュール設計はテスト容易性・本番安全性（ペーパートレード分離、Kill Switch 等）を考慮しています。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方
  - 環境設定ウィザード (.env) の作成
  - 設定検証
  - ExecutionEngine（発注エンジン）の起動
  - Monitoring（監視）の起動
  - Paper Trading 検証レポート
  - AI / レジーム判定
- 重要な環境変数（抜粋）
- 停止 / Kill スイッチ
- ディレクトリ構成（抜粋）

---

## プロジェクト概要

KabuSys は日本株向けの自動売買基盤です。主な目的は以下：

- ファクター計算（モメンタム、バリュー、ボラティリティ等）
- ポートフォリオ構築（候補選定、ウェイト計算、株数算出）
- 発注エンジン（本番 / ペーパートレード分離）
- 監視コンポーネント（システム状態・注文・リスク監視、Kill Switch）
- ニュース NLP（OpenAI を用いた銘柄別センチメント）
- レポート生成（Paper Trading 検証）

設計上、分析用 DB は DuckDB、監視/注文ログは SQLite を使用します。設定は .env ファイル／環境変数で行います。

---

## 主な機能

- ポートフォリオ構築
  - 候補選定（score / rank ベース）
  - 等金額 / スコア重み配分
  - 単元株丸め・投下資金スケーリング
  - セクター集中制限・レジーム乗数

- 発注
  - 本番およびペーパートレードモード（ペーパーモードでは MockBroker を使用し専用 DB に記録）
  - リスク管理（最大ポジション比率、利用率、サーキットブレーカーなど）

- 監視
  - SystemMonitor: CPU/メモリ/Disk、プロセス生存確認、データ鮮度チェック
  - TradeMonitor: 発注ログ解析（滞留注文・異常約定など）
  - RiskMonitor: Drawdown / ポジション上限の監視とリスクイベント記録
  - KillSwitch: 指定条件で data/kill.flag を書き込み ExecutionEngine を停止

- AI（OpenAI）
  - ニュースを集約して銘柄ごとにセンチメントスコアを生成し ai_scores に格納
  - マクロニュースを用いた市場レジーム判定（bull/neutral/bear）

- ユーティリティ
  - .env 生成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成スクリプト

---

## セットアップ手順（ローカル）

※依存パッケージ要確認（requirements.txt が無い場合は下記を参考にインストールしてください）。

1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Unix/macOS)
   - .venv\Scripts\activate     (Windows)

2. 必要なパッケージをインストール（例）
   - pip install duckdb psutil openai PyYAML

   （上記は一例です。プロジェクトに requirements.txt がある場合はそれを使用してください。）

3. プロジェクトルートで data / logs ディレクトリを作成（実行時に自動作成されますが手動でも可）
   - mkdir -p data logs

4. 環境変数設定（.env を利用することを推奨）
   - python -m kabusys.config_setup
   - もしくは .env を作成して以下の必須項目を設定：
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - その他: KABUSYS_ENV, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_LEVEL, OPENAI_API_KEY 等

5. 設定の検証（任意だが推奨）
   - python -m kabusys.validate_config
   - strict モード: python -m kabusys.validate_config --strict

---

## 使い方

### .env の対話式作成
- python -m kabusys.config_setup
  - 指示に従って .env を生成できます。
  - 既存の .env があれば読み込み、Enter で既存値を再利用可能です。

自動ロード:
- デフォルトで .env/.env.local はプロジェクトルートから自動読み込みされます（OS 環境変数優先）。
- 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

### 設定の検証
- python -m kabusys.validate_config
  - 必須環境変数・ファイルの存在や基本的な整合性をチェックします。
  - --strict オプションで警告も失敗（exit 1）扱いにできます。

### ExecutionEngine（発注エンジン）の起動
- python -m kabusys.run_execution

挙動:
- KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用し DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録され、本番 DB と分離されます。
- 起動時に data/stop_requested.flag が存在すると起動しません。
- 実行中、停止要求は data/stop_requested.flag を作成することで検知します。
- エンジンは data/execution.pid に PID を書きます。

### Monitoring（監視）の起動
- python -m kabusys.run_monitoring

挙動:
- 環境変数 MONITOR_POLL_INTERVAL によってポーリング間隔を変更できます（秒、デフォルト 60）。
  - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Monitoring 側は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用して監視データを記録します（意図的な挙動）。
- 停止はプロジェクトルート data/stop_requested.flag を作成することで検知します。

### Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

用途:
- ペーパートレード DB（デフォルト data/paper_trading.db）から稼働率、注文成功率、レイテンシ等を集計して PASS/FAIL 判定を出力します。

### AI / ニューススコアリング・レジーム判定
- OpenAI API を利用する機能は環境変数 OPENAI_API_KEY を参照します（もしくは各関数へ引数で渡す）。
- ニューススコアリング: kabusys.ai.score_news（内部で DuckDB を使って raw_news 等のテーブルを参照）
- レジーム判定: kabusys.ai.regime_detector.score_regime

---

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading：Mock broker、専用 DB を使用
  - live：本番（注意して設定）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能で必要）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
- MONITOR_POLL_INTERVAL（監視のポーリング秒数、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（本番での自動クリア防止設定。0 推奨）

自動 .env 読み込み順:
1. OS 環境変数
2. .env.local（存在すれば上書き）
3. .env

自動読み込みを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 停止 / Kill スイッチ

- 実行停止（外部から）
  - プロセスはプロジェクトルートの data/stop_requested.flag を検知して安全に停止します（run_execution/run_monitoring）。
  - これを手動で作成すれば次のポーリングで停止処理が走ります。

- Kill Switch（自動停止トリガー）
  - リスク監視が条件を満たすと KillSwitch が Settings.kill_flag_path（デフォルト data/kill.flag）を書き込みます。
  - ExecutionEngine はこの kill.flag を参照して停止します（kill.flag は明示的にクリアしない限り残ります）。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアしますが、本番では 0 を推奨します。

---

## ログ

- ログは標準出力（stdout）とログファイルの両方へ出力されます（logs/<app_name>.log、日次ローテーション・30日保持）。
- ログディレクトリは環境変数 LOG_DIR、またはデフォルト logs/ を使用します。
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一されています。

---

## ディレクトリ構成（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込み
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — 発注エンジン起動スクリプト
  - run_monitoring.py        — 監視ループ起動スクリプト
  - utils/
    - logging_setup.py       — ログ初期化ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (参照)
  - execution/               — 発注関連（Engine, OrderManager 等）
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

- data/                     — デフォルトの DB / flag / pid ファイル置き場（実行時に作成）
  - monitoring.db (SQLITE_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kabusys.duckdb (DUCKDB_PATH)
  - execution.pid
  - stop_requested.flag
  - kill.flag

- logs/                     — デフォルトログ保存先

---

## 開発・運用上の注意

- 本番（KABUSYS_ENV=live）では設定ミスによる重大事故を避けるため validate_config でのチェックを必ず行ってください。
- .env は機密情報（API トークンやパスワード）を含みます。絶対に Git リポジトリへコミットしないでください。
- ペーパートレードモードは本番 DB と完全分離するよう設計されています。PAPER_TRADING_SQLITE_PATH を確認してください。
- OpenAI 等の外部 API を使う機能は失敗時にフェイルセーフ（スコア 0.0 や処理スキップ）となるよう設計されていますが、実行ログで必ず結果を確認してください。
- システム監視は MONITOR_POLL_INTERVAL（秒）で制御できますが、短くしすぎるとリソース影響を受けます（デフォルト 60 秒）。

---

もし README に追加してほしい具体的なサンプルコマンド、より詳しいディレクトリツリー、または CI / デプロイ手順があれば教えてください。