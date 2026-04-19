# CHANGELOG

このファイルは Keep a Changelog の形式に準拠して記述しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

全ての変更は semver に従います。

## [0.1.0] - 2026-04-19

### 追加
- 基本アプリケーション骨格を実装
  - パッケージ初期化とバージョン情報を追加（src/kabusys/__init__.py: __version__ = "0.1.0"）。
- 実行用スクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時はペーパートレード用の SQLite（data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の起動ロジックを組み立て。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止、実行 PID ファイル（data/execution.pid）の取り扱い。
  - 監視（モニタリング）ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する仕様。
    - 停止フラグ検知によるループ終了、例外ハンドリングと接続クリーンアップを実装。
- 設定管理
  - Settings クラスを追加（src/kabusys/config.py）。
    - .env 自動ロード機能（.env / .env.local、OS 環境変数保護、無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD）。
    - .env パースロジック（export 形式、クォート文字列、インラインコメントの取り扱い）を備えた実装。
    - 各種環境変数プロパティ（J-Quants / kabu API / DB パス / Paper Trading 設定 / 監視閾値 / 実行環境等）と妥当性チェックを提供。
  - 対話式 .env 作成ウィザードを追加（src/kabusys/config_setup.py）。
    - CLI で .env を生成・更新できるウィザード。既存 .env の読み込み・編集、秘密項目のマスク表示、保存確認を実装。
- 設定検証ツール
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、config/*.yaml の存在および PyYAML によるパース検証（PyYAML が無い場合はスキップ）を実施。
    - --strict オプションで警告を失敗扱いにできる。
- ロギング / プロセス制御ユーティリティ
  - 統一ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout への StreamHandler と、日次ローテーション（30日保持）のファイルハンドラをルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップ。
    - LOG_LEVEL / LOG_DIR / 引数からの解決ロジックを提供。
  - プロセス優先度・CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX（Linux, macOS 等）差分を吸収して優先度（high/normal/low）を設定。CPU affinity 固定機能も提供。権限不足時は警告ログでフェイルソフトに動作。
- ポートフォリオ構築関連（純粋関数群）
  - 候補選定・重み付け（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates、calc_equal_weights、calc_score_weights を実装。スコアが全て 0 の場合のフォールバックを含む。
  - セクター制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（セクター集中上限による候補除外）、calc_regime_multiplier（market regime に応じた資金乗数）を実装。未知のレジームはフォールバックで扱う。
  - ポジションサイジング（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes を実装。allocation_method（risk_based / equal / score）に対応し、単元株（lot_size）丸め、per-stock 上限や aggregate cap、cost_buffer を考慮したスケーリングを行う。
  - パッケージエクスポート（src/kabusys/portfolio/__init__.py）
    - 主要関数をまとめて公開。
- 解析 / ツール
  - Paper Trading 検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）。
    - SQLite（PAPER_TRADING_SQLITE_PATH 指定可）からシステム安定性、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）等を集計しレポート出力。
    - Pass/Fail 判定の閾値（稼働率、成功率、送信率、P95 レイテンシ等）を定義。
- 研究用モジュール（ファクター計算）
  - 基本構成を追加（src/kabusys/research/factor_research.py）。
    - DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity 系の定量ファクターを計算する設計を実装（モジュール内定数や calc_momentum の雛形を含む）。DuckDB の prices_daily / raw_financials を利用する方針。

### 変更
- （初回リリースのため変更履歴はありません）

### 修正
- （初回リリースのため修正履歴はありません）

### 注意事項 / 補足
- .env 自動読み込みはデフォルトで有効。テストや特殊環境で無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring と run_execution はログ設定・プロセス優先度設定等の初期化処理を行います。サービス化・監視下での運用時はログディレクトリの権限や PID ファイルの取り扱いに注意してください。
- Paper Trading と本番 DB は明確に分離される設計です（paper_trading モード時は paper_sqlite_path を使用）。
- 一部モジュール内に TODO コメントや将来的な拡張に関する注記があります（例: position_sizing の銘柄別 lot_size 化や risk_adjustment の価格フォールバック等）。
- config/*.yaml の雛形は codebase に含まれない可能性があります。validate_config で不足が警告されます。scripts/generate_config.py 等での生成を想定しています。

（初回公開: 0.1.0）