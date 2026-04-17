CHANGELOG
=========

すべての注目すべき変更をこのファイルに記録します。  
このファイルは「Keep a Changelog」の形式に準拠しています。

Unreleased
----------

Added
- 全体
  - プロジェクト初期機能の拡張に伴う各種モジュールを追加/整備。
  - DuckDB / SQLite を併用するデータ処理基盤の導入（prices_daily / raw_financials 等を想定）。
- config
  - .env 自動ロード機能を実装（プロジェクトルートの .env, .env.local を優先度付で読み込む）。
  - .env パーサの強化:
    - export KEY=val 形式対応、クォート文字列（シングル/ダブル）とバックスラッシュエスケープ処理の実装。
    - コメントの取り扱い、無効行のスキップ等に対応。
  - Settings クラスを追加し、環境変数をラップして型変換・バリデーションを実行（J-Quants / kabu API / DB パス / Paper Trading 設定 / 監視閾値 等）。
  - 自動ロード無効化用 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 環境変数の未設定チェックを行う _require() を導入して必須変数の早期検出を実現。
- run_execution / run_monitoring
  - 実行エントリスクリプトを追加:
    - run_execution: ExecutionEngine を起動するスクリプト。KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用して本番 DB と分離。
      - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
      - Engine を別スレッドで実行し、 data/stop_requested.flag による外部停止制御と execution.pid 管理。
    - run_monitoring: SystemMonitor をポーリングで定期実行するスクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可能（デフォルト 60 秒）。監視は本番 sqlite_path を環境にかかわらず使用する設計。
  - 起動時にプロセス優先度を設定する仕組みを導入（utils.process_priority.set_process_priority を呼び出し）。
- utils.process_priority
  - クロスプラットフォームなプロセス優先度設定ユーティリティを実装（Windows の HIGH_PRIORITY_CLASS / POSIX の nice 値対応）。
  - CPU affinity 設定関数 set_cpu_affinity を追加（最初の N コアに固定）。
  - 権限不足や未対応 OS の場合は警告して安全にスキップするフェイルセーフを実装。
- portfolio
  - portfolio_builder: 候補選定（select_candidates）および配分重み計算（calc_equal_weights / calc_score_weights）を実装。スコア総和が 0 の場合は等金額配分にフォールバック。
  - risk_adjustment: セクター集中上限を適用する apply_sector_cap、マーケットレジームに応じた投下資金乗数 calc_regime_multiplier を実装。unknown セクターの扱い、売却予定銘柄の除外等に対応。
  - position_sizing: 発注株数計算 calc_position_sizes を実装。risk_based / equal / score の配分方式に対応し、単元株丸め、個別上限・全体上限（aggregate cap）スケーリング、cost_buffer による保守的見積り、残差に対する lot 単位での再配分ロジックを備える。
- research
  - factor_research: モメンタム（calc_momentum）、ボラティリティ／流動性（calc_volatility）、バリュー（calc_value）ファクター計算を実装。DuckDB SQL を用いて prices_daily / raw_financials を直接参照する設計。
  - feature_exploration: 将来リターン calc_forward_returns、スピアマンランク相関による IC 計算 calc_ic、ランク関数 rank、ファクター統計サマリー factor_summary を実装。外部依存を持たず純粋 Python 実装。
  - research パッケージの __all__ を整備し、zscore_normalize（kabusys.data.stats を利用）と合わせてエクスポート。
- tools.paper_verification_report
  - Paper Trading の検証レポート生成ツールを追加。CLI（--from/--to/--db）で期間指定可能。
  - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を算出。閾値（稼働率 99%、成立率 90%、送信率 95%、P95 200 ms）に基づく PASS/FAIL 判定を出力。
  - P95 計算、公平な日付フィルタ生成、DB 存在チェックやテーブル未存在時の回復的ハンドリングを実装。
- ai.news_nlp
  - ニュース記事を OpenAI（gpt-4o-mini）でスコアリングする設計を追加。バッチ処理、トークン肥大対策（記事数/文字数制限）、エラー時の指数バックオフ、レスポンス検証、スコアクリッピング（±1.0）などを想定。
  - calc_news_window 実装（JST に基づくニュース収集ウィンドウ → UTC に変換）。
  - score_news の前半設計（API キー解決、ウィンドウ計算、記事集約開始）を実装。
  - 実装方針として「ルックアヘッドバイアスを防ぐため datetime.today()/date.today() を参照しない」等の注意点を明記。
- package metadata
  - __version__ を 0.1.0 に設定（パッケージ初期バージョン）。

Changed
- なし（Unreleased は新規機能中心のため変更履歴は主に Added）

Fixed
- なし（主に新規実装）

Known issues / TODO
- ai.news_nlp.score_news の実装が途中で切れており、記事集約以降の処理（OpenAI 呼び出し、レスポンス処理、DuckDB への書き込み）が未完。Unreleased のうち優先実装項目。
- position_sizing の price フォールバック（price が 0 の場合の扱い）は TODO コメントあり。前日終値や取得原価でのフォールバック検討が必要。
- DuckDB executemany のパラメータ空チェックに関する注意がコード中にあるため、部分失敗時のトランザクション設計やエラーハンドリングを要確認。
- ロギングの詳細レベル調整、ユニットテストの整備、CI パイプラインの追加を推奨。

0.1.0 - 2026-04-17
------------------

Added
- 初期リリース。上記 Unreleased に記載されている主要機能群をパッケージ化してリリース。
  - 環境/設定管理（.env パーサ・Settings）
  - 実行・監視スクリプト（run_execution, run_monitoring）
  - Portfolio 構築（候補選定、重み計算、リスク調整、ポジションサイズ計算）
  - Research（ファクター計算: momentum, volatility, value / feature exploration: forward returns, IC, summary）
  - Tools（paper_verification_report CLI）
  - AI ニュース NLP （設計および一部実装）
  - utils（process_priority / CPU affinity）
  - DuckDB / SQLite を用いたデータ処理基盤との統合

Security
- なし

Deprecated
- なし

Removed
- なし

注記
- 本 CHANGELOG はコードの静的読み取りに基づいて推測して作成しています。実際のリリースノート作成時は変更セット（コミットログ）や実装完了状況に合わせて更新してください。