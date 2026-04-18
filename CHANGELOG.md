# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従い、日本語で記載しています。

## [Unreleased]
- （現在差分なし）

## [0.1.0] - 2026-04-18
初回リリース。KabuSys の基礎機能群を実装しました（環境設定 / 起動スクリプト / Execution/Monitoring / ポートフォリオ構築 / 各種ユーティリティ / 検証ツール）。

### 追加
- 全体
  - パッケージ初期バージョンを追加（src/kabusys/__init__.py に __version__ = "0.1.0" を設定）。

- 起動スクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB を使用し、MockBrokerClient を利用する挙動をサポート。
    - ストップフラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）の取扱い、バックグラウンドスレッドでのエンジン実行と安全な停止処理を実装。
    - 起動時にプロセス優先度を "high" に設定する処理を追加。
  - システム監視起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - SystemMonitor のポーリングループを実装。環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグの検出、監視 DB 初期化（監視用テーブルの冪等初期化）、DuckDB 接続管理を実装。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番用 sqlite_path を使用する旨を明示。

- 設定管理
  - 環境設定読み込みモジュールを追加（src/kabusys/config.py）。
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）と .env / .env.local の自動ロード（OS 環境変数を保護）。
    - 厳密な .env 行パーサ実装（export 形式対応、シングル/ダブルクォート内のエスケープ、インラインコメントの扱いなど）。
    - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / env/log level 等）と入力値検証（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等）。
    - paper_trading 用 DB パス、paper_fill_mode など Paper Trading 向け設定を追加。

  - 設定ウィザード CLI を追加（src/kabusys/config_setup.py）。
    - 対話式で .env ファイルを作成・更新するウィザードを提供。デフォルト値と秘匿入力対応、保存前確認を実装。

  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガードチェックを実装。
    - --strict オプションで警告を FAIL 扱いにできる。

- Execution コンポーネント（起動スクリプトから組み立てられる主要コンポーネントの呼び出し）
  - BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager など実行系の依存コンポーネントを統合して起動するフローを run_execution で実装（設定に基づくデフォルトパラメータをセット）。

- ポートフォリオ構築（純粋関数群）
  - 銘柄選定・重み付け（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順で候補選定（同点は signal_rank でタイブレーク）
    - calc_equal_weights: 等金額配分
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等分配へフォールバック）
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存ポジションのセクター比率が閾値を超える場合に当該セクターの新規候補を除外
    - calc_regime_multiplier: market レジームに応じた資金乗数（bull/neutral/bear マップ、未知レジームは警告の上フォールバック）
  - ポジションサイズ計算（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: risk_based / equal / score の各配分方式をサポート。単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash によるスケールダウン）、手数料/スリッページ考慮（cost_buffer）などのロジックを実装。

- ユーティリティ
  - ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）
    - StreamHandler（stdout）と TimedRotatingFileHandler（ログの毎日ローテーション、30世代保持）をルートロガーに統一的に設定。ログディレクトリの自動作成と失敗時のフォールバックを実装。
    - ログレベル / ログディレクトリの解決順を明記（引数 > 環境変数 > デフォルト）。
  - プロセス優先度 / CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）
    - Windows / POSIX を吸収した set_process_priority（high/normal/low）と set_cpu_affinity を提供。psutil ベースでアクセス拒否等の例外は警告でスキップ。

- ツール
  - Paper Trading 検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）
    - paper_trading DB（デフォルト: data/paper_trading.db）からシステム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（avg/max/P95）を算出し、閾値比較（稼働率 99% / 成功率 90% / 送信率 95% / P95 200ms）で PASS/FAIL を判定するレポートを生成。
    - 日付フィルタ（--from / --to）をサポート。DB 未存在時にはエラーメッセージ出力。

- 研究用モジュール（骨格）
  - ファクター計算モジュールの骨格を追加（src/kabusys/research/factor_research.py）。
    - モメンタム / MA200 / ATR / ボリューム系等の計算仕様を定義（DuckDB を用いた prices_daily/raw_financials 参照を想定）。（一部実装途中）

- パッケージ初期化
  - portfolio / tools / utils モジュールの __init__ を整備（エクスポート指定等）。

### 変更
- ログ出力先の設計
  - コンソール出力は stderr ではなく stdout に統一（cron / スケジューラでのリダイレクト運用を考慮）。
  - ログファイル出力に失敗した場合はコンソールのみでフォールバックする設計を採用。

- プロセス起動フロー
  - 起動時にプロセス優先度を最初に設定するよう統一（run_execution, run_monitoring）。

### 修正（バグ修正／改善）
- .env パーサの堅牢化
  - クォート内のバックスラッシュエスケープ、export プレフィックス対応、インラインコメントの扱いなどを正しく処理するよう改善。

- validate_config の動作改善
  - PyYAML 未導入時の挙動を警告にして YAML 検証をスキップするように変更。config/*.yaml が無ければ警告を出す。

- position sizing / sector cap の安全弁
  - 価格欠損時の挙動についてログを出すなどの防御的実装を追加（将来のフォールバック価格導入をコメントで明記）。

### 注意事項 / 既知の制約
- run_monitoring は「監視は環境にかかわらず本番 sqlite_path を使用する」設計になっています（意図的な仕様）。
- research/factor_research.py は一部実装が途中（ファイル末尾が未完）であり、完全実装は今後の課題です。
- 一部の機能（ブローカークライアント、ExecutionEngine の内部実装等）は本リリースでの参照を前提とした起動/統合のための呼び出し箇所を用意していますが、実際の詳細な実装は別モジュールに依存します。
- ログディレクトリ作成やプロセス優先度設定は環境依存で失敗する可能性があり、その場合は警告を出してフォールバックします。

---

この CHANGELOG はコードベースの内容から推測して作成しています。実際の変更履歴（コミット履歴やリリースノート）に基づく正確な差分が必要な場合は、Git の履歴やリリース時のノートを参照してください。