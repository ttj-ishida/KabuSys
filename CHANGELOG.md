# Changelog

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。  
このファイルは、コードベースから推測可能な機能追加・振る舞い・改善点を基に作成した初期リリースの変更履歴です。

全般
- 初期バージョンのリリース。コア機能（設定管理、実行/監視スクリプト、ポートフォリオ構築、ユーティリティ、検証/ウィザード、ペーパートレード検証ツール、リサーチ用ファクタ計算）を実装。

## [0.1.0] - 2026-04-20

### Added
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading のときは paper_trading 専用 SQLite を使用し、本番 DB と完全分離する挙動を実装。
    - 起動前にプロセス優先度を "high" に設定。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル管理による安全な起動/停止手順を採用。
    - スレッドでエンジンを起動し、停止フラグ検知でエンジン停止を実行。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ検出・例外捕捉・KeyboardInterrupt による安全終了を実装。

- 設定管理
  - config.py: Settings クラスを導入し、環境変数からの設定取得を統一。
    - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env / .env.local の読み込み順序（OS 環境変数を保護）を実装。
    - J-Quants・kabu・DB パス・ログレベル・Kill Switch 等の設定プロパティを提供。
    - PAPER_FILL_MODE の入力検証（有効値チェック）などの堅牢化。
  - config_setup.py: 対話式ウィザードで .env を初期生成/更新する CLI を追加。
    - 必須項目/オプション項目のプロンプト、シークレット値のマスク、保存前の確認などを実装。
    - .env の書き出しテンプレートに注意書きを含む（.env を Git にコミットしない旨）。

- 設定検証
  - validate_config.py: 起動前チェック用 CLI を実装。
    - 必須環境変数、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・パース検査（PyYAML が存在する場合）等を実行。
    - --strict モードで警告をエラー扱いにできる。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順で候補抽出（タイブレークは signal_rank）。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分の実装（スコア全て 0 の場合はフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存保有を考慮し、上限超過セクターの新規候補を除外）。
    - calc_regime_multiplier: 市場レジーム ("bull","neutral","bear") に応じた投下資金乗数を提供（未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: 発注株数計算ロジックを実装。
      - allocation_method: "risk_based" / "equal" / "score" に対応。
      - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金を超える場合のスケーリング）、cost_buffer を使った保守的コスト見積り、余剰キャッシュを用いた端数配分のアルゴリズムを実装。

- モニタリング & DB 初期化
  - スクリプト実行時に監視テーブルの初期化を保証する init_monitoring_db 呼び出しを導入（冪等）。

- ツール
  - tools/paper_verification_report.py: ペーパートレード向け検証レポート生成ツールを追加。
    - 稼働率、注文成功率（fill rate）、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計して PASS/FAIL 判定する。
    - 日付フィルタ (--from / --to) と DB パス指定 (--db / 環境変数) をサポート。
    - デフォルト閾値（稼働率 99%、fill rate 90%、送信率 95%、P95 200ms）を設定。

- リサーチ（ファクター計算）基盤
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールの骨組みを追加（Momentum, Value, Volatility, Liquidity を想定）。
    - calc_momentum 周辺の定数や P95 計算ユーティリティ等を実装（DuckDB 接続を受ける設計）。

- ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。
    - コンソール出力は stdout、ファイル出力は日次ローテート（TimedRotatingFileHandler、30日保持）。
    - 既存ハンドラの重複防止のためクリアしてから再設定。LOG_DIR / LOG_LEVEL の解決順を実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: プロセス優先度および CPU affinity のユーティリティ。
    - Windows / POSIX の差分を吸収（psutil ベース）、アクセス拒否時は警告を出してスキップ。
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(n) を提供。

### Changed
- なし（初期リリース）

### Fixed
- なし（初期リリース）

### Security
- .env の生成スクリプトに「.env を絶対に Git にコミットしない」旨の注意書きを明記。

### Notes / Known limitations
- research/factor_research.py はファクター計算の実装骨格を含むが、すべての計算ロジックが完全実装されているわけではなく、DuckDB 上のテーブル構成（prices_daily, raw_financials 等）に依存する。
- position_sizing の価格取得が欠損（0.0）だとエクスポージャー評価や発注量が過少見積りされる可能性がある旨の TODO コメントあり（フォールバック価格の導入を検討）。
- process_priority / cpu_affinity はプラットフォームと権限に依存し、失敗時は警告を出して処理を続行する設計。
- monitoring は明示的に本番用 sqlite_path を使用するため、環境設定と DB 運用に注意が必要。

---

今後のリリース候補（例）
- ファクター計算の完全実装（momentum/value/volatility/liquidity）および関連ユニットテスト追加
- ExecutionEngine / BrokerClientFactory の詳細実装（モックブローカや実ブローカの差分テスト）
- モニタリング・アラート送信（LINE 通知）実装の拡張
- 単体テスト・統合テスト・CI 設定の追加

（この CHANGELOG はコードから推測して作成しています。実際のリリース管理や差分はリポジトリのコミット履歴に基づいて更新してください。）