KEEP A CHANGELOG
All notable changes to this project will be documented in this file.

フォーマット: Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）に準拠。
日付形式: YYYY-MM-DD

[Unreleased]
- なし

[0.1.0] - 2026-04-12
Added
- 初回リリース。KabuSys 自動売買フレームワークのコア機能を実装。
- 環境設定管理 (kabusys.config.Settings)
  - .env / .env.local の自動読み込み（プロジェクトルート検出: .git または pyproject.toml）。
  - export 付き行、クォート文字列、インラインコメントなどを考慮した .env パース実装。
  - 必須環境変数取得ヘルパー (_require)、各種デフォルト値とバリデーション（KABUSYS_ENV, LOG_LEVEL 等）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
- 実行用エントリスクリプト
  - run_execution.py: ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading 時は paper_sqlite_path を用いた DB 分離。
    - BrokerClientFactory を用いたブローカークライアントの抽象化（Mock 対応を想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせてセッション実行。
    - デフォルトの RiskConfig を設定（max_position_pct、max_utilization、rate_limit_per_sec 等）。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関係なく本番 sqlite_path を使用する設計（monitoring 用 DB 初期化含む）。
    - プロセス起動時にプロセス優先度を設定するフックを実行。
- 監視関連
  - monitoring_db 初期化呼び出しを各起動スクリプトで保証（冪等に実行）。
- ポートフォリオ構築モジュール (kabusys.portfolio)
  - portfolio_builder: 候補選定 select_candidates、等金額・スコア加重の重み計算 calc_equal_weights / calc_score_weights。
    - スコア合計が 0 の場合は等配分へフォールバックし警告を出力。
  - position_sizing: ポジションサイズ計算 calc_position_sizes（risk_based / equal / score をサポート）。
    - 単元株（lot_size）丸め、単銘柄上限、aggregate cap（利用可能現金超過時のスケーリング）を実装。
    - cost_buffer を考慮した保守的コスト見積り、端数分配アルゴリズムを実装（再現性のため安定ソート使用）。
    - 将来の拡張ポイントとして銘柄別 lot_size マップを検討する TODO を記載。
  - risk_adjustment: apply_sector_cap（セクター集中制限）と calc_regime_multiplier（市場レジームに応じた乗数）。
    - 既存ポジションを基にセクター暴露を計算し、閾値超過セクターの候補除外を行う。
    - レジーム乗数は bull/neutral/bear を対応し未知レジームはフォールバック。
- リサーチ / ファクター計算 (kabusys.research)
  - factor_research: calc_momentum, calc_volatility, calc_value を実装。DuckDB 接続を受け prices_daily / raw_financials を参照してファクターを計算。
    - MA200, ATR20, 1/3/6 ヶ月リターン等を算出。データ不足時は None を返す実装。
  - feature_exploration: calc_forward_returns（将来リターン取得）、calc_ic（Spearman ランク相関）、rank（同順位平均ランク）、factor_summary（基本統計量）。
    - calc_ic は有効レコード数が 3 未満の場合 None を返す安全設計。
  - research パッケージ __init__ で zscore_normalize 等ユーティリティを公開。
- AI ニュース NLP スコアリング (kabusys.ai.news_nlp)
  - raw_news から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）を用いてセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ保存する設計を実装。
  - バッチ処理（最大 20 銘柄 / リクエスト）、トークン肥大化対策（最大記事数・最大文字数トリム）、429/ネットワーク/5xx に対する指数バックオフリトライ（上限回数）を考慮。
  - OpenAI API キー未設定時は ValueError を送出して明示的に要求。
  - スコアは ±1.0 にクリップ、部分失敗時に既存スコアを保護するため対象コードのみ差し替えする戦略を想定。
  - 注: ファイル末尾に実装の断片（ログ出力行での切断）が存在するため、スコア保存後の以降処理に未実装箇所が残る可能性あり（下記 Known issues 参照）。
- ユーティリティ (kabusys.utils)
  - process_priority: set_process_priority / set_cpu_affinity のクロスプラットフォーム実装（Windows / POSIX を吸収）、失敗時は警告でスキップ。
- ツール (kabusys.tools)
  - paper_verification_report: Paper Trading 向け検証レポート生成 CLI。
    - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）を集計し、Pass/Fail 判定を出力。
    - DB 存在チェック、OperationalError に対するフォールバックを実装。

Changed
- なし（初回リリース）

Fixed
- 各所での安全ガードと入力バリデーションを導入・調整
  - MONITOR_POLL_INTERVAL が不正（0 以下や非数）の場合、警告を出してデフォルト 60 秒にフォールバック。
  - PAPER_FILL_MODE の許容値チェックと不正値時の ValueError。
  - .env ロード時の既存 OS 環境変数保護（protected set）を実装し、環境依存の上書きを防止。
  - DuckDB / SQLite 参照クエリでデータ不足や OperationalError が発生した場合に安全にフォールバックしてレポート生成やファクター計算が継続するように対応。
  - calc_score_weights: スコア総和 0 の場合等金額配分へフォールバックして警告。

Removed
- なし

Security
- OpenAI API キーの未設定を明示する安全なエラー処理を実装（APIキーの漏洩を防ぐための直接出力は行わない設計）。

Known issues / TODO
- news_nlp モジュールの末尾で実装が途中で切れている個所が見られます（score_news の最終ログ/後続処理が不完全）。本機能を本番で利用する前にファイル末尾の実装完了と統合テストが必要です。
- portfolio.risk_adjustment.apply_sector_cap 内で price が欠損（0.0）の場合にエクスポージャーが過少見積もられる旨の TODO コメントあり。将来的に前日終値や取得原価をフォールバック価格として扱う拡張を検討する必要があります。
- position_sizing: 現状は全銘柄共通の lot_size（デフォルト 100）を想定。銘柄別単元対応は将来的な拡張ポイント。
- 単体テスト・統合テストは同梱されていません。本リリースでは動作設計に基づく安全ガードを多く導入していますが、環境（DuckDB のスキーマ・SQLite DB）整備後に E2E テスト推奨。

以上

----- 
注: この CHANGELOG は提供されたコードベースの内容（コメント、関数実装、デフォルト値、TODO コメント等）から推測して作成しています。実際のコミット履歴が存在する場合はコミット単位の変更点（作者、詳細差分）を反映することを推奨します。