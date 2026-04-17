# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
日付はコードベースから推測したリリース日（当該スナップショット取得日）を使用しています。

全般的な注記
- 本 CHANGELOG はソースコードの内容から推測して作成しています。実際のコミット履歴やリリースノートと差異がある場合があります。

Unreleased
- (なし)

[0.1.0] - 2026-04-17
----------------------------------------
Added
- 基本機能の初期実装（KabuSys v0.1.0）。
  - パッケージエントリポイント定義（src/kabusys/__init__.py）。
  - 環境変数・設定読み込み機能（src/kabusys/config.py）。
    - プロジェクトルート検出（.git / pyproject.toml を基準）により .env 自動読み込みを行う（無効化オプションあり: KABUSYS_DISABLE_AUTO_ENV_LOAD）。
    - .env ファイルパーサが export プレフィックス、クォート、エスケープ、インラインコメントを適切に扱うよう実装。
    - Settings クラスを提供し、J-Quants / kabuステーション / DB / 監視 / システム設定等をプロパティ経由で取得可能に。
    - paper_trading 向け設定項目（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH 等）を追加。
    - PID / kill flag / リソース閾値（CPU/MEM/DISK）など監視関係の設定を追加。

- 設定ウィザード CLI（src/kabusys/config_setup.py）。
  - 対話式で .env を生成・更新するウィザードを提供。
  - 秘匿項目はマスク表示、デフォルト・選択肢表示、既存 .env の読み取りと統合に対応。
  - 生成される .env のテンプレートは Git にコミットしない旨のヘッダを含む。

- 設定検証 CLI（src/kabusys/validate_config.py）。
  - 必須環境変数の有無、KABUSYS_ENV / LOG_LEVEL の妥当性、DBパスの親ディレクトリ確認、config/*.yaml の存在と YAML パースの検証（PyYAML が利用可能な場合）等をチェック。
  - --strict オプションで警告をエラー扱いにできる。

- 実行用起動スクリプト
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
    - プロセス優先度を最初に "high" に設定。
    - KABUSYS_ENV=paper_trading 時は paper 用専用 SQLite DB を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成（paper/live を透過的に扱う想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を別スレッドで起動。停止フラグ（data/stop_requested.flag）検知で安全に停止。
    - PID ファイル出力場所を指定可能。

  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番の sqlite_path を使用する設計。
    - 停止フラグファイル検知でループを終了、例外発生時はログに記録して次ポーリングへフォールバック。

- モニタリング DB 初期化呼び出し（init_monitoring_db を run_execution/run_monitoring で実行してテーブル存在を保証）。

- Portfolio 構築関連（純粋関数群、DB 参照なし）
  - 候補選定 / 等配分・スコア配分（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates、calc_equal_weights、calc_score_weights（スコア全0 の場合のフォールバック警告含む）。
  - セクター上限適用、レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター別時価を計算し上限を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 'bull'/'neutral'/'bear' に応じた投下資金乗数（フォールバックと警告あり）。
  - ポジションサイジング（src/kabusys/portfolio/position_sizing.py）
    - risk_based / equal / score の割当方式に対応。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash に対するスケーリング）実装。
    - cost_buffer を考慮した保守的見積り、スケールダウン時に残差基準で lot 単位を再配分するアルゴリズム実装。

- 研究・計算モジュール（src/kabusys/research/factor_research.py）
  - DuckDB 接続を受けて各種ファクターを計算する機能を実装。
    - モメンタム（1M/3M/6M・MA200乖離）、ボラティリティ（ATR20 等）、流動性指標を計算するための SQL ベース実装。
    - データ不足時には None を扱う安全設計。
    - DuckDB を用いた列指向集計で大規模データに対応。

- ツール（src/kabusys/tools/paper_verification_report.py）
  - Paper Trading 検証レポート生成ツールを追加。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシなどを集計。
    - PASS/FAIL の判定基準を定義（稼働率 >= 99%, fill_rate >= 90%, send_rate >= 95%, P95 <= 200 ms）。
    - 日付範囲フィルタや DB パス指定オプションをサポート。

- プロセス制御ユーティリティ（src/kabusys/utils/process_priority.py）
  - set_process_priority(level) によるクロスプラットフォーム優先度設定（Windows / POSIX）を実装。失敗時は警告でフォールバック。
  - set_cpu_affinity(cpu_count) によりプロセスの CPU affinity を最初 N コアに固定可能（未対応 OS や権限不足時は警告でスキップ）。

Changed
- 各コンポーネントでログ出力を適切に追加・整備（起動ログ、警告、例外トレースなど）。
- run_execution と run_monitoring でプロセス優先度設定を起動直後に行うよう統一。

Fixed
- 環境値のパースと検証に関する堅牢化（例: MONITOR_POLL_INTERVAL の 0 以下や非整数入力をハンドルしてデフォルトにフォールバック）。
- DB パスや .env の読み込み失敗時に警告を出しつつ動作継続するよう改善。

Notes / Usage hints
- .env 自動読み込みは便利ですが、テスト環境等では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- Paper Trading は本番 DB と分離されるため誤って本番データを汚染する心配が減ります。PAPER_TRADING_SQLITE_PATH と PAPER_FILL_MODE を確認してください。
- 実運用時は KABUSYS_ENV=live の設定や KILL FLAG の設定（KILL_FLAG_CLEAR_ON_START）に注意してください。validate_config の --strict モードで本番向けチェックを厳格化できます。

今後の改善候補（ソースから推測）
- 銘柄ごとの lot_size を stocks マスタで管理して個別化する（position_sizing の TODO）。
- apply_sector_cap の price 欠損時のフォールバック価格導入（前日終値等）。
- monitoring_db や ExecutionEngine の詳細ログ・監査強化（トレース・メトリクス出力）。
- DuckDB のクエリ最適化や並列処理の検討（factor_research のスケール改善）。

--- End of CHANGELOG ---