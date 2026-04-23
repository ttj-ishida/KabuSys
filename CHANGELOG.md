CHANGELOG.md

すべての変更は Keep a Changelog に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
---------
- ドキュメント化/注記
  - 一部モジュール（research/factor_research）が実装途中である旨の注記を追加（計算範囲の定義等）。
  - 各モジュールに設計方針・想定動作の docstring を充実させ、挙動を明確化。

Added
-----
- 初期リリース相当の機能群を追加（バージョン 0.1.0 にまとめてリリース）。
  - 実行スクリプト
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合はペーパートレード用の分離 DB を使用し、MockBrokerClient を選択する設計をサポート。
    - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（不正値はデフォルトにフォールバック）。監視は本番 sqlite_path を利用する仕様。
  - 設定関連
    - config.py: 環境変数パーサと Settings クラスを追加。.env/.env.local の自動ロード（OS 環境変数保護含む）や、複数の設定プロパティ（DB パス、PID/kill flag、しきい値、env/log レベル等）を提供。
    - config_setup.py: 対話式 .env 作成ウィザードを追加（既存 .env の読み込み/更新、シークレットマスク表示、保存確認）。
    - validate_config.py: 起動前の設定検証 CLI を追加（必須環境変数、KABUSYS_ENV, LOG_LEVEL, DB パス、config/*.yaml の存在など）。--strict オプションで警告を FAIL 扱いにできる。
  - ポートフォリオ構築（純関数群）
    - portfolio/portfolio_builder.py: シグナル選定（select_candidates）と重み計算（calc_equal_weights, calc_score_weights）を追加。スコアが全て 0 の場合は等金額配分にフォールバックして警告を出す。
    - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を追加。未知レジームはフォールバックし警告を出す。
    - portfolio/position_sizing.py: 発注株数計算ロジック（risk_based / equal / score に対応）、単元株丸め、aggregate cap によるスケーリング（端数処理を考慮）や cost_buffer を使った保守的見積りを実装。
  - ユーティリティ
    - utils/logging_setup.py: 統一ロギング設定ユーティリティ追加。コンソール（stdout）と日次ローテーションファイル出力を設定。ログディレクトリ作成に失敗した場合はファイルハンドラをスキップして継続。
    - utils/process_priority.py: プロセス優先度と CPU affinity を OS を吸収して設定するユーティリティを追加（Windows / POSIX 対応、権限不足時は警告でスキップ）。
  - ツール
    - tools/paper_verification_report.py: ペーパートレード DB から検証レポートを生成する CLI を追加。稼働率・注文成功率・送信率・P95 レイテンシなどを算出して PASS/FAIL 判定を行う。P95 計算や日付フィルタ、DB 存在チェックを実装。
  - パッケージメタ
    - __init__.py にバージョン __version__ = "0.1.0" を設定。

Changed
-------
- ログ出力動作
  - logging_setup: デフォルトで stdout を使用するように設計（stderr ではなく）。ログディレクトリ作成不可時もプロセス継続できるフォールバックを追加。
- DB 使用ポリシー
  - run_monitoring: 監視コンポーネントは KABUSYS_ENV に依存せず本番 sqlite_path を使用する明示的な仕様に。
  - run_execution: paper_trading 環境では paper_sqlite_path を使用し、本番 DB と完全分離。

Fixed
-----
- 環境変数パーサの堅牢化（config.py）
  - .env の行解析で export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いを適切に処理するよう改善。無効行は安全にスキップ。
- MONITOR_POLL_INTERVAL の取り扱い（run_monitoring）
  - 環境変数が整数でない、または 1 未満の値の場合、警告を出してデフォルト値にフォールバックするように変更（time.sleep に渡せない値を防止）。
- プロセス優先度の失敗ハンドリング（utils/process_priority）
  - 権限不足や未対応 OS 時に例外で落ちないよう例外をキャッチして警告を出すフォールバックを追加。
- position_sizing のスケーリング端数処理
  - aggregate cap のスケールダウン時、lot_size 単位での再配分ロジックを導入し残余資金の活用を改善。価格欠損時のスキップ処理を明確化。

Security
--------
- 環境設定ウィザードおよび .env 書き込み時にシークレット項目は表示をマスク（画面上）し、.env をリポジトリにコミットしない旨を明記。

Removed
-------
- 該当なし（初期リリース）。

0.1.0 - 2026-04-23
-----------------
- 初回公開リリース。上記「Added」項目を含む基本機能を実装：
  - 実行/監視スクリプト、環境設定・検証 CLI、ポートフォリオ構築ロジック（選定・重み付け・リスク調整・株数計算）、ユーティリティ（ロギング・プロセス優先度）、ペーパートレード検証レポート生成ツール等を含む。
  - 開発向けの設計ドキュメントや注釈（PortfolioConstruction.md 等参照）に沿った純関数実装を採用。

注記
----
- research/factor_research.py はモジュール実装の途中（コメント/定義が存在）です。将来的に DuckDB を用いたファクター計算（Momentum / Value / Volatility / Liquidity）機能を追加予定です。
- 本 CHANGELOG はソースコードから推測して作成しています。実際のコミット単位や履歴とは差異がある可能性があります。必要であればコミットログやリポジトリ履歴に基づく正式な CHANGELOG の生成を支援します。