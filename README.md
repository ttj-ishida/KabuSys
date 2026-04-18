# KabuSys — 日本株自動売買システム README

このリポジトリは日本株向けの自動売買システム（KabuSys）の一部実装です。
戦略・ポートフォリオ構築・発注・監視・研究（DuckDB利用）・AI支援（OpenAI）などの機能群を含みます。

---

## プロジェクト概要

KabuSys は以下の責務を持つモジュール群で構成されています。

- 発注エンジン（ExecutionEngine）：ブローカークライアント経由で発注・注文管理・リスク管理を行う。
- 監視（Monitoring）：システム状態、注文滞留、リスク（ドローダウン・ポジション上限）を定期チェックし、必要に応じて Kill Switch（停止フラグ）を発動。
- ポートフォリオ構築：銘柄選定・重み付け・ポジションサイズ計算・セクター制約、レジーム乗数処理等。
- 研究（Research）：DuckDB を用いたファクター計算・特徴量解析・IC計算など。
- AI（OpenAI）連携：ニュースのセンチメント評価やマクロセンチメントを用いたレジーム判定。
- ツール：Paper Trading 検証レポート生成などのユーティリティ。

設計方針の一部：
- 本番とペーパートレードを明確に分離（DBやブローカーは別扱い）。
- ルックアヘッドバイアス対策（date.today() などに依存しない設計）。
- フェイルセーフ（外部API失敗時は安全側にフォールバック）や冪等性を重視。

---

## 主な機能一覧

- Execution
  - 実際の/モックのブローカー経由での発注処理
  - リスク管理（ポジション割合、利用率、回路遮断など）
  - 注文履歴の保持（SQLite）
- Monitoring
  - CPU/メモリ/ディスク使用率・プロセス生存チェック
  - データ鮮度チェック（DuckDB の価格データ）
  - 注文滞留・約定異常検出
  - ドローダウン・ポジション上限検出と Kill Switch（data/kill.flag）発動
  - アラート通知（LINE等の設定を利用可能）
- Portfolio
  - 候補選定、等配分/スコア配分、スコアが0の場合のフォールバック
  - セクターキャップ適用、レジーム乗数計算
  - 株数決定（リスクベース／等配分／スコア配分）と lot_size 単位丸め、aggregate cap のスケーリング
- Research
  - Momentum／Volatility／Value 等のファクター計算
  - 将来リターン、IC（Spearman）計算、統計サマリー
  - DuckDB を使った SQL + Python 実装
- AI
  - ニュース記事の銘柄別センチメントスコア算出（OpenAI 使用）
  - マクロニュース + ETF MA200 を組み合わせた市場レジーム判定（bull/neutral/bear）
- ツール
  - Paper Trading 検証レポート生成（稼働率・成功率・レイテンシ等）

---

## 必要条件（依存関係）

- Python 3.9+
- 必要な Python パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で任意）
- SQLite（Python に同梱）
- kabuステーション や J-Quants 等外部サービスの設定（API トークン等は .env で管理）

パッケージは requirements.txt がある場合はそれを利用してください（本サンプルでは明示的な requirements は含まれていません）。

例:
pip install duckdb psutil openai PyYAML

---

## セットアップ手順

1. リポジトリルートへ移動
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を使用する設計です。

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - pip install duckdb psutil openai PyYAML

4. .env ファイルの作成（対話ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードは .env を生成/更新します。生成した .env は絶対に Git にコミットしないでください。

5. 設定検証
   - python -m kabusys.validate_config
   - 警告も厳密に扱いたい場合は --strict を付けます:
     python -m kabusys.validate_config --strict

6. DB 初期化・データ配置
   - DuckDB（デフォルト: data/kabusys.duckdb）や SQLite（デフォルト: data/monitoring.db / data/paper_trading.db）に必要なテーブルやデータを用意します（本リポジトリの一部機能は既存テーブルを前提にします）。
   - monitoring の初期化は起動スクリプトが行います（init_monitoring_db）。

---

## 環境変数（主要なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要な任意/デフォルト値:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- KILL_FLAG_CLEAR_ON_START: 0 or 1
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで必要）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

設定は .env/.env.local または OS 環境変数で指定できます。config モジュールは自動で .env をロードします（自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

---

## 使い方

基本的な起動・運用コマンドの例。

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告を FAIL 扱い）: python -m kabusys.validate_config --strict

