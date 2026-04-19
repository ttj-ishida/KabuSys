# CHANGELOG

すべての重要な変更は Keep a Changelog の慣例に従って記載します。  
このファイルは、コードベース（リリース v0.1.0 相当）の現状から推測して作成した変更履歴です。

## [0.1.0] - 2026-04-19

### 追加 (Added)
- 実行用エントリポイントを追加／整備
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。環境に応じて本番 DB / ペーパートレード用 DB を切り替え、BrokerClientFactory を使ってブローカークライアントを生成、ExecutionEngine をスレッドで実行・停止する制御を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。

- 環境設定／検証ツールを追加
  - config_setup.py: .env の対話式ウィザードを実装。既存 .env 読み込み、項目説明、マスク表示、保存機能を提供。
  - validate_config.py: .env と config/*.yaml の起動前検証ツールを追加。必須環境変数チェック、パス存在チェック、YAML のパース検証（PyYAML があれば）や本番環境向けのガードを含む。--strict オプションをサポート。

- 環境設定管理
  - config.py: 自動 .env ロード機能（プロジェクトルート検出）、.env パースの堅牢化（クォート、export 形式、インラインコメント処理等）、Settings クラスによる環境変数のプロパティ化とバリデーションを実装。

- ペーパートレード検証ツール
  - tools/paper_verification_report.py: ペーパートレード用 SQLite DB を解析して、稼働率、注文成功率、送信率、レイテンシ（P95 など）を集計して PASS/FAIL 判定するレポート生成スクリプトを追加。コマンドライン引数で日付範囲・DB パスを指定可能。

- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py: シグナルの候補選択（スコア降順、同点時 tie-break）と重み計算（等金額、スコア加重）を実装。スコア全0 の場合のフォールバックを含む。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を追加。未知レジームは警告してフォールバック。
  - portfolio/position_sizing.py: 各銘柄の発注株数計算を実装（allocation_method: risk_based / equal / score）。単元（lot_size）で丸め、1銘柄上限・aggregate cap（利用可能現金超過時のスケーリング）や cost_buffer を考慮したスケールダウンロジックを実装。余剰キャッシュの再配分アルゴリズムを追加。

- ユーティリティ
  - utils/logging_setup.py: ルートロガーの統一設定ユーティリティを実装。stdout への StreamHandler と日次ローテートする TimedRotatingFileHandler（logs/<app_name>.log、30日保持）を設定。LOG_DIR/LOG_LEVEL の解決、既存ハンドラのクリーンアップ、ファイル出力失敗時のフォールバックに対応。
  - utils/process_priority.py: psutil を使ったクロスプラットフォームのプロセス優先度設定（high/normal/low）と CPU affinity 設定ユーティリティを実装。Windows / POSIX の差分を吸収し、権限不足等を安全にハンドリング。

- research/factor_research.py（ファクター計算）
  - DuckDB 接続を受けてモメンタム等のファクターを計算するモジュールを追加（モジュール冒頭と設計方針を実装済み、モメンタム計算関数の雛形を含む）。

- パッケージ定義
  - __init__.py にバージョン（__version__ = "0.1.0"）と公開モジュール一覧を追加。

### 変更 (Changed)
- 実行スクリプト動作
  - run_execution/run_monitoring が起動時にプロセス優先度を "high" に設定するよう変更（set_process_priority を呼び出し）。
  - run_execution は KABUSYS_ENV=paper_trading 時に paper_sqlite_path を使用して本番 DB と分離。init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等処理）。
  - run_monitoring は Monitoring が KABUSYS_ENV にかかわらず本番 sqlite_path を利用する方針を明示。

- 環境読み込みロジック
  - config.py: 自動 .env ロードの優先順位を OS 環境変数 > .env.local > .env として実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード抑止を追加。

- ログ出力
  - logging_setup.py: 標準出力は stdout を使用するように明確化（cron 等でリダイレクトしやすくするため）。

- ポートフォリオ／リスク関係の実装の詳細化
  - risk_adjustment.calc_regime_multiplier: mapping を実装（bull/neutral/bear）し、未知レジームでの警告とフォールバックを追加。
  - position_sizing: risk_based と equal/score の両方のフローを詳細実装し、aggregate cap のスケーリングと lot_size 丸め・残差配分処理を追加。

### 修正 (Fixed)
- .env パーサの堅牢化（config._parse_env_line）
  - export プレフィックス対応、クォート内でのバックスラッシュエスケープ処理、インラインコメント処理（クォートなしの場合は '#' の直前が空白であればコメントと認識）等の改善により、実運用での .env 記述パターンに対応。

- CLI の妥当性チェック
  - validate_config.py の各チェック関数で、不足やプレースホルダ値を警告/エラーとして検出するロジックを追加。

### セキュリティ (Security)
- 秘匿情報の取り扱い
  - config_setup の対話式 UI ではシークレット項目（J-Quants トークン、kabu API パスワード）をマスクして表示。.env に平文で保存する旨の注意を README 相当のヘッダに記載。

### 既知の制限 / 注意事項（ドキュメント的なメモ）
- position_sizing は現時点で単元（lot_size）を全銘柄共通と想定している（将来的に銘柄別 lot_size を導入予定）。
- apply_sector_cap は sector_map に存在しない銘柄を "unknown" とみなし、その銘柄にはセクター上限を適用しない。price_map に欠損（0.0）があるとエクスポージャーが過少見積りされる可能性があり、将来的にフォールバック価格を検討する旨の TODO コメントあり。
- logging_setup はログディレクトリ作成に失敗した場合にファイル出力をスキップして stdout のみで継続する設計。
- process_priority, set_cpu_affinity は権限不足や未対応 OS の場合は警告を出してスキップする安全設計。
- research/factor_research.py の実装は途中（モメンタム計算関数の雛形あり）。完全なファクター計算ロジックは今後の実装予定。

### 破壊的変更 (Breaking Changes)
- なし（このリリースは新機能追加と内部実装の整備が中心であり、既存 API の破壊的変更は含まれていない想定）

---

使用上の補足（コマンド例）
- .env 初期化ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視プロセス起動:
  - python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

（注）上記はコードベースの内容から推測してまとめた CHANGELOG です。環境や依存ライブラリの有無により挙動が変わる箇所があるため、実行前に validate_config.py 等で設定を確認してください。