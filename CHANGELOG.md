# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このファイルは、コードベース（src/kabusys 以下）の内容から推測して作成しています。

フォーマット:
- Unreleased: 今後の変更予定
- 各リリースは日付付きで記載

## [Unreleased]

- なし

## [0.1.0] - 2026-04-18

初回公開リリース。以下の主要機能・モジュールを追加しました。

### 追加 (Added)
- 全体
  - パッケージの初期バージョンを 0.1.0 として公開。
  - モジュール構成を整備（config / execution / monitoring / portfolio / utils / research / tools など）。
  - DuckDB と SQLite を併用するデータレイヤを導入（DuckDB を分析、SQLite を監視/トレードログ用に使用）。

- 実行系
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV に応じて paper_trading 用 DB を分離（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。
    - BrokerClientFactory を用いて本番/モックブローカーを切り替え。
    - ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager の組み立てと起動ロジックを追加。
    - PID ファイル管理、停止フラグ（data/stop_requested.flag）検知、スレッド駆動のセッション実行。
    - デフォルトでプロセス優先度を "high" に設定。

- 監視系
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）。
    - 監視は環境に関係なく本番の sqlite_path（data/monitoring.db）を使用して初期化。
    - 停止フラグ検出 / エラーハンドリング（check_once の例外ログ）を実装。
    - DuckDB と SQLite の接続管理を実装。

- 設定管理
  - config.py:
    - .env 自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml）。
    - .env / .env.local の読み込み順序を実装（OS 環境変数保護機能あり）。
    - 複雑な .env パースロジックを実装（export 対応、シングル/ダブルクォート、エスケープ、インラインコメントの取り扱い）。
    - Settings クラスを導入し、環境変数アクセスとバリデーション（KABUSYS_ENV, LOG_LEVEL など）を集中管理。
    - Paper Trading 関連設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH）と監視閾値設定を追加。

  - config_setup.py:
    - 対話式ウィザードで .env を生成 / 更新する CLI を追加。
    - デフォルト値、選択肢、シークレット入力（マスク）などをサポート。
    - .env の読み取り／書き込みテンプレートを実装（保存前に確認プロンプト）。

  - validate_config.py:
    - 起動前チェック CLI を追加（必須環境変数、パス検証、YAML ファイル検証、ライブ環境ガードなど）。
    - --strict オプションで警告をエラー扱いにできる。

- ユーティリティ
  - utils/process_priority.py:
    - プロセス優先度設定ユーティリティを追加（Windows / POSIX を吸収）。
    - CPU affinity 設定関数を提供（最初の N コアに固定）。
    - psutil の例外に対する安全なフォールバックとログ出力を実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルから候補抽出（スコア降順、タイブレークロジック）。
    - calc_equal_weights / calc_score_weights: 重み計算（スコア全0 の場合は等配分にフォールバック）。

  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター別上限チェック（既存ポジションのエクスポージャ参照、売却予定銘柄の除外対応）。
    - calc_regime_multiplier: 市場レジームに応じた乗数（bull/neutral/bear をマップ、未知値は警告して 1.0 にフォールバック）。

  - portfolio/position_sizing.py:
    - calc_position_sizes: 銘柄ごとの発注株数計算（allocation_method: risk_based/equal/score）。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash 超過時の比例縮小と残差分配）を実装。
    - cost_buffer による保守的なコスト見積り対応。
    - 価格欠損時のスキップやログ出力、将来的な拡張ポイント（銘柄別 lot_size）を注記。

- リサーチ / ファクター計算
  - research/factor_research.py:
    - DuckDB を使ったファクター計算モジュールを追加（momentum, volatility 等）。
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率の計算（ウィンドウサイズ・データ不足時の None 処理）。
    - calc_volatility: ATR / 相対 ATR、20日平均売買代金、出来高比率等の計算（true_range の NULL 伝播制御など）。
    - 集計範囲のバッファや P95 計算（別モジュールで使用可能なユーティリティ）に対応。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 向け検証レポート生成 CLI を追加。
    - システム安定性（稼働率）、注文成功率、送信率、リスク却下数、API レイテンシ（平均 / 最大 / P95）を集計して判定（PASS/FAIL）。
    - デフォルトのパスは data/paper_trading.db。期間指定オプション（--from/--to）と --db オーバーライドをサポート。
    - 判定基準（稼働率 >= 99%、Fill Rate >= 90%、Send Rate >= 95%、P95 <= 200ms）を導入。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### 廃止 (Deprecated)
- なし

### 削除 (Removed)
- なし

### セキュリティ (Security)
- なし

---

備考（実装上の注意・既知事項・今後の改善案）
- .env の自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト向け）。
- run_monitoring は監視用 DB として常に settings.sqlite_path（デフォルト data/monitoring.db）を使用する設計のため、本番／ペーパーの分離が必要な場合は運用手順で対応すること。
- position_sizing 等は現状全銘柄共通の lot_size を想定。将来的に銘柄別 lot_map を導入する予定（コード中に TODO コメントあり）。
- 複数箇所で「データ不足時は None を返す」など安全側の設計を採用。運用時にメトリクス欠落が多い場合はデータ投入側の確認が必要。
- calc_regime_multiplier は未知レジームで 1.0 にフォールバックし警告を出す。レジーム検出器との整合性に注意。

---

（この CHANGELOG はコードの現状から推測して作成しています。詳しい変更履歴・意図はコミットログや開発者コメントを参照してください。）