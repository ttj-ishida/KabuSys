# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに準拠して記載しています。  
主にソースコードから推測できる機能追加・改善・バグ修正をまとめています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

### Added
- run_monitoring 起動スクリプトを追加
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 停止はプロジェクトルート/data/stop_requested.flag の存在検知で行う。
  - Monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する。
  - 例外発生時にログを残して次ポーリングへ復帰する堅牢化。

- run_execution 起動スクリプトを追加
  - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使用し MockBrokerClient 経由で完全分離されたペーパートレード実行をサポート。
  - エンジンはデーモンスレッドで実行し、停止フラグで安全に停止可能。
  - 起動前に停止フラグが既に立っている場合は起動をスキップ。

- 設定管理 (kabusys.config)
  - .env 自動ロード機能を実装（.env, .env.local）。OS 環境変数を保護して上書きを制御。
  - .env パースロジック改善：
    - export プレフィックス対応、シングル/ダブルクォート中のバックスラッシュエスケープ、インラインコメントの取り扱いなどに対応。
  - Settings クラスで各種環境変数（DB パス、KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）をラップし、バリデーションを実装。

- 設定ウィザード (kabusys.config_setup)
  - 対話式に .env ファイルを作成・更新する CLI を実装。
  - 秘匿値のマスク表示、選択肢/デフォルトの提示、既存 .env の読込・利用が可能。
  - .env の安全なテンプレート生成機能を提供。

- 設定検証 CLI (kabusys.validate_config)
  - 起動前に .env と config/*.yaml の整合性を検証するツールを実装。
  - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パス・YAML ファイル存在の確認、KABUSYS_ENV=live 時の追加ガードを実装。
  - --strict オプションで警告を FAIL として扱える。

- ロギングユーティリティ (kabusys.utils.logging_setup)
  - ルートロガーの一元設定機能を実装（stdout StreamHandler + 日次ローテートの TimedRotatingFileHandler）。
  - LOG_DIR / LOG_LEVEL の解決順を定義、既存ハンドラのクリアで二重出力を防止。
  - 日次ローテーション、30日分保持、ログディレクトリ作成失敗時のフォールバック挙動を実装。

- プロセス優先度ユーティリティ (kabusys.utils.process_priority)
  - Windows / POSIX (Linux/Mac/FreeBSD) を吸収するプロセス優先度設定と CPU affinity 設定を実装。
  - 権限不足や未対応プラットフォーム時に警告を出して安全にスキップ。

- ポートフォリオ構築モジュール (kabusys.portfolio)
  - 銘柄選定: select_candidates（スコア降順＋タイブレーク処理）
  - 重み算出: calc_equal_weights, calc_score_weights（全スコア 0 の場合は等配分へフォールバック）
  - セクター集中制限: apply_sector_cap（既存ポジションに基づくセクターエクスポージャー算出と候補フィルタ）
  - レジーム乗数: calc_regime_multiplier（bull/neutral/bear のマッピングと不明レジームのフォールバック）
  - 株数決定: calc_position_sizes
    - risk_based / equal / score の allocation_method をサポート。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap のスケーリング、cost_buffer を使った保守的見積り、端数処理による追加配分ロジックを実装。

- Paper Trading 検証レポート ツール (kabusys.tools.paper_verification_report)
  - paper_trading DB から稼働率・注文成功率・送信率・レイテンシ指標（平均・最大・P95）を抽出してレポート出力。
  - P95 計算、期間フィルタ（--from / --to）、DB 無し時のエラーメッセージなどを実装。
  - 一連の閾値定義（稼働率、成功率、送信率、P95）による PASS/FAIL 判定出力。

### Changed
- run_monitoring/run_execution 起動フローの共通改善
  - 起動直後にプロセス優先度を high に設定する呼び出しを追加。
  - sqlite/duckdb 接続を明示的に作成して終了時にクローズするように統一。

- デフォルト値とバリデーションの明確化
  - PAPER_FILL_MODE の有効値チェックを実装（instant/partial/never/reject）。
  - LOG_LEVEL / KABUSYS_ENV の許容値チェックを厳格化（不正値で ValueError を送出）。

- .env 自動ロードの振る舞い
  - OS 環境変数を保護して .env/.env.local からの上書きを制御。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。

### Fixed
- ロギング初期化の堅牢化
  - 既にハンドラが設定されている場合は一度 flush/close してから削除し、重複ログを防止。
  - ログディレクトリ作成失敗時はファイルハンドラを諦めてコンソール出力のみで継続するようにフォールバック。

- process_priority / CPU affinity の失敗時ハンドリング強化
  - psutil の権限不足や未実装 API 呼び出しで例外が発生した場合は警告ログを出して継続。

- run_monitoring のポーリング間隔取得
  - MONITOR_POLL_INTERVAL の値検証を追加。0 以下や非整数が指定された場合にデフォルトへフォールバックして警告を出す。

- run_execution の起動条件の安全化
  - 停止フラグが既にある場合はエンジンを起動せずに終了するようにした。

- DB 初期化の冪等性
  - Execution 起動時に init_monitoring_db を呼び出して監視テーブルの存在を保証（既存テーブルがあっても安全）。

- paper_verification_report の堅牢化
  - テーブル欠落や OperationalError 発生時に個別指標の取得をスキップし、全体レポートは出力するようにした（N/A 表示）。

## [0.1.0] - 2026-04-19

初回公開相当の機能セットをリリース。上記 Unreleased に記載の多くのコア機能・CLI・ユーティリティを含む。

### Added
- パッケージ基礎: バージョン情報 (kabusys.__version__ = "0.1.0")
- 主要モジュール・ユーティリティ・CLI（詳細は Unreleased の Added を参照）。

### Known issues / Notes
- 一部モジュール（例: execution 内の詳細実装、research.calc_momentum の続きなど）はコメントや TODO が残っており、将来的な拡張・改善が想定される。
- position_sizing の価格欠損時の挙動（price が 0.0 の場合にエクスポージャーが過少見積りされる点）については TODO コメントあり。フォールバック価格の導入が検討課題。
- ローカル環境での .env 自動ロードはプロジェクトルート検出に依存するため、配布後の挙動確認やテスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を活用することを推奨。

---

今後のリリースでは以下を想定:
- research.factor_research の完全実装（calc_momentum 続きの完成）
- execution 周りの詳細実装（Engine/OrderManager/Reconciler 等の安定化・テスト）
- 単体テスト・CI ワークフロー用の整備
- さらに詳細なドキュメント（API リファレンス・設計資料）および運用ガイドの追加

（以上）