# CHANGELOG

すべての注目すべき変更点を記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-04-18
初回リリース。

### Added
- 実行スクリプトを追加
  - run_execution.py: ExecutionEngine を起動する CLI。環境に応じてペーパートレード用の MockBrokerClient を使用し、ペーパートレード時は別DB（data/paper_trading.db）で運用する仕組みを追加。
    - ファイル: src/kabusys/run_execution.py
    - 特徴: 起動時にプロセス優先度を「high」に設定、停止フラグ検知で安全に停止、PIDファイル管理。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - ファイル: src/kabusys/run_monitoring.py
    - 特徴: 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグでループ終了。監視は環境に関わらず本番用 sqlite_path を使用。

- 設定・環境関連
  - Settings クラスを導入し、環境変数や .env を統一的に扱う API を提供。
    - ファイル: src/kabusys/config.py
    - サポート項目: J-Quants / kabuAPI / LINE / DB パス / 監視閾値 / 実行環境 等。
    - 機能: PAPER_FILL_MODE の妥当性チェック、KABUSYS_ENV / LOG_LEVEL の検証、paper_trading 用 DB パス分離など。
  - .env 自動読み込み機能を追加
    - 優先順位: OS 環境変数 > .env.local > .env（プロジェクトルートが検出可能な場合）
    - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD`
    - .env パーサーは export 形式、クォート、インラインコメント等に対応。
    - ファイル: src/kabusys/config.py

- 設定支援ツール
  - config_setup.py: 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。
    - ファイル: src/kabusys/config_setup.py
    - 入力項目定義や既存 .env の読み込み・マスキング表示、保存確認までを提供。
  - validate_config.py: 起動前に .env と config/*.yaml の設定不備を検出する検証 CLI を追加。
    - ファイル: src/kabusys/validate_config.py
    - 特徴: 必須環境変数チェック、パスの親ディレクトリ存在チェック、YAML のパース検査（PyYAML が無ければスキップ）、本番環境向けの追加ガード、`--strict` オプションで警告を FAIL 扱いに可能。

- ログ・プロセスユーティリティ
  - logging_setup.py: 統一的なログ設定ユーティリティを追加。
    - ファイル: src/kabusys/utils/logging_setup.py
    - 特徴: stdout への StreamHandler と 日次ローテーションの TimedRotatingFileHandler（30 日保持）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力を自動的に回避してコンソール出力のみで継続。
  - process_priority.py: クロスプラットフォームのプロセス優先度／CPU affinity 設定ユーティリティを追加。
    - ファイル: src/kabusys/utils/process_priority.py
    - 特徴: Windows / POSIX(nice) を吸収。権限不足や未対応 OS の場合は警告を出してスキップ。CPU affinity 固定機能も提供。

- ポートフォリオ構築関連（純関数群）
  - portfolio_builder.py: 候補選定・重み算出を実装（等分配・スコア重み）。
    - ファイル: src/kabusys/portfolio/portfolio_builder.py
  - risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）を実装。
    - ファイル: src/kabusys/portfolio/risk_adjustment.py
    - 特記事項: unknown セクターは上限適用除外、レジームに対する乗数マップ（bull/neutral/bear）を定義。
  - position_sizing.py: 株数算出（risk_based / equal / score）、単元株丸め、aggregate cap によるスケールダウンと端数配分ロジックを実装。
    - ファイル: src/kabusys/portfolio/position_sizing.py
    - 特徴: cost_buffer を考慮した保守的推定、lot_size 単位での丸め、残余キャッシュでの追加配分アルゴリズムを実装。
  - portfolio パッケージのエクスポートを整理。
    - ファイル: src/kabusys/portfolio/__init__.py

- 研究・分析ツール
  - tools/paper_verification_report.py: ペーパートレード結果の検証レポート生成スクリプトを追加。
    - ファイル: src/kabusys/tools/paper_verification_report.py
    - 機能: 稼働率（uptime）、注文成功率（fill）、送信率（send）、レイテンシ（P95）などを集計し PASS/FAIL 判定を行う。期間指定（--from/--to）と DB パス指定（--db）に対応。閾値定義付き。
  - research/factor_research.py: ファクター計算モジュールの骨組みを追加（モメンタム、MA200、ATR、流動性等の計算方針）。
    - ファイル: src/kabusys/research/factor_research.py
    - 注意: 実装は継続中（スニペット末尾で未完の箇所あり）。

- パッケージ基本情報
  - __version__ を 0.1.0 に設定。
    - ファイル: src/kabusys/__init__.py

### Changed
- 監視用 DB の使用方針を明確化
  - run_monitoring は KABUSYS_ENV に関係なく「本番 sqlite_path」を使用して監視テーブルを操作する設計になっている点を明示（運用上の注意）。

- ログの標準出力挙動
  - StreamHandler を stdout に向けることで cron / Task Scheduler からの起動時に stdout/stderr リダイレクトを容易に。

### Fixed / Robustness improvements
- .env パーサーの堅牢化
  - export 句、単・二重クォート内のバックスラッシュエスケープ、インラインコメントの扱いなどに対応してより現実的な .env フォーマットをパース可能にした。
  - ファイル: src/kabusys/config.py

- ログディレクトリ作成失敗時のフォールバック
  - logging_setup はログディレクトリ作成に失敗しても StreamHandler のみで継続するようにし、例外で落ちないようにした。
  - ファイル: src/kabusys/utils/logging_setup.py

- プロセス優先度／CPU affinity 設定のフォールバック
  - 未サポート環境や権限エラー時に警告を出しつつ処理を続行するように改善。
  - ファイル: src/kabusys/utils/process_priority.py

### Known issues / Notes
- research/factor_research.py の実装は途中で終わっている箇所があり（スニペット末尾の未完部分）、完全なファクター計算は未完。実運用前に実装完了とテストが必要。
- position_sizing の価格欠損時の挙動について注記あり（price が 0.0 の場合にエクスポージャーが過少見積もられる可能性）。将来的にフォールバック価格導入を検討中。
- run_monitoring が本番 DB を参照する仕様は意図的だが、開発環境でのテスト時には注意が必要（監視テーブル初期化の冪等性は確保）。

---

この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴やリリースノートと差分がある場合は、正確な履歴に基づいて適宜修正してください。