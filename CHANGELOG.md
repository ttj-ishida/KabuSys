# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  

最新: 0.1.0

## [Unreleased]


## [0.1.0] - 2026-04-21

### 追加 (Added)
- 初回リリース (0.1.0) — KabuSys の基本機能群を実装。
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用する分離動作を実装。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを実装。
    - RiskManager のデフォルト設定を導入（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker など）。初期ポートフォリオ値は broker.get_available_cash() に依存。
    - ExecutionEngine をデーモンスレッドで起動し、 data/stop_requested.flag を検出して安全に停止する仕組みを実装。PID ファイル出力をサポート。
  - run_monitoring.py
    - SystemMonitor のポーリングループ開始スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告出力。
    - 監視は KABUSYS_ENV に依存せず本番用 sqlite_path を使用して監視データを保存する設計。
    - 停止フラグ（data/stop_requested.flag）検出でループを終了。KeyboardInterrupt をハンドルして正常シャットダウン。

- 設定・環境管理
  - config.py
    - .env 自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - `.env` / `.env.local` の読み込み順序および OS 環境変数保護を実装。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で自動ロードを無効化可能。
    - .env 1行パーサーにおいて、`export KEY=val`、クォート文字列（バックスラッシュエスケープ対応）、およびインラインコメント処理を実装。
    - Settings クラスを提供し、各種設定値（J-Quants, kabu API, LINE, DB パス, 監視しきい値, 環境名/ログレベル判定等）と妥当性チェックを実装。
    - Paper Trading 用設定: `PAPER_FILL_MODE`（instant/partial/never/reject）と `PAPER_TRADING_SQLITE_PATH` をサポート。
  - config_setup.py
    - ユーザ対話式の .env ウィザードを追加。既存 .env 読み込み、シークレットマスク表示、選択肢/デフォルトのサポート、生成された .env の保存を実装。
    - 生成される .env のテンプレートと注意書きを出力。

- 設定検証 CLI
  - validate_config.py
    - .env および config/*.yaml の存在・妥当性チェックを行う CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、YAML パースチェック（PyYAML 利用可否に応じてスキップ）などを実装。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。システム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を集計して PASS/FAIL 判定を出力。
    - CLI オプション `--from`, `--to`, `--db` をサポート。環境変数 `PAPER_TRADING_SQLITE_PATH` と連携。
    - デフォルトの合格基準（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200 ms）を定義。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選択 (`select_candidates`) と重み計算（等分: `calc_equal_weights`, スコア加重: `calc_score_weights`）を実装。score が全て 0 の場合は等分へフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する `apply_sector_cap` を実装（既存ポジションに基づくセクター露出算出と候補除外）。"unknown" セクターは除外対象外にする挙動を採用。
    - 市場レジームに応じた投下資金乗数 `calc_regime_multiplier`（bull/neutral/bear）を実装。未知レジームは警告を出して 1.0 フォールバック。
  - portfolio/position_sizing.py
    - 発注株数計算 `calc_position_sizes` を実装。`allocation_method` に応じた計算（risk_based / equal / score）と lot_size（単元株）丸め、1銘柄上限や aggregate cap（available_cash によるスケーリング）、cost_buffer を用いた保守的見積り、残余キャッシュによる補正（端数処理）をサポート。

- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30世代保存）を設定する共通ユーティリティを追加。ログディレクトリ自動作成、ログレベル解決順（引数 > 環境変数 > デフォルト）、エラー時のフォールバックを実装。
    - stdout を採用して cron/task scheduler との親和性を考慮。
  - utils/process_priority.py
    - Windows / POSIX の差異を吸収するプロセス優先度設定ユーティリティを追加（`set_process_priority("high"|"normal"|"low")`）。
    - CPU affinity を部分固定する `set_cpu_affinity` を実装（存在しない場合は安全にスキップ）。
    - 権限不足や未対応環境での例外は警告に変換してスキップ。

- パッケージ情報
  - __init__.py にてパッケージバージョンを `0.1.0` として定義。

### 変更 (Changed)
- なし（初回リリースのため新規追加が主）

### 修正 (Fixed)
- なし（初回リリース）

### 廃止 (Deprecated)
- なし

### 削除 (Removed)
- なし

### セキュリティ (Security)
- なし

### 既知の制限 / 注意事項 (Known issues / Notes)
- research/factor_research.py はモジュール設計と大部分の定数・関数を定義しているが、ファイル末尾でモメンタム計算関数の実装が途中で終わっている（ソースが途中で切れている）。今後のリリースで calc_momentum の完成および他ファクター（Value, Volatility, Liquidity）の実装が必要。
- 一部の処理で価格が未取得（0.0）だった場合の取り扱いに TODO コメントあり（将来的にフォールバック価格を導入予定）。
- process_priority / set_cpu_affinity は権限不足や未対応 OS で効果がない場合がある。警告を出して安全にスキップする設計。
- .env ファイルには機密情報が含まれるため、生成された .env を Git にコミットしないことを強く推奨（config_setup にも注記あり）。

---

翻訳・要約: この CHANGELOG はソースコードから推測できる機能追加・動作仕様に基づき作成しています。実際のリリースノートとして使用する場合は、実装者の確認を行ってください。