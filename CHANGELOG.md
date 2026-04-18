# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

なお、本 CHANGELOG は現在のコードベースの内容から機能追加や実装方針を推測して作成したものです（コミット履歴ではなくソースコードの解析結果に基づきます）。

## [Unreleased]

（今後の変更予定や TODO をここに追記してください）

---

## [0.1.0] - 2026-04-18

初回リリース — KabuSys の基本コンポーネントを提供します。  
主に以下の機能群を実装しています: 設定管理、起動スクリプト（実行・監視）、ロギング・プロセス制御ユーティリティ、ポートフォリオ構築ロジック、ペーパートレード検証ツール、各種 CLI（設定ウィザード・設定検証）およびリサーチ用ファクタ計算の骨組み。

### Added
- 全体
  - パッケージ初期化とバージョン設定を追加（src/kabusys/__init__.py, __version__ = "0.1.0"）。

- 設定管理
  - .env 自動ロード機能を実装（OS 環境変数 > .env.local > .env の優先順）。プロジェクトルート検出は .git / pyproject.toml を基準（src/kabusys/config.py）。
  - 高度な .env パーサを実装：export プレフィックス、クォート文字内のエスケープ、インラインコメント処理などに対応（src/kabusys/config.py）。
  - 必須環境変数取得ヘルパー（_require）と Settings クラスを追加。J-Quants / kabu API / DB / 監視閾値 / 環境判定プロパティを提供（src/kabusys/config.py）。
  - Paper Trading 用の DB パスや fill モード、各種閾値などの設定プロパティを実装。

- 起動スクリプト・実行エンジン
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合に本番 DB と完全分離して paper_trading 用 SQLite を使用する実装。
    - BrokerClientFactory によるブローカークライアント生成と、OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立て。
    - RiskConfig のデフォルト値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker_* 等）を設定し、初期ポートフォリオ価値に基づく初期化を行う。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）を使った安全な起動・終了ロジック。スレッド実行・監視によるデーモン動作。

- 監視（Monitoring）
  - 監視ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 停止フラグ（data/stop_requested.flag）検出で安全にループを抜ける実装。
    - SystemMonitor 初期化、監視用 DB 初期化（monitoring_db の init 関数呼び出し）、DuckDB 接続の確立。

- ロギング・プロセス制御ユーティリティ
  - 統一ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout への StreamHandler と、日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app>.log、30日保持）をルートロガーに設定。
    - LOG_DIR 作成失敗時のフォールバック（ファイル出力無効化）処理、既存ハンドラの安全なクローズ/削除。
  - プロセス優先度 / CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows と POSIX（Linux/Mac/FreeBSD）双方を吸収して nice 値や HIGH_PRIORITY_CLASS 等を設定。例外・権限不足時は警告を出してスキップ。

- 設定支援 CLI
  - 対話式 .env ウィザードを追加（src/kabusys/config_setup.py）。
    - 一覧定義に基づく対話入力、既存 .env の読み込み・再利用、秘密値のマスク表示、確認後の .env 上書き機能を備える。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在確認（PyYAML があればパース検証）など。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - 銘柄選定と単純重み付け関数（src/kabusys/portfolio/portfolio_builder.py）。
    - select_candidates（スコア降順・タイブレーク）、calc_equal_weights、calc_score_weights（スコア合計が 0 の場合は等金額にフォールバック）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）。
    - apply_sector_cap（既存保有のセクター暴露を計算し、上限を超えたセクターの新規候補を除外。unknown セクターは制限適用外）。
    - calc_regime_multiplier（"bull"/"neutral"/"bear" に対応、未知レジームは警告の上で 1.0 にフォールバック）。
  - ポジションサイズ決定（src/kabusys/portfolio/position_sizing.py）。
    - allocation_method = "risk_based"（許容リスク率・損切り率に基づく）、"equal"/"score" に対応。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap（available_cash）に基づくスケーリングロジックを実装。スケール時は残差に基づいて lot 単位で配分を調整。
    - cost_buffer（手数料・スリッページ見積り）を考慮した保守的なコスト推定。

- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - SQLite（デフォルト data/paper_trading.db）から system_status / trade_logs / risk_logs を集計して稼働率・注文成功率・送信率・レイテンシ（平均・最大・P95）などを出力。
    - P95 計算、期間フィルタ（--from/--to）サポート、基準値（稼働率 99%、成功率 90% など）による PASS/FAIL 判定。
    - DB 未存在時のエラーメッセージ。

- リサーチ（骨組み）
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）の骨組みを追加。
    - モメンタム（1M/3M/6M リターン、MA200 乖離）、ATR、出来高等の計算方針と定数を定義。DuckDB からの prices_daily テーブル参照を想定した calc_momentum 関数を実装（途中までの実装あり）。

- モジュール公開
  - kabusys.portfolio パッケージの __all__ を設定し、主要関数を外部に公開。

### Changed
- ログ設定の挙動を明確化：stdout を使用する設計（stderr ではなく stdout）とし、ログハンドラの重複設定を防ぐため既存ハンドラをクリアする実装（src/kabusys/utils/logging_setup.py）。
- .env 読み込み時に OS の環境変数を保護する仕組みを導入（既存 OS 環境を上書きしない、.env.local の上書きルールを保持）。

### Fixed
- 環境変数や設定値の不正入力に対する安全策を多数追加：
  - MONITOR_POLL_INTERVAL の不正値で ValueError が発生しないよう警告してデフォルトにフォールバック（src/kabusys/run_monitoring.py）。
  - Settings.paper_fill_mode の不正値チェックと ValueError 投げる実装（src/kabusys/config.py）。
  - process_priority の未対応 OS や権限不足時に例外で停止しないよう例外処理を追加（src/kabusys/utils/process_priority.py）。

### Notes / Implementation details
- 多くの機能は外部依存（psutil, duckdb, PyYAML など）を想定しており、利用環境により一部動作が制限されることがあります。例えば PyYAML が未インストールの場合は config/*.yaml のパース検証がスキップされ、警告が出ます（validate_config）。
- ExecutionEngine 周り（broker, order_manager, risk_manager, reconciler 等）は起動スクリプト内で組み立てられるように設計されており、実際のブローカー実装は BrokerClientFactory を通じて注入されます（paper_trading 用の Mock クライアント分離あり）。
- position_sizing の集約スケーリングロジックは lot_size（単元株）単位で丸めを行うため、小口配分の精度や端数処理に注意が必要です。コメント内に将来的な拡張（銘柄別 lot_size のサポート等）の TODO を記載しています。

### Files of interest
- 起動／運用: src/kabusys/run_execution.py, src/kabusys/run_monitoring.py
- 設定: src/kabusys/config.py, src/kabusys/config_setup.py, src/kabusys/validate_config.py
- ログ・プロセス: src/kabusys/utils/logging_setup.py, src/kabusys/utils/process_priority.py
- ポートフォリオ: src/kabusys/portfolio/*
- ツール: src/kabusys/tools/paper_verification_report.py
- リサーチ: src/kabusys/research/factor_research.py

---

今後のリリースでは以下のような改善が想定されます（例）:
- factor_research の完全実装（全ファクター・正常系のユニットテスト追加）
- ExecutionEngine / BrokerClient の統合テスト、MockBrokerClient の拡張
- 単体テスト・CI の追加とカバレッジ向上
- 銘柄別単元株情報の対応、手数料・スリッページモデルの明確化
- monitoring_db のスキーマ明記と migration 支援スクリプトの追加

（必要であれば、上記 CHANGELOG を要望に合わせて日付や細部の表現を修正します。）