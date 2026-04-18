CHANGELOG
=========

すべての変更は「Keep a Changelog」形式に準拠して記載しています。  
フォーマットと慣習について: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（このワークツリーに対する保留中の変更はありません。現状のスナップショットを 0.1.0 として記録しています。）

[0.1.0] - 2026-04-18
-------------------

初回リリース。本リリースでは自動売買システム "KabuSys" のコアユーティリティ群・実行スクリプト・ポートフォリオ構成ロジック・検証ツール類を実装しています。

Added
- 全体
  - パッケージ初期化とバージョン定義を追加（kabusys.__version__ = "0.1.0"）。
- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - プロセス優先度を "high" に設定して起動。
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler を組み立ててエンジンをデーモンスレッドで稼働。
    - 停止フラグ（data/stop_requested.flag）および PID ファイル（data/execution.pid）による制御。
  - run_monitoring.py: SystemMonitor 用のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用（監視データの分離方針）。
    - 停止フラグ検知で安全にループを終了。
- 設定管理・CLI
  - config.py: 環境変数/ .env 読み込み・Settings クラスを実装。
    - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env 自動ロード（.env.local が優先）。
    - .env パースロジックは export 形式、シングル/ダブルクォート、エスケープ、インラインコメントを考慮。
    - 各種設定プロパティ（DB パス、PAPER_FILL_MODE、監視閾値、KABUSYS_ENV 判定、ログレベルなど）を提供。
  - config_setup.py: .env を対話式に作成/更新するウィザードを実装。
    - シークレット入力サポート、選択肢・デフォルト表示、既存 .env の読み込み・再利用、最終確認と保存機能。
    - .env 保存時にコミット禁止の注意コメントを追加。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス親ディレクトリ存在チェック、config/*.yaml の存在・パース（PyYAML がインストールされている場合）。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定の確認、KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict オプションで警告も失敗扱いにできる。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: ルートロガーの統一設定ユーティリティを実装。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を用いたファイル出力（既定 logs/<app_name>.log）。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続するフォールバック処理。
    - 環境変数 LOG_LEVEL / LOG_DIR による挙動調整。
  - utils/process_priority.py: プロセス優先度と CPU affinity の設定ユーティリティを実装。
    - Windows と POSIX（Linux, macOS 等）差異を吸収して set_process_priority("high"|"normal"|"low") を提供。
    - set_cpu_affinity によるコアピニング（指定が None の場合は変更しない）。
    - psutil による権限不足等を安全に扱う警告ハンドリングを実装。
- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順ソート（同点時は signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装。スコア合計が 0 の場合は等分配にフォールバック。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限（最大セクター比率）を適用して候補を除外するロジック。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知値は警告して 1.0 フォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に応じた発注株数計算を実装。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap（available_cash）に伴うスケールダウン、cost_buffer を考慮した保守的コスト見積り、残差分の公平な配分ロジックを実装。
- 監視・検証ツール
  - monitoring/monitoring_db.py (参照される初期化関数を使用して監視テーブルを準備) — スクリプトから冪等に呼び出し。
  - tools/paper_verification_report.py: ペーパートレーディング検証レポートの生成スクリプトを追加。
    - DB（PAPER_TRADING_SQLITE_PATH または引数 --db）から system_status / trade_logs / risk_logs を集計。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、平均/最大/P95 レイテンシ等を算出。
    - PASS/FAIL 判定基準（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 <= 200ms）を実装。
- リサーチ
  - research/factor_research.py: ファクター計算モジュール開始（モメンタム・MA200乖離・ATR・流動性等を計算する方針を実装）。DuckDB 接続を受けて prices_daily を参照する設計。関数シグネチャと定数を定義（実装の続きあり）。

Changed
- n/a（初回リリースのため「追加」が中心）。ただし各ユーティリティは堅牢性向上のため例外処理やフォールバック動作を含む。

Fixed
- n/a（初回リリース）

Security
- .env の取り扱いに関する注意を config_setup.py の出力で明記（.env を Git にコミットしないよう警告）。
- config.py の _require() は未設定時に ValueError を投げ、起動前に設定不足を明確化。

Notes / Implementation details
- .env 自動読み込みはデフォルトで有効。OS 環境変数が優先され、.env.local（存在する場合）で上書きされる。
- Paper Trading モードは実運用 DB とデータを分離する設計（settings.paper_sqlite_path を使用）。
- ログは stdout とファイルの二重出力だが、ログディレクトリ作成に失敗した際は安全にファイル出力を無効化してコンソールのみで継続する。
- プロセス優先度設定や CPU affinity は権限不足や未対応プラットフォームを検出して警告し、起動失敗とならないよう設計されている。
- position_sizing の aggregate cap スケーリングは lot_size（単元株）単位の丸めと残余キャッシュを活用した再配分ロジックを持ち、再現性のため安定ソートを使用。

今後の作業候補（提案）
- research/factor_research.py のモメンタム計算など実装完了。
- 単体テストの追加（.env パーサ、position_sizing のスケールダウンロジック、paper_verification_report の集計ロジック等）。
- 戦略・実行コンポーネントのモックを用いた統合テスト（paper_trading モードの検証）。
- 銘柄別 lot_size の対応（stocks マスタの導入）や手数料・スリッページモデルの拡張。

--- End of CHANGELOG ---