# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ （日本語訳に準拠）

注意: 以下の履歴は提示されたソースコードから推測して作成したリリースノートです。実際のコミット履歴がある場合はそれに基づき調整してください。

## [0.1.0] - 2026-04-19

初回公開リリース。本リリースでは自動売買システム KabuSys のコアユーティリティ、設定管理、起動スクリプト、ポートフォリオ構築ロジック、検証/運用支援ツールが実装されています。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 起動スクリプト
  - `run_execution.py`
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - プロセス優先度を "high" に設定し、バックグラウンドスレッドでエンジンを実行。
    - 停止制御用フラグファイル（data/stop_requested.flag）と PID ファイル（data/execution.pid）を使用。
    - KABUSYS_ENV が `paper_trading` の場合はペーパートレード用 SQLite（デフォルト: `data/paper_trading.db`）を使用し、本番 DB と分離。
    - BrokerClient の抽象化（BrokerClientFactory）により実運用/ペーパートレードを切り替え可能。
    - RiskManager、OrderManager、Reconciler を組み合わせて ExecutionEngine を構成。RiskConfig のデフォルト値を定義（例: max_position_pct=0.20 など）。

  - `run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視用 DB（SQLite）と分析用 DuckDB への接続を初期化。monitoring は環境にかかわらず本番 sqlite_path を使用する設計となっている。
    - 停止フラグファイル検知でループ終了、KeyboardInterrupt の捕捉処理あり。

- 設定管理 / ユーティリティ
  - `config.py`
    - 環境変数/`.env` の自動読み込み機能を実装（プロジェクトルートは `.git` または `pyproject.toml` を起点に探索）。
    - `.env` のパースはクォート、export プレフィックス、インラインコメント（スペース/タブ直前の `#`）などに対応。
    - 設定取得用 `Settings` クラスを実装。J-Quants、kabu API、DB パス、PID/kill フラグ、閾値（CPU/MEM/DISK）などのプロパティを提供。
    - `PAPER_FILL_MODE` のバリデーション（有効値: "instant" | "partial" | "never" | "reject"）。
    - `is_live` / `is_paper` / `is_dev` の判定プロパティ。

  - `config_setup.py`
    - 対話式ウィザードで `.env` を生成・更新する CLI を追加。各設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE トークン等）を対話形式で収集・保存。
    - 既存 `.env` の読み込みと Enter による既存値再利用、シークレット項目のマスク表示をサポート。

  - `validate_config.py`
    - 起動前検証用 CLI を追加。必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、`config/*.yaml` の存在/パースチェック（PyYAML がある場合）などを実施。
    - `--strict` オプションで警告を失敗扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - `utils/logging_setup.py`
    - 統一ロギング初期化関数 `setup_logging` を追加。
    - stdout への StreamHandler（標準出力）と、日次ローテーション（TimedRotatingFileHandler）でのファイル出力を組み合わせたデフォルト構成を提供。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
    - ログレベル解決順（引数 > 環境変数 LOG_LEVEL > デフォルト）。

  - `utils/process_priority.py`
    - プロセス優先度設定ユーティリティを追加（Windows / POSIX 差分を吸収）。
    - `set_process_priority(level)`： "high" / "normal" / "low" をサポート。権限不足などで失敗した場合は警告を出力してスキップ。
    - `set_cpu_affinity(cpu_count)`：カレントプロセスを先頭 N コアにピン留め（未対応環境では警告を出力してスキップ）。

