# Changelog

すべての変更点は Keep a Changelog の形式に従って記載しています。  
リリース日付は 2026-04-21（コード上の参照日付に合わせています）。

全般的な注意:
- この CHANGELOG は与えられたコードベースの内容から推測して作成しています。
- 初回リリース相当として v0.1.0 に機能群をまとめています。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-21

### Added
- 基本アプリケーションパッケージ `kabusys` を追加。
  - バージョン: `__version__ = "0.1.0"`

- 起動スクリプト / デーモン用エントリを追加
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は常に本番用の sqlite_path を使用（KABUSYS_ENV に依存しない）。
    - 停止はプロジェクト内 `data/stop_requested.flag` を配置することで行う。
    - 起動時にプロセス優先度を "high" に設定してから動作を開始。
  - run_execution.py
    - ExecutionEngine を起動するスクリプト。
    - `KABUSYS_ENV=paper_trading` の場合、専用の MockBrokerClient を使用し、Paper Trading 用 DB（data/paper_trading.db）に記録して本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグおよび PID ファイル管理を含む（data/execution.pid, stop_requested.flag）。
    - ExecutionEngine を別スレッドで実行し、停止フラグを検知したら安全に停止を試みる。

- 設定管理・ロード機能
  - config.py
    - プロジェクトルートを .git / pyproject.toml から自動検出するロジックを追加（CWD に依存しない）。
    - `.env` / `.env.local` の自動ロード機能を実装（OS 環境変数を保護して上書き制御）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` で自動ロードを無効化可能（テスト等で利用）。
    - .env の行パーサが `export KEY=...`、シングル/ダブルクォート内のバックスラッシュエスケープ、行末コメント処理などに対応。
    - `Settings` クラスを追加し、環境変数から各種設定値を読み出すプロパティ群を提供（DB パス、API トークン、Paper Trading 設定、監視しきい値、ログレベルなど）。
    - `Settings` は値の妥当性チェックを行い、無効な値は ValueError を送出。

- 設定の確認・初期化ツール
  - validate_config.py
    - .env と config/*.yaml の設定検証 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェックを実施。
    - PyYAML が存在する場合は config/*.yaml のパース検証を実行。存在しない場合は YAML 検証をスキップして警告を出す。
    - `--strict` オプションで警告も失敗扱いにできる。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成／更新する CLI を追加。
    - シークレット項目のマスク表示、選択肢、デフォルト値、保存確認を実装。
    - `.env` を安全に書き出すロジックを提供（例: .env を絶対にコミットしないことを注意書き）。

- ログ / プロセスユーティリティ
  - utils/logging_setup.py
    - 全起動スクリプトから利用可能な統一ロギング設定ユーティリティを追加。
    - stdout への StreamHandler と、日次ローテーション（TimedRotatingFileHandler）でファイル出力（デフォルト logs/）を設定。ファイル出力はディレクトリ作成失敗時に自動で無効化される。
    - ログレベルとログディレクトリの解決順を明確化。既存ハンドラをクリアして二重設定を防止。
  - utils/process_priority.py
    - プラットフォーム差分を吸収するプロセス優先度設定ユーティリティを追加（psutil ベース）。
    - Windows / POSIX（Linux, macOS, FreeBSD）向けの優先度調整をサポート。
    - CPU affinity を最初の N コアに固定する関数も提供（set_cpu_affinity）。
    - 権限不足や未サポート環境では安全にログ警告を出してスキップ。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - BUY シグナルから候補選定（score 降順、signal_rank を破棄解決）を行う select_candidates。
    - 等配分 calc_equal_weights、スコア加重 calc_score_weights（全スコア 0 の場合は等配分にフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限を適用して、上限超過セクターの銘柄を候補から除外するロジックを実装。売却予定銘柄を除外して既存エクスポージャーを計算可能。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数を返す（bull=1.0, neutral=0.7, bear=0.3）。未知のレジームは 1.0 にフォールバック。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数を算出する calc_position_sizes を実装。
    - allocation_method による振る舞い:
      - "risk_based": 許容リスク率（risk_pct）とストップロス率（stop_loss_pct）に基づくサイズ計算。
      - "equal"/"score": 重み（weights）に基づく配分。
    - 1 銘柄上限、lot_size（単元株）で丸め、コストバッファ(cost_buffer) を考慮した保守的見積り、aggregate cap による縮小、端数の lot 単位での再配分（fractional 残差を使った公平な配分）を実装。
    - 価格欠損や 0 の場合はログを出して銘柄をスキップ。

- 解析 / リサーチ関連
  - research/factor_research.py（ファクター計算モジュール）
    - DuckDB 接続を受け、prices_daily / raw_financials を参照して定量ファクター（Momentum, Value, Volatility, Liquidity 等）を計算する設計を追加。
    - モメンタム計算（mom_1m, mom_3m, mom_6m, MA200 乖離）を想定する API を実装（関数の冒頭ロジックを含む）。（ファイルは部分的に含まれる）

- ツール
  - tools/paper_verification_report.py
    - Paper Trading（ペーパートレード）用の検証レポート生成スクリプトを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ 等を計算して表示。
    - デフォルト DB は data/paper_trading.db。コマンドラインで期間指定 --from / --to および --db で DB パス上書き可能。
    - 判定基準（しきい値）を定義し、PASS/FAIL を出力する（稼働率 >= 99%、fill >= 90% など）。
    - P95 の独自計算、latency 平均/最大も出力。

- 監視 DB 初期化ユーティリティ参照
  - 各起動脚本で監視用テーブルが存在することを保証するため init_monitoring_db を呼び出す設計（冪等に動作）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数・シークレットの取り扱いに関する注意を `.env` 生成テンプレートおよび対話ウィザード内に明記（.env を Git にコミットしないこと等）。

---

注記:
- この CHANGELOG は提供されたソースコードから推測してまとめたものであり、実際の変更履歴（コミット履歴）とは一致しない場合があります。必要であれば、実際の Git 履歴やリリースノートに合わせて調整してください。