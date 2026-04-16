# Changelog

すべての非破壊的変更はセマンティックバージョニングに従って記録します。  
このファイルは Keep a Changelog のフォーマットに従っています。  

## [Unreleased]

（現在未リリースの変更はありません）

---

## [0.1.0] - 2026-04-16

初回リリース。自動売買システム「KabuSys」のコア機能を実装しました。以下はコードベースから推測してまとめた主要な追加・設計上の注意点です。

### Added
- 全体
  - パッケージ初期公開: kabusys v0.1.0（__version__ = "0.1.0"）。
  - DuckDB / SQLite を利用したデータ処理基盤を搭載（prices_daily / raw_financials 等を想定）。

- 実行・監視ランナー
  - run_execution.py
    - ExecutionEngine 起動スクリプトを実装。
    - KABUSYS_ENV によるモード分岐: paper_trading の場合は MockBroker を用い、Paper Trading 用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離。
    - プロセス優先度を起動時に設定（utils.process_priority.set_process_priority）し、PID ファイルを管理。
    - 停止フラグ（data/stop_requested.flag）を監視して安全に停止。
    - ExecutionEngine の依存コンポーネント（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler）を組み立てるロジックを含む。
    - RiskManager にデフォルト構成を与え、broker.get_available_cash() を初期ポートフォリオ値として使用。

  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番の sqlite_path を使用する仕様（運用上の意図的な設計）。

- 設定管理
  - config.py
    - 環境変数・.env 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準にサーチ）。
    - .env/.env.local 読み込みの優先度と override/保護（protected）挙動を実装。
    - 多数の設定プロパティを実装（J-Quants / kabu API / LINE / DB パス / 監視しきい値 / 環境判定 等）。
    - PAPER_FILL_MODE のバリデーション（instant, partial, never, reject）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。

- ポートフォリオ構築（pure 関数群）
  - portfolio.portfolio_builder
    - シグナル選定（select_candidates）と重み算出（calc_equal_weights, calc_score_weights）。
    - スコア全0 の場合は等金額配分へフォールバック（警告ログ）。

  - portfolio.risk_adjustment
    - セクター集中制限の適用（apply_sector_cap）。
    - 市場レジームに応じた乗数計算（calc_regime_multiplier）。"bull"/"neutral"/"bear" をサポートし、未知レジームはフォールバックで 1.0。

  - portfolio.position_sizing
    - position sizing ロジック（risk_based / equal / score ベース）を実装。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash）に基づくスケーリング、cost_buffer による保守的見積り、残差配分の実装。

- 研究・リサーチ
  - research.factor_research
    - モメンタム（calc_momentum）、ボラティリティ（calc_volatility）、バリュー（calc_value）ファクター計算。DuckDB を用いた SQL ベースの実装でデータ不足時は None を返す設計。
    - 長期 MA / ATR / turnover 等の定義済みウィンドウを使用。

  - research.feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、統計サマリー（factor_summary）、rank ユーティリティを実装。
    - 外部依存を避け標準ライブラリのみで実装。

  - research.__init__
    - zscore_normalize（data.stats より）含めたエクスポートを整備。

- AI ニュース NLP
  - ai.news_nlp
    - raw_news から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）を用いてセンチメント（-1.0〜1.0）を算出して ai_scores に書き込む処理を設計。
    - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST）、記事トリム（最大記事数・文字数）、バッチ処理（1回最大 20 銘柄）、JSON Mode 指定、レスポンス検証、スコアクリップを実装。
    - 429/ネットワーク/5xx に対する指数バックオフによるリトライ設計。
    - APIキーは引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を使用。未設定時は ValueError。

- ユーティリティ
  - utils.process_priority
    - Windows / POSIX（Linux/Mac/FreeBSD）を吸収したプロセス優先度設定（set_process_priority）を実装。アクセス権限不足や未サポート OS は警告ログを出してフォールバック。
    - CPU affinity を設定する set_cpu_affinity を実装（None で無効、検査・例外ハンドリング付き）。

- ツール
  - tools.paper_verification_report
    - Paper Trading 用の検証レポート作成スクリプトを実装（コマンドライン実行可能）。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等を算出し、定義済み閾値（稼働率 99%、fill rate 90%、send rate 95%、P95 200 ms）で PASS/FAIL 判定。
    - DB 無しやテーブル欠如時に堅牢に N/A を表示する設計。

### Changed
- 初期リリースのため該当なし（新規実装をまとめてリリース）。

### Fixed
- .env パーサーの強化（config._parse_env_line）
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの正しい取り扱いを実装。
- run_monitoring の MONITOR_POLL_INTERVAL 読み取りで不正値に対するフォールバックを追加（負の数や非整数に対して警告してデフォルトを使う）。

### Deprecated
- なし

### Removed
- なし

### Security
- OpenAI API キーは外部に漏れないよう引数／環境変数で扱う設計。キー未設定時は明示的にエラーで停止するため意図せぬ外部送信は発生しない想定。

### 注意・破壊的変更（運用上の重要点）
- 監視（run_monitoring）は KABUSYS_ENV にかかわらず sqlite_path（本番用）を使用します。開発環境で監視データを使い分けたい場合は設定を確認してください。
- Paper Trading（KABUSYS_ENV=paper_trading）は paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離する設計です。Paper と本番の DB を明確に分離してください。
- process priority / cpu affinity の設定はプラットフォーム固有の権限に依存します。AccessDenied 等で設定に失敗した場合はログに警告が出て処理は継続しますが、期待する優先度が適用されない可能性があります。
- AI ニュース処理では OpenAI API のレスポンス検証を行っていますが、API の仕様変更やモデルの挙動変化によりパースエラーが発生する可能性があるため、運用時にはログの監視を推奨します。

---

今後の予定（推測）
- ai.news_nlp の残り実装（記事取得および DB 書き込みの詳細処理の完成）
- テストカバレッジ追加、エンドツーエンド連携テスト、CI 設定
- 銘柄別 lot_size のサポート拡張（stocks マスタからの読み取り）
- さらなる運用監視拡張（アラート連携など）

---

参考: Keep a Changelog — https://keepachangelog.com/（本 CHANGELOG は上記フォーマットに準拠しています）