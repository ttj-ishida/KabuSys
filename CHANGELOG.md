# Changelog

すべての注目すべき変更点を記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

現在のバージョン: 0.1.0（初回公開）  
日付: 2026-04-21

## [Unreleased]

（未リリースの変更はここに記載します）

---

## [0.1.0] - 2026-04-21

### Added
- 初回リリースとして KabuSys のコア機能を追加。
  - パッケージ基盤
    - パッケージバージョン定義: `src/kabusys/__init__.py`（__version__ = "0.1.0"）
  - 設定管理
    - 環境変数 / .env の自動読み込みとパース機能を実装（`src/kabusys/config.py`）。
      - プロジェクトルート自動検出（.git / pyproject.toml を探索）に基づく .env 自動ロード。
      - export プレフィックスや引用符付き値、インラインコメント、エスケープを考慮した堅牢なパーサを提供。
      - OS 環境変数を保護するための上書き制御を実装。
    - Settings クラスでアプリ設定にアクセスする単純なプロパティ群を提供（DB パス、各種閾値、環境判定等）。
  - 設定支援 CLI
    - 対話式 .env 作成/更新ウィザード（`src/kabusys/config_setup.py`）。
    - 設定検証 CLI（`src/kabusys/validate_config.py`）:
      - 必須環境変数チェック、KABUSYS_ENV・LOG_LEVEL の妥当性確認、DB パスや config/*.yaml の存在チェック、
        本番環境に関するガード（LINE 設定や Kill Switch の注意喚起）を実施。
      - `--strict` オプションで警告も FAIL 扱いにできる。
  - 実行/監視エントリポイント
    - ExecutionEngine 起動スクリプト（`src/kabusys/run_execution.py`）:
      - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用 SQLite（`data/paper_trading.db` を想定）を利用することで本番 DB と分離。
      - BrokerClientFactory によるブローカークライアント抽象化、OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てと起動制御。
      - 停止フラグ（data/stop_requested.flag）検出による安全な停止処理。
    - SystemMonitor 起動スクリプト（`src/kabusys/run_monitoring.py`）:
      - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒）。
      - 監視ループと停止フラグ検出、エラー時のロギングおよび後続ポーリングへの復帰処理。
  - ポートフォリオ構築ライブラリ（純粋関数群、DB 非依存）
    - 候補選定と重み計算（`src/kabusys/portfolio/portfolio_builder.py`）:
      - select_candidates, calc_equal_weights, calc_score_weights を提供。スコア全0 の場合は等配分へフォールバック。
    - セクター集中制限・レジーム乗数（`src/kabusys/portfolio/risk_adjustment.py`）:
      - apply_sector_cap によるセクター上限チェック、calc_regime_multiplier によるレジームに応じた投下資金乗数（bull/neutral/bear のマッピングとフォールバック挙動）。
    - 株数決定・リスク制限・単元丸め（`src/kabusys/portfolio/position_sizing.py`）:
      - risk_based / equal / score の割当方式に対応。単元（lot_size）での丸め、aggregate cap（利用可能現金に応じたスケーリング）、手数料等を考慮した cost_buffer を実装。
  - ユーティリティ
    - ログ設定ユーティリティ（`src/kabusys/utils/logging_setup.py`）:
      - stdout 用 StreamHandler と日次ローテートの TimedRotatingFileHandler をルートロガーに設定。
      - LOG_LEVEL, LOG_DIR の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - プロセス優先度・CPU affinity ヘルパー（`src/kabusys/utils/process_priority.py`）:
      - Windows / POSIX の差分を吸収して優先度設定（high/normal/low）と CPU affinity 固定を提供。権限不足や未対応 OS は警告でスキップ。
  - Paper Trading 向け分析ツール
    - Paper Trading 検証レポート生成スクリプト（`src/kabusys/tools/paper_verification_report.py`）:
      - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、P95 レイテンシなどを算出して PASS/FAIL 判定を出力。
      - CLI オプションで期間指定（--from/--to）および DB パス指定（--db）に対応。
      - P95 計算ロジック、日付フィルタビルダー、しきい値（稼働率99%、成立率90% など）を含む。

### Changed / Improvements
- .env 読み込みの堅牢化（`src/kabusys/config.py`）
  - export プレフィックスやシングル/ダブルクォート、バックスラッシュエスケープを正しく処理。
  - クォートなし値のインラインコメント判定ルールを改善。
  - プロジェクトルートが見つからない場合は自動ロードをスキップして安全に動作。
- ロギング（`src/kabusys/utils/logging_setup.py`）
  - ハンドラ二重設定を防ぐため既存ハンドラをクリアして再設定。
  - stdout を標準のストリーム出力に選択（cron 等でのリダイレクト運用を考慮）。
  - ログファイル出力に失敗した場合でもコンソール出力で継続する耐障害性を追加。
- プロセス優先度設定（`src/kabusys/utils/process_priority.py`）
  - Windows と POSIX 両対応のためのフォールバック実装と詳細な警告メッセージを追加。
- 実行/監視周りの安全性強化
  - 停止フラグ検出による早期停止や、安全なリソースクローズ（DB 接続の close）を徹底。
  - ExecutionEngine 起動時に既に停止フラグが立っている場合は起動を中止する挙動を追加。

### Fixed
- 環境変数関連の微妙な不整合に対処
  - _get_poll_interval の 0 以下や不正値に対して警告を出しデフォルトにフォールバック（`src/kabusys/run_monitoring.py`）。
- DB / ファイル操作の耐障害性
  - ログディレクトリ作成失敗やファイルハンドラ作成失敗時に例外伝播させずフォールバックするよう修正（`src/kabusys/utils/logging_setup.py`）。
  - .env ファイル読み込み失敗時に警告出力して処理を継続（`src/kabusys/config.py`）。

### Security
- シークレット扱いの環境変数は config_setup の出力でマスク表示（`src/kabusys/config_setup.py`）。
- .env の自動ロードで OS 環境変数を保護するため protected set を導入（`src/kabusys/config.py`）。

---

今後の予定（例）
- research モジュール（ファクター計算）の完成（`src/kabusys/research/factor_research.py` の継続実装）。
- テストカバレッジと CI の追加、各モジュールのユニットテスト整備。
- 実運用向けの監視/アラート（LINE 通知）統合強化。