CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- Docs / TODO
  - research/factor_research.py が序盤まで実装されており、モメンタム等のファクター計算の続きを実装予定。
  - apply_sector_cap の価格欠損時のフォールバックや position_sizing の銘柄別 lot_size 対応など、将来的な拡張点をコードコメントで明示。

[0.1.0] - 2026-04-19
--------------------

Added
- 基本機能（初期リリース）
  - KabuSys パッケージの初期公開（__version__ = 0.1.0）。
  - 自動売買エンジン用の主要コンポーネントを実装:
    - ExecutionEngine 起動スクリプト (src/kabusys/run_execution.py)
      - Paper trading 時は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し本番 DB と分離。
      - BrokerClientFactory 経由で本番 / モックブローカーを切り替え。
      - スレッドでエンジンを起動し、 data/stop_requested.flag による停止をサポート。
      - 起動時に PID ファイルを扱う（data/execution.pid）。
    - SystemMonitor 起動スクリプト (src/kabusys/run_monitoring.py)
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
      - stop フラグ検知、例外捕捉、KeyboardInterrupt ハンドリングを実装。
  - 環境設定関連 CLI:
    - 対話式 .env ウィザード (src/kabusys/config_setup.py)
      - シークレットマスクや選択肢、デフォルト値をサポートし .env を生成/更新。
    - 設定検証ツール (src/kabusys/validate_config.py)
      - 必須環境変数、KABUSYS_ENV の妥当性、ログレベル、DB パス、config/*.yaml の存在・パース（PyYAML があればパース検証）などをチェック。
      - --strict オプションで警告も失敗扱いにできる。
  - 環境変数管理 (src/kabusys/config.py)
    - .env 自動ロード機構（プロジェクトルートを .git / pyproject.toml で検出）。
    - .env/.env.local の読み込み順を実装（OS 環境変数を保護する仕組みを備える）。
    - 複雑な .env 値パースを実装（export プレフィックス、クォート内のエスケープ、インラインコメントの扱い等）。
    - Settings クラスを提供し、PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の妥当性検証を実施。
  - ロギング・ユーティリティ (src/kabusys/utils/logging_setup.py)
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）を設定。
    - 既存ハンドラのクリアと再設定を行い二重出力を防止。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - プロセス優先度・CPU 固定ユーティリティ (src/kabusys/utils/process_priority.py)
    - Windows / POSIX を吸収する set_process_priority と set_cpu_affinity を提供（psutil 利用）。
    - 権限不足や未対応 OS は警告して安全にスキップ。
  - ポートフォリオ構築モジュール (src/kabusys/portfolio/)
    - portfolio_builder:
      - select_candidates: スコア降順で候補選定（タイブレーク: signal_rank）。
      - calc_equal_weights / calc_score_weights（スコア全0時は等配分へフォールバック）。
    - risk_adjustment:
      - apply_sector_cap: 既存保有のセクターエクスポージャーを算出し、上限超過セクターの候補を除外。
      - calc_regime_multiplier: market regime に応じた投下資金乗数を返却（bull/neutral/bear をマップ）。
    - position_sizing:
      - calc_position_sizes: risk_based / equal / score の配分ロジック、単元株丸め、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積りを実装。
  - Paper Trading 検証レポート (src/kabusys/tools/paper_verification_report.py)
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を算出し、閾値比較で PASS/FAIL 判定を行う。
    - --from / --to / --db オプションをサポート。
    - P95 計算、各種フォールバック（テーブル欠如時の安全ハンドリング）を実装。

Changed
- 設計上の挙動明示
  - run_monitoring は監視用 DB に対して環境変数に依存せず常に sqlite_path（本番想定）を使用する仕様を明示化。
  - run_execution は is_paper の場合 paper_sqlite_path を使用して paper_trading と本番 DB を完全分離。

Fixed
- ロバスト性向上
  - MONITOR_POLL_INTERVAL が不正（0 以下や非整数）の場合は警告を出してデフォルト（60 秒）にフォールバック。
  - .env ファイル読み込みでファイルアクセス失敗時に警告を出して安全に続行。
  - logging_setup はログディレクトリ作成失敗やファイルハンドラ作成失敗時にコンソール出力のみで動作を継続。
  - process_priority 周りで権限不足や未実装 API を捕捉し警告を出すようにして起動失敗を防止。
  - validate_config は PyYAML 未インストール時に YAML 検証をスキップして警告出力する。

Security
- 機密情報の取り扱い
  - config_setup ウィザードでシークレット項目は画面表示時にマスク（表示は "****"）して扱う。
  - .env テンプレート生成時に .env を絶対に Git にコミットしない旨を明記。

Notes / Known limitations
- research/factor_research.py が途中まで実装されており、ファクター計算群（Momentum / Value / Volatility / Liquidity）の完全実装は継続作業が必要。
- apply_sector_cap の価格欠損（price_map に値がない / 0.0 の場合）によりエクスポージャーが過少推定される可能性がある点をコードコメントで指摘。将来的に前日終値等のフォールバックを検討。
- position_sizing の将来拡張として、銘柄ごとの lot_size を stocks マスタで管理する案がコメントとして残されている。

Breaking Changes
- なし（今回が初期公開のため破壊的変更は無し）。

以上。必要があればバージョン分割や項目の追加・日付更新を行います。