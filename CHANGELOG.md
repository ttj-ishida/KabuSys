CHANGELOG
=========

すべての注目すべき変更をこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠します。  
リリースはセマンティックバージョニングに従います。

[Unreleased]
-------------

(現在なし)

[0.1.0] - 2026-04-21
-------------------

Added
- 基本機能・CLI を多数追加（初期リリース）。
  - 起動スクリプト
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。  
      - 停止はプロジェクトの data/stop_requested.flag ファイルで検知。  
      - 監視は環境に関わらず本番用 sqlite_path を使用する設計。
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
      - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し本番 DB と分離。  
      - BrokerClientFactory を介したブローカークライアント生成、ExecutionEngine のスレッド起動／停止制御を実装。停止フラグや実行 PID ファイルの扱いをサポート。
  - 環境設定・検証
    - config_setup.py: 対話式ウィザードで .env を生成/更新する CLI を追加。シークレット項目のマスク表示や推奨値を提示。
    - validate_config.py: .env および config/*.yaml の起動前検証ツールを追加。--strict オプションで警告を FAIL 扱いにできる。
    - config.py: 環境変数読み込み・管理モジュールを実装。  
      - プロジェクトルート自動検出（.git / pyproject.toml 基準）により .env/.env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。  
      - 複数の設定プロパティを提供（J-Quants, kabuAPI, DB パス, PAPER_FILL_MODE など）とバリデーション。
  - ロギング・ユーティリティ
    - utils/logging_setup.py: ルートロガーへ StreamHandler（stdout）と日次ローテーションファイルハンドラを設定するユーティリティを追加。LOG_LEVEL / LOG_DIR の解決順やエラー時のフォールバック挙動を実装。
  - プロセス優先度ユーティリティ
    - utils/process_priority.py: Windows / POSIX の差分を吸収してプロセス優先度（nice / HIGH_PRIORITY_CLASS 等）と CPU affinity 設定関数を提供。アクセスが拒否されても警告を出して安全にフォールバック。
  - ポートフォリオ構築ライブラリ
    - portfolio/portfolio_builder.py: シグナル候補選択（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）を実装。
    - portfolio/risk_adjustment.py: セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）を実装。未知レジーム時のフォールバックとログ警告を実装。
    - portfolio/position_sizing.py: 発注株数計算（risk_based / equal / score）、単元株（lot_size）丸め、aggregate cap によるスケーリングと端数処理ロジックを実装。
    - portfolio/__init__.py: 上記関数を公開。
  - Paper Trading 検証ツール
    - tools/paper_verification_report.py: ペーパートレード用 SQLite を参照して稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）等の集計と PASS/FAIL 判定を行うレポート生成スクリプトを追加。PAPER_TRADING_SQLITE_PATH 環境変数や --db オプションで DB パスを指定可。
  - リサーチ（ファクター）基盤
    - research/factor_research.py: ファクター計算モジュールの骨格を追加（モメンタム・ボラティリティ等の設計方針と定数）。DuckDB 接続を受けて prices_daily などを参照する設計。
  - パッケージ情報
    - __init__.py にてバージョンを 0.1.0 として設定。

Changed
- 設計・挙動に関する明文化
  - run_monitoring の挙動として「監視は環境にかかわらず本番 sqlite_path を使用する」ことをコード上で明示（監視データは本番 DB に統合する運用前提）。
  - run_execution は paper_trading 環境のとき専用 DB に切り替え、発注系と監視系の DB 分離を担保。
  - logging_setup は stdout を使用する方針を採用（cron 等で stdout/stderr を一本化する運用を想定）。

Fixed
- 環境読み込みの堅牢化
  - config._parse_env_line にて quote 内のエスケープ処理や inline コメントの取り扱いを実装し、さまざまな .env フォーマットに耐えるようにした。
  - .env ロード時に OS 環境変数を保護するため protected set を導入し、.env.local を上書き可能とするロード順を明確化。

Security
- 現時点で重大なセキュリティ修正は無し。ただし以下の点に注意:
  - .env ファイルにシークレットを平文で保存するため、config_setup のコメントにもある通り .env を Git に含めないことを強く推奨。

Deprecated
- なし

Removed
- なし

Notes / Known issues
- research/factor_research.py の calc_momentum 実装はファイル末尾が途中で切れており（骨格・定数は定義済み）、完全実装が必要。今後のリリースで SQL/計算ロジックを追加予定。
- portfolio/risk_adjustment.apply_sector_cap 内に price=0.0 の場合のフォールバックが TODO コメントとして残っており、価格欠損時のエクスポージャー見積りに注意が必要。
- position_sizing では現状 lot_size を全銘柄共通の引数としている。将来的な拡張（銘柄別 lot_map）に関する TODO が記載されている。
- run_monitoring は監視 DB に本番 sqlite_path を使うため、ローカル開発時の監視データ分離が必要な場合は設定の調整または設計見直しが必要。

クレジット
- 初期実装: コアモジュール群（起動スクリプト、設定管理、ロギング・プロセスユーティリティ、ポートフォリオ構築、検証ツール、ペーパートレード検証レポート等）

今後の予定
- research/factor_research の完全実装（DuckDB SQL クエリ + 正規化ユーティリティとの連携）
- strategy/engine 周りの更なるテスト強化と障害時のリカバリ改善
- 単体テスト・統合テストの整備、CI ワークフロー導入

---