CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------

（なし）

0.1.0 - 2026-04-24
------------------

Added
- 初回リリースを追加。
- 設定管理と自動読み込み
  - Settings クラスにより環境変数を集中管理。J-Quants / kabuステーション / LINE / DB /監視等の設定をプロパティで提供。
  - プロジェクトルート自動検出（.git / pyproject.toml 基準）により .env をカレントディレクトリに依存せず読み込み。
  - .env 自動読み込み機能を実装（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
  - .env パーサを強化（export プレフィックス対応、シングル/ダブルクォート内でのバックスラッシュエスケープ、インラインコメント処理など）。
- 環境セットアップ / 検証用 CLI
  - config_setup.py: 対話式ウィザードで .env を作成・更新するツールを追加。主要な設定項目（KABUSYS_ENV / JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / DB パス / LOG_LEVEL 等）に対応。
  - validate_config.py: 起動前チェックを実装。必須環境変数、KABUSYS_ENV 値、ログレベル、DB パス、config/*.yaml の存在とパース（PyYAML がある場合）を確認。--strict オプションで警告を FAIL 扱いに可能。
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading のときは paper_trading 用の専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカー抽象化、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine の起動を実装。
    - 停止フラグ（data/stop_requested.flag）検知で安全にシャットダウン。
    - 実行時 PID ファイル (data/execution.pid) の取り扱い。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグによるループ終了、check_once() の例外を捕捉して継続する堅牢化。
- ロギング関連ユーティリティ
  - utils/logging_setup.py: 共通のログ初期化関数 setup_logging を実装。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を設定。
    - ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソールログのみで継続。
    - 既存ハンドラをクリアして二重登録を防止。
- プロセス優先度 / CPU 固定ユーティリティ
  - utils/process_priority.py: set_process_priority と set_cpu_affinity を実装。
    - Windows / POSIX（Linux, Darwin, FreeBSD）間の差分を吸収。
    - 権限や未対応環境時は警告を出し安全にスキップ。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - BUY シグナルの候補選定（スコア降順、タイブレークに signal_rank）と等重・スコア重み付けの実装。スコアが全て 0 の場合は等金額配分にフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。unknown セクターは上限適用除外、未知レジームはフォールバックで 1.0。
    - セクター露出計算時の価格欠損に関する注意点（将来的なフォールバックの TODO）。
  - portfolio/position_sizing.py
    - allocation_method に応じた株数算出（risk_based / equal / score）を実装。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap（利用可能現金に応じたスケーリング）、コストバッファ考慮、残差配分ロジックを含む。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード DB を解析してレポートを出力する CLI を追加。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、レイテンシ（avg / max / P95）などを集計。
    - 閾値を定義（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 <= 200 ms）して PASS/FAIL 判定を行う。
    - --from/--to/--db オプションをサポート。
- 研究モジュールの追加（部分実装）
  - research/factor_research.py: DuckDB 接続を前提としたファクター計算モジュール（モメンタム / MA200 / ATR / 流動性など）を開始。設計方針と計算範囲バッファの定義を含む。calc_momentum 関数等、時系列ファクター計算のための基盤を追加。
- パッケージメタ情報
  - __version__ = "0.1.0" を追加。

Changed
- なし（初回公開）

Fixed
- なし（初回公開）

Deprecated
- なし

Removed
- なし

Security
- .env ファイルに関する注意書き（config_setup が生成する .env は絶対に Git にコミットしないこと）をドキュメント内に明記。

Notes / Known issues / TODO
- portfolio/risk_adjustment.py にて価格が欠損（0.0）の場合の露出過小見積りについて TODO コメントあり。将来的に前日終値や取得原価をフォールバックすることを検討予定。
- research/factor_research.py はファイル末尾が途中で切れている（calc_momentum 実装が続く想定）。研究モジュールは開発中のため、完全なテスト・検証が必要。
- logging_setup はログディレクトリ作成に失敗した場合ファイル出力を行わない設計だが、運用環境では確実に logs ディレクトリを作成することを推奨。
- process_priority の一部機能はプラットフォームや権限に依存するため、運用環境での動作確認を推奨。

ライセンスや貢献方法などその他のメタ情報はプロジェクトの README を参照してください。