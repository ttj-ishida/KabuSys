# Changelog

すべての重要な変更を Keep a Changelog（https://keepachangelog.com/）に準拠して日本語で記載します。

注: このリポジトリは初回リリースとしてバージョン 0.1.0 を公開します。

## [0.1.0] - 2026-04-17

### Added（追加）
- 基本パッケージ情報
  - パッケージメタ情報を追加（kabusys/__init__.py にて __version__ = "0.1.0" を定義）。

- 設定・環境変数管理
  - Settings クラスを実装（src/kabusys/config.py）。.env または環境変数からアプリ設定を取得するためのプロパティ群を提供。
  - 自動 .env ロード機能を実装。プロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を読み込む（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - .env パーサーを強化：クォート、エスケープ、export プレフィックス、インラインコメントの取り扱いに対応。
  - 必須/各種設定値の検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。不正な値は ValueError を送出して早期検出する。

- 設定ウィザード CLI
  - src/kabusys/config_setup.py: 対話式ウィザードで .env の初期作成・更新を支援する CLI を実装。既存 .env の読み込み、シークレットマスク表示、保存機能を提供。

- 設定検証 CLI
  - src/kabusys/validate_config.py: 起動前に環境変数や config/*.yaml の有無・簡易パースを検証する CLI を実装。--strict オプションで警告を FAIL 扱いにできる。

- 実行 / 監視用エントリポイント
  - src/kabusys/run_execution.py: ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用の SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアントの抽象化。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。停止フラグ（data/stop_requested.flag）検知時に安全に停止。
    - PID ファイル管理（data/execution.pid）をサポート。
  - src/kabusys/run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告を出力。
    - 監視用 DB 初期化（monitoring テーブル群を冪等に作成）と DuckDB 接続を行い SystemMonitor.check_once() を定期実行。
    - 停止フラグ検知でループ終了。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計（運用上の意図を明示）。

- Paper Trading 検証レポート
  - src/kabusys/tools/paper_verification_report.py: ペーパートレード用 SQLite を解析して検証レポートを生成する CLI を追加。
    - システム稼働率、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシなどを算出・表示。
    - 判定基準（閾値）を定義して PASS/FAIL 判定を出力。
    - --from / --to / --db オプションで期間・DB を指定可能。

- ポートフォリオ構築ライブラリ
  - src/kabusys/portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルから候補をスコア降順で選択（タイブレーク: signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装。全スコアが 0 の場合は等金額配分にフォールバック（警告）。
  - src/kabusys/portfolio/risk_adjustment.py:
    - apply_sector_cap: 既存保有のセクター比率が閾値を超える場合に新規候補を除外する機能を提供（"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。
  - src/kabusys/portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method に基づく株数決定ロジックを実装（risk_based / equal / score）。
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash）に基づくスケーリング、cost_buffer（手数料等の保守的見積り）対応。
    - スケーリング時の端数処理で再現性を保つアルゴリズムを実装。

- リサーチ / ファクター計算
  - src/kabusys/research/factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率（ma200_dev）を DuckDB の prices_daily テーブルから計算。
    - calc_volatility: ATR/相対 ATR、20 日平均売買代金、出来高比率等を計算する実装を追加（データ不足時は None を返す）。
    - DuckDB 接続を受け取り SQL で効率的に集計する設計。

- ユーティリティ
  - src/kabusys/utils/process_priority.py:
    - set_process_priority(level): Windows / POSIX の差分を吸収してプロセス優先度を設定。アクセス権限不足などは警告を出してスキップ。
    - set_cpu_affinity(cpu_count): カレントプロセスを最初の N コアに固定するユーティリティ（未対応 OS 時や権限不足は警告を出してスキップ）。

- その他
  - monitoring DB 初期化関数（init_monitoring_db）や SystemMonitor / ExecutionEngine 等の呼び出しポイントを追加しており、本体の監視・実行フローを統合するエントリポイントを整備。
  - tools パッケージを導入（空の __init__ でパッケージ化）。

### Changed（変更）
- .env の読み込み順序と保護ルールを明確化
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。OS 環境変数は protected として .env.local の override から保護される。

- 設定検証ロジック（validate_config）を充実化
  - 必須環境変数のプレースホルダ検出（例: 値が "your_value" や "*_here" で終わる場合に警告）。
  - config/*.yaml の存在チェックおよび PyYAML がある場合はパース検査を行う。

### Fixed（修正）
- MONITOR_POLL_INTERVAL の不正値対策
  - run_monitoring のポーリング間隔取得処理で 0 以下や非整数の指定を安全にデフォルトにフォールバックするように改善（time.sleep に無効値が渡るのを防止）。

- データ不足に対する堅牢性向上
  - factor_research と paper_verification_report のクエリでテーブル・列が存在しない場合に sqlite3.OperationalError を捕捉して「データなし」として扱う耐障害性を追加。

### Security（セキュリティ）
- シークレット値の扱い
  - config_setup の表示や .env 書き出しでシークレットはマスク表示（画面上）する等、シークレット漏洩軽減の配慮を追加。なお .env ファイルは「絶対に Git にコミットしない」旨の注意をファイル先頭に明記。

### Notes（備考 / 今後の改善）
- position_sizing の価格欠損に関する TODO コメント（price が 0 の場合のフォールバック価格導入など）を残している。実運用では前日終値等のフォールバック実装を検討する必要あり。
- process_priority と CPU affinity の設定は権限によって失敗し得るため、運用時の権限設定（systemd unit など）を確認すること。
- factor_research のさらなるファクター追加や統合テストは今後の作業項目です。

---

その他の変更やバグ修正は今後のコミットで追記します。質問や誤りの指摘があればお知らせください。