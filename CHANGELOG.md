CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
このファイルは Keep a Changelog のフォーマットに従います。  
安定版リリースは semantic versioning を想定しています。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正 / 安定化
- Removed: 削除項目

Unreleased
----------
（次回リリースに含める予定の変更をここに記載してください）

[0.1.0] - 2026-04-20
-------------------

Added
- 初回リリース: KabuSys 自動売買フレームワークの基本機能を追加。
  - 実行 / 監視関連
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、SQLite/DuckDB 接続、BrokerClientFactory を通じたブローカークライアント生成、OrderManager / RiskManager / Reconciler 組み立て、スレッド実行と停止フラグ検知を実装。
    - run_monitoring.py: SystemMonitor 用のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能、停止フラグ検知機構を実装。
    - 監視テーブル初期化用の init_monitoring_db を導入（起動時に監視 DB スキーマの存在を保証）。
  - 設定・ユーティリティ
    - config.py: 環境変数 / .env 自動読み込み機構を追加（プロジェクトルート検出、.env/.env.local の読み込み順、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）。多数の設定プロパティ（DB パス・Paper Trading 切替・閾値等）を提供。
    - config_setup.py: 対話式の .env 初期化ウィザードを追加。デフォルト値・選択肢・シークレット入力対応・書き込み機能を提供。
    - validate_config.py: 起動前検証 CLI を追加。必須環境変数、KABUSYS_ENV の妥当性、ログレベル、DB パス、config/*.yaml の存在と（PyYAML がある場合は）パース検証を行う。--strict オプションにより警告を FAIL 扱いにできる。
    - utils/logging_setup.py: 統一的なロギング初期化ユーティリティを追加。コンソール(stdout)出力と日次ローテーションのファイル出力を設定し、ログディレクトリ作成失敗時はファイル出力を自動で無効化して継続可能。
    - utils/process_priority.py: クロスプラットフォームのプロセス優先度設定および CPU affinity 設定を追加。Windows / POSIX の差分を吸収し、失敗時は警告を出して安全にスキップ。
  - ポートフォリオ構築
    - portfolio/portfolio_builder.py: 候補選定（スコア降順・タイブレーク）、等金額配分、スコア加重配分（スコアが全て 0 の場合は等配分へフォールバック）などを実装。
    - portfolio/risk_adjustment.py: セクター集中上限適用（既存保有からセクター暴露を計算して新規候補を除外）、市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装。
    - portfolio/position_sizing.py: 発注株数算出ロジック（risk_based / equal / score）、単元株丸め、1銘柄上限・総投下上限の適用、cost_buffer を考慮した保守的なコスト見積りとスケーリングロジックを実装。
  - ツール
    - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）を算出して PASS/FAIL を判定する。閾値はファイル冒頭に定義。
  - リサーチ
    - research/factor_research.py: DuckDB 接続を受け取り Momentum 等の因子計算（モメンタム、MA200乖離、ATR、流動性指標等）のための設計と一部実装（関数骨組み）を追加。

Changed
- .env 読み込みロジックを改善:
  - export KEY=val 形式や引用符付き値（シングル/ダブル、エスケープ対応）を正しくパース可能にした。
  - .env.local を .env の上書きとしてサポート（OS 環境変数は保護）。
  - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
- ロギング:
  - コンソール出力に stdout を使用（stderr ではなく）。ログディレクトリ作成失敗やファイルハンドラ作成失敗に対するフォールバックを実装。
- run_execution/run_monitoring:
  - プロセス起動直後にプロセス優先度を高（High）へ設定する呼び出しを追加して優先度を確保。
  - DB 接続後に必ずリソースをクローズするよう finally ブロックで確実に処理するよう改善。
  - Paper Trading モードでは paper_sqlite_path を使って本番 DB と完全分離（--paper_trading 切替挙動の整合性向上）。
- process_priority:
  - Windows / Linux / Mac の違いを吸収する実装へ変更。権限不足や未対応環境では警告を出してスキップするように変更。

Fixed
- validate_config:
  - PyYAML が未インストールの場合に YAML 検証をスキップし警告を出すよう改善（起動時のハードクラッシュを回避）。
- portfolio/position_sizing:
  - aggregate cap のスケーリング時に小数端数処理を導入し、残余キャッシュを用いて lot_size 単位で再配分することで発注株数の有効活用を改善。
- run_monitoring:
  - MONITOR_POLL_INTERVAL の不正値（0 や負値、非整数）を検出してデフォルト値にフォールバックするように修正。ログで警告を出力。

Removed
- 該当なし（初回リリース）

Notes / その他
- 設定ファイル（.env）は決して Git にコミットしないでください。config_setup で生成される旨を README などに明記することを推奨します。
- 本パッケージは外部依存（psutil, duckdb, sqlite3, PyYAML（任意）等）を想定しています。デプロイ時は必要パッケージをインストールしてください。
- research/factor_research の実装は大型関数となっており、ユニットテストと計算結果の検証が推奨されます。

ライセンス、貢献、連絡先等はプロジェクトドキュメントを参照してください。