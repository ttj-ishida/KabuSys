# Changelog

すべての注目すべき変更はこのファイルで管理します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用します。

## [0.1.0] - 2026-04-25

初回リリース。KabuSys のコアユーティリティ、実行/監視スクリプト、設定ツール、ポートフォリオ構築ロジック、検証ツール群を追加。

### Added
- 基本パッケージ情報
  - src/kabusys/__init__.py にパッケージバージョンを追加（__version__ = "0.1.0"）。

- 環境設定・読み込み
  - Settings クラスを追加（src/kabusys/config.py）。
    - .env/.env.local の自動読み込み（プロジェクトルートの検出: .git / pyproject.toml）。
    - 必須/任意の環境変数定義、値検証（KABUSYS_ENV, LOG_LEVEL など）。
    - デフォルトのパス設定（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH 等）。
    - Paper Trading 向け設定（paper_fill_mode のバリデーション等）。
  - .env パース機能を強化:
    - export KEY=VAL 形式対応、シングル/ダブルクォート内のエスケープ処理、インラインコメントルール等を実装。

- 設定補助 CLI
  - 環境設定ウィザード: src/kabusys/config_setup.py
    - 対話式で .env を作成/更新するウィザードを追加。
    - デフォルト値表示、シークレットマスク表示、保存確認、.env 書き込み機能。
  - 設定検証ツール: src/kabusys/validate_config.py
    - .env と config/*.yaml の存在・基本整合性チェックを実行する CLI。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パス親ディレクトリチェック、YAML パースチェック（PyYAML 未インストール時はスキップ）。
    - KABUSYS_ENV=live に対する追加の安全ガード（LINE 設定や KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict モードで警告を FAIL 扱いにする機能。

- 実行 / 監視用エントリポイント
  - 実行エンジン起動スクリプト: src/kabusys/run_execution.py
    - 起動時にプロセス優先度を high に設定。
    - KABUSYS_ENV=paper_trading 時は paper 用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を利用してブローカークライアント作成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine を起動（スレッド実行）。停止フラグ（data/stop_requested.flag）検知で安全停止。
  - 監視ループ起動スクリプト: src/kabusys/run_monitoring.py
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告。
    - 監視は環境にかかわらず本番 sqlite_path を使用（設計上の注意点）。
    - stop flag ファイル検知でループ終了。例外発生時は例外ログを出力して次回ポーリングへ継続。

- ロギング / プロセス管理ユーティリティ
  - ログ設定ユーティリティ: src/kabusys/utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定。
    - ログレベル/ログディレクトリの解決順序や、ディレクトリ作成失敗時のファイル出力スキップ処理を実装。
  - プロセス優先度/CPU affinity: src/kabusys/utils/process_priority.py
    - Windows / POSIX の差分を吸収してプロセス優先度を設定（high/normal/low）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - 権限不足や未対応 OS の場合は警告を出してスキップ。

- ポートフォリオ構築関連（純粋関数群）
  - 銘柄選定・重み付け: src/kabusys/portfolio/portfolio_builder.py
    - select_candidates（スコア降順で上位 N を選択）、calc_equal_weights、calc_score_weights（スコア合計が 0 の場合は等配分にフォールバック）。
  - セクター制限・レジーム乗数: src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap（既存保有のセクター比率が上限を超える場合に当該セクターの新規候補を除外）。
    - calc_regime_multiplier（regime に応じた乗数: bull/neutral/bear / フォールバック）。
  - 株数決定・リスク制限: src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes（allocation_method に応じた注文株数算出。risk_based / equal / score をサポート、lot_size による丸め、aggregate cap によるスケールダウンと残差配分ロジックを実装）。

- 研究 / 分析モジュール（骨組み）
  - ファクター計算モジュール: src/kabusys/research/factor_research.py
    - モメンタム等の指標計算のための定数と calc_momentum の骨組みを追加（DuckDB 接続経由で prices_daily / raw_financials を参照する設計）。

- 検証レポートツール
  - Paper Trading 検証レポート: src/kabusys/tools/paper_verification_report.py
    - paper_trading 用 SQLite から稼働率、注文成功率、送信率、レイテンシ指標（平均/最大/P95）を集計して標準出力レポートを生成。
    - 閾値を定義して PASS/FAIL 判定を行う（稼働率、fill/send rate、P95 latency など）。
    - DB パスはコマンドライン引数 --db / 環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。

### Changed
- （初回リリースのため、既存からの変更はなし。設計上の重要点を明示）
  - 監視側は環境にかかわらず監視用の本番 sqlite_path を参照する設計に注意（run_monitoring）。
  - 実行エンジンは paper_trading 環境を検出すると専用 DB に記録して本番 DB と分離（run_execution）。

### Fixed
- 環境ファイルパーサーの堅牢化（src/kabusys/config.py）
  - export プレフィックス、クォート内のバックスラッシュエスケープ、コメントの取り扱いなどを正しく処理するように改善。
- validate_config による事前検証で致命的な設定ミス（未設定の必須環境変数や不正な KABUSYS_ENV）を起動前に検出可能に。

### Known issues / TODO
- apply_sector_cap 内で price_map に 0.0（価格欠損）がある場合にエクスポージャーが過少見積りされる旨の注記あり。将来的に前日終値や取得原価でのフォールバックを検討する必要がある（src/kabusys/portfolio/risk_adjustment.py）。
- calc_position_sizes: lot_size を銘柄別に管理する拡張の TODO（将来的にマスタから lot_size を読み取る設計へ）。
- research/factor_research.py はモメンタム計算の骨組みを実装しているが、完全実装・テストが必要（ファイルの先頭で calc_momentum の実装が途中まで含まれている）。
- ログディレクトリ作成失敗やプロセス優先度設定失敗は起動継続するが、運用上の影響を確認すること（警告ログあり）。

### Security
- .env を生成する config_setup において、.env を Git にコミットしないよう注意喚起を出力（README 等にも明記推奨）。

---

今後の予定（提案）
- factor_research の完全実装とユニットテストの追加。
- ExecutionEngine / Monitoring の統合テスト、実環境での検証（特に paper_trading と live の DB 分離）。
- 銘柄別単元（lot_size）対応、価格フォールバック実装。
- ドキュメント（運用手順、デプロイ手順、環境変数一覧）の整備。

--- 

（注）この CHANGELOG はコードベースの内容から推測して作成しています。実際の変更履歴やリリースポリシーに合わせて必要に応じて編集してください。