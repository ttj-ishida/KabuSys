CHANGELOG
=========

この CHANGELOG は Keep a Changelog の形式に準拠しています。  
以下は提供されたソースコードから推測して作成した変更履歴です（自動生成／推測に基づくため実際のコミット履歴と差異がある可能性があります）。

Unreleased
----------

### Added
- さまざまなユーティリティと起動スクリプトの改善予定（詳細は TODO/今後の改善点参照）。
- 単体テスト・ドキュメント強化の計画。

### Changed
- なし（初期リリース以降の差分は未反映）。

### Fixed
- なし（初期リリース以降の差分は未反映）。

0.1.0 - 2026-04-19
------------------

### Added
- パッケージ初期リリース: kabusys v0.1.0
  - 日本株自動売買システムのコア機能群を提供（モジュール分割された実装）。

- 起動スクリプト / ランナー
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）検知でループ終了。
    - Monitoring は KABUSYS_ENV にかかわらず production 用 sqlite_path を使用する挙動。
    - check_once() 実行時の例外をログに出力してポーリングを継続する耐障害処理を実装。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ（data/stop_requested.flag）や実行 PID ファイル（data/execution.pid）による制御を実装。
    - スレッドで ExecutionEngine を実行し、停止フラグ検知で安全停止。

- 設定・環境変数管理
  - config.py
    - Settings クラスを実装し、環境変数から各種設定を取得する API を提供。
    - .env 自動ロード（.env → .env.local、OS 環境変数保護）を実装（無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を用意）。
    - .env パースは export 形式・クォート・インラインコメントを考慮して堅牢に実装。
    - 各種設定値の検証（PAPER_FILL_MODE の許容値チェック、KABUSYS_ENV の許容値チェック、LOG_LEVEL の検証など）。

  - config_setup.py
    - 対話式 .env 作成ウィザードを実装。
    - デフォルト値表示、シークレット入力マスク、選択肢検証、.env の書き込み（テンプレート付き）をサポート。

  - validate_config.py
    - 起動前に .env と config/*.yaml を検証する CLI を追加。
    - 必須環境変数のチェック、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ確認、YAML パース（PyYAML が存在する場合）の検証、live 環境向け追加ガードなどを実装。
    - --strict オプションで警告を失敗扱いにできる。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。
    - スコア全てが 0.0 の場合に等金額配分へフォールバックするロジックと警告。

  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を追加（当日売却予定の銘柄を除外可）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を追加（bull/neutral/bear をマップ、未知はフォールバックして 1.0）。

  - portfolio/position_sizing.py
    - position sizing ロジック calc_position_sizes を追加。
    - allocation_method に "risk_based" / "equal" / "score" をサポート。
    - 単元（lot_size）で丸め、1 銘柄上限・集計上限（available_cash）を考慮したスケーリング処理を実装。
    - cost_buffer を用いた保守的なコスト推定と残差配分ロジック（端数処理）を実装。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加。
    - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を SQLite DB から集計。
    - 閾値（稼働率 99% など）に基づく PASS/FAIL 判定を出力。
    - P95 計算ロジックを実装。

- ユーティリティ
  - utils/logging_setup.py
    - setup_logging ユーティリティを追加。
    - stdout (StreamHandler) と日次ローテーションファイルハンドラ (TimedRotatingFileHandler) をルートロガーに設定。
    - LOG_LEVEL・LOG_DIR 経由での設定、ログディレクトリ作成失敗時のフォールバックをサポート。
    - stdout を利用するデザイン（cron 等での stdout/stderr 集約を考慮）。

  - utils/process_priority.py
    - set_process_priority（Windows / POSIX の差分吸収）を実装（psutil を利用）。
    - set_cpu_affinity を実装（最初の N コアにプロセスをピン留め）。
    - 権限不足や未対応 OS では警告を出し安全にスキップ。

- リサーチ（骨組み）
  - research/factor_research.py
    - DuckDB を用いたファクター計算モジュールの骨組みを追加（モメンタム、MA200、ATR、流動性等を想定）。
    - calc_momentum 関数などの実装を開始（ソースは途中で切れている箇所あり）。

### Changed
- パッケージ初期化
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

### Fixed / Hardened
- ロギング・ファイル作成失敗時のフォールバック（ファイル出力に失敗してもコンソールログを継続）。
- Process priority / CPU affinity 設定で権限エラーや未サポート OS の場合に警告でスキップするよう堅牢化。
- ポーリングループやレポート生成など、DB スキーマが存在しない／クエリが失敗した場合に例外を吸収して継続する防御的実装（OperationalError の捕捉など）。

### Removed
- なし。

### Notes / Known issues / TODO
- apply_sector_cap 内で price が 0.0 の場合にエクスポージャーが過少見積もられる注記あり。前日終値や取得原価などのフォールバック価格の導入が検討課題。
- position_sizing の単元（lot_size）は現状グローバル固定（デフォルト 100）。将来的には銘柄ごとの lot_size を stocks マスタで管理する拡張を検討中（TODO コメントあり）。
- research/factor_research.py の calc_momentum 実装はソースが途中で切れている（未完了）。リサーチ機能は骨組みがあるが追加実装が必要。
- monitoring は環境にかかわらず本番 sqlite_path を使用する設計であるため、paper_trading 用 DB と完全に分離したい場合は注意が必要。
- KILL_FLAG_CLEAR_ON_START の設定（特に本番環境で 1 を設定すると危険）について validate_config で警告を出す実装あり。
- PAPER_FILL_MODE に対する厳密な検証がある（instant/partial/never/reject）。不正な値は例外を発生させる。
- P95 計算は単純なインデックス方式で実装されている（仕様上の妥当性確認が必要）。

Security
--------
- 重要なシークレット（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD）は .env に平文で保存する設計のため、.env の Git 管理禁止を README/コメントで明記（config_setup.py でも注記）。運用時はアクセス管理・OS レベルの環境変数利用を検討してください。

参考（コードベースから読み取れる運用制約）
- 起動スクリプトは開始直後にプロセス優先度を high に設定するため、権限やポリシーに注意。
- ログはデフォルトで logs/<app_name>.log に日次ローテートで保存（logs ディレクトリ作成に失敗した場合はコンソールのみ）。
- Paper Trading と Live の DB 分離が考慮されているが、一部（monitoring）は環境に依らず production DB を参照する設計になっている箇所があるためデプロイルールを明確にすること。

今後の提案（推奨改良点）
- research モジュールの完成（calc_momentum の完実装、value/volatility/liquidity の実装）。
- price フォールバック・銘柄別 lot_size 対応。
- DB マイグレーション・バージョン管理（schema 管理）導入。
- 単体テスト・CI パイプラインの整備。
- ドキュメント（運用手順、デプロイ手順、アラート設定）の充実。

---------
（この CHANGELOG はソースコードのコメントおよび実装内容から推測して作成しています。実際のコミット履歴やバージョン管理タグが存在する場合は、そちらを正式な履歴として利用してください。）