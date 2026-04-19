# Changelog

すべての変更は Keep a Changelog のフォーマットに従い、逆時系列（新しいものが上）で記載しています。  
このファイルはコードベースから推測して作成した変更履歴（日本語）です。

## [Unreleased]

- ドキュメント化や小さな改善（特になし、次リリースにて反映予定）。

---

## [0.1.0] - 2026-04-19

初回リリース。日本株自動売買システム「KabuSys」の主要コンポーネントを実装・公開しました。主な追加点は以下の通りです。

### 追加 (Added)
- 全体
  - パッケージ初期リリース（バージョン 0.1.0）。
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"`。

- 起動スクリプト
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）を監視して安全にループを終了。
    - 監視モジュールは実行環境にかかわらず本番用の sqlite_path を使用して初期化。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 用の専用 SQLite（data/paper_trading.db 等）を使用し、本番 DB と分離。
    - BrokerClientFactory によりブローカークライアントを生成（実運用/モックの切替を想定）。
    - ExecutionEngine を別スレッドで起動し、停止フラグ（data/stop_requested.flag）で停止可能。PID ファイルをサポート。

- 設定管理 / ツール
  - config.py: 環境変数 / .env 管理モジュールを追加。
    - プロジェクトルートを .git または pyproject.toml で自動検出し、`.env` / `.env.local` を自動読み込み（OS 環境変数は保護）。
    - .env のパースは export 形式、シングル/ダブルクォート、エスケープ、行内コメントなどの一般的ケースに対応。
    - 必須項目チェック用の `_require()`、各種設定プロパティ（DB パス、KABUSYS_ENV、ログレベル、Paper Trading 設定など）を提供。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動読み込みを無効化可能（テスト向け）。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - よく使う設定項目を対話的に入力し `.env` を生成。
    - シークレット項目はマスク表示、既存値の再利用、保存確認をサポート。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数の存在確認、KABUSYS_ENV・LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在と YAML パース（PyYAML 利用可の場合）等をチェック。
    - `--strict` オプションで警告もエラー扱いにできる。
    - 本番モード（live）向けのガード（LINE通知設定の未設定警告、KILL_FLAG_CLEAR_ON_START の注意喚起）を実装。

- ロギング / プロセス制御
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler、30日保持）をルートロガーに設定。
    - `LOG_DIR` / `LOG_LEVEL` / 引数でログ出力先やレベルを指定可能。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py: プロセス優先度・CPU affinity ユーティリティを追加。
    - Windows / POSIX（Linux, macOS, FreeBSD）での差分を吸収して優先度設定（high/normal/low）を提供。
    - CPU affinity を最初の N コアに固定する関数を追加（権限や未サポート環境では警告のうえスキップ）。

- Portfolio（ポートフォリオ構築）
  - portfolio/portfolio_builder.py:
    - 候補選定 (select_candidates)：スコア降順、同点は signal_rank でブレーク。
    - 重み算出関数: calc_equal_weights と calc_score_weights（スコアが全て 0 の場合は警告して等配分へフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap：セクター集中制限ロジックを実装。既存保有を考慮して、指定比率を超えるセクターの新規候補を除外。
    - calc_regime_multiplier：市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは 1.0 にフォールバック）。
    - 実装中の注意点（TODO）：価格欠損時のフォールバックなどについての注釈を残す。
  - portfolio/position_sizing.py:
    - calc_position_sizes：allocation_method（risk_based / equal / score）に応じた発注株数計算を実装。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash を超えた場合のスケーリングと残差の優先配分）をサポート。
    - 手数料・スリッページ見積り用 cost_buffer を考慮。

- 監視・モニタリング関連
  - monitoring モジュール初期化（monitoring_db の初期化呼び出しが run_monitoring / run_execution 両方で行われ、冪等性を担保）。
  - SystemMonitor を利用した状態チェック（run_monitoring 内で monitor.check_once() をポーリング実行）。

- Execution（発注実行）関連
  - ExecutionEngine・OrderManager・OrderRepository・Reconciler・RiskManager 等の組み立て（run_execution での起動フロー）を追加。
  - RiskConfig のデフォルトパラメータ（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定し、初期 available_cash を broker.get_available_cash() から取得。

- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率（Fill率）、送信率、レイテンシ（平均 / 最大 / P95）等を集計して PASS/FAIL 判定（閾値はソース内定義）。
    - 閾値（デフォルト）:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - コマンドライン引数で期間指定（--from, --to）および DB パス（--db）を指定可能。

- リサーチ
  - research/factor_research.py: ファクター計算モジュールの骨子を追加（Momentum, Value, Volatility, Liquidity の設計方針と定数設定）。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。
    - 注意: ファイルの途中まで（calc_momentum の実装の先頭）で切れているため、完全実装は今後の作業。

### 変更 (Changed)
- 初回リリースのため既存の大きな変更は無し。内部実装の注釈や TODO、将来の拡張ポイント（銘柄ごとの lot_size 管理、価格フォールバック等）をコードにコメント。

### 修正 (Fixed)
- 初回リリースのためバグ修正履歴は無し。ただし実行時に起こりうる環境差分（ログディレクトリ作成失敗、プロセス優先度設定失敗、CPU affinity 非対応等）に対して警告でフォールバックする実装を行い、稼働性を確保。

### 注意事項 / 既知の制限 (Known issues & notes)
- .env 自動読み込みはプロジェクトルートの検出に依存するため、配布後や特殊配置では自動ロードされない場合がある（その場合は明示的に環境変数を設定してください）。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
- run_monitoring は監視 DB を「環境にかかわらず」 production 用 sqlite_path を使用する設計（監視データは本番監視 DB に記録される想定）。
- risk_adjustment.apply_sector_cap は price_map に価格が欠損（0.0）だった場合に過少評価となる可能性があり、将来的にフォールバック価格（前日終値など）を導入する TODO がある。
- research/factor_research.py の一部が未完（calc_momentum の続きを実装する必要あり）。
- ログディレクトリ作成やファイルハンドラ生成に失敗した場合、ファイル出力はスキップされコンソール出力のみで継続します（警告を出力）。

---

メンテナンスや今後の予定:
- research/factor_research の完全実装（各ファクター計算の SQL + Python 実装）。
- Portfolio の単元株・手数料モデルの強化（銘柄別 lot_size、スリッページ・手数料の実測値導入）。
- ExecutionEngine / BrokerClient のインタフェース整備および統合テスト、さらに paper_trading の検証自動化。
- モニタリングのアラート送信（LINE 連携など）強化。

---
この CHANGELOG はソースコードからの仕様・挙動の推測に基づいて作成しています。実際の変更履歴やリリースノート作成時はコミット履歴やプロジェクト管理情報と突合してください。