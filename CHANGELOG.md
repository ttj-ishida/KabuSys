# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」（https://keepachangelog.com/ja/1.0.0/）に準拠しています。

最新変更: 0.1.0 — 2026-04-17

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-17

初回リリース — KabuSys コードベースの最初の公開版。以下の主要機能・実装を含みます。

### 追加
- 基本パッケージとバージョン情報
  - パッケージ名: KabuSys
  - バージョン: 0.1.0

- 設定管理
  - Settings クラスによる環境変数ラッパーを実装（config.py）。
  - 自動 .env ロード機能:
    - プロジェクトルートを .git または pyproject.toml から検出して .env / .env.local を自動読み込み。
    - OS 環境変数を保護しつつ読み込みを制御。
    - フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能。
  - 多数のプロパティを提供:
    - J-Quants / kabuステーション / LINE API 関連、DuckDB / SQLite のパス、Paper Trading 固有設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH）、監視用しきい値（CPU/MEM/DISK）など。
  - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。

- 設定ウィザード CLI
  - config_setup.py により対話式で .env を作成・更新するウィザードを実装。
  - デフォルト値、選択肢、シークレット入力、保存前の確認をサポート。
  - 書式付きテンプレートによる .env 出力。

- 設定検証 CLI
  - validate_config.py による起動前検証ツールを実装。
  - 必須環境変数、KABUSYS_ENV 値、LOG_LEVEL、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と（PyYAML があれば）パース検証、本番（live）向けガードチェックを実行。
  - --strict オプションで警告を失敗扱いにできる。

- 実行・監視プロセス起動スクリプト
  - run_execution.py:
    - ExecutionEngine の起動スクリプト（高優先度設定、DB 接続、Broker クライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、スレッドでエンジン実行、停止フラグ検知による graceful stop）。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離。
    - 実行中 PID 管理と stop フラグ検知の仕組み。
  - run_monitoring.py:
    - SystemMonitor のポーリングループ起動スクリプト（デフォルト 60 秒、MONITOR_POLL_INTERVAL で上書き可）。
    - 監視用 DB 初期化（monitoring 用テーブルが存在することを保証）。
    - 監視は環境にかかわらず production の sqlite_path を使用する設計（本番監視対象としての意図的な挙動）。
    - 停止フラグ検知でループ終了、例外時はログを残して次回ポーリングへ。

- モニタリング DB 初期化（init_monitoring_db を参照する実装呼び出し）
  - 実装箇所から監視テーブル作成処理を呼び出す仕組みを組み込む。

- ポートフォリオ構築ライブラリ
  - portfolio_builder:
    - select_candidates（スコア降順、タイブレークロジック実装）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア正規化、全て 0 の場合は等金額にフォールバック）
  - risk_adjustment:
    - apply_sector_cap（既存保有によるセクター上限チェック、売却予定銘柄の除外対応、"unknown" セクターの扱い）
    - calc_regime_multiplier（market regime に応じた投下資金乗数: bull/neutral/bear + フォールバック）
  - position_sizing:
    - calc_position_sizes（allocation_method: risk_based / equal / score 対応、lot_size 単位丸め、aggregate cap とスケーリング、cost_buffer による保守見積り、残余の再配分ロジック）

- 研究（リサーチ）モジュール
  - research/factor_research.py:
    - calc_momentum（1M/3M/6M リターン、MA200 乖離の計算。DuckDB の SQL を使用）
    - calc_volatility（ATR, 相対 ATR, 20日平均売買代金, 出来高比率 等の計算。NULL ハンドリングを考慮）
    - DuckDB 接続を受けて SQL＋Python で完結する設計（prices_daily / raw_financials のみ参照）

- ユーティリティ
  - utils/process_priority.py:
    - psutil を用いたプラットフォーム抽象化（Windows の priority class、POSIX の nice 値）。
    - set_process_priority(level) — high/normal/low、権限等で失敗した場合は警告ログでスキップ。
    - set_cpu_affinity(cpu_count) — 指定コア数にプロセスをピン留め（未対応 OS や権限不足は警告でスキップ）。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用検証レポート生成スクリプト（期間指定可能）。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率、リスク却下数、API レイテンシ（avg/max/P95）など。
    - 合否基準（デフォルト）を定義し PASS/FAIL を出力（閾値: uptime >=99%、fill >=90% 等）。
    - DB の存在チェックとエラーハンドリング。

### 変更（設計上の重要点）
- DB の扱い
  - Paper Trading 実行は本番 DB と分離（PAPER_TRADING_SQLITE_PATH を使用）。
  - 監視（run_monitoring）はあえて本番 sqlite_path を使用する設計。

- .env パーサーの強化
  - export KEY=val 形式、シングル／ダブルクォート内のバックスラッシュエスケープ、コメント取り扱い（クォートあり/なしでの振る舞い差分）に対応。

- 実行時のプロセス優先度を起動直後に設定するフローを採用（run_execution/run_monitoring）。

### 修正（例示的）
- calc_score_weights: 全スコアが 0 の場合に等金額配分へフォールバックして警告ログを出す挙動を追加。
- position_sizing: aggregate cap 超過時のスケーリングと lot_size 単位での再配分ロジックを実装。
- factor_research: SQL 内での NULL 制御や窓関数の利用により、欠損データ時の挙動を明確化。

### 既知の制限・注意点
- price の欠損処理:
  - apply_sector_cap と calc_position_sizes は price が欠損（0.0 または None）の場合にエクスポージャーや発注数量が過少見積もりされる可能性があり、将来的に前日終値や取得原価でのフォールバックを検討する旨の TODO が残っています。
- 単元株（lot_size）は現状グローバル定数（現状は 100）で銘柄ごと異なる単元対応は未実装（将来的な拡張予定）。
- PyYAML がインストールされていない場合、validate_config の YAML 内容検証はスキップされる（warning 表示）。
- プロセス優先度 / CPU affinity の設定は OS 権限やプラットフォームに依存するため、権限不足・非対応環境ではスキップされログに警告が出ます。
- run_monitoring は実装上「監視は本番 sqlite_path を使う」ため、意図せず本番 DB を参照・更新しないよう環境設定に注意してください。
- 一部のテストや CI で自動的に .env を読み込ませたくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。

### セキュリティ
- .env は絶対にリポジトリにコミットしないようテンプレートに明記。
- 機密値（トークン、パスワード等）はウィザードでマスク表示および .env に平文で保存される点に注意。

---

今後の予定（例）
- 銘柄ごとの lot_size 対応（マスタ参照）
- price 欠損時のフォールバックロジック（前日終値等）
- モニタリングデータのアラート通知（LINE 連携強化）
- テストカバレッジの拡充と CI/CD パイプライン整備

（以上）