KEEP A CHANGELOG
すべての重要な変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

[0.1.0] - 2026-04-17
Added
- 初回公開リリース。
- 環境設定/起動関連
  - Settings クラスを導入し、環境変数経由で設定値を一元管理（kabusys.config）。
  - プロジェクトルート自動検出による .env / .env.local の自動ロード機能を追加。
    - .env のパースはクォート／エスケープ／コメント処理に対応。
    - OS 環境変数を保護した上で .env.local による上書きをサポート。
  - config_setup CLI を追加（python -m kabusys.config_setup）。対話式ウィザードで .env の生成・更新を支援。
  - validate_config CLI を追加（python -m kabusys.validate_config）。必須環境変数、DB パス、config/*.yaml の存在・パース等を事前チェック。--strict モードをサポート。
- 実行／監視ランナー
  - Execution Engine 起動スクリプトを追加（kabusys.run_execution）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite (デフォルト: data/paper_trading.db) と MockBroker を使用して本番 DB と完全分離。
    - 起動前に stop フラグ確認、PID ファイル管理、スレッドでの実行・安全停止処理を実装。
  - SystemMonitor 起動スクリプトを追加（kabusys.run_monitoring）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視処理は環境に関わらず本番 sqlite_path を使用する仕様。
    - 停止フラグ検知、例外時のログ出力と次ポーリングへの復帰を実装。
- データベース / 分析
  - DuckDB / SQLite 統合サポートを追加（Settings に duckdb_path / sqlite_path / paper_sqlite_path）。
  - 監視テーブル初期化ユーティリティを組み込み（init_monitoring_db を呼び出す箇所を用意）。
- ポートフォリオ構築（純粋関数群）
  - 候補選定・重み計算（kabusys.portfolio.portfolio_builder）
    - select_candidates（スコア降順・タイブレークロジック）
    - calc_equal_weights, calc_score_weights（スコアが全て 0 の場合は等金額にフォールバック）
  - セクター集中制限・レジーム乗数（kabusys.portfolio.risk_adjustment）
    - apply_sector_cap（既存ポジションからセクター別エクスポージャを算出し上限超過セクターの新規候補を除外）
    - calc_regime_multiplier（bull/neutral/bear の乗数を返却。未知レジームは警告のうえ 1.0 にフォールバック）
  - 株数決定・リスク制限・単元丸め（kabusys.portfolio.position_sizing）
    - allocation_method による株数計算（risk_based / equal / score）
    - 単元(lot_size)丸め、1銘柄上限・aggregate cap（available_cash に合わせたスケールダウン）、cost_buffer を考慮した保守的見積り
    - 不足データ（価格欠損等）時のスキップとログ出力
- 研究用ファクター計算（kabusys.research.factor_research）
  - DuckDB を利用したファクター群を実装（momentum, volatility 等）。
    - calc_momentum: mom_1m/mom_3m/mom_6m と 200 日移動平均乖離率（データ不足時は None）。
    - calc_volatility: ATR、相対 ATR、20日平均売買代金、出来高比率など（ウィンドウ不足は None）。
  - DuckDB SQL を用いた効率的な集計実装。
- 運用ユーティリティ
  - process_priority ユーティリティを追加（kabusys.utils.process_priority）。
    - Windows / POSIX(Linux/macOS/FreeBSD) を吸収してプロセス優先度と CPU アフィニティ設定を提供。権限不足や未対応環境では警告ログでフォールバック。
- ペーパートレード検証ツール
  - tools.paper_verification_report を追加（python -m kabusys.tools.paper_verification_report）。
    - paper_trading SQLite を解析して稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL 判定するレポートを出力。
    - デフォルトの閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を採用。日付フィルタや DB パス指定をサポート。

Changed
- 初版のため履歴なし（初回追加が主）。

Fixed
- 初版のため履歴なし（初回追加が主）。

Security
- 初版のため履歴なし。

Notes / 実装上の注意
- .env 自動ロードはプロジェクトルートの検出に失敗した場合はスキップされるため、配布後やテスト環境での挙動に配慮済み。
- run_monitoring は監視用 DB を本番 sqlite_path 固定で参照する仕様のため、テストで分離したい場合は DB パスを適切に用意してください。
- process_priority の設定は OS や権限に依存するため、設定失敗時はログで通知して処理を継続します。
- Paper Trading と本番 DB は明確に分離される設計（PAPER_TRADING_SQLITE_PATH を利用）。

今後の予定（例）
- 銘柄別単元サイズのマスタ対応（lot_size を銘柄毎にする拡張）
- 更なるメトリクス追加（可観測性強化）や YAML 設定の詳細バリデーション強化
- テストケース（ユニット/統合）と CI の整備

[Unreleased]
- （次リリースに向けた変更はここに記載）