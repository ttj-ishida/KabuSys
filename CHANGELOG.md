# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

<!-- NOTE: 実装コードから推測して作成した初期リリース向けの履歴です。 -->

## [Unreleased]

なし

## [0.1.0] - 2026-04-25

### Added
- プロジェクト初期リリース。
- アプリケーション設定管理
  - .env ファイルの自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
  - .env の行パーサを実装（コメント、クォート、export プレフィックス、インラインコメント処理対応）。
  - Settings クラスを追加し、環境変数経由で以下を取得可能:
    - J-Quants / kabuステーション / LINE API 関連設定
    - データベースパス（DuckDB / SQLite）
    - PID / Kill flag 関連、しきい値（CPU/メモリ/ディスク）
    - 実行環境フラグ（development / paper_trading / live）と補助プロパティ（is_live/is_paper/is_dev）
    - Paper Trading 固有設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH 等）
- 環境設定ウィザード CLI (`kabusys.config_setup`)
  - 対話式に .env を新規作成・更新できるウィザードを追加。
  - 秘匿入力（マスク表示）や選択肢／デフォルトのサポート、保存確認を実装。
- 設定検証 CLI (`kabusys.validate_config`)
  - 必須/任意環境変数のチェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パス・親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAMLがある場合は）パース検証。
  - KABUSYS_ENV=live に対する追加ガード（LINE 通知未設定や Kill Flag 自動クリア設定の警告）。
  - --strict オプションで警告を FAIL 扱いにできる。
- 起動スクリプト
  - `run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する旨の明記。
    - 停止フラグ（data/stop_requested.flag）検知によるループ終了処理を実装。
  - `run_execution.py`
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は専用の paper DB（data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory を用いたブローカークライアントの切り替え、ExecutionEngine の起動・停止処理（停止フラグ検知・PID ファイルパス）を実装。
- ロギングユーティリティ (`kabusys.utils.logging_setup`)
  - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を設定する set-up を追加。
  - ログディレクトリの自動作成、環境変数／引数でログレベル・ログディレクトリを解決。
  - 既存ハンドラのクリア・二重設定防止を実装。
- プロセス優先度 / CPU affinity ユーティリティ (`kabusys.utils.process_priority`)
  - Windows / POSIX の差分を吸収してプロセス優先度を設定（high/normal/low）。
  - CPU affinity を最初の N コアに固定する関数を追加（権限不足時は警告でスキップ）。
- ポートフォリオ構築ライブラリ (`kabusys.portfolio`)
  - 候補選定・重み計算（portfolio_builder）
    - select_candidates（スコア降順、タイブレークに signal_rank）
    - calc_equal_weights（等分配）
    - calc_score_weights（スコア比率、全て 0 の場合は等分配へフォールバック）
  - セクター制限・レジーム乗数（risk_adjustment）
    - apply_sector_cap（既存保有を元にセクター上限超過時に同セクターの新規候補を除外、"unknown" セクターは除外対象外）
    - calc_regime_multiplier（regime ラベルに応じた資金乗数: bull=1.0, neutral=0.7, bear=0.3、未知レジームは警告のうえ 1.0 フォールバック）
  - 株数決定・丸めロジック（position_sizing）
    - allocation_method に応じた発注株数計算（risk_based / equal / score）
    - risk_based: risk_pct / stop_loss_pct ベースで算出、単元株（lot_size）丸め、per-stock 上限と aggregate cap の扱い
    - equal/score: weight に基づく配分、max_position_pct / max_utilization を考慮
    - aggregate cap 超過時のスケーリングと lot 単位での端数再配分アルゴリズムを実装
    - price 欠損時のスキップとデバッグログ、cost_buffer による保守的見積り対応
- Paper Trading 検証レポートツール (`kabusys.tools.paper_verification_report`)
  - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から統計を集計し、検証レポートを生成する CLI を追加。
  - 指標:
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数 等
  - デフォルトの合格基準を設定:
    - 稼働率 >= 99.0%
    - 注文成立率 >= 90.0%
    - 送信率 >= 95.0%
    - P95 レイテンシ <= 200 ms
  - 日付フィルタ（--from / --to）をサポート。P95 計算ロジックを実装。
- 研究用ファクター計算モジュール（部分実装）
  - factor_research モジュールを追加。モメンタム / MA200 / ATR / 流動性などを DuckDB 経由で計算する設計（calc_momentum 等、実装途中）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Implementation details & safety
- DB 利用:
  - 監視系は sqlite（monitoring.db）を使用。DuckDB は分析用に併用。
  - paper_trading 環境では paper_trading.db を使用して本番データと完全に分離する設計。
- 停止制御:
  - 起動スクリプト双方で data/stop_requested.flag の検知による安全停止を採用。
- フォールバックと警告:
  - 無効な環境変数や不整合な設定は明示的に警告／例外を発生させる設計（例: PAPER_FILL_MODE の不正値、KABUSYS_ENV の不正値）。
  - ログディレクトリ作成失敗やプロセス優先度変更失敗は警告で処理を継続する（可用性重視）。
- 将来の拡張ポイント（コードコメントより抜粋）
  - position_sizing: 銘柄ごとの lot_size（単元株）を銘柄マスタで扱う拡張。
  - risk_adjustment: price 欠損時のフォールバック価格（前日終値等）の導入検討。
  - factor_research: DuckDB を用いたファクター計算処理の完成とテスト整備。

---

メジャー/マイナー/パッチのポリシーは semver 準拠を想定しています（本リリースは初期リリース v0.1.0）。