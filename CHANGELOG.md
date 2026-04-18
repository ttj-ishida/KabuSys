# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

- ドキュメントや小さな改善（将来的にリリース予定の作業内容のプレースホルダ）。

---

## [0.1.0] - 2026-04-18

初回リリース。本リポジトリは日本株自動売買システム「KabuSys」のコアユーティリティ群を含みます。以下はコードベースから推測してまとめた主な機能・変更点・注意点です。

### Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite を使用（data/paper_trading.db がデフォルト）し、MockBrokerClient を利用して本番 DB と完全分離する設計。
    - 起動時にプロセス優先度を "high" に設定するユーティリティ呼び出しを実装。
    - PID ファイル（data/execution.pid）を扱う仕組みを導入。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止処理を実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番向け sqlite_path を使用する仕様になっている点に注意。

- 設定管理
  - config.py
    - .env 自動ロード機能（.env / .env.local）を実装。OS 環境変数を保護する仕組みを導入。
    - 複雑な .env 行解析実装（export 形式、クォート、エスケープ、インラインコメント扱いなど）。
    - Settings クラスでアプリケーション設定（DB パス、API トークン、環境種別、各種しきい値など）をプロパティとして提供。
    - PAPER_FILL_MODE の入力検証（有効値: instant/partial/never/reject）。
    - 環境種別（development/paper_trading/live）とログレベルの検証。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を追加（既存値の読み込み・マスク表示・保存）。
    - デフォルト値や選択肢を用意し、生成された .env を上書き保存する機能。

- 設定検証ツール
  - validate_config.py
    - .env と config/*.yaml の基本的な整合性チェック CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、YAML パース確認（PyYAML が無ければスキップ）などを実施。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - 候補銘柄選定（スコア降順、同スコア時の tie-breaker）select_candidates を実装。
    - 等分配（calc_equal_weights）およびスコア加重（calc_score_weights、スコア全ゼロ時は等分配へフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用して候補をフィルタする apply_sector_cap を実装。
    - 市場レジームに応じた投入資金乗数 calc_regime_multiplier を実装（"bull"/"neutral"/"bear" マップ、未知値は警告とともに 1.0 フォールバック）。
  - portfolio/position_sizing.py
    - 各銘柄の目標株数を計算する calc_position_sizes を実装。
    - risk_based / equal / score の配分方式に対応。
    - 単元（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金を超える場合のスケーリング）を実装。
    - cost_buffer を使った保守的コスト見積りと残余キャッシュの再配分ロジックを実装。

- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（デイリー、30日保持）を設定するユーティリティを実装。
    - ログディレクトリ生成失敗時にはファイル出力をスキップしてコンソールのみで継続する安全な設計。
  - utils/process_priority.py
    - Windows/Linux/macOS の差を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを実装。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供（権限不足時は警告でスキップ）。

- モニタリング/検査
  - tools/paper_verification_report.py
    - ペーパートレード結果の検証レポート作成スクリプトを追加。DB（デフォルト data/paper_trading.db）から統計を集計して PASS/FAIL 判定を行う。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等の指標を出力。閾値はファイル内定義（例: 稼働率 99% など）。
    - 日付フィルタ（--from/--to）や --db オプションに対応。

- その他
  - パッケージ初期化でバージョンを定義（__version__ = "0.1.0"）。

### Changed
- （設計的決定）監視（run_monitoring）は起動環境にかかわらず monitoring 用に設定された本番 sqlite_path を使用する仕様を明示。これにより monitoring と execution の DB 分離ポリシーが明確化（ただし実運用で意図的に分離したい場合は注意が必要）。

### Fixed
- 設定読み込み・初期化周りでの堅牢性向上
  - .env 読み込み時にファイルオープン失敗を warnings.warn で扱い、起動を継続可能に。
  - logging_setup において既存ハンドラを安全に flush/close してから削除することで二重設定を防止。
  - MONITOR_POLL_INTERVAL の不正値（整数変換失敗や 0 以下）でデフォルトにフォールバックする処理を追加し、time.sleep に渡した際の例外を防止。
  - process_priority の権限不足や未対応 OS での処理は警告に留める安全設計。
  - score_weights 計算で全スコア 0.0 の場合に等分配へフォールバックして警告を出す。

### Documentation
- 各モジュールの docstring / コメントを充実させ、利用方法・設計意図・注意点を明記。
- config_setup の対話ウィザードで生成される .env は Git にコミットしない旨の注記を出力。

### Known issues / Notes
- research/factor_research.py の calc_momentum はファイル末尾で途中（start_da で途切れている）であり、実装が未完の可能性あり。ファクター計算モジュールの完全実装は今後の作業予定。
- 一部コンポーネント（ExecutionEngine、BrokerFactory、OrderManager などの実装ファイルは参照されているが、このスナップショットでは詳細実装が省略されている可能性があるため、統合テストを推奨。
- run_monitoring が常に本番 sqlite_path を参照する仕様は設計上の重要点であり、テスト環境で監視データを分離したい場合は注意して環境変数を設定すること。

---

## 過去のリリース
（なし。初回リリース）

---

変更点の記載はコードベースからの推測に基づきます。実際の変更履歴やリリースノートを作成する際はコミット履歴やリリース記録（Git タグ・リリースノート）を参照してください。