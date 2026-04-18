Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記載します。
このファイルは Keep a Changelog のフォーマットに準拠しています。

履歴
----

### [0.1.0] - 2026-04-18
初回公開リリース。

概要:
- 日本株自動売買フレームワーク「KabuSys」の初期実装を追加しました。
- 実行・監視スクリプト、環境設定ユーティリティ、ログ設定、プロセス制御、ポートフォリオ構築、ペーパートレード検証ツールなど、運用に必要な主要コンポーネントを含みます。

追加 (Added)
- 基本情報
  - パッケージバージョンを __version__ = "0.1.0" として設定。
- 設定管理
  - kabusys.config.Settings クラスを導入:
    - 環境変数取得ラッパー（DB パス、API トークン、ログ設定、閾値等）。
    - KABUSYS_ENV の値検証（development / paper_trading / live）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
    - .env ファイルの自動ロード機能（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
  - .env パース実装はクォートやエスケープ、コメントの取り扱いに対応。
- 環境設定 CLI
  - kabusys.config_setup: 対話式ウィザードで .env を初期作成/更新するツールを追加。
    - デフォルト項目、シークレットマスク、保存時の注意喚起を備える。
- 設定検証 CLI
  - kabusys.validate_config: 起動前チェックツールを追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリチェック、config/*.yaml の存在チェック（PyYAML がある場合はパース検証）、
      本番環境向けのガード（LINE トークン・Kill Switch 設定の警告）を実施。
    - --strict オプションで警告を FAIL 扱いに可能。
- 実行・監視スクリプト
  - run_execution.py:
    - ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory からブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine をスレッドで実行。
    - 停止フラグファイル（data/stop_requested.flag）および pid ファイルの取り扱いを実装。
    - RiskConfig のデフォルトパラメータ（max_position_pct, max_utilization, rate_limit_per_sec 等）を設定。
  - run_monitoring.py:
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告を出力。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを記録（init_monitoring_db を呼び idempotent に初期化）。
    - 停止フラグ検出によりループを安全終了。
- ロギング・プロセス制御
  - kabusys.utils.logging_setup.setup_logging:
    - ルートロガーに対して StreamHandler（stdout）と TimedRotatingFileHandler（日次・30世代保持）を設定。
    - 既存ハンドラの二重設定を防ぐため一度クリアして再設定。
    - LOG_DIR 作成失敗時はファイル出力をスキップし stdout のみで継続。
    - stdout を使用することで cron 等からのリダイレクトを容易に。
  - kabusys.utils.process_priority:
    - set_process_priority(level) を追加し、Windows / POSIX の差分を吸収して優先度設定を行う（"high"/"normal"/"low"）。
    - set_cpu_affinity(cpu_count) を追加（指定がない場合は変更しない）。
    - 権限不足や未対応 OS では警告を出し安全にスキップする実装。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - kabusys.portfolio.portfolio_builder:
    - select_candidates: スコア降順で候補選択（signal_rank でタイブレーク）。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア正規化配分。全スコアが 0 の場合は等配分にフォールバックして警告。
  - kabusys.portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限（max_sector_pct）を考慮して候補をフィルタ。unknown セクターは除外しない。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear）。未知のレジームは 1.0 でフォールバック（警告）。
  - kabusys.portfolio.position_sizing:
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に基づき発注株数を計算。
    - 単元株（lot_size）で丸め、per-stock 上限（max_position_pct）、aggregate cap、cost_buffer を考慮したスケーリングと端数配分ロジックを実装。
- Paper Trading 関連ツール
  - kabusys.tools.paper_verification_report:
    - ペーパートレード向け検証レポート生成ツールを追加。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシ等を集計・判定（閾値を定義して PASS/FAIL 出力）。
    - P95 の計算ロジック、期間フィルタ（--from/--to）、DB パス指定（--db / 環境変数）をサポート。
- 監視 DB 初期化ユーティリティの利用
  - init_monitoring_db が監視用テーブルの存在を保証するため monitoring/関連で呼び出される（冪等）。

変更 (Changed)
- ロギング出力先として stderr ではなく stdout をデフォルトに変更（setup_logging）。これは Task Scheduler / cron 等で stdout/stderr を一本化して扱う用途を想定。
- .env 読み込み順序を OS 環境 > .env.local > .env とし、OS 環境変数を保護（protected）する仕組みを導入。

修正 (Fixed)
- MONITOR_POLL_INTERVAL の不正値（0、負数、非数）に対してデフォルトにフォールバックし、ログで警告を出力するようにして time.sleep の ValueError を回避。
- process_priority の実行で権限不足や未実装 API によりクラッシュしないよう例外を捕捉して警告を出すように改善。

注意・破壊的変更 (Breaking Changes / Notes)
- Settings クラスのバリデーションにより、環境変数値が無効な場合は ValueError が発生します。KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等を正しい値に設定してください。
- .env ファイルはセキュリティ上コミットしないこと（config_setup のヘッダでも注意喚起を記載）。

セキュリティ (Security)
- .env の扱いに関する注意喚起を config_setup に追加（.git へコミットしない旨）。
- シークレット項目は対話式ウィザードで表示をマスク。

既知の制限 (Known limitations)
- research.factor_research の実装はモジュール開始のスキャフォールドが含まれていますが、一部計算処理が未掲載のため追加実装が必要（momentum 計算などは準備済みの定数群あり）。
- position_sizing: price が欠損（0.0）の場合にエクスポージャーが過少評価されうる旨をコメントとして残しています（将来的にフォールバック価格の採用を検討）。

今後の TODO（例）
- factor_research の完全実装（全ファクター算出）。
- 銘柄別 lot_size の扱い拡張（マスタ参照）。
- 詳細なユニットテストの追加（特にポジションサイズ算出、端数配分ロジック、process_priority のプラットフォーム差分）。

配布物・起動方法のヒント
- .env は config_setup で作成し、validate_config で起動前チェックを行ってください。
- 実行: python -m kabusys.run_execution / python -m kabusys.run_monitoring
- Paper Trading: KABUSYS_ENV=paper_trading を指定すると paper 専用 DB を使用します（PAPER_TRADING_SQLITE_PATH）。

-- END --