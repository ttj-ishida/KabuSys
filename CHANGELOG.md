# Changelog

すべての notable な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  
このプロジェクトでは SemVer を採用しています。

- フォーマット詳細: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-19

初回リリース。本リリースでは自動売買システム「KabuSys」のコア機能群および運用用ユーティリティを実装・追加しました。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを追加。バージョンを `__version__ = "0.1.0"` として設定。
- 起動スクリプト / デーモン
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）を監視し安全に停止。
    - Monitoring は環境にかかわらず本番用の sqlite_path を使用して監視情報を保存。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` 時は専用のペーパートレード用 SQLite（data/paper_trading.db を想定）を使用し、本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定し、停止フラグでエンジン停止。
    - 実行用 PID ファイル (data/execution.pid) を利用。
- 設定管理・検証
  - config.py
    - 環境変数・.env 読み込み機構を実装。
    - プロジェクトルート検出（.git または pyproject.toml を探索）に基づき自動で `.env` / `.env.local` を読み込む（自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
    - `.env` の行パースはクォート、エスケープ、インラインコメント（条件付き）等に対応。
    - Settings クラスを提供し、各種設定値（DB パス、API トークン、環境、閾値など）とバリデーションを行う。
    - `PAPER_FILL_MODE`, `KABUSYS_ENV`, `LOG_LEVEL` などの検証を実装。
  - config_setup.py
    - 対話式 .env ウィザードを追加。初期 .env の作成や既存値編集を支援。
    - 出力時に .env ファイルに注意書きを含める（.env をコミットしない旨）。
  - validate_config.py
    - 起動前に .env と config/*.yaml をチェックする CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、YAML パース（PyYAML が有効なら内容検証）および本番環境向けガード（LINE 設定、KILL_FLAG_CLEAR_ON_START）を実施。
    - `--strict` オプションで警告も失敗扱いに可能。
- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング設定ユーティリティを追加。
    - stdout へ StreamHandler（stdout を使用）と、日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log）を設定。
    - ログディレクトリの解決順・ログレベルの解決順を実装。ディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py
    - プラットフォーム差分（Windows / POSIX）を吸収するプロセス優先度設定ユーティリティを追加。
    - `set_process_priority(level)` で "high"/"normal"/"low" を設定。未対応 OS や権限不足時には警告を出して安全にスキップ。
    - `set_cpu_affinity(cpu_count)` によりプロセスの CPU affinity を設定可能（権限や環境に依存）。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - スコア全0 の場合は等配分へフォールバック（警告ログ出力）。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装。
    - 市場レジーム（bull/neutral/bear）に応じた投下資金乗数 calc_regime_multiplier を実装（未知レジームは 1.0 にフォールバック）。
    - 「unknown」セクターの扱いや既存保有の売却予定銘柄を除外するオプションをサポート。
  - portfolio/position_sizing.py
    - position sizing の純粋関数 calc_position_sizes を実装（allocation_method: risk_based / equal / score）。
    - 単元（lot_size）丸め、1銘柄上限、aggregate cap（available_cash 超過時のスケールダウン）、cost_buffer（手数料・スリッページ見積り）を実装。
    - aggregate スケールダウン時の残差配分ロジック（lot 単位）を実装。
- 解析 / レポート
  - tools/paper_verification_report.py
    - ペーパートレード用の検証レポート生成スクリプトを追加。
    - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH / --db で上書き可）。
    - システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計し PASS/FAIL 判定を出力。
    - 基準値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。
- 研究用モジュール（部分実装）
  - research/factor_research.py
    - DuckDB を利用したファクター計算基盤を追加。モメンタム（1M/3M/6M 等）、MA200 乖離、ATR、出来高指標等の計算を想定（関数の一部は実装途中/ファイル末尾は断片で終了）。
- その他
  - monitoring.monitoring_db の初期化呼び出し箇所を run_monitoring と run_execution に追加（監視テーブルの冪等初期化を保証）。
  - ExecutionEngine 周辺で BrokerClientFactory を用いた broker の抽象化を採用（paper_trading 時は MockBrokerClient を想定）。

### 変更 (Changed)
- なし（初回リリースのため新規実装中心）

### 修正 (Fixed)
- なし（初回リリース）

### セキュリティ (Security)
- 環境設定ウィザードおよび .env 書き込みで「.env を Git にコミットしない」旨の注意を明示。

### 既知の制限 / 注意事項 (Notes / Known limitations)
- research/factor_research.py は実装途中の箇所が含まれる（ファイル末尾が切れている／未完）。
- risk_adjustment.apply_sector_cap:
  - price_map に欠損 (0.0) がある場合、エクスポージャーが過小見積もられる可能性がある点を TODO コメントで指摘。将来的に前日終値等でフォールバックすることを想定。
- position_sizing.calc_position_sizes:
  - 現状は全銘柄共通の lot_size（デフォルト 100）を想定。将来的に銘柄別 lot_map に拡張する予定。
- ログディレクトリ作成やプロセス優先度設定は権限に依存し、失敗時は警告ログを出してフォールバックする設計。
- validate_config の YAML 検証は PyYAML の有無に依存。未インストール時は内容検証をスキップして警告を出す。

---

今後の予定（例）
- factor_research の完全実装（Value/Volatility/Liquidity 等のファクター計算と z-score 正規化）
- ExecutionEngine / BrokerClient の詳細実装と統合テスト
- 単体テスト・E2E テストの追加、CI ワークフロー整備
- 銘柄別 lot_size サポート、価格フォールバックロジック強化

（この CHANGELOG はコードベースの現状から推測して作成しています。実際の変更履歴やリリース日などはプロジェクト運用方針に合わせて調整してください。）