# Changelog

すべての変更は Keep a Changelog の形式に準拠します。  
主にコードベースから推測できる追加・修正・設計上の注意点を記載しています。

## [Unreleased]

- research/factor_research.py の実装が途中のため、ファクター計算モジュールは未完成（スキャフォールドのみ）。今後のリリースで続きを実装予定。
- 一部 TODO コメントあり（price フォールバックや銘柄毎 lot_size の拡張など）。

---

## [0.1.0] - 2026-04-21

概要: KabuSys の初期リリース（0.1.0）。日本株自動売買システムのコア機能群（起動スクリプト、設定管理、ポートフォリオ構築、発注/実行基盤の骨格、監視、ユーティリティ、Paper Trading 検証ツールなど）を含む。

### Added
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、DB 接続、Broker クライアント生成、エンジンの起動・停止監視（stop フラグ検出）、実行 PID 管理を実装。
  - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ検出でループ終了。
- 設定管理
  - config.py: 環境変数ラッパー Settings クラスを実装。.env ファイルの自動ロード機構（プロジェクトルート検出）と保護付き上書きロジック、各種設定プロパティ（DB パス、KABUSYS_ENV、LOG_LEVEL、paper_trading 用設定、監視閾値など）を提供。
  - config_setup.py: 対話式ウィザードで .env を作成・更新する CLI を追加。シークレットマスク表示、選択肢サポート、保存前確認を実装。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV 検証、パス存在チェック、config/*.yaml の存在・パース検証（PyYAML 利用時）、本番環境向けのガードを実装。--strict フラグで警告をエラー扱いにできる。
- データベース連携
  - duckdb と sqlite の併用を前提とした接続処理を各スクリプトで導入（duckdb は分析用、sqlite は監視/発注記録用）。
  - monitoring 用 DB 初期化を保証する init_monitoring_db 呼び出し（冪等）。
  - Paper Trading 時は sqlite ファイルを本番 DB と分離（デフォルト data/paper_trading.db）。
- 実行・発注基盤（骨格）
  - execution パッケージの組み立て（BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager 等）を統合。RiskManager にデフォルト構成を与え、ExecutionEngine は PID ファイル・停止フラグ管理・スレッド実行を行う設計。
  - BrokerClientFactory は KABUSYS_ENV=paper_trading の場合に MockBrokerClient を使い、Paper Trading DB に記録する想定（コード中コメント）。
- 監視
  - SystemMonitor（monitoring パッケージ）をポーリングで動作させ、システム状態を monitoring DB に記録する想定。run_monitoring は常に production 用 sqlite_path を使用する設計。
- ポートフォリオ構築（純粋関数）
  - portfolio パッケージを追加:
    - portfolio_builder.select_candidates: スコア降順で候補選択（タイブレークに signal_rank を利用）。
    - portfolio_builder.calc_equal_weights / calc_score_weights: 重み計算（スコア全 0 の場合は警告を出して等金額にフォールバック）。
    - risk_adjustment.apply_sector_cap: セクター集中上限をチェックし候補を除外（unknown セクターは無視）。当日売却予定銘柄を除外して計算。
    - risk_adjustment.calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金乗数を提供。未知レジームは警告を出してフォールバック（1.0）。
    - position_sizing.calc_position_sizes: 複数の配分方式（risk_based / equal / score）に対応し、単元株（lot_size）で丸め、aggregate cap（available_cash）に応じたスケーリングと端数配分ロジックを実装。コストバッファ（手数料・スリッページ見積）考慮。
- ユーティリティ
  - utils/logging_setup.py: ルートロガーに対する統一的セットアップを実装。console (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定。既存ハンドラをクリアして重複設定を防止。ログディレクトリ作成に失敗した場合はファイル出力を無効にして継続。
  - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX）でプロセス優先度（nice / Windows 優先度）と CPU affinity を設定するユーティリティ。アクセス拒否時には警告出力でスキップ。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などを集計し、閾値に対する PASS/FAIL 判定を出力。P95 計算、日付フィルタ機能、DB パス決定ロジック（コマンド引数 > 環境変数 > デフォルト）を実装。
- パッケージ情報
  - __init__.py にてパッケージバージョン __version__ = "0.1.0" を設定。

### Changed
- （初版リリースのため「追加」が中心。設計上の決定を記載）
  - .env 自動ロードはプロジェクトルート検出に基づき実行され、OS 環境変数は保護（上書きしない）する実装。`.env.local` は `.env` の上書きとして読み込まれる。
  - run_monitoring は環境（KABUSYS_ENV）にかかわらず監視用に production の sqlite_path を使う設計（監視は本番 DB を参照する方針）。

### Fixed / Robustness improvements
- .env パーサ: クォート文字列内のバックスラッシュエスケープ対応、export プレフィックス対応、インラインコメントの扱い改善などを実装し、より堅牢に行をパースできるようにした。
- MONITOR_POLL_INTERVAL の読み取りで不正値（非数・0 以下）に対するフォールバックと警告を追加。time.sleep に渡す不正値による例外回避。
- logging_setup: 既存ハンドラの二重設定を回避するため、初期化時に既存ハンドラを flush/close して削除する実装を導入。
- process_priority: 未対応 OS や権限不足でも安全にスキップし、詳細な警告を出すよう改善。
- DB 初期化: init_monitoring_db は冪等に呼べる（存在確認などを想定）ため、起動順序に依存せず安全に実行可能。

### Security
- config_setup と設定確認画面でシークレット項目（トークン・パスワード）を表示する際はマスク（****）を利用。
- .env のヘッダに「.env は絶対に Git にコミットしないこと」を明記。

### Notes / Known limitations
- research/factor_research.py は途中実装（行末でカットオフ）。ファクター計算関数群は設計方針・定義済みだが、完全な実装は今後のリリースで追加予定。
- position_sizing や apply_sector_cap の一部ロジックは価格欠損時のフォールバック（前日終値など）について TODO コメントあり。将来の改善予定。
- Paper Trading と本番 DB の分離はファイルパスベースで切り分けている（環境変数で制御）。運用時は適切に .env を設定すること。

---

今後の予定（推測）
- factor_research の完成（ファクター計算の SQL/DuckDB 実装完了）
- ExecutionEngine / RiskManager の詳細ロジックとエンドツーエンドの統合テスト追加
- 銘柄別 lot_size や価格フォールバックの強化
- 監視・アラートの LINE 連携（LINE トークン設定がある場合）

（以上）