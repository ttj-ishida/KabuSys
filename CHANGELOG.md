CHANGELOG
=========

すべての重要な変更履歴はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠しています。

注: この CHANGELOG はソースコードの内容から推測して作成しています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-24
--------------------

Added
- 全体
  - 初回リリース相当の機能群を追加。
  - パッケージバージョンを __version__ = "0.1.0" に設定。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor を定期ポーリングする監視ループを実装。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番用の sqlite_path を使用して接続。
    - stop_requested.flag を検知して安全にループを終了。
    - 例外は捕捉してログ出力した上で次のポーリングへ続行。
    - 起動時にプロセス優先度を "high" に設定。

  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを実装。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory により環境に応じたブローカークライアントを生成（Mock を含む想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine をスレッドで実行。停止フラグで安全停止。
    - 起動時にプロセス優先度を "high" に設定。

- 設定関連
  - config.py
    - Settings クラスを追加し、環境変数から設定を取得する統一インターフェイスを提供。
    - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / PID_FILE_PATH 等のパス解決を実装。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）を実装。
    - KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL の検証を実装。
    - 自動 .env ロード機能を実装（プロジェクトルートの検出、.env/.env.local の適切な優先順位と保護キーを考慮）。
    - _parse_env_line により export プレフィックス、クォート文字列、バックスラッシュエスケープ、インラインコメントの取り扱いをサポート。

  - config_setup.py
    - .env の対話的ウィザードを実装（ウィザード → .env 書き込み）。
    - J-Quants / kabu API / DB パス / LINE 通知 等の設定項目を分かりやすく収集。
    - 既存 .env の読み込みと Enter による既存値再利用、シークレットのマスク表示に対応。

  - validate_config.py
    - 起動前チェック CLI を実装（必須環境変数の存在・プレースホルダ検出、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスの親ディレクトリ確認、config/*.yaml の存在と（可能なら）パース検証、live 環境時の追加警告）。
    - --strict オプションにより警告も失敗扱いにできる。
    - PyYAML 未インストール時は YAML 検証をスキップして警告を出力。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定関数 setup_logging を追加。
    - stdout 出力用 StreamHandler と 日次ローテーション（TimedRotatingFileHandler、30日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - LOG_LEVEL / LOG_DIR の解決順を実装。

  - utils/process_priority.py
    - set_process_priority(level) を追加（Windows と POSIX の差分を吸収して優先度設定）。
    - set_cpu_affinity(cpu_count) を追加（最初の N コアにプロセスをピン）。
    - 権限不足や未サポート環境では警告を出して安全にスキップ。

- ポートフォリオ構築 / ポジションサイジング
  - portfolio/portfolio_builder.py
    - select_candidates: buy シグナルをスコア降順でソートして上位 N を選択。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア比率で重みを計算し、全スコアが 0 の場合は等金額配分へフォールバック（警告）。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中の上限チェック（既存保有を考慮して新規候補を除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を返す。未知レジームは警告を出して 1.0 にフォールバック。
    - "unknown" セクターは上限適用外とする挙動を明記。
    - 既存ポジション評価時の price 欠損に関する TODO コメントを追加（将来的なフォールバック検討の注記）。

  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method に応じた発注株数計算を実装（"risk_based" / "equal" / "score"）。
    - risk_based: リスク許容率（risk_pct）と stop_loss_pct に基づく目標株数算出、単元株（lot_size）丸め。
    - equal/score: ウェイトに基づく配分、per-position 上限・aggregate cap（available_cash）を考慮。
    - aggregate cap 超過時のスケーリング：スケールダウン後の端数を fractional remainder に基づいて lot_size 単位で追加配分するロジックを実装（再現性のため安定ソートを利用）。
    - cost_buffer による手数料・スリッページ見積りの考慮。
    - lot_size は現在グローバル固定だが将来の銘柄別単元対応の TODO コメントあり。

- モニタリング / ペーパートレード検証ツール
  - monitoring.monitoring_db (初期化呼び出し)
    - 実行前に監視テーブルが存在することを保証（init_monitoring_db を各スクリプトで冪等に呼び出す）。

  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成 CLI を追加。
    - 稼働率、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を集計して PASS/FAIL を判定する基準値を実装。
    - P95 の計算、期間フィルタ（--from/--to）、DB パス解決ロジック（--db / 環境変数 / デフォルト）を実装。
    - DB が存在しない場合やテーブル欠損時は適切に N/A/0 を扱うフォールバックを実装。

- research
  - research/factor_research.py（ファクター計算基盤）
    - DuckDB を利用したモメンタム・ボラティリティ等のファクター計算関数群を追加（設計方針、定数、関数インターフェイスを含む）。
    - prices_daily / raw_financials のみ参照する方針を明示。
    - （ファイルの末尾で実装途中に見える箇所あり：後続の実装が続く想定）

- パッケージ初期化
  - kabusys/__init__.py にパッケージ情報と __all__ を追加。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Deprecated
- なし

Removed
- なし

Security
- なし

Known issues / Notes
- position_sizing や apply_sector_cap にて price が欠損（0.0）の場合にエクスポージャーや発注量が過少評価される可能性がある旨の TODO があり、将来的に前日終値や取得原価などのフォールバック価格を導入することが想定されています。
- research.factor_research.py がファイル末尾で途切れているように見え、モジュールの一部実装が未完了の可能性があります（追加の関数実装やテストが必要）。
- ログディレクトリ作成やプロセス優先度設定は環境によって失敗することがあり、その場合は警告ログを出してフォールバック動作（ファイルハンドラ無効化や設定のスキップ）を行います。
- .env 自動ロードはプロジェクトルートが特定できない場合はスキップされます。また KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化できます（テスト用途を想定）。

今後の改善候補（抜粋）
- 各銘柄ごとの lot_size をサポートするための拡張（stocks マスタの導入）。
- price 欠損時のフォールバックロジック実装（前日終値等）。
- research モジュールの完全実装とユニットテスト整備。
- Monitoring / Execution の統合テスト・シナリオテストの追加。

---

この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴やリリースポリシーに合わせて編集・補完してください。