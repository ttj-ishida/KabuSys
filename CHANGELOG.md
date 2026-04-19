# CHANGELOG

すべての変更は Keep a Changelog の慣習に従い記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

なお、以下は現在のコードベースから推測して作成した初回リリース向けの変更履歴です（実際のコミット履歴をそのまま反映したものではありません）。

## [Unreleased]

- 小さな改善や内部リファクタが今後追加される予定。

---

## [0.1.0] - 2026-04-19

初回公開リリース。日本株自動売買システム「KabuSys」の基礎機能群を実装。

### Added
- 全体
  - パッケージバージョンを設定: `__version__ = "0.1.0"`。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を手がかりに自動検出）。
  - .env 自動読み込み機能を実装（`.env` / `.env.local` をプロジェクトルートから読み込み、OS環境変数は保護）。
  - 環境変数のパース機能を強化（シングル/ダブルクォート、エスケープ、インラインコメントの取り扱いを考慮）。

- 設定関連
  - Settings クラスを実装し、環境変数からアプリ設定を集約:
    - J-Quants / kabuステーション / LINE API / DB パス / 監視閾値等のプロパティを提供。
    - `KABUSYS_ENV` / `LOG_LEVEL` のバリデーション。
    - `paper_fill_mode`（PAPER_FILL_MODE）の有効値チェック。
    - paper_trading 用の別 SQLite パス (`PAPER_TRADING_SQLITE_PATH`) サポート。
  - 設定ウィザード CLI を追加（`kabusys.config_setup`）:
    - 対話式に `.env` を作成・更新するウィザードを提供。
    - シークレット項目は表示をマスクして扱う。
  - 設定検証 CLI を追加（`kabusys.validate_config`）:
    - 必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在や YAML パース（PyYAML がある場合）を検証。
    - `--strict` オプションで警告を失敗扱いにできる。

- 実行/監視関連
  - 実行エントリポイント: `run_execution.py`
    - `ExecutionEngine` 起動スクリプトを提供。
    - `KABUSYS_ENV=paper_trading` 時は MockBroker を使用し、paper_trading 用 DB（data/paper_trading.db）に記録して本番 DB とは完全分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ（data/stop_requested.flag）および PID 管理をサポート。
    - 監視テーブルの初期化を行い冪等に保証。
  - 監視エントリポイント: `run_monitoring.py`
    - `SystemMonitor` のポーリングループを実行。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番用 `sqlite_path` を使用する設計（監視データは本番 DB を想定）。

- ロギング / プロセス制御ユーティリティ
  - `kabusys.utils.logging_setup`:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定する共通セットアップを実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
    - ログレベルとログディレクトリの解決順をドキュメント化。
  - `kabusys.utils.process_priority`:
    - Windows / POSIX（Linux, macOS 等）差分を吸収してプロセス優先度（high/normal/low）を設定。
    - CPU affinity を最初の N コアに固定する `set_cpu_affinity` を実装（アクセス権限や非対応 OS は警告でスキップ）。
    - 権限不足や未対応機能に対する安全なフォールバックとログ出力を実装。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`:
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - スコア全てが 0 の場合のフォールバック（等配）と警告ロギング。
  - `kabusys.portfolio.risk_adjustment`:
    - セクター集中制限（apply_sector_cap）を実装（売却予定銘柄の除外、unknown セクターは上限適用除外）。
    - 市場レジームに基づく投下資金乗数（calc_regime_multiplier）を実装（bull/neutral/bear とフォールバック）。
  - `kabusys.portfolio.position_sizing`:
    - `calc_position_sizes` を実装。allocation_method により:
      - risk_based（リスクベース）、equal、score に対応。
      - 単元株（lot_size）丸め、1 銘柄上限、全体投下資金上限（aggregate cap）を実装。
      - cost_buffer を考慮した保守的見積り、スケーリングと残差処理（lot 単位で追加配分）を実装。

- リサーチ / ファクター計算
  - `kabusys.research.factor_research` を追加（モメンタム / Value / Volatility / Liquidity 等を DuckDB の prices_daily/raw_financials から計算する設計）。
    - モジュールは DuckDB 接続を受け、(date, code) をキーとする結果を返す設計方針を採用。
    - （注）ファイル末尾に未完の実装痕跡があるため、今後の実装拡張が想定される。

- ツール
  - `kabusys.tools.paper_verification_report`:
    - Paper Trading 用の検証レポート生成スクリプトを提供。
    - 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計して PASS/FAIL 判定を出力。
    - デフォルト DB パスは `data/paper_trading.db`、期間フィルタは `--from` / `--to` オプションで指定可能。
    - 判定閾値（稼働率 99%、成功率 90% 等）を定義。

- データベース初期化
  - 監視目的の DB 初期化関数 `init_monitoring_db`（monitoring モジュール）を起動経路で呼び出し、監視テーブルの存在を保証（冪等）。

### Changed
- なし（初回公開）

### Fixed
- なし（初回公開）

### Notes / Implementation details
- `.env` の自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定することで無効化可能（テスト用途を想定）。
- ログ出力は stdout を使用することで、cron や Task Scheduler などからの起動時にリダイレクトしやすいよう配慮。
- process priority / CPU affinity は権限がない環境や未対応 OS で安全にスキップするように設計。
- Paper Trading と Live の DB 分離、監視データの扱いについては設計上の意図が明記されている（監視は本番 sqlite を参照）。

---

今後の予定（例）
- factor_research の完全実装とテスト追加
- ExecutionEngine / SystemMonitor の詳細実装とエンドツーエンドテスト
- 単体テスト・CI ワークフローの追加
- ドキュメント（設計文書・運用手順）の整備

-----
（この CHANGELOG は現状のコードからの推測に基づいて作成しています。実際のコミット履歴やリリースノートとして使用する場合は各コミット情報を合わせて確認してください。）