# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。日付は本リポジトリの現状 (初期リリース: 0.1.0) を基準としています。コードベースから推測して記載しているため、実際のコミット履歴とは差異がある可能性があります。

## [Unreleased]

## [0.1.0] - 2026-04-22

### 追加 (Added)
- 初期リリース: バックテスト/実運用向け日本株自動売買フレームワークの骨組みを実装。
- CLI / 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV に応じて本番/ペーパートレード用 DB を切り替え、BrokerClientFactory によるブローカークライアント生成、スレッドでのエンジン実行、stop フラグ・PID 管理をサポート。
  - run_monitoring.py: SystemMonitor 起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する設計。
  - kabusys.config_setup: .env の対話式ウィザードを実装。既存 .env 読み込み、入力補助、.env 保存機能を提供。
  - kabusys.validate_config: 起動前の設定検証 CLI を実装。.env や config/*.yaml の存在や基本的な妥当性をチェックし、--strict オプションで警告を Fail 扱いにできる。
- 設定管理
  - kabusys.config: .env / .env.local の自動読込（環境変数により無効化可能）、プロジェクトルート検出ロジック（.git または pyproject.toml 基準）、複雑な .env パーサ（クォート・エスケープ・コメント処理対応）、Settings クラスによるプロパティアクセスを提供。
  - Settings により J-Quants / kabu API トークン、DB パス、Paper Trading 設定（PAPER_FILL_MODE 等）、監視しきい値、環境判定プロパティ（is_live/is_paper/is_dev）を取得可能。
- ポートフォリオ構築関連（純粋関数群）
  - kabusys.portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順＋タイブレークで選定。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア比率で重み化（全スコアが 0 の場合は等金額にフォールバック）。
  - kabusys.portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限を超えている場合に候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた資金乗数を返す。
  - kabusys.portfolio.position_sizing:
    - calc_position_sizes: risk_based / equal / score の各配分方式に対応。損切り・リスク％に基づく株数計算、単元株（lot_size）丸め、aggregate cap によるスケールダウン、cost_buffer を用いた保守的コスト見積りを実装。
- ユーティリティ
  - kabusys.utils.logging_setup: stdout ストリームハンドラと日次ローテーションのファイルハンドラ（TimedRotatingFileHandler、30 日保持）を組み合わせた統一ログ設定を提供。ログディレクトリ作成に失敗した場合はコンソールのみで継続。
  - kabusys.utils.process_priority: psutil を使ったプロセス優先度設定（Windows / POSIX を吸収）、および CPU affinity 設定ユーティリティを実装。権限不足や未対応 OS は安全にスキップして警告出力。
- モニタリング / DB
  - monitoring 初期化フック（init_monitoring_db の呼び出し）を run_execution/run_monitoring に統合。SQLite（monitoring DB）と DuckDB の接続管理を追加。
- ツール
  - kabusys.tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計し、PASS/FAIL 判定を行う。--from/--to/--db オプションに対応。
- リサーチ（雛形）
  - kabusys.research.factor_research: ファクター計算モジュールの骨格を追加。モメンタム等の計算に関する定数と calc_momentum の実装方針を含む（ファイル末尾が一部切れているがモジュールが存在）。

### 変更 (Changed)
- N/A（初期リリースのため該当なし）

### 修正 (Fixed)
- N/A（初期リリースのため該当なし）

### 注意事項 / 既知の制限 (Known issues / Notes)
- run_monitoring はドキュメントどおり「環境にかかわらず」本番 sqlite_path を使用する設計になっているため、テスト実行時に監視対象 DB の混在に注意が必要。
- process_priority / set_cpu_affinity は権限や OS に依存するため、実行環境によっては設定に失敗し警告が出力される可能性がある（安全にスキップされる）。
- .env パーサはかなり堅牢だが、特殊なフォーマットに対する完全互換を保証しない。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- calc_position_sizes:
  - 銘柄ごとの lot_size を現在は共通の引数で扱う。将来的には銘柄マスタによる拡張を想定（TODO コメントあり）。
  - price が欠損（0.0）の場合エクスポージャーやポジション計算で過小評価される可能性があり、前日終値などのフォールバックは未実装。
- apply_sector_cap は sector が "unknown" の銘柄に対して上限を適用しない仕様（意図的な挙動）。
- validate_config は PyYAML 未インストール時に YAML ファイル検証をスキップし警告を出す。
- logging_setup はログディレクトリ作成に失敗した場合、ファイル出力を無効化してコンソールのみで稼働する。
- Paper Trading 実行時は BrokerClientFactory により MockBrokerClient が選択され、data/paper_trading.db に記録される（本番 DB と分離される想定）。
- factor_research の実装はモジュール骨格が中心で、すべてのファクター計算ロジックが完成しているかは要確認（ファイルが途中で終わっている箇所あり）。

### セキュリティ (Security)
- N/A（公開ライブラリの初期構成にセキュリティフィックスは含まれていません）

---

今後のリリース案（想定）
- 単体テストの追加・CI 設定
- ファクター計算の完全実装と最適化
- 銘柄ごとの lot_size サポート等、position_sizing の拡張
- monitoring の更なる拡張（アラート送信・LINE 通知の統合）
- 設定・シークレット管理強化（Vault 等の導入）

ご要望があれば、特定ファイルに対するより詳細な変更点（ファンクション単位の説明や既知の振る舞いの追記）を反映した CHANGELOG の改訂を行います。