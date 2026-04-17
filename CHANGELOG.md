# Keep a Changelog
すべての注目すべき変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを採用します。

## [Unreleased]
- 

## [0.1.0] - 2026-04-17
最初の公開リリース。

### Added
- コア機能
  - アプリケーション初期版を追加。パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py）。
  - 環境・設定管理モジュール (kabusys.config)
    - プロジェクトルート自動検出（.git または pyproject.toml）による .env 自動ロード機能。
    - .env のパースロジックを実装（コメント・クォート・export 形式対応）。
    - Settings クラスを提供し、環境変数から各種設定（DB パス、API トークン、閾値、環境種別など）を取得可能。
    - PAPER_FILL_MODE の検証（"instant" / "partial" / "never" / "reject"）。
  - 設定ウィザード CLI (kabusys.config_setup)
    - 対話式で .env を生成・更新するウィザード。
    - デフォルト値表示、シークレットマスク、保存確認を実装。
  - 設定検証 CLI (kabusys.validate_config)
    - 必須環境変数・KABUSYS_ENV の妥当性・DB パスや config/*.yaml の存在・YAML パースをチェック。
    - --strict オプションで警告をエラー扱いにするモードを追加。
  - 実行用スクリプト
    - ExecutionEngine 起動スクリプト (run_execution.py)
      - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db をデフォルト）と MockBrokerClient を使用し、本番 DB と分離。
      - プロセス優先度を起動時に "high" に設定（utils.process_priority を利用）。
      - 停止フラグ（data/stop_requested.flag）および PID ファイル管理を実装。
    - SystemMonitor 起動スクリプト (run_monitoring.py)
      - 監視ポーリングループを実行。環境変数 MONITOR_POLL_INTERVAL で間隔上書き（デフォルト 60 秒）。
      - 監視は環境にかかわらず本番用 sqlite_path を参照する設計。
  - ポートフォリオ構築ライブラリ (kabusys.portfolio)
    - 候補選定・配分 (portfolio_builder.py)
      - select_candidates、等金額/スコア重み算出 (calc_equal_weights, calc_score_weights) を実装。
    - リスク調整 (risk_adjustment.py)
      - セクター集中上限の適用（apply_sector_cap）。
      - 市場レジームに応じた投下資金乗数の計算（calc_regime_multiplier）。未定義レジームは警告のうえ 1.0 でフォールバック。
    - ポジションサイズ計算 (position_sizing.py)
      - allocation_method（risk_based / equal / score）に基づいた発注株数決定、単元株丸め、aggregate cap スケーリング、cost_buffer（スリッページ/手数料）考慮を実装。
  - 研究／因子計算 (kabusys.research.factor_research)
    - DuckDB 接続を受け、prices_daily などを参照して Momentum / Volatility 等のファクターを計算する関数群を実装（モジュールは SQL + Python を併用）。
  - ユーティリティ
    - process_priority (kabusys.utils.process_priority)
      - Windows と POSIX (Linux/macOS/FreeBSD) の差異を吸収してプロセス優先度設定を実装（set_process_priority）。
      - CPU affinity を最初の N コアにピン留めする set_cpu_affinity を追加。
      - 権限不足・未対応 OS 時は警告を出しスキップ。
  - ツール
    - Paper Trading 検証レポート生成スクリプト (kabusys.tools.paper_verification_report)
      - paper_trading SQLite DB から期間集計を行い、稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）等を算出し、PASS/FAIL 判定を出力。
      - デフォルト閾値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。
      - P95 算出、日付フィルタ、DB パスの CLI オプション（--db）を提供。

### Changed
- （初期リリースのため該当なし）

### Fixed / Behavior notes
- .env 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定することで無効化可能（テスト時等の利便性）。
- run_monitoring の MONITOR_POLL_INTERVAL は整数変換に失敗した場合や 0 以下の場合にデフォルト（60 秒）へフォールバックし、警告ログを出力する。
- process_priority/set_cpu_affinity は権限不足や未対応プラットフォームで失敗しても例外を投げず警告でスキップされるように安全化。
- Settings の各プロパティで不正な値（例: KABUSYS_ENV や LOG_LEVEL）の場合は ValueError を投げ、早期に設定ミスを検出する設計。

### Known issues / Limitations
- position_sizing の価格フォールバック未実装:
  - risk_adjustment.apply_sector_cap は price_map に値がない（0.0）場合にエクスポージャーを過小見積もる可能性があり、その場合ブロック除外となる恐れがある（TODO コメントあり）。将来的に前日終値や取得原価でのフォールバックを検討。
- research.factor_research は DuckDB の prices_daily / raw_financials テーブルに依存するため、DB のスキーマ/データが適切でないと計算不能となる。
- config/*.yaml の検証は PyYAML 非インストール時はスキップされ、警告が出る仕様。
- run_monitoring は監視データベースとして常に Settings.sqlite_path を使用する設計（意図的）。監視を別 DB に分離したい場合は運用上の調整が必要。

### Migration / Upgrade notes
- 新規導入時はまず python -m kabusys.config_setup を実行して .env を生成し、python -m kabusys.validate_config で設定検証を行ってください。
- Paper Trading を使用する際は KABUSYS_ENV=paper_trading を設定すると、エンジンは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を利用して本番 DB と完全に分離されます。

### Security
- 本リリースでは外部シークレット（J-Quants トークン、kabu API パスワード等）を .env に保存する前提です。.env は決してリポジトリにコミットしないでください（config_setup でも明示）。
- LINE トークン等が未設定の本番 KABUSYS_ENV=live 環境ではアラートが届かない可能性がある旨を validate_config が警告します。

---

(注) 本 CHANGELOG はコードベースの現状から推測して作成しています。実際のリリースノートを作成する際は運用上の重要な差分やセキュリティ注記をプロジェクトの実情に合わせて追記してください。