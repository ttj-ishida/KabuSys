Keep a Changelog 準拠の CHANGELOG.md（日本語）

フォーマット:
- 変更はカテゴリ別に整理（Added, Changed, Fixed, Removed, Deprecated, Security）
- 初回リリースとして v0.1.0 を記載し、開発中の未リリース変更は Unreleased にまとめています

Unreleased
---------
（現時点でリリースされていない作業や今後の改善点・TODO を記載します）

Added
- 監視・実行ランナー用の起動スクリプトを追加（src/kabusys/run_monitoring.py, src/kabusys/run_execution.py）
  - モニタリング（SystemMonitor）用のポーリングループ実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止は data/stop_requested.flag で行う。
  - ExecutionEngine 起動スクリプトは paper_trading 環境で MockBrokerClient を利用し、paper_trading 用 DB（data/paper_trading.db）を分離して使用。
  - 両スクリプトとも起動時にプロセス優先度を "high" に設定。

- 設定管理と支援ツールを追加
  - 環境変数 / .env 自動読み込み・パース機能（src/kabusys/config.py）
    - プロジェクトルート検出（.git / pyproject.toml）に基づく .env 自動読み込み
    - export KEY=val、クォート文字内のエスケープ、インラインコメント等に対応する堅牢なパーサー
    - .env.local の上書き挙動、OS 環境変数を保護する挙動を実装
    - Settings クラスでアプリケーションの各種設定をプロパティとして提供（DB パス、API トークン、環境フラグ、監視しきい値等）
  - 対話式 .env 作成ウィザード（src/kabusys/config_setup.py）
    - 秘匿入力のマスク表示、既存 .env の読み込み、保存の確認機能
  - 設定検証 CLI（src/kabusys/validate_config.py）
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パス・config/*.yaml の存在チェック、live 環境向けガードの警告
    - --strict モードで警告を失敗扱いにできる

- ポートフォリオ構築ライブラリ（src/kabusys/portfolio/*）
  - 候補選定、等比率・スコア加重による重み計算（portfolio_builder.py）
  - セクター集中制限（apply_sector_cap）、レジームに応じた乗数 calc_regime_multiplier（risk_adjustment.py）
  - 銘柄ごとの株数計算・リスクベース配分・単元丸め・aggregate cap スケーリング（position_sizing.py）
    - lot_size、cost_buffer を考慮した投下金額スケールダウンロジックを実装

- ユーティリティ類
  - 共通ログ設定ユーティリティ（src/kabusys/utils/logging_setup.py）
    - stdout への StreamHandler と日次ローテーション FileHandler（TimedRotatingFileHandler）をルートロガーに設定
    - LOG_DIR の作成失敗時はファイル出力をスキップしてコンソール出力にフォールバック
  - プロセス優先度 / CPU affinity 設定ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows / POSIX（Linux, macOS, FreeBSD）に対応した優先度設定と CPU affinity の API を提供。psutil の実行権限不足時は警告を出してスキップ

- Paper Trading 検証レポート生成ツール（src/kabusys/tools/paper_verification_report.py）
  - system_status / trade_logs / risk_logs を集計して稼働率・注文成功率・送信率・レイテンシ（P95 等）を算出し、閾値に基づく PASS/FAIL 判定を出力
  - CLI オプションで期間指定 (--from / --to) と DB パス指定 (--db) に対応

- 研究用ファクター計算の骨格（src/kabusys/research/factor_research.py）
  - モメンタム・ボラティリティ等の計算仕様と定数を定義（DuckDB 接続を受ける設計）

Changed
- ログの出力先を標準化（stdout 使用）し、運用環境でのログ収集に配慮
- .env 読み込みの優先順位を明確化（OS 環境 > .env.local > .env）し、テスト用途で自動ロードを無効化するフラグを追加（KABUSYS_DISABLE_AUTO_ENV_LOAD）

Fixed
- 環境変数パーサーの不具合修正（export 接頭辞、クォート/エスケープ、コメント処理）により .env の多様な記法を正しく扱うようになった

Deprecated
- なし

Removed
- なし

Security
- なし


[0.1.0] - 2026-04-24
-------------------
Initial release — 基本機能の実装

Added
- プロジェクトの初期バージョンを追加
  - バージョン情報: src/kabusys/__init__.py の __version__ = "0.1.0"
- 実行系・監視系の主要コンポーネントを実装
  - ExecutionEngine 起動フロー（ブローカーファクトリ、OrderRepository、OrderManager、RiskManager、Reconciler 組み立て）
  - SystemMonitor と監視ループ起動スクリプト
  - DB 初期化ユーティリティ（監視テーブルの冪等初期化）
- 設定管理・運用支援ツール
  - Settings クラス、.env ウィザード、設定検証 CLI
- ポートフォリオ構築アルゴリズム群（選定・重み付け・リスク調整・株数算出）
- ロギング・プロセス制御ユーティリティ
- Paper Trading 向け検証レポートツール
- 研究用ファクター計算の基盤（DuckDB ベース設計）

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Notes / Known issues and TODOs
- risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少見積になる旨の注記あり。将来的に前日終値等のフォールバック価格を導入予定。
- position_sizing: lot_size を銘柄ごとに持たせる拡張（stocks マスタに lot_size を追加する等）が TODO。
- research.factor_research.calc_momentum はファイル末尾で実装途中（スケルトン）に見えるため、実装継続の必要あり。

ライセンス・配置
- .env は絶対に Git にコミットしない旨の注意を config_setup に明示。

補足
- 本 CHANGELOG はコードベース内のコメント・実装内容から推測して作成しています。実際のリリースノートや変更履歴として公開する前に、プロジェクトの意図・リリースポリシーに合わせて適宜修正してください。