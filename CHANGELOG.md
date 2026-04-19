# Changelog

すべての重大な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

- リリースは逆順（新しいものが上）に記載します。  
- 日付は ISO 形式 (YYYY-MM-DD) で表記します。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-04-19

初期リリース — KabuSys の基本機能セットを実装しました。主な追加・仕様は以下の通りです。

### Added
- 全体
  - パッケージのバージョンを 0.1.0 として公開（src/kabusys/__init__.py）。
  - 環境設定・起動用ユーティリティ群を追加:
    - 環境読み込みと Settings を提供する config モジュール（src/kabusys/config.py）。
      - .env 自動ロード（プロジェクトルート検出）機能。
      - 必須/任意環境変数のプロパティ（J-Quants, kabu API, DB パス、ログ等）。
      - PAPER_FILL_MODE の検証、環境判定プロパティ（is_live/is_paper/is_dev）。
    - 対話式 .env 作成ウィザード（src/kabusys/config_setup.py）。
      - 初期 .env 作成／更新を支援する CLI。
    - 設定検証 CLI（src/kabusys/validate_config.py）。
      - 必須環境変数・KABUSYS_ENV・ログレベル・DB パス・config/*.yaml 存在チェック等を実施。
      - --strict オプションで警告を失敗扱いにできる。
- 実行・監視ランナー
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時に専用の SQLite（data/paper_trading.db）を使用する分離設計。
    - BrokerClientFactory によるブローカークライアント生成。
    - ExecutionEngine をバックグラウンドスレッドで実行し、stop flag（data/stop_requested.flag）で安全停止。
    - 実行用 PID 管理（data/execution.pid）。
  - SystemMonitor ポーリングループ起動スクリプト（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数によりポーリング間隔を変更可能（デフォルト 60 秒）。
    - 監視は本番 sqlite_path を利用して常に監視 DB を更新。
    - 停止フラグ検知でループを終了、KeyboardInterrupt ハンドリング、DB コネクションクローズを確実化。
- データ・解析
  - DuckDB を用いたリサーチ/ファクター計算の骨子を追加（src/kabusys/research/factor_research.py）（モジュール開始部分を実装）。
  - Paper Trading 検証レポート生成ツール（src/kabusys/tools/paper_verification_report.py）。
    - 稼働率、注文成功率、送信率、レイテンシ（P95 等）を集計して PASS/FAIL 判定を出力。
    - 日付フィルタ、DB パス指定オプション、閾値は定数で管理。
- ポートフォリオ構築（純粋関数群）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates, calc_equal_weights, calc_score_weights を実装。スコア合計が 0 の場合のフォールバック実装あり。
  - セクター制約・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap によるセクター集中制限、calc_regime_multiplier によるレジーム毎の資金乗数（bull/neutral/bear）。
  - ポジションサイズ決定（src/kabusys/portfolio/position_sizing.py）
    - allocation_method（risk_based / equal / score）対応、単元株（lot_size）丸め、aggregate cap によるスケールダウンロジックを実装。
- ユーティリティ
  - ログ設定ユーティリティ（src/kabusys/utils/logging_setup.py）
    - stdout 出力用 StreamHandler と 日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log）をルートロガーに設定。
    - LOG_DIR 生成失敗時はファイル出力をスキップして stdout のみで動作。
  - プロセス優先度 / CPU affinity 設定ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows / POSIX（Linux/Mac/FreeBSD）間差分を吸収して優先度設定（high/normal/low）を提供。権限不足時は警告でスキップ。
    - CPU affinity を最初の N コアに固定する関数を提供。

### Changed
- 設計上の注意・既定値の明記
  - Paper Trading と Live の DB を明確に分離（paper_trading 用の PAPER_TRADING_SQLITE_PATH を利用）。
  - 監視・実行ともにプロセス優先度を起動時に High に設定する挙動を導入。
  - .env 自動ロードの優先順位を OS 環境変数 > .env.local > .env とし、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - logging_setup は既存ハンドラを安全にクリーンアップして再設定するようにした（多重ハンドラ防止）。
  - validate_config は PyYAML 未導入時に YAML 検証をスキップして警告を出す。

### Fixed / Robustness
- .env パーサーの改善（src/kabusys/config.py）
  - export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメントなどに対応してより堅牢にパースするよう実装。
- ポートフォリオロジックの安全性向上
  - calc_score_weights: 全スコアが 0 の場合は等金額配分にフォールバックして例外を防止。
  - apply_sector_cap: セクター不明（"unknown"）の場合はセクター上限を適用しない。
  - calc_position_sizes: 価格欠損や price<=0 の場合はスキップして不正発注を防止。aggregate cap 適用時の丸め・再配分ロジックを実装し資金制約下でも再現性ある配分を実現。
- 実行・監視の安全停止
  - stop flag（data/stop_requested.flag）検知で安全に停止する仕組みを両スクリプトに導入。
  - DB 接続（sqlite3 / duckdb）を finally で確実に閉じるようにした。

### Security
- .env の取り扱いに関する注意文を config_setup に追加（.env を Git にコミットしないよう明記）。
- config._require() は必須環境変数未設定時に ValueError を投げ、起動前に明確に失敗するようにして誤設定での本番起動を防止。

---

今後の予定（例）
- factor_research の完全実装（DuckDB クエリと Z スコア正規化の統合）。
- ExecutionEngine 周りの詳細実装・テスト増強（リコンシリエーション、リスクマネージャの動作確認）。
- 単体テスト・CI の追加、ドキュメント整備（API リファレンス、運用手順）。

もし CHANGELOG に特定の変更点（追加した機能や修正の粒度）を細かく反映したい場合は、どのコミット／PR／機能に重点を置くか教えてください。必要に応じて項目を分割して追記します。