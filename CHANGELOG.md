# Changelog

すべての注目すべき変更点をここに記録します。  
フォーマットは Keep a Changelog に準拠しています。  
<https://keepachangelog.com/ja/1.0.0/>

## [Unreleased]

### Added
- なし（現時点では最新リリースと同等）

### Changed
- なし

### Fixed
- なし

---

## [0.1.0] - 2026-04-19

初回リリース。自動売買システム KabuSys のコア機能群を実装・整理しました。主要な追加点と設計上の特徴は以下の通りです。

### Added
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き対応（デフォルト 60 秒）。
    - 停止制御に data/stop_requested.flag を使用。
    - 監視は KABUSYS_ENV に関わらず本番用 sqlite_path を使用して初期化。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、専用の paper_trading DB（data/paper_trading.db、環境変数で上書き可）に記録して本番 DB と分離。
    - 停止フラグ (data/stop_requested.flag) の検知による安全な停止処理、PID ファイルの扱い、スレッドでの実行管理を実装。
    - 起動時にプロセス優先度を "high" に設定。

- 設定関連
  - config.py
    - Settings クラスを実装。環境変数から各種設定を取得する API を提供（J-Quants、kabu API、DB パス、各しきい値等）。
    - 自動 .env ロード機能を実装（プロジェクトルート検出: .git / pyproject.toml を探索）。.env/.env.local の読み込み順序および OS 環境変数保護機構を備える。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パースで export プレフィックス、クォート（シングル/ダブル）、バックスラッシュエスケープ、インラインコメントの扱いに対応。
    - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH 等、Paper Trading 用設定をサポート。
    - 環境値の検証（KABUSYS_ENV, LOG_LEVEL 等）を行い、不正な値は ValueError を投げる。

  - config_setup.py
    - 対話式ウィザードで .env を生成・更新するツールを追加。主要項目の説明、既存値の再利用、秘密項目のマスク表示、保存確認を実装。

  - validate_config.py
    - 起動前に .env および config/*.yaml の基本チェックを行う CLI を追加。
    - 必須環境変数の未設定チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パスの親ディレクトリ確認、YAML の存在確認（PyYAML 有無に応じてパース）等を実行。
    - --strict オプションで警告を FAIL 扱いにする機能を追加。

- ログ・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定する共通セットアップを追加。
    - LOG_DIR 指定や環境変数 LOG_LEVEL を尊重。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで動作。
  - utils/process_priority.py
    - プラットフォーム差を吸収したプロセス優先度設定 (high/normal/low) を実装（Windows の priority class、POSIX の nice 値を使用）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity 関数を追加。
    - psutil の権限不足や未対応 OS の場合は警告ログを出して安全にフォールバック。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコア合計が 0 の場合は等金額にフォールバックする警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（既存保有を基にセクター別エクスポージャ算出、閾値超過セクターの候補除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマップ、未知レジームは警告の上 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - 各種配分方式（risk_based / equal / score）に対応した株数算出 calc_position_sizes を実装。
    - 単元（lot_size）で丸め、per-position 上限（max_position_pct）・aggregate cap（available_cash）・手数料/スリッページ見積り cost_buffer を考慮したスケーリング処理を含む。
    - 価格欠損時のスキップや利用可能現金を踏まえた正規化ロジックを実装。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加。
    - 指定期間（--from / --to）または DB 全期間で集計し、稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ、リスク却下数などを出力。閾値に基づく PASS/FAIL 判定を行う。
    - P95 計算や日付フィルタの ISO8601 変換、DB 存在チェックを実装。

- リサーチ
  - research/factor_research.py（骨子）
    - DuckDB 接続を受け取って定量ファクター（Momentum/Value/Volatility/Liquidity）を計算するモジュールの骨子を追加。モメンタム計算の設計と定数群を実装（実装途中の関数あり）。

### Changed
- パッケージ情報
  - src/kabusys/__init__.py にバージョン情報 __version__ = "0.1.0" を設定。

### Fixed
- 環境読み込みの堅牢化
  - .env パーサーでクォート内のバックスラッシュエスケープや inline コメント処理に対応し、より多様な .env フォーマットに耐性を持たせた。
  - .env ロード時に OS 環境変数を保護する protected 引数を導入し、意図せぬ上書きを防止。

### Security
- 秘密情報の扱い
  - config_setup の対話式 UI で秘密項目（J-Quants トークン、KABU_API_PASSWORD 等）はマスクして表示。README 等へのコミット注意をコメントに明記（.env を絶対に Git にコミットしない旨）。

### Notes / Known limitations
- research/factor_research.py は設計・定数は整備済みだが、calc_momentum 等の一部実装がファイル末尾で途切れている（今後の実装継続予定）。
- portfolio モジュールは純関数でメモリ内処理を想定しており、将来的に銘柄マスタから銘柄別 lot_size を読み込む拡張を想定した TODO コメントが存在。
- process_priority/set_cpu_affinity は権限やプラットフォーム依存のため、失敗した場合は警告ログを出してスキップする設計。

---

今後の予定（推測）
- factor_research の完成（各ファクター計算の SQL 実装・統合）。
- ExecutionEngine / Monitoring 周りの詳細ロギング・テスト追加。
- 戦略定義や実際のブローカー実装の追加・安定化。

もしさらに詳細（ファイルごとの差分やコミットメッセージから正確な変更履歴を生成するなど）が必要であれば、該当する Git diff / コミットログを提供してください。コードのみからの推測に基づくまとめのため、一部実装状態は推定を含みます。