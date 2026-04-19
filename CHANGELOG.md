# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
日付はこのリリースの想定日です。

## [Unreleased]

### 注意事項
- 今後のリリースで細かな API 安定化、テスト追加、ドキュメント整備、エラーハンドリング強化等を予定しています。

---

## [0.1.0] - 2026-04-19

### 追加 (Added)
- 初回公開リリース。以下の主要機能を実装しました。

- 起動スクリプト / ランタイム
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV による動作分岐（paper_trading の場合は MockBrokerClient を使用し、paper_trading 用の SQLite DB を使用して本番 DB と完全分離）。
    - プロセス優先度を高 ('high') に設定して実行。
    - 停止は data/stop_requested.flag を監視して安全に停止。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視データを記録。

- 設定管理・検証・ウィザード
  - config.py: 環境変数と設定を一元管理する Settings クラスを実装。
    - .env 自動読み込み機能（.env / .env.local）を実装（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）。
    - 複数の設定プロパティ（DB パス、KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）とバリデーションを提供。
  - config_setup.py: 対話式 .env 生成/更新ウィザードを追加。
    - .env の読み込み・既存値の再利用・シークレットマスク表示・確認後保存まで。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数や DB パス、config/*.yaml の存在/パース検証。
    - --strict オプションで警告も失敗扱いにできる。

- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルのスコアソートと上位 N 選定。
    - calc_equal_weights / calc_score_weights: 等重およびスコア加重の重み計算（スコアが全て 0 の場合は等重へフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限チェックと候補除外ロジック。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をマップ）。
  - portfolio.position_sizing:
    - calc_position_sizes: 各銘柄の発注株数決定ロジックを実装。
      - allocation_method に "risk_based" / "equal" / "score" をサポート。
      - 単元株（lot_size）丸め、1銘柄上限、aggregate cap (available_cash) によるスケーリング、cost_buffer を考慮した保守的見積り、残差処理ロジックを実装。

- ユーティリティ
  - utils/logging_setup.py:
    - 共通ロギングセットアップを追加（コンソール stdout 用 StreamHandler と 日次ローテーションの TimedRotatingFileHandler を root ロガーに設定）。
    - ログディレクトリ自動作成、既存ハンドラのクリーンアップ、環境変数によるレベル/ディレクトリ設定をサポート。
  - utils/process_priority.py:
    - プロセス優先度（high/normal/low）設定と CPU affinity 設定関数を追加。
    - Windows/Linux(macOS, FreeBSD 含む) を考慮した実装。権限不足時は警告を出してスキップ。

- 監視・メトリクス系
  - monitoring_db 初期化呼び出しを各起動スクリプトで実行して監視テーブル存在を保証（冪等）。
  - SystemMonitor（起動スクリプトから利用）によりシステム稼働状況を DB に記録（詳細は monitoring モジュール内実装）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用 SQLite DB を読み取り、稼働率（uptime）、注文成功率、送信率、レイテンシ（平均/最大/P95）等の検証レポートを生成。
    - CLI オプション: --from / --to（YYYY-MM-DD）/ --db。環境変数 PAPER_TRADING_SQLITE_PATH からの指定も可能。
    - 基準値（稼働率 99%、fill_rate 90%、send_rate 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を出力。

- 研究 / ファクター計算（骨格実装）
  - research/factor_research.py: DuckDB 接続を受けてモメンタム等のファクターを計算するための基盤を追加（モジュール設計・定数・関数群の骨格を含む）。
    - 目的: prices_daily / raw_financials テーブルのみ参照し、Momentum/Value/Volatility/Liquidity の計算を行う設計。

- パッケージ公開情報
  - __init__.py にてバージョンを 0.1.0 に設定し、主要サブパッケージを __all__ でエクスポート。

### 変更 (Changed)
- （新規リリースのため該当なし）

### 修正 (Fixed)
- （新規リリースのため該当なし）

### 非推奨 (Deprecated)
- （該当なし）

### 削除 (Removed)
- （該当なし）

### セキュリティ (Security)
- 本リリースではセキュリティ関連の修正は含まれていません。運用環境でのシークレット管理・アクセス権限設定等は適切に行ってください。

### 既知の制限 / 注意点
- .env ファイルは絶対に Git にコミットしないでください（config_setup.py のヘッダにも注意喚起あり）。
- paper_trading の DB は本番 DB と分離される設計ですが、運用時のパス設定ミスに注意してください（validate_config で検出可能）。
- process priority / CPU affinity の設定は権限が必要な場合があり、権限不足時には設定がスキップされます（警告ログ出力）。
- research/factor_research.py は一部実装が続くことを想定（骨格はあるが完全なファクター計算・テストは今後追加予定）。
- position_sizing の価格欠損 (price が 0.0 や None) による過少見積りやフォールバック挙動については注記あり（TODO コメントあり）。

---

発行: KabuSys プロジェクトチーム