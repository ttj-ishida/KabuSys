# CHANGELOG

すべての重要な変更点はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-17

初回リリース。システム全体のコア機能、CLI、ユーティリティ、ポートフォリオ構築ロジック、レポート生成等を含みます。

### 追加 (Added)
- プロジェクトの初版を公開。
- 実行スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite(DB)（デフォルト: data/paper_trading.db）と分離して実行する仕組みを実装。
    - 起動時にプロセス優先度を設定し、停止フラグ (data/stop_requested.flag) と PID ファイルの取り扱いをサポート。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB 初期化 (monitoring テーブル) を保証し、停止フラグ検出で安全に終了。
- 環境設定関連
  - config.py: 環境変数および .env ファイルの自動読み込み機能、Settings クラス（各種設定プロパティ）を実装。
    - .env/.env.local の自動読み込み（プロジェクトルート検出: .git または pyproject.toml）。
    - .env の行パーサーは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
    - 各種設定プロパティ（DB パス、PID パス、閾値、KABUSYS_ENV 検証、PAPER_FILL_MODE 検証 等）を提供。
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加（秘密値はマスク、既存値の再利用可能）。
  - validate_config.py: 起動前設定検証 CLI を追加（必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パス/設定ファイル存在確認、live 環境向けガード等）。
- 監視・モニタリング
  - monitoring_db 初期化呼び出しを実行/監視スクリプトで行い、監視テーブルの存在を保証。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順で候補選定（タイブレーク: signal_rank）。
    - calc_equal_weights, calc_score_weights: 等金額配分とスコア加重配分を実装。スコア合計が 0 の場合は等配分へフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: risk_based / equal / score 各方式の株数決定ロジックを実装。
    - ロット丸め（lot_size 単位）、1 銘柄上限、aggregate cap（可用現金に基づくスケーリング）を実装。残差処理で再分配ロジックを導入。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存保有のセクター比率が上限を超える場合、新規候補を除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を提供（bull/neutral/bear）。
- 研究・ファクター計算
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールを追加（Momentum, Volatility/ATR, Liquidity 等の計算を想定）。prices_daily テーブル参照。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。
    - 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを算出し PASS/FAIL 判定を出力。
    - DATE 範囲フィルタ、DB パス指定 (--db) をサポート。
- ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level): Windows / POSIX に対応したプロセス優先度設定を提供（"high"|"normal"|"low"）。
    - set_cpu_affinity(cpu_count): 指定コア数への CPU affinity 設定を追加。
    - psutil による権限不足や未対応 OS の場合は警告を出して安全にスキップ。
- パッケージ初期化
  - __init__.py にバージョン情報 __version__ = "0.1.0" と主要サブパッケージの __all__ を追加。

### 変更 (Changed)
- システム起動挙動
  - run_execution/run_monitoring の起動時にプロセス優先度を最初に "high" に設定するよう共通化。
- DB ハンドリング
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（run_monitoring 側で明示）。
  - run_execution は paper_trading 環境時に paper_sqlite_path を優先して接続する（本番 DB と完全分離）。
- .env 自動読み込みの優先度を明確化（OS 環境変数 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化を追加。

### 修正 (Fixed)
- 環境変数の検証/フォールバック
  - MONITOR_POLL_INTERVAL が不正（0 や負数、非整数）の場合に警告を出してデフォルト（60 秒）へフォールバックするよう修正。
  - PAPER_FILL_MODE の不正値チェックを追加（有効値: instant|partial|never|reject）。不正な場合は ValueError を送出。
  - calc_score_weights: 全銘柄スコアが 0 の場合に等金額配分へフォールバックし、警告ログを出すよう対応。
  - apply_sector_cap: "unknown" セクター（マッピング未登録）は除外対象にしない（制限を適用しない）ように仕様明確化。
- ロバストネス向上
  - .env 読み込みでファイル入出力エラー時に警告を出すようにしてプロセスを中断させない。
  - validate_config にて PyYAML 未インストール時は YAML 検証をスキップして警告を出す挙動を追加。
  - run_execution/run_monitoring が使用する SQLite / DuckDB 接続を finally ブロックで確実にクローズするように修正。
- position_sizing のスケールダウン後の端数処理で再分配ロジックを導入し、利用可能残余キャッシュを有効活用するよう改善。

### ドキュメント (Documentation)
- 各モジュールに日本語の docstring を追加し、使用例・設計方針・引数仕様・返り値を明記。
- config_setup による .env テンプレート生成のヘッダをわかりやすく整備（.env を Git にコミットしない注意喚起等）。
- tools/paper_verification_report にコマンド例と閾値の定義をドキュメント化。

### 既知の制限 (Known limitations)
- position_sizing, apply_sector_cap 等で価格データが欠損（0 や None）の場合のフォールバック価格（前日終値や取得原価）をまだ実装していない（TODO コメントあり）。このため価格欠損時にエクスポージャーが過少評価される可能性がある。
- set_process_priority / set_cpu_affinity は権限不足の環境や未サポート OS では機能しない場合があり、その際は警告出力にとどまる。
- research/factor_research は DuckDB 上の prices_daily/raw_financials テーブル依存。テーブルが存在しない場合は例外／空リストになる可能性がある。

---

今後のリリースでは、以下を予定しています／検討中です:
- 銘柄ごとの単元株数 (lot_size) をマスタデータから取得する対応
- 価格欠損時のフォールバックロジック（前日終値や取得原価）
- モニタリング・アラートの LINE 通知連携強化
- 単体テストと CI の追加（自動検証）

（この CHANGELOG はコードベースから推測して作成されており、実際の変更履歴管理ポリシーにあわせて調整してください。）