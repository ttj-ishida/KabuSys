# KabuSys

日本株自動売買システムのサンプル実装。戦略（ファクター計算・ポートフォリオ構築）・Execution（発注管理・リスク管理）・Monitoring（監視・Kill Switch）・AI（ニュースセンチメント / レジーム判定）など、実運用を念頭に置いた複数コンポーネントで構成されています。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の主要機能を備えたモジュール群から構成されます。

- 市場データ（DuckDB）を利用したファクター計算・研究（research）
- 銘柄選定・重み付け・株数決定（portfolio）
- 発注・注文管理・リスク管理を含む ExecutionEngine（execution）
- システム状態・注文・リスクの監視と Kill Switch（monitoring）
- ニュースを用いた LLM ベースのセンチメント評価 / レジーム判定（ai）
- 設定ウィザード・設定検証ツール・運用ツール（config, tools）
- ロギング・プロセス優先度設定等のユーティリティ（utils）

設計方針の例：
- 本番 DB と Paper Trading は分離（paper_trading モードで専用 SQLite を使用）
- .env を使った設定管理（プロジェクトルートの .env / .env.local を自動ロード）
- OpenAI API を用いた NLP 処理は失敗時にフェイルセーフ（0 またはスキップ）で継続

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py — ExecutionEngine を起動
  - run_monitoring.py — SystemMonitor のポーリングループを起動
- 設定関連
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — 起動前の設定検証 CLI
- 監視
  - monitoring_engine / SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch
  - 監視ログの永続化（SQLite）
- ポートフォリオ構築
  - 候補選定、重み計算、ポジションサイズ計算、セクター制限、レジーム乗数
- 研究・分析
  - ファクター計算（momentum / value / volatility）
  - 将来リターン・IC 計算・統計サマリー
- AI（OpenAI）
  - ニュースセンチメント（news_nlp）
  - 市場レジーム判定（regime_detector）
- 運用ツール
  - tools/paper_verification_report.py — ペーパートレードの検証レポート生成

---

## 前提・依存パッケージ

（最低限の例）
- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（設定ファイル検証を行う場合）
- その他: 標準ライブラリ

インストール例（仮の requirements）:
pip install duckdb psutil openai PyYAML

※ 実際の requirements.txt はリポジトリに含めることを推奨します。

---

## セットアップ手順

1. リポジトリをクローン / 展開
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
4. 環境変数設定（.env の作成）
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - または .env を手動作成（.env.example を参考に）
   - 自動ロードはデフォルトで有効。無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱い（exit 1）
6. 必要に応じてデータディレクトリ作成
   - data/（SQLite / PID / stop フラグ / kill.flag などを保持）
   - logs/（ログ出力先、ログ設定で自動作成されます）

---

## 環境変数（主要）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）
  - paper_trading: 発注は MockBrokerClient を使用し data/paper_trading.db を利用
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: Paper Trading の約定モード（instant / partial / never / reject）

注意事項:
- .env は絶対に Git にコミットしないでください（シークレット含む）。
- validate_config.py で起動前に必須変数のチェックを行えます。

---

## 使い方

基本的な起動例:

- ExecutionEngine の起動
  - 環境を Paper Trading にする例:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - 本番(ライブ)の場合:
    - export KABUSYS_ENV=live
    - python -m kabusys.run_execution
  - 実行前に kill.flag / stop フラグファイルの有無を確認してください。
    - ストップフラグ: data/stop_requested.flag（存在すると起動／ループを停止）
    - Kill Switch: data/kill.flag（Monitoring が書き込むと Execution 側で停止シグナルとして扱う）

- Monitoring の起動（システム監視ループ）
  - MONITOR_POLL_INTERVAL で間隔を変更可能:
    - export MONITOR_POLL_INTERVAL=30
    - python -m kabusys.run_monitoring
  - Monitoring は Settings.env に関係なく本番用 sqlite_path を参照します。

- 設定ウィザード・検証
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]

- Paper Trading レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH

- AI 機能（スコアリング / レジーム判定）
  - OpenAI API キーを設定してから該当関数を呼び出します（ライブラリ API を直接使用）。
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)

ログ:
- 共通のロギング初期化は kabusys.utils.logging_setup.setup_logging を使用します。
- デフォルトログディレクトリ: logs/
- 各アプリ名（例: execution, monitoring）に応じたログファイルが作成されます（日次ローテーション、30日保持）。

停止・リセット:
- run_execution/run_monitoring は data/stop_requested.flag を監視します。ファイルを作成すると安全に停止できます。
- KillSwitch は data/kill.flag を書き込み、Execution 側で停止を促します。起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動クリアされますが、本番では 0 を推奨。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py — 環境変数読み込み・Settings クラス
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor 起動スクリプト

subpackages:
- ai/
  - news_nlp.py — ニュースセンチメント（OpenAI 経由）
  - regime_detector.py — レジーム判定
- monitoring/
  - monitoring_db.py — SQLite 監視ログの永続化層
  - system_monitor.py — システム・データ鮮度監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - monitoring_engine.py — 複数 Monitor の統合ループ
  - kill_switch.py — kill.flag 書き込みユーティリティ
  - (alert_manager / trade_monitor 等のファイルが存在する想定)
- execution/
  - (broker_factory, execution_engine, order_manager, order_repository, reconciler, risk_manager 等)
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py — モメンタム/バリュー/ボラティリティ計算
  - feature_exploration.py — 将来リターン・IC・統計サマリー
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート
- utils/
  - logging_setup.py — ログ設定
  - process_priority.py — プロセス優先度・CPU affinity

トップレベル運用ファイル・ディレクトリ（リポジトリルート想定）
- data/ — SQLite、PID、flag ファイルを配置（自動作成するコードあり）
- logs/ — ログファイル（自動作成）

---

## 既知の注意点・運用上のヒント

- process priority の設定は OS によって権限が必要な場合があります（psutil による実装）。権限不足時は警告が出て続行します。
- OpenAI API 呼び出しはレート制限・ネットワーク断に対してリトライを実装していますが、API キーの課金・制限に注意してください。
- Paper Trading では PAPER_FILL_MODE で約定モードを制御できます（instant / partial / never / reject）。
- monitoring は常に本番用 sqlite_path を使用して監視ログを集中管理します（KABUSYS_ENV に関係なく）。
- .env 自動ロードはデフォルトで有効です。CI やテストで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 開発・拡張メモ

- config/*.yaml のテンプレートや scripts/generate_config.py の利用を想定（validate_config が存在をチェック）。
- DuckDB を用いた大規模なデータ分析・フェッチは research モジュールで行われます。DuckDB のスキーマ（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime 等）を準備してください。
- モジュール間の IO はできるだけ副作用を避ける設計（例: research や portfolio の関数は純関数的設計）を意識しています。

---

もし README に追加したい運用例（systemd / supervisor の unit ファイル例、Docker コンテナ化手順、requirements.txt の候補）や、実際の設定例（.env.example）をご希望であれば教えてください。必要に応じて追記します。