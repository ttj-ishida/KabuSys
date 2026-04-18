# CHANGELOG

すべての注記は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠します。  
このファイルはソースコードから推測して作成した変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-04-18
初回リリース — 基本機能の一式を追加。

### 追加 (Added)
- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の MockBroker を利用し、data/paper_trading.db を使用して本番 DB と完全に分離する挙動を実装。
    - 実行中の停止フラグ (data/stop_requested.flag) と PID 管理 (data/execution.pid) に対応。
    - エンジンはスレッドで起動され、停止フラグ検知または正常終了でシャットダウンする。
    - RiskManager によるデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec 等）を導入し、broker.get_available_cash() を初期ポートフォリオ値に使用。

- 監視スクリプト
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視 DB は環境にかかわらず本番 sqlite_path を使用して初期化。
    - 停止フラグ (data/stop_requested.flag) を検知してループを終了する処理を追加。
    - 例外発生時はログ出力してポーリングを継続する耐障害性を確保。

- 設定管理
  - config.py: 環境変数/.env の自動読み込みと Settings クラスを実装。
    - プロジェクトルート検出ロジック（.git または pyproject.toml）を導入し、CWD に依存しない `.env` 自動ロードを実現。
    - .env の行パーサを作成（コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応）。
    - 環境変数の保護 (protected keys) を考慮した読み込み方式を実装。
    - 各種設定プロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE 等）。
    - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）。
    - 環境・ログレベルの妥当性チェック（KABUSYS_ENV, LOG_LEVEL）。
    - settings = Settings() によるモジュールレベルの利用を提供。

- 設定補助 CLI
  - config_setup.py: 対話式ウィザードを追加（.env の初期作成/更新を支援）。
    - 秘匿入力（トークン等）や選択肢、デフォルト表示、既存 .env の読み込み／Enter で再利用に対応。
    - 生成された .env に注意書きとセクション分けを付与して書き出す。
    - 実行例: python -m kabusys.config_setup

  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数やパス、config/*.yaml の存在・パース確認、KABUSYS_ENV の警告/エラー判定等を行う。
    - --strict オプションで警告も失敗扱いにできる。
    - 実行例: python -m kabusys.validate_config

- ロギング・ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。
    - コンソール (stdout) 出力と TimedRotatingFileHandler による日次ローテーション（30日保持）をルートロガーへ設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベルとログディレクトリの解決順を明確化（引数 > 環境変数 > デフォルト）。
    - 全起動スクリプトから呼び出して統一的ログ管理が可能。

- プロセス制御ユーティリティ
  - utils/process_priority.py: プロセス優先度 (nice / Windows priority) と CPU affinity 設定を追加。
    - Windows/Linux/macOS に対する差分吸収ロジックを実装。
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(N) を提供。
    - 設定に失敗した場合は警告ログを出力してスキップ。

- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順＋同点時は signal_rank でタイブレークして上位 N を選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を提供。全スコアが 0 の場合は警告を出し等金額にフォールバック。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限 (max_sector_pct) を適用して候補をフィルタリング。売却予定銘柄をエクスポージャー計算から除外可能。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数を返す。未知レジームは 1.0 でフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes: risk_based / equal / score の配分方式をサポートし、lot_size（単元株）丸め、per-position 上限、aggregate cap（available_cash によるスケールダウン）、cost_buffer を加味したスケーリングと残差処理を実装。

- リサーチ（ファクター計算）モジュール
  - research/factor_research.py: ファクター計算の骨格を追加（Momentum, Value, Volatility, Liquidity を想定）。
    - DuckDB を用いた prices_daily/raw_financials 参照設計。
    - モメンタム計算関数 calc_momentum のインターフェース・定数を実装（実装途中の箇所あり）。

- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、リスク却下数、平均/最大/P95 レイテンシを算出して判定（PASS/FAIL）。
    - デフォルト DB パスは data/paper_trading.db。--from/--to/--db オプションをサポート。
    - 判定閾値（稼働率99%、成立率90%、送信率95%、P95レイテンシ200ms）を設定。

- パッケージメタ
  - __init__.py にバージョン情報 __version__ = "0.1.0" と主要サブパッケージの __all__ を追加。

### 変更 (Changed)
- なし（初回リリースのため既存機能からの変更はなし）。

### 修正 (Fixed)
- なし（初回リリースのため既知のバグ修正エントリはなし）。

### 非推奨 (Deprecated)
- なし。

### 削除 (Removed)
- なし。

### セキュリティ (Security)
- なし（公開 API キー等の管理は .env に委ね、.env の Git コミット防止を README・ウィザードにて注意喚起）。

---

注記:
- この CHANGELOG は提供されたソースコードの内容から機能追加・動作を推測して作成したものです。実際のコミット履歴や設計仕様に基づくものではないため、必要に応じて日付・説明・カテゴリをプロジェクト実情に合わせて調整してください。