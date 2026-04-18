# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
タグ付けやリリース日付は該当リリースを示します。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-04-18

初回公開リリース。日本株自動売買システム KabuSys の基本コンポーネントを実装しました。主な追加点は以下の通りです。

### 追加 (Added)
- 基本パッケージ情報
  - src/kabusys/__init__.py にバージョン情報 (__version__ = "0.1.0") と公開 API を追加。

- 実行用スクリプト
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV に応じて paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用。
    - BrokerClientFactory を用いて本番 / モックブローカーを切り替え。
    - PID ファイル管理、停止フラグ (data/stop_requested.flag) による安全停止処理を実装。
    - スレッドでエンジンを起動し、停止フラグ検知で engine.stop() を呼出して終了。
  - src/kabusys/run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）。不正な値はデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ検出、例外時のロギングと継続処理を実装。

- 環境設定管理
  - src/kabusys/config.py
    - .env 自動読み込み（プロジェクトルートの検知: .git または pyproject.toml）。
    - .env のパース機能（コメント、export プレフィックス、クォートとバックスラッシュエスケープ対応）。
    - Settings クラスで環境変数をラップ（各種パス、閾値、フラグ、paper_trading 用パスや挙動設定を提供）。
    - 環境ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
  - src/kabusys/config_setup.py
    - 対話式 .env ウィザード。初期作成／更新を支援し .env を安全に生成。
    - デフォルト値、マスク表示（シークレット）や選択肢による入力検証を実装。
    - .env 書き込みフォーマットと注意書きを自動生成。

- 設定検証ツール
  - src/kabusys/validate_config.py
    - 起動前に .env と config/*.yaml の設定不備を検出する CLI。
    - 必須環境変数チェック、KABUSYS_ENV や LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、YAML ファイルの存在・パース検証（PyYAML 未インストール時はスキップ）など。
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - 統一的なログ初期化関数 setup_logging を提供。
    - stdout 出力用 StreamHandler と日次ローテートの TimedRotatingFileHandler（デフォルト logs/、30 日保持）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップして stdout のみで継続。
    - ログレベル解決順序（引数 > 環境変数 LOG_LEVEL > デフォルト）を実装。
  - src/kabusys/utils/process_priority.py
    - プロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）。
    - Windows / POSIX（Linux / macOS / FreeBSD）での差分を吸収。
    - 権限不足などの例外は警告に留め、安全にスキップする。

- ポートフォリオ構築モジュール（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - 候補選定 select_candidates（スコア降順、同点は signal_rank によるタイブレーク）。
    - 配分比率 calc_equal_weights、calc_score_weights（全スコアが 0 の場合は等配分にフォールバックして WARNING ログ）。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存保有比率が指定上限を超えるセクターの新規候補除外）。
    - レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear をマップ、未知レジームは 1.0 にフォールバック）。
    - sell_codes を考慮して当日売却予定銘柄をエクスポージャー計算から除外。
  - src/kabusys/portfolio/position_sizing.py
    - 株数決定ロジック calc_position_sizes（allocation_method: risk_based / equal / score）。
    - 単元株丸め（lot_size 単位）や per-position / aggregate キャップ、cost_buffer（手数料・スリッページ保守見積り）を実装。
    - 合計投資額が available_cash を超える場合はスケールダウンし、端数の分配ロジックで lot 単位を追加配分する実装を追加。
  - src/kabusys/portfolio/__init__.py にエクスポートを提供。

- 研究 / ファクター計算
  - src/kabusys/research/factor_research.py
    - DuckDB を用いたファクター計算モジュールの骨格を実装（Momentum / Value / Volatility / Liquidity を想定）。
    - モメンタム計算のための定数定義や設計方針を記載（prices_daily / raw_financials のみ参照、外部 API 不使用）。

- ペーパートレード検証ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading SQLite（デフォルト data/paper_trading.db）から検証レポートを生成する CLI。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシなどを集計し PASS/FAIL 判定を出力。
    - --from/--to/--db オプションに対応。

### 変更 (Changed)
- （初回リリースのため履歴からの差分なし）

### 修正 (Fixed)
- （初回リリースのため履歴からの差分なし）

### 注意点 / 動作上の仕様
- .env 自動読み込みはプロジェクトルートを基準に行われます。プロジェクトルートが特定できない場合、自動ロードはスキップされます。
- セキュリティ: .env は生成時に「絶対に Git にコミットしないこと」と注意書きを付与しています。config_setup により .env を簡単に生成できますが、運用ではシークレット管理に注意してください。
- paper_trading モードは本番 DB と分離される設計（デフォルトパス: data/paper_trading.db）。実発注は行われません（MockBrokerClient が利用される想定）。
- ログは標準出力 (stdout) を使用するため、cron 等での実行時にリダイレクトしやすい設計です。
- process_priority / cpu_affinity 設定は権限やプラットフォーム制約によりスキップされる場合があります（ログに警告を出力）。

---

今後の予定（例）
- research/factor_research の各ファクター実装完了・統合テスト
- ExecutionEngine / SystemMonitor のユニットテスト整備
- Broker クライアント実装の明確化（実ブローカー API の接続部分）
- ドキュメント（操作手順、運用ガイド、デプロイ例）の充実

もし特定ファイルや機能についてより詳細な変更点や補足説明が必要でしたら、どの部分を深掘りするか教えてください。