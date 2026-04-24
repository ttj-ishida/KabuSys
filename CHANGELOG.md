# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルは、リポジトリ内のコード（src/kabusys/ 以下）から推測できる機能追加・改善・注意点を基に作成した推定の変更履歴です。

注: 実際のコミット履歴がないため、内容はコードの実装から推測したものです。

## [0.1.0] - 2026-04-24

### 追加 (Added)
- プロジェクト初期リリース相当の主要コンポーネントを追加。
- 実行エントリ / 運用ツール
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=`paper_trading` 時は専用の paper_trading DB を使用し、MockBrokerClient を利用する設計。
    - 停止フラグ（data/stop_requested.flag）および PID ファイル管理をサポート。
  - run_monitoring.py: SystemMonitor を定期実行するポーリングスクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60秒）。
    - 停止フラグ検知でループを終了。
- 設定関連 CLI / ユーティリティ
  - config_setup.py: 対話式 .env 作成 / 更新ウィザードを追加（.env を生成・書き込み）。
  - validate_config.py: 起動前に .env や config/*.yaml の検証を行う CLI を追加（--strict モード搭載）。
- 環境設定読み込み
  - config.py: .env 自動読み込み（プロジェクトルート検出）と堅牢な .env パースロジックを実装。
    - export 形式、クォート文字列、インラインコメント等に対応。
    - 必須環境変数取得用のヘルパ（_require）と Settings クラスを提供。
    - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の入力検証を実装。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py: StreamHandler（stdout）と日次ローテーションのファイルハンドラを組み合わせた統一ログ設定を実装。
    - ログディレクトリ作成に失敗した場合はファイル出力を無効化してコンソール出力のみで継続。
  - utils/process_priority.py: プロセス優先度（high/normal/low）設定と CPU affinity 固定機能を提供。
    - Windows / POSIX を抽象化し、権限不足等の失敗は警告でスキップする堅牢性を実装。
- ポートフォリオ構築モジュール（純関数）
  - portfolio/portfolio_builder.py: シグナル選定（select_candidates）と等金額・スコア加重（calc_equal_weights, calc_score_weights）を実装。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。
  - portfolio/position_sizing.py: 各銘柄の発注株数計算（複数方式対応: risk_based, equal, score）、単元株丸め、aggregate キャップによるスケーリング、cost_buffer を考慮した保守的見積りを実装。
  - portfolio/__init__.py: 主要関数のエクスポート。
- 分析／検証ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を計算し PASS/FAIL 判定を出力。
    - デフォルト DB は data/paper_trading.db（環境変数および --db オプションで上書き可）。
- 研究用モジュール（部分実装）
  - research/factor_research.py: DuckDB を使ったファクター計算基盤（モメンタム、Value、Volatility、Liquidity）を実装開始。
    - モメンタム計算 calc_momentum の実装が開始されている（コード末尾で途中の可能性あり）。

### 変更 (Changed)
- Monitoring / Execution のデータベースの扱いが明確化
  - 監視（monitoring）は KABUSYS_ENV に関係なく production の sqlite_path を使用する設計になっている（run_monitoring.py）。
  - Execution は paper_trading 環境時に専用の paper_sqlite_path を使用して本番 DB と分離（run_execution.py）。
- ロギングの挙動改善
  - stdout を標準出力に使う方針に統一（sys.stderr ではなく stdout）、Cron 等での運用を想定した設計。

### 修正 (Fixed)
- 環境変数パースの安定化
  - .env のパースで export キーワードやシングル/ダブルクォート内のエスケープ、行内コメント等に対応。
  - MONITOR_POLL_INTERVAL に不正値が設定された場合にデフォルトへフォールバックする処理を追加（run_monitoring.py）。
- SQL / DB 初期化の安全化
  - init_monitoring_db を利用して monitoring 用テーブル存在を保証（冪等に初期化）。

### 注意事項 / 既知の制約 (Known issues)
- research/factor_research.calc_momentum がファイル末尾で途中（start_da で切れている）になっており、未完の可能性があります。研究用ファクター計算は今後の実装が必要です。
- position_sizing の将来改善点として、銘柄ごとの lot_size を個別に扱う拡張（stocks マスタ参照）がコメントで示されており、現状は全銘柄共通の lot_size を想定しています。
- process_priority/set_cpu_affinity は権限やプラットフォーム依存で動作しない場合があり、その場合は警告を出してスキップする設計です。
- apply_sector_cap の price 欠損（0.0）時にエクスポージャーが過少見積もられる点が TODO コメントで指摘されています。
- .env 自動読み込みはプロジェクトルートの検出に依存するため、配布後や特殊な配置では自動読み込みがスキップされる可能性があります（_find_project_root の挙動）。

### ドキュメント / コメント
- 各モジュールに設計方針や参照ドキュメント（例: PortfolioConstruction.md, StrategyModel.md）への言及があり、設計がドキュメント準拠で行われていることが示されています。
- config_setup の .env 書式や注意点（.env を絶対に Git にコミットしない等）を明示。

### セキュリティ (Security)
- 機密情報（API トークンやパスワード）は .env に保存する想定であり、config_setup の出力 / README に「Git にコミットしない」旨の注意を含めている点は配慮あり。
- 実行前検証ツール (validate_config) により本番向けの注意点（LINE 設定未設定、KILL_FLAG_CLEAR_ON_START 等）を検出して警告する仕組みがある。

---

将来のリリースでは、未完のファクター計算の完成、テストケース・CI の整備、銘柄毎の lot_size サポートやより厳密な価格フォールバック処理の追加などが想定されます。必要であれば、この CHANGELOG を基により詳細なリリースノートや担当者向けの TODO リストを作成します。