- ポートフォリオ構築ロジック（純粋関数群）
  - `portfolio/portfolio_builder.py`
    - 候補選定 `select_candidates`（スコア降順、同点は signal_rank でタイブレーク）。
    - 重み計算 `calc_equal_weights`（等分配）、`calc_score_weights`（スコア正規化、全銘柄スコアが 0 の場合は等分配にフォールバック）。

  - `portfolio/risk_adjustment.py`
    - セクター集中制限 `apply_sector_cap`：既存ポジションのセクター比率に基づき新規候補を除外。`unknown` セクターは上限適用外。
    - レジームに応じた乗数 `calc_regime_multiplier`： "bull" / "neutral" / "bear" をサポート。未知のレジームは 1.0 でフォールバック。

  - `portfolio/position_sizing.py`
    - 注文株数計算 `calc_position_sizes` を実装。以下をサポート:
      - allocation_method: "risk_based" / "equal" / "score"
      - ロット丸め（lot_size、デフォルト 100）
      - per-position 上限（max_position_pct）と aggregate cap（available_cash）によるスケーリング
      - cost_buffer による保守的見積り（スリッページ・手数料考慮）
      - 利用可能現金を超えた場合のスケールダウンと端数処理（lot 単位での再配分）

- 分析 / 検証ツール
  - `tools/paper_verification_report.py`
    - ペーパートレード用 SQLite DB を集計し、システム稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などのレポートを生成する CLI。
    - デフォルト閾値を定義して PASS/FAIL を判定:
      - 稼働率 >= 99.0%
      - 注文成立率（Fill rate） >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - 日付フィルタ（--from, --to）をサポート。DB が存在しない場合にエラーメッセージを出力。

- 監視 DB 初期化
  - `monitoring/monitoring_db.py`（参照されているが本体はソース断片に含まれず）を利用して起動時に監視用テーブルを冪等に初期化。

- 研究モジュール（初期）
  - `research/factor_research.py`
    - モメンタム等のファクター計算用モジュールのスケルトンを追加（DuckDB 接続を受け取り、prices_daily / raw_financials を参照する設計）。
    - 定数やインターフェイス説明、モメンタム指標（1M/3M/6M、MA200乖離）などの仕様を準備（実装の一部は未完）。

### Changed
- 設定自動ロードの挙動
  - `.env` 自動読み込みはプロジェクトルートが特定できない場合はスキップされる（配布環境で CWD に依存しない動作を想定）。

- `run_monitoring` の動作
  - 監視プロセスは環境にかかわらず monitoring DB の sqlite_path を使用して監視テーブルを保つ設計（運用・分析が環境に依存しないようにする意図）。

### Fixed
- 環境変数パースの堅牢化
  - `_parse_env_line` にてクォート内のバックスラッシュエスケープや export プレフィックス、コメント扱いの明確化を実装。これにより `.env` ファイルの多様な表記に対処。

- ロギング初期化時の二重ハンドラ問題に対応
  - `setup_logging` が既存ハンドラを一度 flush/close してから削除し、ログの重複出力を防止。

### Known issues / Notes / TODO
- price フォールバック:
  - `apply_sector_cap` にコメントで指摘があるように、price が欠損（0.0）の場合にエクスポージャーが過少見積もられる問題があり、前日終値や取得原価などのフォールバック価格の導入が検討課題として残っています。

- factor_research の未完実装:
  - `research/factor_research.py` は仕様・定数・関数スケルトンが存在するが、ファイル末尾で実装が途中で切れている（完全実装は別途必要）。

- monitoring の DB 選択ポリシー:
  - 監視は常に本番用 sqlite_path を使用するため、開発/ペーパートレード環境で監視データを分離したい場合は適宜設定やコードの変更が必要。

- 権限依存の機能:
  - `set_process_priority` / `set_cpu_affinity` は OS と実行権限に依存し、失敗時は警告を出して安全にスキップする設計。ただし期待通りに実行されない環境があり得ます。

### Security
- シークレット項目（J-Quants リフレッシュトークン、kabu API パスワード等）は `.env` に保存する設計だが、`config_setup.py` のコメントにある通り `.env` を Git にコミットしないことを強く推奨します。

---

今後の提案（想定）
- factor_research の完全実装とユニットテストの追加。
- monitoring と execution のログ/メトリクスを Prometheus/外部監視に連携するオプション追加。
- 銘柄ごとの lot_size をマスターデータから読み込むようにして position sizing を拡張。
- データ欠損時のフォールバック価格導入（apply_sector_cap の TODO 対応）。
- CI による lint / type check / unit tests の追加。

（以上）