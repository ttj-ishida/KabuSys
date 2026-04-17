Keep a Changelog
=================

すべての重要な変更をここに記録します。  
フォーマットは Keep a Changelog に準拠します。

Unreleased
---------

- （現在変更なし）

0.1.0 - 2026-04-17
-----------------

Added
- 初期リリース: KabuSys 基本機能群を実装
  - 実行用スクリプト
    - run_execution.py
      - ExecutionEngine を起動・管理するエントリポイントを追加。KABUSYS_ENV に応じて本番 DB / ペーパートレード用 DB を切り替え（paper_trading 時は専用 MockBroker + data/paper_trading.db を使用）。
      - 起動時にプロセス優先度を "high" に設定。停止フラグ (data/stop_requested.flag) を検知して安全に停止。
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は環境にかかわらず本番 sqlite_path を使用し、監視 DB の初期化を保証。
  - 設定・検証
    - config.py
      - .env 自動読み込み機能（プロジェクトルート検出: .git / pyproject.toml）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
      - 強力な Settings クラスを実装。環境変数のデフォルト／妥当性検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を提供。
      - データベースパスや PID ファイル等のパスプロパティを提供。
    - config_setup.py
      - 対話式ウィザードで .env の初期作成・更新を支援。シークレットはマスク表示し、保存前に内容確認を行う。出力される .env は Git にコミットしない旨の注記を含む。
    - validate_config.py
      - 起動前検証 CLI を追加。必須環境変数、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在および（PyYAML がインストールされている場合）パース検証を行う。
      - --strict モードで警告を FAIL 扱いにできる。
  - ポートフォリオ構築ライブラリ（純粋関数群）
    - portfolio/portfolio_builder.py
      - シグナル選定（スコア降順、タイブレーク処理）と等重・スコア加重の重み計算を実装。スコアが全て 0 の場合は等金額配分にフォールバック（警告を出力）。
    - portfolio/risk_adjustment.py
      - セクター集中上限チェック（既存ポジションのセクター別時価算出、上限超過セクターの新規候補除外）、および市場レジームに応じた投下資金乗数の算出を実装（bull/neutral/bear をサポート、未知のレジームはフォールバック）。
    - portfolio/position_sizing.py
      - weight／candidates／現金等に基づく株数決定ロジックを実装。risk_based / equal / score の配分方式をサポート。
      - 単元株（lot_size）で丸め、最大ポジション比率・利用可能現金による aggregate cap を考慮。コストバッファ（手数料・スリッページ）を加味した保守的見積りとスケールダウンロジックを含む。
  - 解析・リサーチ
    - research/factor_research.py
      - DuckDB 接続を受け取り、prices_daily/raw_financials テーブルからモメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR）、流動性指標等を計算する関数を実装。ウィンドウ不足時の None ハンドリングや SQL ウィンドウ関数を利用した実装。
  - ユーティリティ
    - utils/process_priority.py
      - Windows / POSIX の差分を吸収するプロセス優先度設定ユーティリティを実装。set_process_priority(level) と set_cpu_affinity(cpu_count) を提供し、権限不足や未対応 OS の場合は警告を出力してフォールバック。
  - ツール
    - tools/paper_verification_report.py
      - ペーパートレード用 SQLite データを集計して検証レポートを生成する CLI を追加。
      - 稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）を算出し、しきい値に基づく PASS/FAIL 判定を出力。
      - DB が存在しない、またはテーブルが不足している場合に対する待機的ハンドリング（OperationalError を捕捉して N/A 等で報告）。
  - パッケージ定義
    - __init__.py にバージョン 0.1.0 を設定。

Changed
- n/a（初回リリースのため既存振る舞いの変更なし）

Fixed
- n/a（初回リリース）

Notes / Implementation details
- .env パーサーは export プレフィックス、クォート／エスケープ、インラインコメント処理に対応。既存の OS 環境変数は保護され（protected）、override フラグで書き込み挙動を制御。
- MONITOR_POLL_INTERVAL は不正値（0 以下や非整数）の場合にデフォルト（60 秒）にフォールバックし、警告を出力。
- ペーパートレードと本番 DB は明確に分離され、paper_trading 環境では PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用。
- position_sizing のスケーリングロジックは lot_size 単位での端数配分を考慮し、残余キャッシュで残差が大きい銘柄順に追加配分することで再現性を確保。
- research モジュールは DuckDB に依存し、prices_daily 等が存在しない場合は早期に None / N/A を返す設計で安全性を優先。

Breaking Changes
- なし（初回リリース）

Security
- なし特記事項

Contributing
- 今後の変更はこの CHANGELOG に記録してください。