CHANGELOG
=========
（このファイルは Keep a Changelog の形式に準拠しています）
https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
（なし）

[0.1.0] - 2026-04-19
-------------------

Added
- 初回リリース。KabuSys の基本機能群を追加。
  - 実行用スクリプト
    - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。  
      - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用して paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）に記録することで本番 DB と分離。
      - 停止フラグ（data/stop_requested.flag）検出による安全停止、実行 PID ファイル管理の実装。
  - 監視用スクリプト
    - run_monitoring.py: SystemMonitor のポーリングループを起動するエントリポイントを追加。  
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
      - 監視は環境にかかわらず本番用 sqlite_path を使用するよう設計。
  - 設定管理・ユーティリティ
    - config.py: 環境変数・設定管理クラス（Settings）を実装。.env 自動読み込み機能を備える。
      - .git または pyproject.toml を探索してプロジェクトルートを決定する実装により、CWD に依存しない自動ロードを実現。
      - .env のパースではクォート（シングル/ダブル）やエスケープ、インラインコメントに対応。
      - 各種設定プロパティ（DB パス、ログレベル、paper_trading 周りの設定、監視しきい値など）を提供。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - config_setup.py: 対話式 .env 作成/更新ウィザードを実装。必須/任意項目、シークレット入力、デフォルト値をサポート。
    - validate_config.py: 起動前設定検証 CLI を実装。必須環境変数や config/*.yaml の存在・パース検証、KABUSYS_ENV のチェックや本番環境に対する注意喚起を行う。--strict オプションで警告を FAIL 扱いにできる。
  - ロギング / プロセス制御ユーティリティ
    - utils/logging_setup.py: ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（ログの毎日ローテーション、既定 30 日保持）を設定するユーティリティを追加。LOG_DIR/LOG_LEVEL の環境変数と引数で上書き可能。既存ハンドラの二重登録を防ぐため再初期化時にクリアする。
    - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX）でプロセス優先度（high/normal/low）を設定する関数を追加。CPU affinity 設定用の set_cpu_affinity も提供。
  - ポートフォリオ構築モジュール（純粋関数群）
    - portfolio/portfolio_builder.py: 候補選定（スコア降順・タイブレーク）、等金額/スコア重みの計算を実装。
    - portfolio/risk_adjustment.py: セクター集中制限の適用（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。
    - portfolio/position_sizing.py: 発注株数決定ロジック（risk_based / equal / score）を実装。単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金に合わせたスケーリング）を実装。cost_buffer を考慮した保守的なコスト見積り、端数配分ロジックも含む。
    - portfolio/__init__.py で API をエクスポート。
  - Paper Trading 検証ツール
    - tools/paper_verification_report.py: ペーパートレードの検証レポート生成スクリプトを実装。指定期間の system_status / trade_logs / risk_logs を集計し、稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などを出力。閾値（稼働率 99%、成功率 90% 等）との比較による PASS/FAIL 判定を行う。コマンドライン引数で期間・DB パスを指定可能。
  - 研究用モジュール（開始実装）
    - research/factor_research.py: DuckDB を用いたファクター計算モジュールを追加（モメンタム、MA200、ATR、出来高等の計算方針と定数を定義。calc_momentum の実装開始）。
  - パッケージメタ情報
    - __init__.py にバージョン __version__ = "0.1.0" を設定。

Changed
- ロギング初期化ロジックの挙動を明確化:
  - 既にハンドラが設定されている場合は一旦 flush/close してから差し替えることで多重ログ出力を防止。
  - stdout を StreamHandler に使うことでスケジューラ／cron でのリダイレクト運用を想定。
- .env 読み込みの優先度と保護:
  - OS 環境変数を保護する protected 機構を導入し、.env.local の上書きを行うが OS 環境変数は上書きしない設計。

Fixed
- 設定値の堅牢化・フォールバック動作を追加:
  - MONITOR_POLL_INTERVAL が不正（非整数または <=0）な場合、警告を出してデフォルト (60 秒) にフォールバック。
  - logging_setup でログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソール出力のみで継続するように変更（起動失敗を回避）。
  - process_priority のプラットフォーム差異と権限問題（AccessDenied 等）を捕捉し、失敗しても警告を出して継続するようにした。
  - Paper verification レポートや各種クエリで SQLite のテーブルが存在しない場合（OperationalError）に耐えるフォールバックを実装。
  - .env パーサーでのクォート内部のバックスラッシュエスケープやコメント扱いの挙動を改善し、より現実的な .env の記述に耐性を持たせた。

Notes / Known limitations
- research/factor_research.py はファクター計算の骨組みを実装していますが、calc_momentum 等の詳細な実装は途中（ファイル末尾が切れている状態）です。今後のリリースで追加実装・テストを行う予定です。
- monitoring 側は設計上「監視は本番用 sqlite_path を使用する」仕様です（意図的に環境分離しない）。運用時は監視 DB の保存先にご注意ください。
- position_sizing の lot_size は現状で全銘柄共通の単元数（デフォルト 100）を前提としています。将来的には銘柄別単元サポートを予定。
- 一部の機能は外部モジュール（psutil、duckdb、PyYAML 等）に依存します。実行環境にこれらがない場合、一部機能が制限されるか警告が発生します。
- .env 自動ロードはデフォルトで有効。テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

Acknowledgments
- 初期設計は自動売買システムの運用・検証に必要なコンポーネント（実行エンジン、監視、設定ツール、検証レポート、ポートフォリオ構築ロジック）を優先して実装しています。今後のリリースで戦略本体・ブローカークライアント等の詳細実装とテスト、ドキュメント整備を進めます。