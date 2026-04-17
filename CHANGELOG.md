# Changelog

すべての主な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-04-17

### Added
- 初期リリース。パッケージバージョンを __version__ = "0.1.0" に設定 (src/kabusys/__init__.py)。
- 実行用エントリスクリプトを追加:
  - 実行エンジン起動スクリプト run_execution.py（プロセス優先度設定、停止フラグ／PID 管理、paper_trading 用 DB 分離） (src/kabusys/run_execution.py)。
  - 監視ポーリングループ起動スクリプト run_monitoring.py（MONITOR_POLL_INTERVAL 環境変数対応、停止フラグ検知、監視 DB 初期化） (src/kabusys/run_monitoring.py)。
- 環境設定関連 CLI を追加:
  - 対話式 .env ウィザード config_setup.py（.env 作成・更新、出力テンプレート） (src/kabusys/config_setup.py)。
  - 設定検証ツール validate_config.py（必須環境変数、KABUSYS_ENV/LOG_LEVEL の検証、config/*.yaml の存在／パースチェック、--strict モード） (src/kabusys/validate_config.py)。
- Paper Trading 検証レポート生成ツールを追加（period 指定・P95 等の指標計算） (src/kabusys/tools/paper_verification_report.py)。
- 設定読み込み・管理機構を追加・強化:
  - プロジェクトルート検出ロジック (.git / pyproject.toml を基準) による自動 .env ロード (src/kabusys/config.py)。
  - .env の柔軟なパース（export 宣言、シングル/ダブルクォート内のエスケープ、インラインコメント対応）を実装 (src/kabusys/config.py)。
  - 各種設定プロパティ（DB パス、paper_trading 用パス、PID/kill flag パス、監視閾値、PAPER_FILL_MODE バリデーション等）を提供 (src/kabusys/config.py)。
- プロセス制御ユーティリティを追加:
  - set_process_priority と set_cpu_affinity（Windows / POSIX の差異吸収、権限失敗時のフォールバック） (src/kabusys/utils/process_priority.py)。
- ポートフォリオ構築モジュールを追加（純粋関数群、DB 非依存）:
  - 候補選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights） (src/kabusys/portfolio/portfolio_builder.py)。
  - セクター集中抑制・レジーム乗数（apply_sector_cap, calc_regime_multiplier） (src/kabusys/portfolio/risk_adjustment.py)。
  - 株数決定ロジック（risk_based / equal / score、単元丸め、aggregate cap スケーリング） (src/kabusys/portfolio/position_sizing.py)。
- 研究用ファクター計算モジュールを追加（DuckDB 経由で momentum / volatility 等を計算） (src/kabusys/research/factor_research.py)。

### Changed
- 監視用処理は KABUSYS_ENV に関係なく「本番」用 sqlite_path を使用する設計にした旨を明示（monitoring は環境分離しない） (src/kabusys/run_monitoring.py)。
- ExecutionEngine は paper_trading 環境下では paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と完全に分離する（src/kabusys/run_execution.py）。
- .env 自動読み込みの優先順位を OS 環境 > .env.local > .env とし、OS 環境変数を保護する仕組みを導入（既存環境変数は上書きされない） (src/kabusys/config.py)。
- config_setup により生成される .env テンプレートと項目セットを用意（J-Quants / kabu / DuckDB / SQLite / LINE / LOG_LEVEL / Kill Switch など） (src/kabusys/config_setup.py)。
- validate_config により起動前に主要な設定不備（必須環境変数未設定、KABUSYS_ENV/LOG_LEVEL の不正値、DB パスの親ディレクトリ欠如、config/*.yaml の存在/パース）を検出可能にした (src/kabusys/validate_config.py)。
- run_* スクリプト起動時に最初に set_process_priority("high") を呼ぶようにして、実行中の優先度を上げる (src/kabusys/run_execution.py, src/kabusys/run_monitoring.py)。

### Fixed / Robustness
- MONITOR_POLL_INTERVAL の環境変数値が不正（非整数や 0 以下）だった場合にデフォルト値にフォールバックし、警告を出す実装を追加 (src/kabusys/run_monitoring.py)。
- .env パーサーの挙動を堅牢化（クォート内のバックスラッシュエスケープ、インラインコメント判定の改善、export プレフィックス対応） (src/kabusys/config.py)。
- PAPER_FILL_MODE の値検証を実装し、不正な値時に ValueError を出して早期に検出する（有効値: instant|partial|never|reject） (src/kabusys/config.py)。
- set_cpu_affinity の引数検証を追加（1 未満は ValueError）および、利用不可時は警告出力でスキップするようにした (src/kabusys/utils/process_priority.py)。
- calc_score_weights: 全銘柄のスコア合計が 0 の場合に等金額配分へフォールバックしログ警告を出すことでゼロ除算を回避 (src/kabusys/portfolio/portfolio_builder.py)。
- calc_regime_multiplier: 未知のレジームに対してフォールバック値 1.0 を返し、警告ログを出す (src/kabusys/portfolio/risk_adjustment.py)。
- position sizing:
  - 価格欠損（None または <=0）の銘柄はスキップする安全策を追加。
  - 単元（lot_size）単位で丸め、aggregate cap を超える場合はスケールダウンして再分配するロジックを実装 (src/kabusys/portfolio/position_sizing.py)。
- Paper Verification レポート:
  - P95 レイテンシ計算、稼働率/成功率/送信率の閾値判定と PASS/FAIL 表示を追加。DB が存在しない／テーブルが無い場合にも安全に N/A を返す (src/kabusys/tools/paper_verification_report.py)。

### Security
- 機密値（J-Quants リフレッシュトークン、kabu API パスワード、LINE トークン）は .env ウィザードでシークレット扱いとし、出力時にマスクするよう配慮 (src/kabusys/config_setup.py)。
- .env ファイル生成時に「絶対に Git にコミットしないこと」を明記するテンプレートを追加 (src/kabusys/config_setup.py)。

### Removed / Deprecated
- なし。

(注) 上記はソースコードから推測してまとめた初期リリース向けの主な変更点・特徴です。実際の変更履歴やリリースノートはコミット履歴・リリース作業に基づいて確定してください。