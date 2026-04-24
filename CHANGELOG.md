# Changelog

すべての変更は Keep a Changelog のガイドラインに準拠して記載しています。  
日付はリリース日を示します。

## [0.1.0] - 2026-04-24

### 追加
- 初版リリース。
- 起動スクリプト／運用ユーティリティ
  - run_execution.py: 実行エンジン起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（既定: data/paper_trading.db）を使用し、MockBrokerClient 経由で分離されたペーパートレードが可能。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可能（デフォルト 60 秒）。停止フラグ（data/stop_requested.flag）検知で安全に終了。
- 設定関連 CLI / ユーティリティ
  - config_setup.py: 対話式 .env ウィザードを追加。.env の初期作成・更新を支援。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パスや config/*.yaml の存在確認（PyYAML が未インストール時は YAML 検証をスキップ）や本番環境向けの追加ガードを実装。--strict オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder: シグナル選定（スコア降順）、等金額配分、スコア加重配分を実装。全スコア 0.0 の場合は等配分へフォールバック。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知のレジームは警告を出してフォールバック。
  - portfolio.position_sizing: 各銘柄の発注株数計算を実装（risk_based / equal / score）。単元株（lot_size）丸め、単銘柄上限・全体利用率上限（aggregate cap）のスケーリング、コストバッファ（手数料・スリッページ見積り）を考慮。
- ログ・プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。コンソール出力は stdout、日次ローテートのファイルハンドラ（TimedRotatingFileHandler）をサポート。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: クロスプラットフォームでのプロセス優先度設定（high/normal/low）および CPU affinity 設定ユーティリティを追加。権限不足や未サポート環境では安全にスキップして警告を出力。
- データ調査ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。P95 計算、稼働率・注文成功率・送信率・レイテンシ指標を集計し PASS/FAIL 判定を行う。CLI で期間指定（--from/--to）と DB パス指定（--db）に対応。
- リサーチ基盤
  - research/factor_research.py: ファクター計算モジュールの骨組みとモメンタム計算用定数を追加（prices_daily / raw_financials を使用する設計）。

### 変更（挙動・設計上の決定）
- 環境変数の自動読み込みを実装
  - プロジェクトルート（.git または pyproject.toml を探索）を基準に .env/.env.local を自動読み込み。読み込み順は OS 環境変数 > .env.local > .env。OS 環境変数は保護（上書き禁止）される。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト等で利用）。
  - .env パーサは export プレフィックス、クォート（シングル／ダブル）とバックスラッシュエスケープ、行内コメントの取り扱いなどに対応し堅牢化。
- データベース接続方針
  - monitoring コンポーネントは KABUSYS_ENV にかかわらず本番 sqlite_path（既定: data/monitoring.db）を使用する設計とした（監視は本番 DB を参照するため）。
  - Execution は paper_trading 環境時に paper_sqlite_path（既定: data/paper_trading.db）へ切り替え、ペーパートレードを本番 DB と完全分離。
- ログ設定の挙動
  - setup_logging は既存ハンドラをクリアしてから設定を行い、重複ハンドラ登録を防止。
  - ログ出力は stdout を使用（stderr ではない）。ログディレクトリの解決順は引数 > LOG_DIR 環境変数 > デフォルト logs/。
- 起動時の優先度設定
  - run_execution/run_monitoring の最初に set_process_priority("high") を呼び出すことで、運用プロセスの優先度を上げる。

### 修正（バグ修正・堅牢化）
- run_monitoring.py
  - MONITOR_POLL_INTERVAL の値が不正（整数でない、0 以下など）の場合にデフォルト（60 秒）へフォールバックし、警告を出すように改善。time.sleep に渡して ValueError を起こさないように保護。
  - monitoring ループ内で monitor.check_once() が例外を投げてもループを継続するように例外をキャッチしてログ出力することで単発エラーでの停止を防止。
  - 停止フラグの監視を実装し、フラグ存在時は正常終了するようにした。
- run_execution.py
  - 実行エンジンを別スレッドで起動し、停止フラグ検知時に安全に engine.stop() を呼び出してシャットダウンするフローを実装。起動前に停止フラグが既に立っている場合は起動を回避。
  - SQLite / DuckDB 接続を finally ブロックで確実にクローズするようにした。
- .env 読み込み
  - ファイル読み込みに失敗した場合は警告を出して処理を継続（例外でプロセスが死なないように保護）。
- portfolio モジュール
  - calc_score_weights: 全スコアが 0.0 の場合に等金額配分へフォールバックして警告を出すように改善。
  - apply_sector_cap: sector が不明（"unknown"）な場合はセクター上限の適用対象外とし、安全に動作するように設計。
  - calc_position_sizes: 価格欠損や 0 円の価格を安全に扱う（不足データはスキップ）、aggregate cap 超過時のスケーリングを導入し残余キャッシュでの端数配分ロジックを採用。
- utils/process_priority.py
  - Windows/Linux の差分を吸収。権限不足や非対応 OS では警告を出してスキップ。
- tools/paper_verification_report.py
  - P95 計算や各種集計でデータ欠損やテーブル不在（OperationalError）を考慮してフォールバックするように堅牢化。

### 既知の制限 / 注意事項
- research/factor_research.py はファクター計算の枠組みと定数を含むが、関数の一部（実際の SQL / 実装）は未完・継続実装が必要な箇所があります（モジュールコメントにも注意）。
- 一部の機能（config/*.yaml の内容検証等）は PyYAML に依存。PyYAML 未インストール時はその検証をスキップし警告を出します。
- process priority / cpu affinity の変更は OS 権限に依存し、全環境で確実に適用できるわけではありません。権限エラーは警告で扱われます。
- .env ファイルは秘密情報を含むため、絶対にリポジトリにコミットしないでください（config_setup.py の出力にも注意書きあり）。

### セキュリティ
- 初期リリースのため特別なセキュリティ修正履歴はありません。環境変数や秘密情報の管理は .env を使用する設計のため、運用時は適切なアクセス制御と秘密管理を行ってください。

---

今後の予定（例）
- factor_research の完全実装（各ファクターの SQL 実装、標準化ユーティリティの統合）
- 単体テスト・CI の整備
- 発注ロジックおよびブローカーインターフェースの追加テストと耐障害性強化

（この CHANGELOG はソースコードから推測して生成しています。実際の変更履歴やリリースノートはプロジェクトの方針に合わせて調整してください。）