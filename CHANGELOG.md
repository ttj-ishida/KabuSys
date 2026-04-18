CHANGELOG
=========

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

Unreleased
----------

- なし

[0.1.0] - 2026-04-18
--------------------

Added
- コア CLI / 実行スクリプトを実装
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV が paper_trading の場合は専用の paper_trading DB を使用し、本番 DB と完全に分離されるように設計。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視モジュールは環境に関わらず本番 sqlite_path を使用する仕様。
- 設定関連のユーティリティと CLI を追加
  - config.py: .env 自動読み込み、堅牢な .env パーサー（クォート、エスケープ、export 形式、インラインコメント処理等）を実装。Settings クラスで各種設定（DB パス、各種閾値、KABUSYS_ENV 判定、PAPER_FILL_MODE の検証等）を提供。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを実装（秘密項目マスク表示・既存値再利用・確認プロンプト付き）。
  - validate_config.py: 起動前に .env と config/*.yaml を検証する CLI を実装。必須環境変数のチェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、PyYAML の有無に応じた YAML 検証、live 環境用のガード（LINE 設定や Kill Flag の扱い）を提供。--strict モードで警告を失敗扱いにできる。
- ポートフォリオ構築（純関数群）を実装（db 非依存）
  - portfolio/portfolio_builder.py: 候補選定 select_candidates、等分配 calc_equal_weights、スコア加重 calc_score_weights を実装。スコアが全て 0 の場合は等分配へフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限を適用する apply_sector_cap、および市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（未知レジームはフォールバックで 1.0 を返す）。
  - portfolio/position_sizing.py: allocation_method("equal" / "score" / "risk_based") に基づく株数算出を実装。単元株（lot_size）で丸め、1 銘柄上限・aggregate 上限（available_cash）に基づくスケーリング、cost_buffer を考慮した保守的見積り、残差配分ロジックを備える。
- 監視／実行周りの基盤ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを実装。stdout へ StreamHandler、日次ローテート（TimedRotatingFileHandler）でログファイル出力（logs/<app_name>.log）を行う。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: Windows / POSIX の差分を吸収するプロセス優先度設定（high/normal/low）と CPU affinity 設定を実装。権限不足や未対応 OS は警告でスキップ。
- ペーパートレード検証ツールを追加
  - tools/paper_verification_report.py: Paper Trading の SQLite（デフォルト data/paper_trading.db）を参照し、稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）・リスク却下数を算出するレポートを生成。判定閾値（稼働率 99%、成立率 90% 等）による PASS/FAIL 判定を出力。
- research/factor_research.py（ファクター計算基盤）を追加（設計・一部実装）
  - Momentum / Value / Volatility / Liquidity の計算方針を定義。DuckDB 接続を受け取り prices_daily / raw_financials を用いて計算する設計。モジュール内に計算ウィンドウや定数を定義（例: MA200、ATR 期間等）。

Changed
- ロギングのデフォルト動作調整
  - StreamHandler は stderr ではなく stdout を使用（cron 等で stdout/stderr を一本化する運用を想定）。
  - ログローテーションは日次、30 日分保持に設定。
- 環境変数の自動ロード優先順位を定義
  - OS 環境 > .env.local > .env の順で読み込み。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを抑制可能。OS 環境変数は保護され上書きされない。
- Execution / Monitoring の DB 接続規則
  - 監視（run_monitoring）は環境に関係なく sqlite_path（本番用）を使用。
  - 実行（run_execution）は paper_trading 環境時に paper_sqlite_path を使用することで本番 DB と分離。

Fixed
- .env 解析の改善
  - export KEY=val 形式、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いを正しく処理するように改善。無効行は無視。
- 環境値の検証追加
  - Settings.paper_fill_mode の検証（許容値: instant|partial|never|reject）を追加し、不正値時は ValueError を送出。
  - Settings.env / LOG_LEVEL の妥当性チェックで不正値を早期に検出するように。

Security
- シークレット値の取り扱いに注意を促す .env テンプレートと README 相当のコメントを config_setup に追加（.env を絶対にコミットしない旨を明記）。

Known issues / Notes
- portfolio/risk_adjustment.apply_sector_cap:
  - price_map に価格が欠損（0.0）の場合、エクスポージャーが過少見積もられ除外されない可能性あり。将来的に前日終値や取得原価等のフォールバックを検討する旨の TODO を残している。
- research/factor_research.py:
  - モジュールは設計と一部実装が含まれるが、全ファクターの最終的な SQL / 出力整形が未完成の可能性あり（コード末尾が途中で切れている）。
- run_monitoring / run_execution:
  - 外部モジュール（SystemMonitor, ExecutionEngine, BrokerClient 等）の実装に依存しており、それらの振る舞い次第で運用上の注意点が発生し得る。
- process_priority / set_cpu_affinity:
  - 権限不足や未対応プラットフォームでは警告を出してスキップする挙動。完全なプラットフォーム互換性は保証しない。

その他
- パッケージバージョンを 0.1.0 に設定。
- 初期リリースとして、実行／監視基盤、設定管理、ポートフォリオ設計ロジック、レポート生成ツールを提供。

参考
- 主な環境変数:
  - KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_LEVEL, LOG_DIR, MONITOR_POLL_INTERVAL, PAPER_FILL_MODE, KILL_FLAG_CLEAR_ON_START
- ログファイル: デフォルト logs/<app_name>.log（日次ローテーション）

-------------------------------------------------------------------------------
この CHANGELOG はコードベース中の実装とコメントから推測して作成しています。実際の変更履歴・リリースノートはプロジェクトのリリース管理ポリシーに従って調整してください。