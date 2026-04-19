CHANGELOG
=========

すべての重要な変更点を記録します。このファイルは "Keep a Changelog" の形式に準拠しています。変更は下位互換性の観点で分類しています（Added, Changed, Fixed, ...）。

[Unreleased]
------------

（現時点では特に未リリースの変更はありません）

[0.1.0] - 2026-04-19
-------------------

Added
- 初回リリース: KabuSys v0.1.0 を公開。
- 実行スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。環境により paper_trading 用の MockBrokerClient を使用し、ペーパートレード時は data/paper_trading.db に記録して本番 DB と分離する挙動をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ（data/stop_requested.flag）を検知してグレースフルに終了する仕組みを備える。
- 設定関連
  - config.py: 環境変数/ .env の読み込みと設定取得を担当する Settings クラスを実装。自動 .env ロード（プロジェクトルート検出: .git または pyproject.toml を基準）、OS 環境変数保護（上書き禁止）、クォート／エスケープ対応の .env パーサを備える。
  - config_setup.py: インタラクティブな環境設定ウィザードを追加。.env の初回作成・更新を支援し、秘密値はマスク表示して保存可能。
  - validate_config.py: 起動前検証ツールを追加。必須環境変数、KABUSYS_ENV の妥当性、DB パス、config/*.yaml の存在と YAML パース（PyYAML があれば）を検査。--strict モードで警告も失敗扱いにできる。
- ログ・プロセスユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加。コンソール（stdout）と日次ローテートファイルハンドラ（30 日保持）を設定。LOG_DIR / LOG_LEVEL の解決順やハンドラ重複回避を実装。
  - utils/process_priority.py: プロセス優先度（Windows / POSIX 対応）と CPU affinity 設定を提供。例外発生時は安全にスキップして警告出力する。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定と等分配・スコア加重配分の関数を実装（select_candidates, calc_equal_weights, calc_score_weights）。
  - portfolio/risk_adjustment.py: セクター集中制限の適用、レジームに応じた投下資金乗数（calc_regime_multiplier, apply_sector_cap）を実装。未知レジーム時はフォールバックと警告出力。
  - portfolio/position_sizing.py: 各種配分方式（risk_based / equal / score）に基づく株数決定ロジックを実装。単元株（lot_size）、cost_buffer（手数料/スリッページ見積）および aggregate cap のスケーリング処理をサポート。
  - portfolio/__init__.py: ポートフォリオ関連 API を整理してエクスポート。
- 解析・レポート
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。システム稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計し PASS/FAIL 判定を行う。閾値はソース内定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 200 ms）。コマンドラインで期間指定可能（--from / --to）かつ DB パスをオーバーライド可。
- 研究モジュール（骨格）
  - research/factor_research.py: DuckDB を使ったファクター計算モジュールの骨格を追加（Momentum, Value, Volatility, Liquidity を想定）。設計方針と定数を定義し、calc_momentum 等の計算関数を実装する方向で準備。

Changed
- なし（初回リリースのため）

Fixed
- なし（初回リリースのため）

Security
- なし

Notes / 実装に関する補足
- 設定の自動ロードはデフォルトで有効だが、テスト等で無効化するために KABUSYS_DISABLE_AUTO_ENV_LOAD を用意。
- .env の自動ロードでは OS 環境変数を保護するため既存の環境変数は上書きされない（.env.local を override=True で読み込むが protected set によってシステム環境は保護される）。
- ロギングは標準出力（stdout）を優先して使用する設計。cron 等で stdout/stderr をリダイレクトする運用を想定。
- 実運用に際しては config/*.yaml（system_config.yaml 等）の生成（scripts/generate_config.py を参照）および validate_config による事前チェックを推奨。
- Paper Trading と Live はデータベース・ブローカーの面で明確に分離される設計（paper_sqlite_path / is_paper 判定、BrokerClientFactory）。

今後の予定（例）
- factor_research の各ファクター実装の完了（calc_momentum の続きなど）。
- 単体テスト・統合テストと CI 設定の追加。
- 銘柄毎の lot_size を考慮した拡張（stocks マスタ参照）。
- 監視・アラート（LINE 通知）周りの連携強化。

----- 
（補足）この CHANGELOG は提供されたソースコードから推測して作成しています。実際の変更履歴およびリリースノートはプロジェクト運用ポリシーに合わせて適宜編集してください。