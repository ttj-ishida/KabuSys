# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。（https://keepachangelog.com/ja/）

## [Unreleased]
- 現時点で未リリースの変更はありません。

---

## [0.1.0] - 初回リリース
リリース日: 2026-04-19（コードベースの日付・内容から推測）

### 追加 (Added)
- 全体
  - パッケージ初期版を公開。日本株自動売買システム「KabuSys」の基本機能を実装。
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。

- 設定・起動
  - Settings / 環境変数管理モジュールを実装（src/kabusys/config.py）。
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml）。
    - .env ファイルのパース機能（クォート・エスケープ・インラインコメント処理対応）。
    - 必須/任意の各種環境変数プロパティ（J-Quants, kabuAPI, DBパス, 各種閾値、環境フラグ等）。
    - 環境（development / paper_trading / live）やログレベルの検証。
  - 対話式環境設定ウィザード（src/kabusys/config_setup.py）を追加。
    - .env の初期作成・更新を支援する CLI（項目定義・既存値の読み込み・保存）。
  - 設定検証ツール（src/kabusys/validate_config.py）を追加。
    - 必須環境変数、KABUSYS_ENV、ログレベル、DBパス、config/*.yaml の存在とパース検証。
    - --strict モードで警告を失敗として扱うオプション。

- 実行系・監視
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）を追加。
    - 環境に応じて本番 DB / Paper Trading 専用 DB を切り替え（paper_trading は data/paper_trading.db を使用）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て。
    - ExecutionEngine のデーモン・スレッド起動と stop flag による安全停止処理。
    - 起動時にプロセス優先度を「high」に設定。
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ検知でループを終了。KeyboardInterrupt を考慮したクリーンアップ。

- ログ・プロセス管理
  - 統一ロギング設定ユーティリティ（src/kabusys/utils/logging_setup.py）。
    - stdout への StreamHandler と日次ローテーションする TimedRotatingFileHandler をルートロガーに設定。
    - ログ保存先・ログレベルの解決順を実装（引数 > 環境変数 > デフォルト）。
  - プロセス優先度 / CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX の差分を吸収してプロセス優先度を設定できる関数を提供（set_process_priority, set_cpu_affinity）。
    - 権限不足等の失敗は警告ログで安全にスキップ。

- ポートフォリオ構築（純粋関数群）
  - 銘柄選定・重み付け（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順で上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装。スコア合計が 0 の場合はフォールバック。
  - セクター集中・レジーム調整（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存ポジションのセクター露出が閾値を超える場合に新規候補を除外。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear）を提供（未知はフォールバック）。
  - 株数決定・リスク制限（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: risk_based / equal / score の割当方式に対応。単元株（lot_size）で丸め、aggregate cap によるスケールダウンロジックを実装。
    - コストバッファ（手数料・スリッページ想定）を加味した保守的な算出。

- リサーチ / ファクター計算
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）を追加。
    - Momentum / Value / Volatility / Liquidity の計算方針と定数定義を実装（DuckDB 経由で prices_daily / raw_financials を参照する設計）。
    - calc_momentum の骨組み（引数・戻り仕様）を準備。

- ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均・P95）等を集計して PASS/FAIL 判定を出力。
    - デフォルト DB パスは data/paper_trading.db。期間指定オプション（--from / --to）をサポート。

### 変更 (Changed)
- なし（初回リリースのため既存バージョンからの変更は無し）。

### 修正 (Fixed)
- なし（初回リリースとして新規実装主体）。

### 注意事項 / 既知の問題 (Notes / Known issues)
- research.calc_momentum は設計と一部の定数・ドキュメントが追加されていますが、関数本体の SQL 実装が未完の可能性があります（コード断片が存在）。実運用前にテストと実装の完成が必要です。
- apply_sector_cap の価格欠損時の注記:
  - price_map に価格が欠損（0.0）の場合、現状はエクスポージャーが過少見積りされ、ブロックが外れる可能性がある旨の TODO コメントあり。より堅牢なフォールバック価格戦略の実装が推奨されます。
- posix/windows の優先度設定は権限不足や未対応 OS で失敗する可能性があり、その場合は警告を出してスキップします。必要な権限の確認を推奨。

---

今後の予定（参考）
- ファクター計算の完全実装およびユニットテストの追加
- ExecutionEngine / RiskManager 周りの E2E テストとモックによる検証強化
- ポートフォリオ最適化の拡張（銘柄別 lot_size、手数料モデルの導入）
- monitoring / logging の監視アラート（LINE 通知等）の統合強化

--- 

（注）この CHANGELOG は提供いただいたソースコードの内容から推測して作成しています。実際のリリース日・追加機能の意図・既存履歴がある場合はそちらに合わせて編集してください。