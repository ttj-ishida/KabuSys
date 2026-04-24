CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記載しています。
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- 今後の変更予定をここに記載します。

v0.1.0 - 2026-04-24
-------------------

Added
- パッケージ初期リリース（__version__ = 0.1.0）。
- 起動スクリプトを追加:
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の専用 SQLite DB（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）を使用する。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ (data/stop_requested.flag) の検出、PID ファイル管理、デーモンスレッドでの実行制御をサポート。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイント。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視 DB を初期化。
    - 停止フラグ検出で安全にループを終了。
- 環境設定・検証ユーティリティを追加:
  - config_setup.py
    - 対話式ウィザードで .env を作成/更新する CLI。
    - 一連の設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE トークン等）をサポート。
    - 既存の .env 読み込み、シークレット値のマスク表示、保存前の確認を実装。
  - validate_config.py
    - .env と config/*.yaml の基本的な整合性検証 CLI。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの存在チェック、YAML パースチェック（PyYAML がない場合はスキップ）を実装。
    - --strict オプションで警告も失敗扱いにできる。
- 設定管理モジュールを追加:
  - config.py
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）に基づく .env 自動読み込み（.env → .env.local、OS 環境変数を保護）。
    - .env ファイルの堅牢なパーサ実装（export 接頭辞、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント取り扱い）。
    - Settings クラスで各種設定プロパティを提供（パス解決、値検証、paper_trading 用 DB/モード設定、閾値等）。
- ロギング / プロセス管理ユーティリティ:
  - utils/logging_setup.py
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定するユーティリティ。
    - ログレベル / ログディレクトリの解決順を明示、既存ハンドラのクリーンな再設定を実装。
    - 標準出力へは stdout を使用（cron 等でのリダイレクト想定）。ファイルハンドラ作成失敗時はコンソールのみで継続。
  - utils/process_priority.py
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティ。
    - CPU affinity を最初の N コアにピン留めする set_cpu_affinity() を実装。権限不足や未対応 OS に対する安全なフォールバックを実装。
- ポートフォリオ構築関連（純粋関数群）:
  - portfolio/portfolio_builder.py
    - シグナルから候補選定（スコア降順、同点は signal_rank でタイブレーク）。
    - 等金額配分 calc_equal_weights、スコア加重 calc_score_weights（全スコア 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存保有と当日売却予定を考慮）。
    - 市場レジームに基づく資金乗数 calc_regime_multiplier（bull/neutral/bear をマップ、未知レジームはフォールバックで警告）。
  - portfolio/position_sizing.py
    - allocation_method（risk_based / equal / score）に基づく発注株数計算。
    - リスクベース算出、単元株（lot_size）丸め、単銘柄上限・aggregate cap（利用可能現金）に基づくスケーリング、cost_buffer を考慮した保守的見積り、残余キャッシュを用いた端数配分の再配分ロジックを実装。
- リサーチ / ファクター計算（骨子）:
  - research/factor_research.py
    - Momentum、Value、Volatility、Liquidity などのファクター計算方針と calc_momentum の骨組みを追加（DuckDB 接続を受け prices_daily / raw_financials を参照する設計）。
    - P95 計算や期間定数等を定義。
- Paper Trading 検証ツール:
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite DB から各種指標（稼働率、注文成功率、送信率、レイテンシ等）を集計してレポートを出力する CLI。
    - デフォルト基準値（稼働率 99%、注文成功率 90% 等）による PASS/FAIL 判定を実装。
    - 日付フィルタ（--from / --to）と DB パス指定（--db）に対応。
- パッケージエクスポート:
  - kabusys/__init__.py と kabusys/portfolio/__init__.py による公開 API の整理。

Changed
- ログ出力方針: ログの標準出力は stdout を用いるように統一（cron/task 実行時の扱いを想定）。
- .env 読み込みの挙動: OS 環境変数を保護しつつ .env.local を優先して上書きできる仕組みを採用。

Fixed
- .env パーサの堅牢化:
  - export プレフィックス、引用符内のバックスラッシュエスケープ、インラインコメントの扱い、空行・コメント行のスキップ等を正しく処理するよう改善。
- DB 初期化: monitoring 用のテーブルが存在することを保証する init_monitoring_db 呼び出しを起動処理に追加し、冪等に初期化することで起動失敗を低減。

Deprecated
- なし。

Removed
- なし。

Security
- シークレット値（J-Quants トークン、kabu API パスワード等）は config_setup の対話でマスク表示。 .env は Git へコミットしない旨をドキュメントに明記。

Notes / 今後の課題
- research/factor_research.py は calc_momentum 以降の実装が続く想定（スナップショットは途中まで）。Value 等ファクターの具体実装と総合正規化のユーティリティ連携が必要。
- position_sizing の price 欠損時のフォールバック（前日終値や取得原価を使う等）は TODO コメントあり。実運用/テストに合わせた拡張を推奨。
- ログディレクトリ作成やプロセス優先度設定は権限に依存するため、運用環境での動作確認を推奨。

--- 

この CHANGELOG は現行コードベースの内容から推測して作成しています。実際のリリースノートとして使用する際は、コミット履歴やリリース文書に基づいて必要に応じて修正してください。