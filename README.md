# KabuSys — 日本株自動売買システム

このリポジトリは、日本株を対象とした自動売買システムのコアライブラリ群です。
ポートフォリオ構築、ポジションサイズ算出、監視（Monitoring）、発注実行（Execution）、
リサーチ（DuckDB を用いたファクタ計算）、および AI を用いたニュース分析などの機能を提供します。

---

## 目次
- プロジェクト概要
- 主な機能
- 前提条件
- セットアップ手順
- 環境設定（.env）と検証
- 実行方法（主要スクリプト）
- 重要な環境変数
- ログ / データファイル
- 停止・Kill Switch の扱い
- ディレクトリ構成

---

## プロジェクト概要
KabuSys は自動売買のコアロジック（シグナル → ポートフォリオ構築 → 注文発行）と、
運用を安全に行うための監視・リスク管理機能を備えた Python パッケージです。

設計方針（抜粋）:
- DuckDB を分析（価格・財務データ）に使用。DuckDB 接続を受ける純粋関数でファクタを計算。
- SQLite を監視・トレードログ保存に使用（monitoring.db / paper_trading.db）。
- 実行エンジンは paper_trading（モックブローカー）と live（実ブローカー）で分離。
- OpenAI を利用したニュースセンチメント（AI）モジュールを内包。失敗を許容するフェイルセーフ設計。
- .env による設定管理と対話型ウィザード / 検証 CLI を提供。

---

## 主な機能
- Execution エンジン起動スクリプト（run_execution）
  - 本番 / ペーパー（mock）切替、OrderManager / RiskManager / Reconciler 等の組み立て。
- Monitoring エンジン起動スクリプト（run_monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリングしてログ・アラート管理。
- 監視 DB レイヤ（monitoring_db）: system_status / trade_logs / positions / risk_logs / dashboard を管理。
- ポートフォリオ関連ユーティリティ
  - 候補選定（select_candidates）、等重/スコア重み（calc_equal_weights / calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）
  - セクターキャップ適用（apply_sector_cap）・レジーム乗数（calc_regime_multiplier）
- リサーチ
  - ファクター計算（momentum / volatility / value）、将来リターン・IC 計算、統計サマリ等
  - DuckDB を利用した SQL / Python 混在実装
- AI（OpenAI）連携
  - ニュース NLP スコアリング（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）
  - バッチ/リトライ・レスポンス検証を含む安全な実装
- ユーティリティ
  - ロギング設定（utils.logging_setup）
  - プロセス優先度 / CPU affinity（utils.process_priority）
  - 設定ウィザード（config_setup.py）と設定検証 CLI（validate_config.py）
- ツール
  - ペーパートレード検証レポート生成（tools.paper_verification_report）

---

