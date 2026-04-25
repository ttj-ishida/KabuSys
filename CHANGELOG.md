# Changelog

すべての重要な変更をここに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

全てのリリースはセマンティックバージョニングに従います。

## [0.1.0] - 2026-04-25

初回リリース — KabuSys の基本機能群を実装しました。主な追加点・改善点は以下のとおりです。

### Added
- 基本パッケージ構成を追加
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。
  - エントリポイントやユーティリティ群を含むモジュール群を収録。

- 環境設定・ロード
  - .env 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。
  - 読み込み順序: OS環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
  - .env のパース改善: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。

- 設定管理 API
  - Settings クラスを追加。各種環境変数を property として提供（J-Quants、kabu API、DB パス、監視閾値、実行環境フラグ等）。
  - Paper Trading 用 DB パス・fill モードなどの設定を提供。

- 対話式設定ウィザード
  - `kabusys.config_setup` により `.env` の初期作成・更新を対話形式で支援する CLI を実装。
  - シークレット扱い項目はマスク表示、デフォルト/既存値の再利用をサポート。
  - 書き込み時にテンプレートヘッダを出力（.env を Git にコミットしない旨の注意文含む）。

- 設定検証 CLI
  - `kabusys.validate_config` により起動前に必須環境変数、KABUSYS_ENV の妥当性、DB パス、config/*.yaml の存在（および PyYAML があればパース検証）等を検査するツールを実装。
  - `--strict` オプションで警告を失敗扱いにできる。

- ロギング基盤
  - `kabusys.utils.logging_setup.setup_logging` を実装。root ロガーに stdout ストリームハンドラと日次ローテーションのファイルハンドラを設定。
  - 既存ハンドラをクリアして二重設定を防止。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。

- プロセス優先度 / CPU affinity
  - `kabusys.utils.process_priority` で Windows / POSIX を吸収したプロセス優先度設定（high/normal/low）と CPU affinity 設定を実装（psutil 利用）。
  - 権限不足や未対応 OS の際は安全にスキップして警告出力。

- 実行系・監視エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を high に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db）を使用し本番 DB と分離。
    - BrokerClientFactory を用いてブローカークライアントを生成。OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）と PID ファイルをサポート。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）。無効値は警告してデフォルトにフォールバック。
    - 監視処理は本番 sqlite_path を利用（環境に依存せず本番 DB を参照する設計）。
    - 停止フラグの検出、例外耐性、接続クローズ処理を実装。

- ポートフォリオ構築モジュール
  - portfolio_builder: シグナル選定（select_candidates）、等金額・スコア加重配分（calc_equal_weights / calc_score_weights）を実装。スコア合計が 0 の場合は等金額にフォールバックして警告を出す。
  - risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジームに基づく乗数（calc_regime_multiplier）を実装。unknown セクターは制限対象外。未知レジームはフォールバックして警告。
  - position_sizing: 株数決定ロジックを実装（risk_based / equal / score）。単元株（lot_size）丸め、per-position 上限・aggregate cap のスケールダウン、cost_buffer による保守的コスト見積り、残余キャッシュを使った端数配分をサポート。

- リサーチ（ファクター計算）開始
  - research/factor_research にモメンタム等のファクター計算基盤を追加（DuckDB を用いた prices_daily 参照、calc_momentum 実装の開始）。関数は (date, code) ベースの dict を返す設計。

- Paper Trading 検証ツール
  - tools/paper_verification_report を追加。Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH 指定可）から各種指標（稼働率・注文成功率・送信率・レイテンシ（P95）など）を集計し、閾値と比較して PASS/FAIL を判定するレポートを出力。
  - 日付フィルタ、P95 計算、DB 不備時の安全なフォールバックを実装。

### Fixed (robustness / usability)
- .env パーサーを強化してクォート/エスケープ/コメント処理の不整合による誤読みを減らす。
- ロギング設定で既存ハンドラを閉じてから削除することで、複数回の初期化による重複出力を防止。
- run_monitoring の MONITOR_POLL_INTERVAL が 0 以下や非数値の場合に ValueError を避けるためデフォルトにフォールバックして警告を出す。
- position_sizing の合計投下資金が available_cash を超えた際のスケールダウンアルゴリズムにおいて、lot_size 単位での丸めと残余キャッシュの扱いを整備。
- process_priority / set_cpu_affinity で権限不足や未対応 API の場合に例外を握りつぶして警告し、起動継続できるようにした。

### Security
- .env 書き出しテンプレートに「.env を絶対に Git にコミットしないこと」と明記（config_setup）。
- シークレットは対話ウィザードおよび確認表示でマスク表示。

### Behavior
- 監視（monitoring）は環境設定にかかわらず本番 sqlite_path を使用する仕様（運用上の意図的な隔離）。一方で実行エンジンは KABUSYS_ENV=paper_trading 時に paper_trading 用 DB を利用して本番 DB と分離する。

### Known limitations / Notes
- research/factor_research はモジュールの実装が継続中（ファイル末尾が途中で途切れているため、全機能実装は今後の作業）。
- position_sizing は現状全銘柄共通の lot_size を想定。将来的には銘柄別 lot_map への拡張を予定。
- apply_sector_cap 内で価格欠損（0.0）を扱う際に過少見積りが発生する可能性があるため、将来的にフォールバック価格の導入を検討。
- validate_config の YAML 検証は PyYAML がインストールされている場合のみ実行される（未導入時はスキップして警告）。

---

今後の予定（例）
- research モジュールの追加ファクター実装（Value, Volatility, Liquidity）と Z スコア正規化の統合。
- ExecutionEngine / BrokerClient の詳細実装と統合テスト。
- 戦略設定ファイル（config/*.yaml）に基づく自動テスト・CI の整備。

以上。