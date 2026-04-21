# CHANGELOG

このファイルは Keep a Changelog の形式に準拠しています。  
次回以降の変更はトップの Unreleased セクションに追加してください。

全般的な注記
- このリリースはコードベースの最初の公開相当の状態を元に作成した変更履歴（推測）です。実装内容から機能追加・改善点・注意点をまとめています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-21

初回リリース（推定）。主要な機能、CLI、ユーティリティ、ポートフォリオ構築ロジック、実行/監視ランナーを含みます。

### Added
- 基本アーキテクチャと主要コンポーネント
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
    - KABUSYS_ENV による paper_trading モード判定を実装。paper_trading の場合は専用の SQLite（data/paper_trading.db デフォルト）を使用して本番 DB と分離。
    - BrokerClientFactory を介したブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - ExecutionEngine をバックグラウンドスレッドで実行し、data/stop_requested.flag により安全に停止可能。
    - PID ファイル(data/execution.pid) をサポート。
  - SystemMonitor 起動スクリプト（src/kabusys/run_monitoring.py）
    - 監視ループの実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を制御（デフォルト 60 秒）。
    - 監視は実行環境にかかわらず本番用 sqlite_path を使用する設計。
    - stop フラグ検知、例外時のログ出力とループ継続処理を実装。
  - 設定管理（src/kabusys/config.py）
    - .env 自動読み込み機能（プロジェクトルート検出: .git / pyproject.toml を基準）。
    - .env/.env.local の読み込みルール（OS 環境変数の保護、override 挙動）。
    - .env パースの堅牢化（export 形式対応、クォート文字列のエスケープ処理、インラインコメント処理等）。
    - Settings クラスで各種設定（DB パス、API トークン、Paper Trading 設定、閾値、フラグパス 等）をプロパティとして提供。
  - 環境設定ウィザード CLI（src/kabusys/config_setup.py）
    - 対話式で .env を生成・更新するウィザード。シークレットはマスク表示、既存値の再利用が可能。
  - 設定検証 CLI（src/kabusys/validate_config.py）
    - .env と config/*.yaml の存在・基本妥当性をチェックする CLI。--strict で警告をエラー扱いに。
    - PyYAML が未インストールの場合は YAML 検証をスキップして警告。
    - 本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE 設定未設定、KILL_FLAG_CLEAR_ON_START の危険性警告等）。
  - ロギングユーティリティ（src/kabusys/utils/logging_setup.py）
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定する統一 API を提供。
    - LOG_DIR が作成できない場合はファイル出力をスキップして安全にフォールバック。
  - プロセス優先度・CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows / POSIX の差分を吸収して優先度設定（high/normal/low）を行う set_process_priority。
    - set_cpu_affinity によるプロセスのコアピン留め機能を提供。実行時の権限不足等は警告でスキップ。
  - ポートフォリオ構築モジュール（src/kabusys/portfolio/**）
    - 銘柄選定: select_candidates（スコア降順、同点は signal_rank でブレーク）
    - 重み計算: calc_equal_weights、calc_score_weights（スコア合計が 0 の場合は等配分でフォールバック）
    - リスク調整: apply_sector_cap（セクター上限による候補除外）、calc_regime_multiplier（市場レジームに応じた乗数）
    - 銘柄数量計算: calc_position_sizes
      - risk_based / equal / score の配分方式に対応
      - 単元株（lot_size）丸め、1 銘柄上限・合計上限（available_cash）を考慮したスケーリング処理の実装
      - cost_buffer を用いた保守的コスト見積り、残余キャッシュでの端数配分ロジックを実装
  - Paper Trading 検証レポートツール（src/kabusys/tools/paper_verification_report.py）
    - ペーパートレード用 DB から稼働率、注文成功率、送信率、レイテンシ（平均・P95）などを集計してレポート出力。
    - 判定基準（閾値）を定義し PASS/FAIL を出力。
    - --from/--to/--db オプションに対応。
  - 研究用ファクター計算スケルトン（src/kabusys/research/factor_research.py）
    - モメンタム / ボラティリティ / バリュー / 流動性 等の計算を想定した設計（DuckDB 経由で prices_daily 等を参照する方針、関数群の雛形を含む）。

### Changed
- ロギング設計
  - stdout を利用する StreamHandler を採用（cron 等で stdout/stderr をまとめてリダイレクトしやすくするため）。ファイル出力失敗時はコンソール出力のみで継続。
- .env 読み込みポリシー
  - OS 環境変数を優先し、.env.local で上書き可能にする（override の扱い）。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
- 実行/監視ランナーの挙動
  - 起動時にプロセス優先度を "high" に設定する呼び出しを追加（set_process_priority）。
  - run_monitoring は例外発生時にも監視ループを継続するよう例外ハンドリングを強化。
  - run_execution は既に停止フラグが立っている場合に起動せず終了する安全ガードを追加。

### Fixed
- .env パーサの堅牢性向上
  - export 先頭キーワード対応、クォート内のバックスラッシュエスケープ対応、インラインコメントの扱いなどを改良して .env 読み込みでの誤解析を減少。
- ログディレクトリ作成失敗時のフォールバック
  - 失敗時にファイルハンドラの作成をスキップし、コンソールログのみで継続することで起動失敗を回避。
- プロセス優先度設定の失敗を安全にハンドリング
  - 権限不足や未対応 OS の場合に例外を投げず警告ログを出すようにして、起動時の致命的障害を防止。

### Security
- 機密情報取り扱い
  - config_setup の対話ではシークレット項目をマスク表示（画面上）。ただし .env ファイルはローカルに平文で保存されるため「Git にコミットしない」旨の注意を明記。

### Notes / Known limitations
- research/factor_research.py は機能の骨格を含むが一部未完（コメントの末尾で切れている等）。実装の続きが必要。
- price や lot_size の欠損時のフォールバックロジックは限定的（例: apply_sector_cap の price=0 の場合の TODO 注釈あり）。
- 一部 API 依存（kabuステーション、J-Quants）や外部パッケージ（psutil, duckdb, PyYAML）が必須。validate_config で未存在を警告。
- Paper Trading（モックブローカー）と本番ブローカーは DB を完全に分離する設計だが、設定ミスによりパスを共有しないよう注意が必要。

---

参考: Keep a Changelog (https://keepachangelog.com/ja/1.0.0/)