# CHANGELOG

このプロジェクトの変更履歴は「Keep a Changelog」形式に準拠します。  
日付はコードベースから推測して設定しています。

全体方針:
- 主要な追加機能、CLI、設定/環境変数、データベース挙動、ユーティリティ、アルゴリズム実装の要点を記載。

## [Unreleased]
- 次回リリースに向けた保留事項（なし）

## [0.1.0] - 2026-04-18
初期公開リリース。以下の主要機能と実装を含みます。

### 追加 (Added)
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプトを実装。スレッドで ExecutionEngine を起動・監視し、外部停止フラグ（data/stop_requested.flag）を検知して安全に停止可能。
    - KABUSYS_ENV が `paper_trading` の場合はペーパートレード専用の SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - ブローカークライアント生成を BrokerClientFactory に委譲。
    - OrderRepository, OrderManager, RiskManager, Reconciler 等の依存コンポーネントを組み立てて ExecutionEngine に注入。
    - PID ファイル管理用のパス（data/execution.pid）をサポート。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - 停止フラグを監視してループを安全に抜ける実装。
    - Monitoring は KABUSYS_ENV に依らず本番 sqlite_path を使用する（監視情報は本番 DB を対象）。

- 設定管理
  - config.py
    - Settings クラスを実装し、様々な設定値（DB パス、API トークン、環境フラグ、各種閾値など）をプロパティとして提供。
    - .env 自動ロード機能を実装（プロジェクトルートの検出: .git または pyproject.toml）。.env と .env.local の読み込み順・上書きルールをサポート。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
    - .env パース改善: export 形式、クォート文字列、エスケープ、行末コメントの扱いに対応。
    - 環境値の検証（enum 値チェック、PAPER_FILL_MODE の有効値検査等）を組み込み。

- 設定ユーティリティ / CLI
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を実装。既存 .env 読み込み、シークレット値のマスク表示、選択肢チェック、保存確認をサポート。
  - validate_config.py
    - 起動前の設定検証 CLI を実装。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・パースチェック（PyYAML 未インストール時はスキップ）などを実施。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築 (純粋関数群)
  - portfolio/portfolio_builder.py
    - シグナルから候補銘柄選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコアが全て 0 の場合は等金額へフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。セクター不明銘柄は上限の適用対象外、未知レジームはフォールバックで 1.0 を返す。
  - portfolio/position_sizing.py
    - 株数決定ロジック（risk_based / equal / score）を実装。単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金に基づくスケーリング）、コストバッファの考慮、残差分配ロジック等を含む。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング初期化関数 setup_logging を追加。stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler、30 日保持）を設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップして標準出力のみで継続。
  - utils/process_priority.py
    - マルチプラットフォーム対応のプロセス優先度設定 (set_process_priority) と CPU affinity 設定 (set_cpu_affinity) を実装。Windows / POSIX の差分を吸収し、権限不足等が発生しても安全に警告でスキップする。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）から検証指標（稼働率、注文成功率、送信率、レイテンシ P95 等）を算出し、PASS/FAIL 判定を行うレポート生成 CLI を実装。日付範囲フィルタ、P95 計算、メトリクスのフォーマットをサポート。

- 研究用モジュール
  - research/factor_research.py（開始実装）
    - DuckDB 接続を受けて各種ファクター（Momentum、Value、Volatility、Liquidity）を計算する設計。モメンタム計算関数を含む（途中までの実装が含まれていることを示唆）。

- パッケージ情報
  - __init__.py にてバージョンを "0.1.0" に設定。

### 変更 (Changed)
- なし（初期リリース）

### 修正 (Fixed)
- .env 読み込みの堅牢化
  - ファイル読み込み失敗時に警告を出して継続するように改善。
  - クォート内のエスケープ処理やインラインコメントの扱いを改善。

### 破壊的変更 (Breaking)
- なし（初期リリースのため互換性の過去版は存在しない想定）

### セキュリティ (Security)
- なし特記

---

注意事項（運用上のポイント、コードから推測）
- 本番実行時は KABUSYS_ENV の設定に注意（特に `live`）。validate_config で本番用の追加警告を出すため、起動前に検証を推奨。
- ログディレクトリ作成やプロセス優先度の変更は実行環境の権限に依存するため、権限不足によるフォールバックが発生する可能性がある（ログは stdout に落ちる等）。
- Paper Trading は本番 DB と分離される設計だが、環境変数やパス設定を誤るとデータ混在リスクがあるため .env の適切な管理を推奨。