## 前提条件
- Python 3.10 以上（typing の構文等を使用）
- 主な Python パッケージ:
  - duckdb
  - psutil
  - openai
  - (任意) PyYAML — config/*.yaml の検証に使用
- SQLite は標準ライブラリで問題ありません。

インストール例（仮想環境推奨）:
pip install -r requirements.txt
（requirements.txt がない場合は上記パッケージを個別インストールしてください）

---

## セットアップ手順

1. リポジトリをクローンし仮想環境を作成
   - git clone ...
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （検証用に: pip install pyyaml）

3. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
     - 対話的に .env を生成します（.env は Git にコミットしないでください）。
   - あるいは .env.example を参考に手動で作成。

4. 設定検証
   - python -m kabusys.validate_config
   - 厳密モード: python -m kabusys.validate_config --strict
   - 必須環境変数（例）: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等を確認します。

5. DB 初期化は起動スクリプトが自動で行います（monitoring 用 テーブル作成等）。

---

## 使い方（主要スクリプト/機能）

- 実行エンジン（Execution）
  - 起動:
    - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV によって paper_trading（mock broker）か live（実ブローカー）を選択。
    - paper_trading の場合、デフォルトで data/paper_trading.db を使用（環境変数で変更可）。
    - 実行時に data/execution.pid に PID を書き、data/stop_requested.flag や data/kill.flag を監視して停止制御。

- 監視ループ（Monitoring）
  - 起動:
    - python -m kabusys.run_monitoring
  - 動作:
    - SystemMonitor を含む監視コンポーネントを初期化し、ポーリングループで定期実行。
    - ポーリング間隔はデフォルト 60 秒。環境変数で上書き可能:
      - MONITOR_POLL_INTERVAL（秒、1 以上）
  - 注意:
    - Monitoring は常に本番の sqlite_path（Settings.sqlite_path）を使用して監視 DB に記録します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - --db PATH
    - 環境変数: PAPER_TRADING_SQLITE_PATH を利用可能（デフォルト: data/paper_trading.db）

- 設定ウィザード / 検証
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]

- AI モジュール（プログラム内呼び出し）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # api_key は環境変数 OPENAI_API_KEY にフォールバック
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

- モジュール単体テスト的な実行
  - MonitoringEngine の単発実行: 組み合わせてテスト用に run_once() を呼ぶことができます（ユニットテスト向け）。

---

## 重要な環境変数（主要なもの）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (AI 機能使用時に必須)
- KABUSYS_ENV: execution モード（development | paper_trading | live）デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR）
- LOG_DIR: ログファイル出力先（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading の成行約定挙動（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

（その他、config_setup で参照される項目があります。validate_config でチェックできます。）

---

## ログ / データファイル
- ログ:
  - デフォルトログディレクトリ: logs/
  - 起動時に app_name によるファイル <app_name>.log に日次ローテートで出力（TimedRotatingFileHandler）
  - コンソール出力は stdout に出力されます
- データファイル:
  - data/kabusys.duckdb（デフォルト）
  - data/monitoring.db（監視 DB）
  - data/paper_trading.db（ペーパートレード用 DB）
  - data/execution.pid（実行エンジン PID）
  - data/stop_requested.flag（ローカル停止要求フラグ。run_execution / run_monitoring が参照）
  - data/kill.flag（Kill Switch により作成。ExecutionEngine に停止を指示）

---

## 停止 / Kill Switch
- KillSwitch（kill.flag）:
  - RiskMonitor 等が一定条件（例: ドローダウン超過、ポジション数上限）を満たすと、data/kill.flag を書き込みます。
  - ExecutionEngine は起動時および実行中にこのフラグを監視し、存在したら安全に停止します。
  - flag の自動クリアは KILL_FLAG_CLEAR_ON_START=1（本番では推奨されない）で設定可能。
- ローカル停止:
  - data/stop_requested.flag を作成すると run_execution / run_monitoring のループは検知して終了します（運用者が明示的に停止したいときに使用）。

---

## ディレクトリ構成（主なファイル）
以下はパッケージ内の主要ファイルを抜粋した構成例です。

src/kabusys/
- __init__.py
- config.py                      — 環境変数 / Settings クラス、自動 .env ロードロジック
- config_setup.py                — .env 対話式ウィザード
- validate_config.py             — 起動前チェック CLI
- run_execution.py               — ExecutionEngine 起動スクリプト
- run_monitoring.py              — Monitoring ポーリング起動スクリプト

subpackages:
- ai/
  - news_nlp.py                  — ニュースセンチメント（OpenAI）処理
  - regime_detector.py           — レジーム判定（MA + マクロセンチメント）
- monitoring/
  - monitoring_db.py             — SQLite 永続化レイヤ
  - system_monitor.py            — システム・データ鮮度監視
  - trade_monitor.py             — （トレード監視）※実装あり
  - risk_monitor.py              — ドローダウン/ポジション上限監視
  - kill_switch.py               — kill.flag 管理
  - monitoring_engine.py         — 各 Monitor を束ねる
  - alert_manager.py             — （アラート送信管理）※実装あり
- execution/
  - execution_engine.py          — 実行エンジン本体（セッション管理）
  - broker_factory.py            — ブローカークライアント生成（mock / real）
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py           — ファクター計算（momentum/volatility/value）
  - feature_exploration.py       — IC などの解析ユーティリティ
- utils/
  - logging_setup.py             — ログ初期化ユーティリティ
  - process_priority.py          — プロセス優先度 / CPU affinity 設定
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成ツール

---

## 開発時の注意事項 / 運用上の留意点
- .env は決してリポジトリにコミットしないでください（秘密情報が含まれます）。
- KABUSYS_ENV=live のときは本番運用向けの追加警告が出ます。設定を慎重に確認してください。
- OpenAI の呼び出しは API 失敗時にフォールバック（例: macro_sentiment=0.0）しますが、APIキーは確実に設定してください（AI 機能が必要な場合）。
- Monitoring は監視用 DB へ常に本番 sqlite_path を使用する設計です（環境に依らず）。
- run_execution と run_monitoring は起動時にプロセス優先度を High に設定する試みを行います（OS 権限によって失敗する場合は警告を出します）。

---

README の内容はコードベースからの抜粋に基づき要点をまとめたものです。各モジュールの詳細な挙動は該当ファイルの docstring／コメントを参照してください。運用前に必ず python -m kabusys.validate_config による設定チェックを実行してください。