CHANGELOG
=========

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。
なお、本 CHANGELOG は提示されたコードベースの内容から推測して作成したものであり、実際のコミット履歴ではありません。

[Unreleased]
------------

- なし

0.1.0 - 2026-04-20
------------------

Added
- 初期公開: KabuSys 自動売買フレームワークの基本コンポーネントを追加
  - 実行・監視スクリプト
    - run_execution.py: ExecutionEngine 起動スクリプト（スレッド実行、停止フラグ検知、PID ファイル管理）
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL による間隔調整）
  - 設定関連 CLI / モジュール
    - config.py: 環境変数ラッパー（Settings クラス）、プロジェクトルート検出、自動 .env ロード
    - config_setup.py: 対話式 .env ウィザード（.env の読み書き・入力プロンプト）
    - validate_config.py: 起動前設定検証 CLI（--strict モード対応）
  - ポートフォリオ構築モジュール
    - portfolio/portfolio_builder.py: 候補選定・等配分／スコア配分
    - portfolio/position_sizing.py: 株数計算（risk_based / equal / score、lot 単位丸め、aggregate cap スケーリング、cost_buffer 対応）
    - portfolio/risk_adjustment.py: セクター上限適用、レジーム乗数（bull/neutral/bear）
  - 実行系コンポーネント（設計要素）
    - 実行時のブローカークライアント生成（BrokerClientFactory 経由）
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立て（run_execution での利用想定）
  - 監視・ツール
    - monitoring 側 DB 初期化ユーティリティ（init_monitoring_db の利用を想定）
    - tools/paper_verification_report.py: ペーパートレード検証レポート生成ツール（稼働率、注文成功率、レイテンシ等の集計と PASS/FAIL 判定）
  - ユーティリティ
    - utils/logging_setup.py: ルートロガーの統一セットアップ（stdout StreamHandler + 日次ローテート FileHandler、30日保持）
    - utils/process_priority.py: プロセス優先度と CPU affinity 設定（Windows/Linux/macOS対応ラッパー、フォールバック処理あり）

Changed
- .env 自動ロードの仕様を明確化（config.py）
  - プロジェクトルートを .git または pyproject.toml で探索して自動ロード
  - 読み込み順: OS 環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能
  - OS 環境変数は保護され、.env.local の上書きでも保護される
- logging_setup の挙動整理
  - ログ出力先: 標準出力は stdout に固定（cron 等で stdout/stderr を統合する運用を想定）
  - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続する堅牢な実装
- run_execution/run_monitoring の動作に関する運用仕様
  - run_execution: KABUSYS_ENV=paper_trading の場合は paper_sqlite_path を使用して本番 DB と分離（Paper Trading と実 DB を完全分離）
  - run_monitoring: Monitoring は環境に関係なく本番 sqlite_path を使用（監視データは本番 DB を想定）
  - 両スクリプトでプロセス優先度を最初に "high" に設定する（process_priority.set_process_priority を使用）
  - 停止は data/stop_requested.flag (プロジェクトルート下 data) によるフラグファイルで検知

Fixed / Robustness improvements
- .env パーサ (.env 読み込み) の堅牢化（config.py）
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ考慮、行末コメント処理（クォートあり/なしそれぞれの挙動を精緻化）
  - 無効行・空行・コメント行を無視
- MONITOR_POLL_INTERVAL の取り扱いを堅牢化（run_monitoring.py）
  - 環境変数が不正（数値以外、0 以下）の場合はログ警告の上でデフォルト 60 秒にフォールバック
- process_priority / cpu_affinity の例外ハンドリング強化（utils/process_priority.py）
  - 権限不足や未実装機能（AccessDenied / NotImplementedError 等）時は警告を出して処理を継続
  - 未対応 OS の場合はスキップして警告
- logging_setup: 既存ハンドラの flush/close とクリアを行い二重設定を防止
- position_sizing の aggregate cap スケーリング:
  - コストバッファ (cost_buffer) を計算に取り込むことで、手数料/スリッページ分を保守的に見積もる
  - スケールダウン後の端数処理で lot_size 単位に丸め、残余キャッシュで残差が大きい順に追加配分する処理を実装（再現性確保のためソート順を安定化）

Security / Secrets handling
- config_setup ウィザードではシークレット値を表示時にマスク（****）して表示し、.env 保存時も注意喚起コメントを付与
- validate_config により必須トークン等が未設定のまま起動するのを防ぐチェックを追加

Notes / Known limitations / TODOs
- portfolio/position_sizing.py:
  - 将来的な拡張として銘柄ごとの lot_size を持たせる設計（TODO コメントあり）
- portfolio/risk_adjustment.apply_sector_cap:
  - price が不足（0.0）した場合に露出が過小見積りされブロックが外れる問題がコメントで指摘されており、前日終値等のフォールバック価格の導入が検討課題
- research/factor_research.py はモジュール実装途中の箇所があり（ファイル終端が途中）、実運用前に追加実装・テストが必要
- run_monitoring は監視用 DB として本番 sqlite_path を常に使用する設計のため、監視データの扱いには注意が必要

開発者向けメモ
- バージョニングはパッケージ __version__ = "0.1.0"
- 日次ログローテーションはデフォルトで 30 日分保持（utils/logging_setup.py の _BACKUP_COUNT）
- validate_config の --strict オプションで警告を失敗扱いにできるため、本番導入前のチェックに便利

お問い合わせ / 貢献
- この CHANGELOG はコードの静的な内容から推測して作成しています。実際のコミット履歴やリリースノート作成では、コミットメッセージ・PR 説明等に基づいた正確な差分記載を行ってください。