- ExecutionEngine 起動（本番または paper_trading に応じた動作）
  - python -m kabusys.run_execution
  - 実行中に data/stop_requested.flag を作成すると（または外部で作成済みの場合）起動しない/停止します。
  - 実行時は PID ファイル (data/execution.pid) を作成します。
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、data/paper_trading.db を使用します（実口座とは完全分離）。

- Monitoring 起動（ポーリングで各種チェックを実行）
  - MONITOR_POLL_INTERVAL 環境変数で秒数を上書き可能（デフォルト 60 秒）。
  - python -m kabusys.run_monitoring
  - 監視は常に本番 sqlite_path を使用（環境に関係なく monitoring DB は同一の本番パスを想定）。
  - 停止には data/stop_requested.flag を作成するか KeyboardInterrupt。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH でも可）

- AI モジュール（プログラム内呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続（DuckDBPyConnection）、target_date（date型）、api_key（未指定なら OPENAI_API_KEY を使用）
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 同様に使用

注意:
- monitoring は monitoring_db.init_monitoring_db を使って監視用テーブルを初期化します（冪等）。
- Kill Switch は data/kill.flag を書き込み、ExecutionEngine に停止を促します（ExecutionEngine は起動時に kill.flag を検査）。

---

## 実行時フラグ・ファイル

- data/stop_requested.flag
  - run_execution.py / run_monitoring.py が参照する外部停止フラグ。存在すると監視ループや実行エンジンの起動/継続を停止します。

- data/kill.flag
  - KillSwitch が作成するフラグ。ExecutionEngine 側はこのファイルの存在を検知して停止します。KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動でクリアされる設定が可能（本番では 0 推奨）。

- PID ファイル
  - data/execution.pid: 実行エンジン稼働時に PID を書き込む。system monitor が stale PID を検知し削除することがある。

---

## ディレクトリ構成（主要ファイル）

以下はリポジトリ内の主要なディレクトリ・ファイルの概観（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings 管理
  - config_setup.py               — .env 対話ウィザード
  - validate_config.py            — 起動前チェック CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading レポート
  - ai/
    - news_nlp.py                 — ニュース NLP（OpenAI 呼び出し）
    - regime_detector.py          — レジーム判定（MA200 + macro）
  - monitoring/
    - monitoring_db.py            — SQLite 監視ログ層
    - monitoring_engine.py        — 各 Monitor を束ねるループ
    - system_monitor.py           — CPU/メモリ/データ鮮度/プロセス監視
    - trade_monitor.py            — 注文滞留・約定異常監視
    - risk_monitor.py             — ドローダウン・ポジション上限監視
    - kill_switch.py              — kill.flag 書き込みユーティリティ
    - alert_manager.py            — （アラート送信の集約, 実装ファイルあり）
  - execution/                     — 発注エンジン関連（OrderManager 等）
  - portfolio/
    - portfolio_builder.py        — 候補選定・重み計算
    - position_sizing.py          — 株数計算・キャップ適用
    - risk_adjustment.py          — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py          — ファクター計算（momentum/value/vol）
    - feature_exploration.py      — 将来リターン・IC・統計サマリ
  - utils/
    - process_priority.py         — プロセス優先度 / CPU affinity 設定
  - data/                          — デフォルト DB ファイル等（.gitignore 推奨）

（実際のファイルは src/kabusys 以下の各モジュール参照）

---

## 開発・運用時の注意点

- .env は機密情報を含むため決して Git に含めないこと（config_setup.py のヘッダにも注意書きあり）。
- KABUSYS_ENV を `live` に設定する前に validate_config で設定を十分に確認してください（本番用ガードあり）。
- OpenAI を使う機能は API キーを必要とし、レート制限やエラーに対してリトライ・フォールバック実装があるものの、費用やレートに注意してください。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と完全に分離されるよう設計されています。テスト時はこれを活用してください。
- プロセス優先度設定や CPU affinity 設定は psutil を使用します。権限や OS により適用できない場合があります（警告ログでスキップ）。

---

## 参考コマンドまとめ

- .env ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- ExecutionEngine 起動:
  - python -m kabusys.run_execution
- Monitoring 起動（ポーリング間隔を 30 秒にする例）:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または DB 指定: python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

---

必要であれば README にサンプル .env テンプレート、運用手順（systemd ユニット例、ログ管理、バックアップ方針）や設計ドキュメント（PortfolioConstruction.md 等参照）を追加できます。追加希望があればどの情報を含めるか教えてください。