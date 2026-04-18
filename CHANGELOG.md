# Changelog

すべての重要な変更点を Keep a Changelog の形式で記載します。  
日付はリポジトリ内容から推測して付与しています。実際のリリース日・バージョン運用に合わせて適宜修正してください。

フォーマット:
- Unreleased: 今後の変更予定・未完成/要改善点
- 各バージョン: そのリリースで追加・変更・修正された内容

---

## [Unreleased]

### 追加予定 / 改善予定
- research/factor_research.py のファクター計算機能（calc_momentum など）の実装完了。現状ファイルの途中で実装が途中のため、完全なファクター計算とテストを追加予定。
- テストカバレッジと CI ワークフローの整備（現在はコード本体のみから推測）。
- 銘柄別 lot_size のサポート強化（現在は global lot_size 固定、将来的に銘柄毎の lot_map を想定）。
- logging のファイルハンドラ作成失敗時のフォールバック動作の追加通知やリトライ。

---

## [0.1.0] - 2026-04-18

初回公開想定リリース。自動売買システム「KabuSys」のコアユーティリティ、エントリポイント、ポートフォリオ構築、監視、設定ツール群を含む。

### 追加
- パッケージ基盤
  - パッケージバージョンを `__version__ = "0.1.0"` として定義（src/kabusys/__init__.py）。
- 起動スクリプト / デーモン
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は常に本番の sqlite_path を使用（環境に依らず監視 DB を共通化）。
    - 停止フラグファイル（data/stop_requested.flag）を検知してループを終了。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 専用 SQLite を使用（data/paper_trading.db）し、MockBrokerClient を利用して本番 DB と分離。
    - エンジンはデーモン Thread で実行、停止フラグで安全停止。PID ファイル管理。
- 設定・環境管理
  - config.py: 環境変数読み込み・ラッパー Settings を実装。
    - 自動 .env ロード（プロジェクトルートに .env / .env.local がある場合。ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化）。
    - .env パースは export 形式やクォート、エスケープ、インラインコメント機構に対応。
    - 各種設定プロパティを提供（J-Quants / kabu API / DB パス / PID/kill flag /監視しきい値 / env/log レベル判定 等）。
    - Paper Trading の動作モード（PAPER_FILL_MODE）を検証（instant/partial/never/reject）。
- 設定ユーティリティ
  - config_setup.py: 対話式 .env ウィザードを追加。既存 .env 読み込み、シークレット扱い項目のマスク表示、ファイルへの保存。
  - validate_config.py: 起動前検証 CLI を追加。必須環境変数、KABUSYS_ENV 値、ログレベル、DB パスの存在チェック、config/*.yaml の存在とパース検証（PyYAML があればパース検証を実行）。`--strict` オプションで警告を失敗扱いに可能。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。
    - stdout ストリームハンドラ + 日次ローテートファイルハンドラ（TimedRotatingFileHandler、30日分保持）。
    - LOG_LEVEL / LOG_DIR 解決順を実装、既存ハンドラのクリア処理を含む。
    - ログディレクトリ作成に失敗してもコンソール出力にフォールバック。
  - utils/process_priority.py: プロセス優先度（high/normal/low）と CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX（Linux/Mac/FreeBSD）を抽象化して nice / priority を設定。
    - 権限不足時は警告を出し処理をスキップ。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選定。
    - calc_equal_weights, calc_score_weights: 等配分・スコア加重配分。全スコアが 0 の場合は等配分にフォールバックし warning を出力。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限を超える場合に候補を除外するロジック（unknown セクターは制限対象外）。当日売却予定銘柄をエクスポージャー計算から除外可能。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた資金乗数を返す。未知レジームは 1.0 でフォールバック（警告）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method による発注株数算出（risk_based / equal / score）を実装。
      - risk_based: 損切り幅・リスク率に基づく株数決定。
      - equal/score: 重みに基づく投下額から株数算出。
      - 単位株（lot_size）で丸め、単銘柄上限 (max_position_pct) や aggregate cap（available_cash）超過時のスケーリングと残差処理を実装。
      - cost_buffer により手数料・スリッページを保守的に見積もる。
- 監視 DB 初期化
  - monitoring/monitoring_db.init_monitoring_db を利用して起動時に監視テーブルの存在を保証（冪等）。
- Execution コンポーネント組立て（run_execution から推測）
  - BrokerClientFactory によるブローカークライアント生成（paper_trading 時は Mock を想定）。
  - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の連携。
  - RiskManager のデフォルト設定（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）、リスク却下数など。
    - デフォルト閾値: uptime >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 latency <= 200 ms。
    - --from/--to/--db オプションで期間・DB 指定が可能。DB にテーブルが存在しない場合は耐障害的に N/A 扱い。
- research/factor_research.py（研究用）
  - DuckDB を利用したファクター計算の設計と一部定数（モメンタム窓長等）を実装。関数の実装途中（calc_momentum が途中まで）であることをコメントで明記。
- エクスポート
  - portfolio パッケージは主要関数を __all__ で公開。

### 変更
- なし（初回リリース想定のため大きな変更履歴はなし。ドキュメント化により挙動が明確化）。

### 修正
- なし（初期実装）。

### 既知の制約 / 注意点
- .env 自動読み込みはプロジェクトルート検出に依存（.git または pyproject.toml）。配布環境では無効化オプション有り（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
- run_monitoring は監視用 DB として常に Settings.sqlite_path を使用する設計（環境に依らず本番 DB を参照する点に注意）。
- price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性があり、将来的に価格フォールバックを検討する旨コメントあり。
- position_sizing の lot_size は全銘柄共通。将来的に銘柄別単元対応の拡張を想定している。
- research/factor_research.py は未完。ファクター計算を利用する機能はまだ完全ではない。

### セキュリティ
- なし（外部公開鍵/トークンの取り扱いは .env で管理する想定、.env の Git コミット禁止を README 等でも推奨すべき）。

---

参考: 今後のリリースに向けたタスク（推奨）
- factor_research の完成とユニットテスト追加
- Broker/Execution 系の単体テスト・統合テストの整備（paper_trading DB を活用）
- ログ周りの異常系テスト（ログディレクトリ作成失敗等）
- ドキュメント（README、運用手順、デプロイ・サービス化スクリプト）
- CI / 自動静的解析・型チェック導入

---

（注）この CHANGELOG は提供されたコードを元に「コードの振る舞い・意図」から推測して記載しています。実際の変更履歴やリリース運用方針に応じて適宜調整してください。