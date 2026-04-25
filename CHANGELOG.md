# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  

各エントリは機能追加（Added）、変更（Changed）、修正（Fixed）などに分類しています。

## [Unreleased]

（現在の配布バージョンは 0.1.0。次のリリースに向けての未リリース項目があればここに追加してください。）

---

## [0.1.0] - 2026-04-25

初回公開リリース。日本株自動売買システム KabuSys のコア機能を実装しています。主な追加・改良点は以下の通りです。

### Added
- 全体
  - パッケージ初期化（__version__ = 0.1.0）。
  - プロジェクト共通のユーティリティ群・CLI・ランナーを追加。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するメインスクリプトを実装。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory を使ったブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を別スレッドで実行。
    - 停止フラグ（data/stop_requested.flag）検知により安全に停止する仕組みを実装。
    - 起動時に実行 PID を data/execution.pid に保持（Engine 側で扱う）。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視モジュールは環境に関わらず本番の sqlite_path を使用して監視データを記録。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。

- 設定管理 / CLI
  - config.py
    - .env 自動読み込み機能（プロジェクトルートが .git または pyproject.toml で特定できる場合）。
    - .env のパース実装：export 形式、シングル・ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
    - Settings クラスを実装（各種環境変数の取得・検証用プロパティ）。
      - PAPER_FILL_MODE の妥当性チェック（instant, partial, never, reject）。
      - KABUSYS_ENV / LOG_LEVEL の妥当性チェック。
      - データベースパス、PID ファイル、Kill フラグ等のアクセス用プロパティを提供。

  - config_setup.py
    - 対話式 .env 作成・更新ウィザードを提供。
    - シークレット項目はマスク表示。既存 .env の読み込みと Enter による再利用をサポート。
    - 最終的に .env を安全に書き込む機能を実装（デフォルト値やコメント付きテンプレートを出力）。

  - validate_config.py
    - 起動前に設定の静的検証を行う CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ存在確認、config/*.yaml の存在/パースチェック（PyYAML がある場合）など。
    - --strict オプションで警告を失敗扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）：score 降順、同点時は signal_rank 昇順でタイブレーク。
    - 重み計算（calc_equal_weights, calc_score_weights）：スコア合計が 0 の場合のフォールバックを含む。

  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）：既存ポジションのセクター露出が上限を超える場合、新規候補を除外。
    - レジーム乗数（calc_regime_multiplier）：regime に応じた投下資金乗数を返す（bull/neutral/bear）と、未知レジーム時のフォールバック。

  - portfolio/position_sizing.py
    - 発注株数計算（calc_position_sizes）
      - allocation_method="risk_based"/"equal"/"score" をサポート。
      - 単元株（lot_size）で丸め、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap スケーリングを実装。
      - スケーリング時の端数処理（残差の大きい順に追加配分）を実装。

- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定する共通セットアップ関数を提供。
    - 既存ハンドラをクリアして二重設定を防止。LOG_DIR / LOG_LEVEL の解決順をサポート。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。

  - utils/process_priority.py
    - psutil を用いたクロスプラットフォームなプロセス優先度（high/normal/low）設定および CPU affinity 固定ユーティリティを提供。
    - Windows/Linux/Mac の差分を吸収し、権限不足・未対応環境は警告ログでスキップ。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード結果検証レポート生成スクリプト。
    - 指標: 稼働率(uptime)、注文成功率(fill rate)、送信率(send rate)、P95 レイテンシ 等を算出。
    - 日付範囲フィルタ（--from, --to）と DB パス指定（--db / 環境変数）をサポート。
    - テーブル欠損時は安全に N/A を扱う。

- 研究用（開発中）
  - research/factor_research.py（モメンタム等のファクター計算の骨組み）
    - DuckDB を使った prices_daily / raw_financials に基づくファクター計算実装方針と一部定数を追加。関数（calc_momentum 等）の骨格あり（実装継続）。

### Changed
- ロギング
  - 標準出力は stdout を用いるように明示（cron 等で stdout/stderr を一本化しやすくするため）。

- DB 接続の扱い
  - 監視用スクリプトは環境にかかわらず設定された sqlite_path（本番向け）を使用する方針に統一。

### Fixed
- 環境変数読み込みの堅牢化
  - .env パーサはクォート内のバックスラッシュエスケープ、export プレフィックス、インラインコメントの扱いを正しく処理するように改善。
  - 自動ロード時に OS 環境変数を保護する仕組み（protected set）を導入し、.env.local の上書き動作を制御。

- ポジションサイズ計算の安定化
  - aggregate cap 適用時に小数/単元の端数処理を明示的に行い、残余キャッシュを用いた再配分アルゴリズムを導入。

### Known issues / Notes
- research/factor_research.py は一部実装が継続中（calc_momentum の先頭でファイルがトランケートされた状態で提供されている）。ファクター計算の完全実装は今後のコミットで追加予定。
- apply_sector_cap の価格欠損（price_map の値が 0.0 の場合）によりエクスポージャーが過少見積りされる可能性がある旨の TODO コメントあり。将来的にフォールバック価格（前日終値等）の導入を検討。

---

今後の予定（短期）
- research モジュールの完実装（ファクター群の SQL/Python 実装）。
- ExecutionEngine / Monitoring の統合テストと障害時の堅牢化（リトライ／回復処理の強化）。
- テストカバレッジ拡充と CI 設定。

もし特定ファイルや機能について、より詳細な変更点や補足説明が必要であればお知らせください。