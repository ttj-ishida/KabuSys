# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-18

初回リリース。日本株自動売買システム KabuSys の基礎機能群を追加しました。
主要なコンポーネントは設定管理、起動スクリプト、ログ/プロセスユーティリティ、ポートフォリオ構築、ポジション決定、リスク調整、ペーパートレード検証ツールなどです。

### 追加（Added）
- 一般
  - パッケージのバージョンを定義（kabusys.__version__ = "0.1.0"）。
- 設定管理
  - Settings クラスを実装し、環境変数経由で設定を取得する機能を追加（src/kabusys/config.py）。
    - 多数の環境変数をプロパティとして提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 等）。
    - KABUSYS_ENV の検証（development / paper_trading / live）。
    - PAPER_FILL_MODE の検証（instant / partial / never / reject）。
  - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
    - 読み込み順: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - 既存 OS 環境変数は protected として上書きを防止。
  - .env ファイルのパースロジックを実装（クォート、export プレフィックス、インラインコメント処理等）。
- .env ウィザード
  - 対話式設定ウィザードを追加（python -m kabusys.config_setup）。
    - 初期 .env 作成/更新をサポート。シークレット項目のマスク表示、デフォルト/選択肢対応、保存用ヘッダーを出力（src/kabusys/config_setup.py）。
- 設定検証 CLI
  - 起動前の設定チェック CLI を追加（python -m kabusys.validate_config）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在/パース検証（PyYAML 任意）等。
    - --strict オプションで警告を失敗扱いにできる。
- 起動スクリプト
  - 監視プロセス起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル data/stop_requested.flag による安全停止検出。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用する旨の明確化。
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を利用し、Paper Trading 用 DB（data/paper_trading.db または PAPER_TRADING_SQLITE_PATH）に記録して本番 DB と分離。
    - 停止フラグ / PID ファイル管理、ExecutionEngine を別スレッドで起動して監視する構成。
- ログ & プロセスユーティリティ
  - 統一的なログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout へ StreamHandler、日次ローテーションのファイルハンドラ（logs/<app>.log、30 日保持）を設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - LOG_LEVEL / LOG_DIR の解決順をサポート。
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX を吸収し set_process_priority(level)（high/normal/low）を提供。
    - CPU affinity の設定 set_cpu_affinity(cpu_count) を実装。
    - 権限不足や未対応 OS では警告を出して安全にスキップ。
- ポートフォリオ構築（純粋関数群）
  - 候補選定 & 重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates、calc_equal_weights、calc_score_weights を実装。スコア合計が 0 の場合は等金額でフォールバック。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有を基にセクター上限を超える候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: regime に応じた資金乗数（bull/neutral/bear）を返却。未知レジームは警告して 1.0 フォールバック。
  - 株数決定・リスク制限（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method (risk_based / equal / score) による発注株数計算、単元株（lot_size）丸め、max_position_pct / max_utilization / cost_buffer による上限管理、aggregate cap によるスケールダウンと端数分配ロジックを実装。
- 調査・リサーチ
  - ファクター計算モジュール追加（src/kabusys/research/factor_research.py）。
    - Momentum / Value / Volatility / Liquidity に関する設計とモジュール骨格。DuckDB を受け取り prices_daily / raw_financials を参照する設計方針（関数部分は実装中）。
- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - 指標: 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg/max/P95）。
    - 合否基準（デフォルト閾値）を定義（稼働率 >= 99%、成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）。
    - コマンドライン引数で期間指定 (--from/--to) と DB パス指定 (--db) が可能。

### 変更（Changed）
- ログ出力
  - ログハンドラは既存ハンドラを一旦 flush/close してから再設定することで二重設定を防止（logging_setup）。
- .env 読み込み
  - .env のパースを堅牢化（export プレフィックス、クォート内エスケープ、インラインコメントの取り扱い等）。
  - .env.local が .env より優先される（override=True）挙動を明確化。
- 起動スクリプトの安全性
  - run_execution/run_monitoring 起動時に最初にプロセス優先度を設定するように統一（set_process_priority("high") を呼び出し）。

### 修正（Fixed）
- 環境変数の妥当性チェック
  - Settings と validate_config において KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の不正値検出を追加し、明確なエラーメッセージを返すようにした。
- ポジション算出の数値安定性
  - position_sizing: price が欠損または 0 の場合にスキップし、不正な計算を回避するガードを追加。
- run_monitoring の MONITOR_POLL_INTERVAL
  - 環境変数が不正（整数変換失敗や 0 以下）な場合にデフォルト（60 秒）へフェールバックするようにした（警告ログあり）。

### ドキュメント（Documentation）
- 各モジュールに docstring と使用例を追加。CLI 用の使い方コメントも含め説明を強化。

### 既知の問題（Known issues）
- research.factor_research の calc_momentum 等の実装が途中（ファイルが途中で切れている）。ファクター計算の詳細実装は今後のリリースで追加予定。
- 一部の TODO（価格フォールバックや銘柄ごとの lot_size 等）が残存。

### 破壊的変更（Breaking Changes）
- なし（初回リリース）

---

今後の予定:
- factor_research のフル実装（DuckDB クエリと正規化処理）。
- ExecutionEngine / Broker クライアント周りのさらなるテストとドキュメント追加。
- 単体テスト・CI の整備と自動化。