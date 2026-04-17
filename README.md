# KabuSys

日本株自動売買システム（参考実装）

このリポジトリは、シグナル生成〜ポートフォリオ構築〜発注〜監視／フェイルセーフまでを含む自動売買プラットフォームのコアユーティリティ群です。モジュールはできるだけ副作用を抑え、テストしやすい純粋関数や小さなクラスで構成されています。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要スクリプト・CLI）
- 環境変数（主要）
- 停止・フェイルセーフの仕組み
- ディレクトリ構成（主要ファイルの説明）
- 開発／運用上の注意

---

プロジェクト概要
- DuckDB/SQLite をデータ層に用い、ファクター計算・特徴量探索・ポートフォリオ構築・ポジションサイジング・発注管理・監視（Monitoring）・AI（ニュースセンチメント／レジーム判定）など、自動売買の主要機能を提供するモジュール群です。
- 設定は .env ファイル（または環境変数）から読み込み、実行モード（development / paper_trading / live）に応じて挙動を切り替えます。
- 実行中のプロセス優先度や CPU affinity を設定するユーティリティを備え、監視モジュールは DB にログを残してリスク（ドローダウン／滞留注文等）を検出すると kill.flag により ExecutionEngine を停止できます。

機能一覧（ハイライト）
- 環境設定ウィザード: kabusys.config_setup.run_wizard（.env を対話式生成）
- 設定検証 CLI: kabusys.validate_config（必須環境変数や config/*.yaml の簡易チェック）
- Execution 起動スクリプト: run_execution.py
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い paper_trading.db に記録（本番 DB と分離）
  - 実行中は PID ファイルを作成／チェック、停止フラグを監視
- Monitoring 起動スクリプト: run_monitoring.py
  - SystemMonitor / TradeMonitor / RiskMonitor を定期ポーリングして監視ログを SQLite に保存
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60秒）
- Monitoring 用永続化層: monitoring_db (テーブル作成・CRUD ユーティリティ)
- Kill Switch: kill_switch（条件を満たすと data/kill.flag を書き込み Execution を停止）
- Risk monitor: ドローダウン、ポジション上限の検出と記録
- Trade monitor: 滞留注文・約定異常価格の検出
- Portfolio モジュール:
  - 候補選定（select_candidates）、等分配／スコア加重（calc_equal_weights / calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）: risk_based / equal / score の各方式をサポート、単元株（lot_size）丸めや aggregate cap のスケーリングを実装
  - セクター上限の適用（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）
- Research モジュール:
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算（calc_forward_returns）、IC 計算、統計サマリー
  - DuckDB を使った SQL ベースの高性能集計
- AI モジュール:
  - news_nlp.score_news: OpenAI（gpt-4o-mini）でニュースをスコアリングして ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF（1321）MA 比率とマクロニュースの LLM 評価を合成して market_regime を決定
  - 再試行・JSON バリデーション・部分書き込みによる堅牢性を考慮
- ツール:
  - tools.paper_verification_report: Paper Trading DB を解析して稼働率・注文成功率・レイテンシ等のレポートを生成

セットアップ手順（ローカル開発向け）
1. Python バージョン
   - Python 3.10+ を推奨（型ヒントに | 演算子を使用）

2. 依存ライブラリ（最低限）
   - pip install duckdb psutil openai
   - PyYAML（config/*.yaml を検証したい場合）: pip install pyyaml
   - 必要に応じてその他のパッケージ（実装によっては追加依存あり）

   例:
   ```
   pip install duckdb psutil openai pyyaml
   ```

3. プロジェクトルートで .env を用意
   - 対話式で作成する: python -m kabusys.config_setup
   - あるいは .env.example を参照して手動作成（このリポジトリに .env.example がない場合は README の「環境変数」を参照）
   - .env は決してバージョン管理にコミットしないでください。

4. 初期 DB（実行時に自動作成されます）
   - monitoring DB（SQLite / デフォルト: data/monitoring.db）は run_execution/run_monitoring で init_monitoring_db を呼びます
   - DuckDB（デフォルト: data/kabusys.duckdb）は別途初期化するか、必要なテーブル（prices_daily / raw_financials / raw_news など）をロードしてください

使い方（主なコマンド・モジュール）
- 設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict   # 警告も FAIL 扱い
  ```

- Execution エンジン起動
  - 本番/ペーパーいずれもこのスクリプトを用いる
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、専用の paper_trading DB に記録され本番 DB と分離されます。
  - 実行中は data/execution.pid を作成・チェックします。停止は data/stop_requested.flag（または外部で kill.flag を設置）で実行できます。

- Monitoring 起動
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定（デフォルト 60）
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視は本番 DB を想定）

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で DB パスを指定可能

- ライブラリとしての利用（コード内呼び出し例）
  - AI ニューススコアリング:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="sk-...")
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="sk-...")
  - ポートフォリオ計算:
    from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes

主要な環境変数（デフォルト／説明）
- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード
- 動作モード
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- データベース
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- AI
  - OPENAI_API_KEY: OpenAI API キー（news_nlp/regime_detector で使用）
- ログ / 実行制御
  - LOG_LEVEL: DEBUG / INFO / ...
  - PID_FILE_PATH: 実行エンジン PID ファイル（デフォルト data/execution.pid）
  - KILL_FLAG_PATH: Kill Switch 用フラグ（デフォルト data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする (0/1)
- Monitoring
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）

停止・フェイルセーフの仕組み
- stop_requested.flag（data/stop_requested.flag）を作成すると run_monitoring/run_execution のループが検知して終了します。
- Kill Switch:
  - RiskMonitor / TradeMonitor / SystemMonitor の結果を基に KillSwitch が評価し、条件に合致すると data/kill.flag を書き込みます。
  - ExecutionEngine は起動時に kill.flag の有無を確認し、存在する場合は起動を中止します。起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動でクリアします（本番では 0 推奨）。

ディレクトリ構成（主要ファイル説明）
- src/kabusys/
  - __init__.py: パッケージ初期化（バージョンなど）
  - config.py: .env 自動ロード、Settings クラス（環境変数取得・検証）
  - config_setup.py: .env 対話式ウィザード
  - validate_config.py: 起動前チェック CLI
  - run_execution.py: ExecutionEngine 起動スクリプト
  - run_monitoring.py: Monitoring ポーリングループ起動スクリプト
  - utils/
    - process_priority.py: psutil を用いたプロセス優先度・CPU affinity 設定ユーティリティ
  - portfolio/
    - portfolio_builder.py: 候補選定・重み計算
    - position_sizing.py: 株数決定・スケーリング・単元丸め
    - risk_adjustment.py: セクターキャップ・レジーム乗数
  - monitoring/
    - monitoring_db.py: SQLite スキーマ作成・読み書き用クラス
    - system_monitor.py: システム状態・データ鮮度チェック
    - trade_monitor.py: 滞留注文・約定異常検出
    - risk_monitor.py: ドローダウン・ポジション上限監視
    - kill_switch.py: Kill Switch 実装
    - monitoring_engine.py: 全 monitor を束ねるエンジン
    - alert_manager.py: （アラート送信を担う想定のマネージャ — 実装分はファイル断片）
  - research/
    - factor_research.py: momentum / volatility / value 等のファクター計算（DuckDB）
    - feature_exploration.py: 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py: ニュースを LLM でスコアリングし ai_scores に保存
    - regime_detector.py: ETF MA とマクロセンチメントで市場レジームを判定
  - tools/
    - paper_verification_report.py: Paper Trading DB の検証レポート生成ツール
  - execution/, data/, strategy/ ... : 発注・データパイプライン・戦略などのコンポーネント（本 README に含まれる主要参照モジュール以外もプロジェクトに依存）

開発／運用上の注意
- .env は絶対にリポジトリに含めないでください（API キーやパスワードを含むため）。
- run_monitoring は監視用 DB を使用します。監視対象（ExecutionEngine）と DB が分離されていることを確認してください。
- process priority 設定は OS 権限に依存します。権限不足で警告が出ることがありますがフェイルオープンで続行します。
- OpenAI API を使う機能は API キーと利用制限に注意してください。失敗時は安全にフォールバックする設計ですが、スコア品質は API 依存です。
- DuckDB / SQLite のスキーマ整合性は重要です。データロードやマイグレーションは十分に検証してください。

サポート／拡張案
- strategy 実装（シグナル生成）、execution のブローカー実装（kabu/MockBroker）の接続
- alert_manager の LINE / Slack / Email 実装（LINE_TOKEN/USER_ID は設定可能）
- テスト用モック（OpenAI / Broker）や CI 用軽量 DB フィクスチャの追加
- Docker コンテナ化、systemd ユニットによるプロセス管理

---

ここに記載した情報はコードベースの主要部分からまとめたドキュメントです。各モジュールの詳細は該当モジュールの docstring / コメントを参照してください。追加の説明や具体的な実行例が必要であれば教えてください。