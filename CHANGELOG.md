CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに準拠して記載しています。  
（コードベースから推測して作成した初期リリース向けの変更履歴です）

[Unreleased]
------------

なし

[0.1.0] - 2026-04-19
--------------------

Added
- 初期リリース: KabuSys パッケージを追加（__version__ = 0.1.0）。
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動する CLI。  
    - KABUSYS_ENV に応じて本番 / ペーパートレード用 DB を分離（paper_trading 時は PAPER_TRADING_SQLITE_PATH / data/paper_trading.db を使用）。  
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine をスレッドで実行。  
    - 停止フラグ (data/stop_requested.flag) と PID ファイル管理 (data/execution.pid) に対応。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。  
    - 監視処理は本番の sqlite_path を使用（KABUSYS_ENV に依存せず本番 DB を参照）。
- 設定・環境管理
  - config.py: 環境変数・設定を扱う Settings クラスを実装。  
    - .env/.env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。  
    - 自動読み込みの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。  
    - 各種設定プロパティ（DB パス、ログレベル、KABUSYS_ENV 判定、paper_trading 用 fill mode など）とバリデーションを実装。
  - config_setup.py: .env を対話式で作成・更新するウィザードを実装。  
    - シークレット項目のマスク表示、保存時のテンプレート出力、デフォルト値・選択肢サポート。
  - validate_config.py: 起動前の設定検証 CLI を実装。  
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パス・config/*.yaml の存在（および PyYAML があればパース検証）、本番環境向けのガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）を実行。  
    - --strict モードで警告を FAIL 扱いに出来る。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: ルートロガー設定ユーティリティを実装。  
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler）を設定。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。  
    - ログレベル / ログディレクトリの解決ルールをドキュメント化。
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを実装。  
    - Windows / POSIX の差分を吸収して set_process_priority/set_cpu_affinity を提供。権限不足や未対応環境では警告を出してスキップ。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）と等配分・スコア加重（calc_equal_weights / calc_score_weights）を実装。  
    - スコアが全て 0 の場合は等金額配分へフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。  
    - unknown セクターはセクター上限チェックの対象外にする仕様。
  - portfolio/position_sizing.py: 発注株数算出（calc_position_sizes）を実装。  
    - allocation_method（"risk_based" / "equal" / "score"）をサポート。  
    - 単元株 (lot_size) に丸め、per-position 上限・aggregate cap によるスケールダウン、cost_buffer による保守的見積り、残差に基づく追加配分ロジックを実装。
- Research / Tools
  - research/factor_research.py: DuckDB を用いたファクター計算モジュール（モメンタム等の計算ロジックを開始）。DuckDB の prices_daily / raw_financials を利用する設計。  
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成 CLI を実装。  
    - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、レイテンシ（平均 / 最大 / P95）を集計し PASS/FAIL 判定を出力。  
    - P95 計算、日付フィルタ、DB パスの引数/環境変数サポートを追加。
- DB/監視
  - monitoring.monitoring_db.init_monitoring_db を各起動スクリプトから呼び出し、監視テーブルが存在することを冪等に保証。
- CLI/UX
  - 対話式ウィザードや検証スクリプトでの入力中断処理（EOF/KeyboardInterrupt）のハンドリング、保存キャンセル、マスク表示などユーザビリティを考慮。

Fixed / Improved
- .env パーサの堅牢化（config._parse_env_line）
  - export プレフィックス、シングル / ダブルクォート、バックスラッシュエスケープ、インラインコメント処理、クォートなし時のコメント判定などに対応してより正確にパースするよう改良。
- 自動読み込みの安全化
  - プロジェクトルートが見つからない場合は自動 .env 読み込みをスキップ。OS 環境変数は保護（protected）し、.env.local で上書き可能にする挙動を明示。
- 環境変数の値検証とフォールバック
  - MONITOR_POLL_INTERVAL の値が不正（非整数や 0 以下）の場合はデフォルト（60 秒）にフォールバックして警告を出す。
  - PAPER_FILL_MODE の許容値検査を実装し、不正値で例外を送出。
  - KABUSYS_ENV / LOG_LEVEL の不正値チェックと適切なエラーメッセージを追加。
- ログ周りの堅牢化
  - ログディレクトリ作成失敗やファイルハンドラ作成失敗時にストリーム出力のみで継続し、失敗原因を警告するように改善。
- プロセス優先度設定の例外処理強化
  - 権限不足や未実装 API に対して警告を出してスキップする実装により起動失敗を回避。
- validate_config の柔軟性
  - PyYAML 未インストール時は YAML 内容検証をスキップして警告を出力。config/*.yaml の存在チェックとパースエラー検出を実装。
- ExecutionEngine と Monitoring の安全停止
  - data/stop_requested.flag を用いた外部停止フラグ検知を追加。ExecutionEngine はフラグ検知で engine.stop() を呼び出して安全停止。

Security
- config_setup の出力でシークレット項目は表示時にマスク（****）するようにして、画面上での漏洩リスクを軽減。

Known limitations / Notes
- research/factor_research.py は DuckDB を前提としたファクター計算の実装を開始しており、外部モジュールや完全なユニットテストの整備が今後の作業として残る可能性があります（コード断片が存在します）。
- position_sizing の価格フォールバックについて注釈があり（price が欠損の際の挙動）、将来的に前日終値等での補完が検討されています。
- 一部機能は実運用（特に本番環境の KABUSYS_ENV=live）での十分な検証・監査を推奨（validate_config の警告を参考にしてください）。

---

今後の予定（例）
- research モジュールの完全実装（各ファクターの完成・テスト）
- ユニットテストの整備と CI の導入
- 発注ロジック（ExecutionEngine / BrokerClient）のエラー耐性強化とマルチ環境での検証
- 単体テスト・統合テスト向けに KABUSYS_DISABLE_AUTO_ENV_LOAD を利用したテスト用設定ロードの改善

（以上）