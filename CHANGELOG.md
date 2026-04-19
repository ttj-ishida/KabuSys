# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従っています。  
このファイルは、提供されたコードベースの内容から推測して作成した変更履歴です（実コードのコミット履歴ではありません）。

## [Unreleased]

### Added
- 共通設定/環境変数管理
  - Settings クラスによる環境変数ラッパーを追加。J-Quants / kabu API / DB パス /ログ設定 /監視しきい値等をプロパティ経由で取得可能に。
  - 自動 .env 読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml）。.env と .env.local の取り扱い（OS 環境変数を保護しつつ上書き可能）。
  - .env のパース機能を強化: `export KEY=val` 形式、クォート内のエスケープ、インラインコメント扱い、空行やコメント行を無視。

- CLI / ユーティリティ
  - 環境設定ウィザード（kabusys.config_setup）を追加。対話形式で .env を初期作成・更新する機能を提供。
  - 設定検証 CLI（kabusys.validate_config）を追加。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在や YAML パース（PyYAML がある場合）などをチェック。`--strict` フラグで警告を失敗扱いにできる。
  - Paper Trading の検証レポート生成ツール（kabusys.tools.paper_verification_report）を追加。稼働率、注文成功率、送信率、レイテンシ(P95など)を集計し PASS/FAIL を判定。

- 起動スクリプト
  - 実行エンジン起動スクリプト（kabusys.run_execution）を追加。以下を含む:
    - プロセス優先度を高（High）に設定。
    - KABUSYS_ENV が paper_trading の場合は paper 用専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を用いた動的クライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
    - stop フラグ（data/stop_requested.flag）で安全に停止。
  - 監視ループ起動スクリプト（kabusys.run_monitoring）を追加。以下を含む:
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 環境にかかわらず本番 sqlite_path を使って監視 DB を初期化。
    - SystemMonitor.check_once を定期実行、例外はログに残してループ継続。

- ポートフォリオ構築（純関数群）
  - kabusys.portfolio モジュールを追加:
    - portfolio_builder: 候補選定 select_candidates、等金額 calc_equal_weights、スコア加重 calc_score_weights。
    - risk_adjustment: セクター集中制限 apply_sector_cap、レジーム乗数 calc_regime_multiplier（'bull'/'neutral'/'bear' をサポート、未知レジームは警告の上 1.0 でフォールバック）。
    - position_sizing: 投入株数計算 calc_position_sizes（risk_based / equal / score の allocation_method、lot_size 単位で丸め、aggregate cap によるスケールダウン、cost_buffer を考慮）。

- ロギング・プロセス管理ユーティリティ
  - ログ設定ユーティリティ（kabusys.utils.logging_setup）を追加。stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップして継続。
  - プロセス優先度設定ユーティリティ（kabusys.utils.process_priority）を追加。Windows / POSIX の差分を吸収して `set_process_priority(level)`（high/normal/low）を提供。CPU affinity 設定用の set_cpu_affinity も実装（権限や未対応 OS では警告を出してスキップ）。

- データベース / 分析
  - DuckDB 接続サポート（設定経由で duckdb_path を指定）。
  - 監視用 DB 初期化用ヘルパー（init_monitoring_db）を起動スクリプトから呼び出す設計を導入（冪等に監視テーブルを保証）。

- リサーチ（ファクター計算）
  - kabusys.research.factor_research を追加（Momentum, Value, Volatility, Liquidity を想定）。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計の骨子と定数を実装。
  - calc_momentum 関数の骨格を実装（対象日ベースで 1M/3M/6M リターン、MA200 乖離などを計算する意図）。（注: 一部実装途上の箇所あり）

### Changed
- packaging / メタ
  - パッケージバージョンを __version__ = "0.1.0" に設定（初期リリース相当）。

### Fixed
- .env 読み込みの堅牢性向上
  - ファイル読み込み失敗時に warnings.warn で通知して処理を継続するように改善。

### Documentation
- 各モジュールに日本語のドキュメンテーション文字列（docstring）を充実させ、設計方針・引数・返り値・使用例を明記。

### Known issues / Notes
- research.factor_research.calc_momentum はファイル末尾で実装が途中になっている箇所が確認される（スニペット終端の途切れ）。完全実装が必要。
- position_sizing / risk_adjustment にて価格欠損時（price が 0.0 や None）のハンドリングにコメントで注意が書かれている。将来的にフォールバック価格の導入を検討すること。
- process_priority/set_cpu_affinity は権限不足やプラットフォーム非対応時に設定できない可能性があり、警告を出してスキップする挙動。
- .env の自動ロードはプロジェクトルートが検出できない場合はスキップされる（CI / パッケージ配布後の挙動を考慮）。

---

## [0.1.0] - 2026-04-19

初期公開（コードベースの現状を反映）。上記「Added」項目のほとんどをこのリリースに含む想定。

- 基本機能:
  - 実行エンジン（ExecutionEngine）起動/制御スクリプト。
  - 監視ループ（SystemMonitor）起動スクリプト。
  - 設定ウィザードと検証ツール（.env生成 / 検証 CLI）。
  - Paper Trading 用検証レポートツール。
  - ポートフォリオ構築・リスク調整・サイズ計算の純粋関数群。
  - ロギング・プロセス優先度ユーティリティ。
  - DuckDB/SQLite を用いたデータアクセスの基盤。

- 互換性:
  - Paper Trading モードでは SQLite DB を本番 DB と完全分離（data/paper_trading.db を使用）。
  - 既存の OS 環境変数を保護する .env の読み込み仕様（.env.local は上書き可能だが OS 環境は保護）。

- その他:
  - README や外部ドキュメントはソースの docstring を参照のこと。
  - セキュリティ上 .env を Git 管理に含めない旨を強調するテンプレートを config_setup に含む。

---

保守・今後の予定（提案）
- research.factor_research の完全実装（ファクター計算の SQL/処理完成）。
- tests の追加（calc_position_sizes, apply_sector_cap, calc_score_weights 等のユニットテスト）。
- モニタリング・アラート（LINE 通知）との統合テストとドキュメント整備。
- 銘柄ごとの lot_size 対応（stocks マスタの導入）と手数料・スリッページモデルの改善。

---

（注）本 CHANGELOG は提供されたソースコードを解析して推測した変更履歴です。実際のコミット履歴やリリースノートと差異がある可能性があります。必要であれば、コミットログに基づく正確な CHANGELOG 生成も支援できます。