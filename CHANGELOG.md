# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
コード内容から推測してまとめたため、実際のコミット履歴と差異がある場合があります。

## [0.1.0] - 2026-04-21

### 追加 (Added)
- 全体
  - 初期リリース。自動売買システム KabuSys のコアユーティリティ、CLI、およびポートフォリオ構築ロジックを追加。
  - パッケージバージョンを `__version__ = "0.1.0"` として設定（src/kabusys/__init__.py）。

- 起動スクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用して `data/paper_trading.db` を利用（本番 DB と完全分離）。
    - エンジンの PID ファイル管理、停止フラグ（data/stop_requested.flag）検出機構を実装。
    - スレッドで ExecutionEngine を起動し、停止フラグ検出時に安全に停止するループを実装。
  - 監視（モニタリング）ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様（設計上の注意点）。
    - 停止フラグ（data/stop_requested.flag）検出でループ終了。

- 設定管理・ユーティリティ
  - 環境設定管理モジュールを追加（src/kabusys/config.py）。
    - .env 自動ロード（プロジェクトルートを .git / pyproject.toml から検出）、`KABUSYS_DISABLE_AUTO_ENV_LOAD` による無効化。
    - .env パースロジックはクォート/エスケープや inline コメントを考慮。
    - 必須設定取得ヘルパー `_require()`、各種設定プロパティ（DB パス、PID パス、閾値、PAPER_FILL_MODE など）を提供。
    - `Settings` クラス経由で環境設定を取得可能。
  - .env 対話ウィザード CLI を追加（src/kabusys/config_setup.py）。
    - インタラクティブに .env を作成・更新し、シークレット項目はマスク表示。`.env` 書き込み機能を提供。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在・パース検証（PyYAML が未インストール時は警告）。
    - `--strict` モードで警告も失敗扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - 候補選定・重み付け（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順で上位 N を選択（タイブレークは signal_rank）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（全銘柄のスコア合計が 0 の場合は等配分にフォールバック）。
  - セクター制約・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存ポジションのセクター・エクスポージャに基づき、新規候補を除外するロジック（"unknown" セクターは上限適用免除）。
    - calc_regime_multiplier: レジームに基づく投下資金乗数（bull/neutral/bear をマップ、未知レジームは警告して 1.0 にフォールバック）。
  - ポジションサイズ計算（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: risk_based / equal / score 各方式に対応。単元（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash）に応じたスケーリング、cost_buffer を考慮した保守的見積りを実装。

- ロギング・プロセス管理ユーティリティ
  - 統一ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）の導入、既存ハンドラのクリア、ログディレクトリ作成失敗時のフォールバックを実装。
  - プロセス優先度 / CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX の差分吸収、優先度（high/normal/low）設定の実装。アクセス権限不足時は警告してスキップ。
    - CPU affinity 固定機能（最初の N コアに固定）。

- Paper Trading 関連ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - 検証指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシなどを計算してレポート出力。
    - デフォルト閾値: 稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms。
    - 日付フィルタ `--from` / `--to`、DB パス `--db` オプションを提供。

- リサーチ / ファクター計算
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - Momentum / Value / Volatility / Liquidity の設計方針と定数を定義。DuckDB 接続を受けて prices_daily / raw_financials を参照して計算する想定（実装は一部記述）。

### 変更 (Changed)
- （初期リリースのため該当なし）

### 修正 (Fixed)
- 入力値の堅牢性改善（例: MONITOR_POLL_INTERVAL の不正値に対するフォールバック）
  - run_monitoring.py: 環境変数 `MONITOR_POLL_INTERVAL` が不正（整数化失敗や 1 未満）な場合、デフォルト 60 秒にフォールバックし警告ログを出力。

- .env パースの堅牢化
  - config.py: クォート有無、バックスラッシュエスケープ、インラインコメント処理をサポートし、より多様な .env フォーマットへの耐性を向上。

- DB ハンドリングの安全性
  - run_execution.py / run_monitoring.py: 起動時に monitoring 用テーブルの初期化（init_monitoring_db）を行い、監視テーブルが存在することを保証（冪等）。

### 注意点 / 既知の制約 (Known issues / Notes)
- 監視（run_monitoring）は「環境にかかわらず本番 sqlite_path を使用」する仕様となっているため、開発環境での実行時に本番 DB を上書きしないよう注意が必要（意図的な設計としてコードに明記あり）。
- position_sizing の価格フォールバックは現時点では未実装（price が欠損した場合は 0.0 を使用し、過少見積りのリスクあり）。将来的に前日終値や取得原価によるフォールバックを検討する旨の TODO コメントあり。
- factor_research モジュールは設計・一部定数を記載しているが、関数実装はファイル末尾で途切れているため、完全実装が必要。
- config の自動 .env ロードはプロジェクトルート検出に依存する（.git / pyproject.toml）。配布後や一部環境で検出できない場合、自動ロードを行わない。

### ドキュメント / 使い方（抜粋）
- run_monitoring:
  - 実行: python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合: MONITOR_POLL_INTERVAL 環境変数を設定
- run_execution:
  - 実行: python -m kabusys.run_execution
  - paper_trading: KABUSYS_ENV=paper_trading を設定すると専用 DB に記録
- .env ウィザード:
  - 実行: python -m kabusys.config_setup
- 設定検証:
  - 実行: python -m kabusys.validate_config (--strict オプションで警告を失敗扱い)
- Paper Trading レポート:
  - 実行: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---

今後のリリースで期待される改善点（提案）
- factor_research の完全実装とユニットテスト整備
- position_sizing の価格フォールバックと銘柄別単元対応
- run_monitoring/run_execution のさらに細かい監視・リカバリ・Graceful shutdown の強化
- CI での設定検証（validate_config）を導入して設定ミスを早期に検出

（以上）