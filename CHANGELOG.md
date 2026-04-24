KEEP A CHANGELOG 準拠の CHANGELOG.md（日本語）を以下に作成しました。リポジトリのコードから実装内容を推測して記載しています。必要に応じて日付や詳細を調整してください。

KEEP A CHANGELOG
================

すべての可視的な変更はこのファイルに記録します。慣例に従い主なカテゴリ（Added / Changed / Fixed / Deprecated / Removed / Security）で整理しています。

なお、本CHANGELOGはコードベースの内容から推測して作成しています。実際のコミット履歴と差異がある場合は適宜修正してください。

[0.1.0] - 2026-04-24
--------------------

Added
- 初期リリース: KabuSys 自動売買システムのコア機能群を追加。
- 環境設定
  - Settings クラスを追加（kabusys.config）。環境変数から各種設定値を取得・検証。
  - .env 自動ロード機能を追加（プロジェクトルート検出: .git または pyproject.toml を基準）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env パーサを実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの取り扱いに対応）。
  - PAPER_FILL_MODE（paper trading のフィルモード）や PAPER_TRADING_SQLITE_PATH などペーパートレード向けの設定を追加。
- 設定ユーティリティ / CLI
  - 対話式環境設定ウィザードを追加（kabusys.config_setup）。.env の作成・更新を支援。
  - 設定検証 CLI を追加（kabusys.validate_config）。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在とパース（PyYAML が利用可能な場合）などを検証。--strict オプションで警告を FAIL 扱いにできる。
- 起動スクリプト
  - 実行エンジン起動スクリプトを追加（kabusys.run_execution）。
    - KABUSYS_ENV=paper_trading 時は専用の paper DB を使用して本番 DB と分離。
    - BrokerClientFactory 経由のブローカークライアント選択、OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てと起動。
    - 停止フラグ（data/stop_requested.flag）を監視して安全にシャットダウン。
  - 監視ループ起動スクリプトを追加（kabusys.run_monitoring）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバック。
    - 監視は本番の sqlite_path を参照（環境に依らず本番用の監視 DB を使用する設計）。
    - SystemMonitor の check_once を定期実行し、例外をログに記録して継続。
- ロギング / プロセス管理
  - 統一的なログ設定ユーティリティを追加（kabusys.utils.logging_setup）。
    - stdout 出力用 StreamHandler と日次ローテーションでファイル出力する TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30 日保持）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソール出力のみで継続。
    - stdout を使用することでスケジューラ運用との相性を考慮。
  - プロセス優先度 / CPU affinity ユーティリティを追加（kabusys.utils.process_priority）。
    - Windows と POSIX を吸収して "high"/"normal"/"low" を設定。未対応 OS や権限不足時は警告を出してスキップ。
    - CPU affinity を最初の N コアに固定するユーティリティを提供。
- ポートフォリオ構築（純粋関数群）
  - 銘柄選定と重み付け（kabusys.portfolio.portfolio_builder）
    - select_candidates: score 降順 + 同点時 signal_rank によるタイブレーク。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分。全銘柄スコアが 0 の場合は等金額配分にフォールバック（警告ログ）。
  - セクター制約・レジーム乗数（kabusys.portfolio.risk_adjustment）
    - apply_sector_cap: 既存ポジションに基づくセクター集中上限の適用（"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金乗数（未知レジームはフォールバック 1.0、警告ログ）。
  - 銘柄ごとの株数決定（kabusys.portfolio.position_sizing）
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じた発注株数計算、単元（lot_size）丸め、1 銘柄上限・aggregate cap の適用、cost_buffer を用いた保守的見積り、スケールダウン時の残差処理（再現性確保のため順序安定化）。
- Paper Trading 検証ツール
  - paper_verification_report を追加（kabusys.tools.paper_verification_report）。
    - PAPER_TRADING_SQLITE_PATH（または --db） の SQLite DB から統計を抽出してレポートを出力（稼働率、注文成功率・送信率、リスク却下数、レイテンシ指標（avg/max/P95））。
    - 閾値判定（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）に基づく PASS/FAIL 判定。
    - P95 計算、日付フィルタ（ISO8601 UTC 変換）をサポート。
- パッケージメタデータ
  - パッケージ初期バージョンを設定（kabusys.__version__ = "0.1.0"）。

Changed
- （初回リリースのためなし）

Fixed
- .env パーサの堅牢性向上（export プレフィックス対応、クォート内のバックスラッシュエスケープ、インラインコメント処理など）。
- logging_setup: ログディレクトリ作成失敗時にファイルハンドラ作成をスキップし、代わりにコンソールへ警告を出す挙動を追加。

Deprecated
- （現時点なし）

Removed
- （現時点なし）

Security
- 必須機密情報（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は .env に保存する想定だが、.env を決してリポジトリにコミットしない旨を config_setup のヘッダで明示。

Migration Notes / 注意点
- 環境変数の必須項目:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須。validate_config で未設定はエラー。
- 起動時の環境自動ロード:
  - プロジェクトルートが特定できない場合は自動ロードをスキップするため、パッケージを配布後に使用する場合は明示的に環境変数を設定してください。
- ペーパートレード:
  - KABUSYS_ENV=paper_trading の場合、Execution は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用して本番 DB と完全に分離します。
  - PAPER_FILL_MODE の有効値は instant / partial / never / reject。無効値は ValueError。
- 監視（monitoring）:
  - run_monitoring は環境にかかわらず Settings.sqlite_path（デフォルト data/monitoring.db）を使用して監視 DB を初期化します。
  - MONITOR_POLL_INTERVAL を環境変数で指定可能（秒）。1 秒未満や不正な値はデフォルト 60 秒にフォールバック。
- ログ出力:
  - デフォルトで logs/<app_name>.log に日次ローテーションで保存。ログディレクトリ作成に失敗するとコンソールのみでの出力にフォールバックするため、運用環境でログ格納ディレクトリの書き込み権限を確認してください。
- プロセス優先度:
  - set_process_priority("high") を起動直後に呼ぶ設計。権限不足や未対応 OS の場合は警告が出て処理は継続されます。

補足
- config/*.yaml（system_config.yaml 等）の存在チェックとパース検証は validate_config が担当します（PyYAML がインストールされている場合は内容のパースまで検証します）。
- 実行エンジンと監視は stop flag ファイル（data/stop_requested.flag）と pid ファイルパスを用いてプロセス制御とシャットダウンを行います。

以上。追加のリリース（パッチや機能追加）を行う場合は、この形式に従ってバージョンと変更点を追記してください。必要であれば、さらに細かい変更点（関数単位の仕様や挙動のサンプル）を追記して更新します。