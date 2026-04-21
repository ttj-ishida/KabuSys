CHANGELOG
=========

すべての変更は Keep a Changelog の規約に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
---------
（今後のリリース予定の変更点）


0.1.0 - 2026-04-21
-----------------
初回リリース。本リポジトリに含まれる主要な機能群とユーティリティを公開。

Added
- 基本パッケージ情報
  - パッケージのバージョンを `__version__ = "0.1.0"` として追加 (src/kabusys/__init__.py)。

- 起動スクリプト
  - 実行エンジン起動スクリプト `run_execution.py` を追加。ExecutionEngine を起動し、スレッドでセッション実行、停止フラグ検知および PID 管理を行う。
    - Paper Trading モードでは本番 DB と分離して `data/paper_trading.db`（環境変数で上書き可）を使用し、MockBroker を利用する想定。
    - 起動時にプロセス優先度を "high" に設定する処理を追加。
  - 監視用ループ起動スクリプト `run_monitoring.py` を追加。SystemMonitor を初期化してポーリングループを実行。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ検知によりループを安全に終了する仕組みを実装。
    - 監視実行時は環境にかかわらず本番用の sqlite_path を使用する旨の挙動を実装。

- 設定管理とウィザード/検証
  - 環境変数および .env 自動読み込みを行う `config.py` を追加。
    - プロジェクトルートの検出（.git または pyproject.toml 基準）を行い、.env / .env.local を自動で読み込む（無効化可）。
    - .env 行パーサはクォート、エスケープ、コメントの取り扱いに対応。
    - 環境変数の必須チェック・各種設定プロパティ（DB パス、KABUSYS_ENV、PAPER_FILL_MODE 等）を提供。
  - 対話式設定ウィザード `config_setup.py` を追加。
    - .env の初期作成・更新を支援。シークレット項目はマスク表示、既存値の再利用、保存前の確認を実装。
  - 設定検証 CLI `validate_config.py` を追加。
    - 必須環境変数、KABUSYS_ENV の妥当性、ログレベル、DB パス、config/*.yaml の存在・パース（PyYAML がインストールされている場合）等をチェック。
    - --strict モードで警告を失敗扱いにできる。

- Paper Trading 検証ツール
  - `tools/paper_verification_report.py` を追加。Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から集計を行い、稼働率、注文成功率、送信率、レイテンシ等の指標を出力して PASS/FAIL 判定する。
    - P95 レイテンシ計算、日付フィルタ（--from/--to）に対応。
    - しきい値はファイル内定数で定義（稼働率 99%、注文成功率 90% 等）。

- ポートフォリオ構成モジュール
  - 銘柄選定/重み計算: `portfolio/portfolio_builder.py`
    - BUY シグナルから候補選定（スコア降順）および等金額／スコア加重の重み計算を実装。
    - スコアが全て 0 の場合は警告を出し等金額配分にフォールバック。
  - セクター制約・レジーム乗数: `portfolio/risk_adjustment.py`
    - 既存保有を考慮したセクター集中防止（max_sector_pct に基づいて候補除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear マッピング、未知レジームはフォールバック）。
  - 株数算出およびリスク制限: `portfolio/position_sizing.py`
    - allocation_method（risk_based / equal / score）に基づき発注株数を計算。
    - 単元株（lot_size）丸め、per-stock cap と aggregate cap、コストバッファによる保守的見積り、スケーリングロジックを実装。

- データリサーチ（骨組み）
  - `research/factor_research.py` にてファクター計算（モメンタム、MA200、ATR 等）を実装するための下地を追加（関数シグネチャ、定数）。

- ユーティリティ
  - ログ初期化ユーティリティ `utils/logging_setup.py` を追加。
    - stdout 出力用 StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app>.log）をルートロガーに設定。
    - 既存ハンドラのクリア、ログディレクトリ作成失敗時のフォールバックに対応。
  - プロセス優先度・CPU affinity ユーティリティ `utils/process_priority.py` を追加。
    - Windows / POSIX の差異を吸収してプロセス優先度（high/normal/low）を設定。CPU affinity を最初の N コアに固定する機能も提供。
    - 許可エラー等を警告でスキップする耐障害性を持つ。

- DB 初期化
  - 監視用 DB の初期化を担う `monitoring/monitoring_db.py`（参照されている）が起動スクリプトから呼び出される前提で実装・利用。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Security
- 環境変数取り扱いの注意事項（.env を決して VCS にコミットしない旨）をウィザードに明示。

Notes / Implementation details
- 起動スクリプトは停止フラグ（data/stop_requested.flag 等）を用いて外部から安全に停止できる設計。
- Execution と Monitoring は DuckDB（分析用）と SQLite（トランザクション/監視用）を併用するアーキテクチャ。
- Paper Trading と本番は SQLite を分離して完全に独立したデータ保存を想定（PAPER_TRADING_SQLITE_PATH で上書き可）。
- .env ローダは既存 OS 環境変数を保護する（上書き禁止）仕組みを備え、.env.local による上書きもサポート。

開発者向け備考
- 自動 .env 読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト時に便利）。
- ログのファイル出力先やログレベルは環境変数 LOG_DIR / LOG_LEVEL で制御可能。
- PAPER_FILL_MODE の値チェックがあり、無効値は ValueError を投げるため注意。

今後の予定（例）
- research/factor_research.py のファクター計算実装完了とユニットテスト追加
- ExecutionEngine・BrokerClient の詳細実装と MockBroker のテストカバレッジ強化
- config/*.yaml のサンプル生成スクリプトや schema バリデーションの追加

--- 
※ 本 CHANGELOG は提示されたソースコードの実装内容から推測して作成しています。実際のリリースノートとして利用する際は、リリース担当者による確認・追記を推奨します。