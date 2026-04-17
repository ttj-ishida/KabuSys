# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。本ファイルは「Keep a Changelog」仕様に準拠します。

- ルール: https://keepachangelog.com/ja/1.0.0/
- バージョン付けは SemVer を想定します。

## [Unreleased]

- （現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-17

初回リリース。日本株自動売買フレームワーク「KabuSys」の基礎機能を実装しました。主要な追加点・仕様は以下の通りです。

### 追加 (Added)
- 環境・設定関連
  - Settings クラス（kabusys.config）を実装し、環境変数から各種設定値を取得する API を提供。
  - .env の自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で検出）。環境変数の保護（OS 環境変数優先）に対応。
  - 環境変数パース機能の実装: export プレフィックス、クォート文字列（エスケープ対応）、インラインコメントの処理をサポート。

- 設定支援・検証 CLI
  - 環境設定ウィザード（kabusys.config_setup）を追加。対話式に .env を作成・更新可能。
  - 設定検証コマンド（kabusys.validate_config）を追加。必須環境変数、KABUSYS_ENV の妥当性、YAML 設定ファイルの存在/パース検証、運用向けのガードチェックなどを実行（--strict オプションあり）。

- 実行 / 監視ランナー
  - 実行エンジン起動スクリプト run_execution.py を追加。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を利用し、paper_trading 専用 SQLite（data/paper_trading.db をデフォルト）で本番 DB と完全分離。
    - プロセス優先度を起動時に設定（高優先度）。
    - 停止フラグ（data/stop_requested.flag）および PID ファイルによる制御を実装。スレッドで ExecutionEngine を実行し、停止フラグ検出時に安全に停止。
    - ExecutionEngine 起動前に監視テーブルが存在することを保証するため init_monitoring_db を呼び出す。
    - RiskManager / Reconciler / OrderManager 等の組み立てとデフォルト構成を用意（RiskConfig のデフォルト値を含む）。

  - 監視ループ起動スクリプト run_monitoring.py を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバックして警告を出力。
    - 監視は環境にかかわらず本番 sqlite_path を使用してデータを記録（監視 DB の初期化を保証）。
    - 停止フラグの検知による安全終了処理を実装。例外発生時はログを残して次ポーリングへ継続。

- ポートフォリオ構築（純関数群）
  - select_candidates / calc_equal_weights / calc_score_weights を実装（kabusys.portfolio.portfolio_builder）。
    - スコア降順・タイブレークの扱い、スコアが全て 0 の場合のフォールバックなどを実装。
  - セクター集中上限チェック apply_sector_cap を実装（kabusys.portfolio.risk_adjustment）。
    - 既存保有のセクター別エクスポージャ算出（売却予定銘柄の除外もサポート）。
    - unknown セクターの扱い、ポートフォリオ値が 0 の場合の安全処理。
  - レジーム乗数 calc_regime_multiplier を実装（bull/neutral/bear のマッピング、未知レジームはフォールバック）。
  - ポジションサイジング calc_position_sizes を実装（kabusys.portfolio.position_sizing）。
    - allocation_method（risk_based / equal / score）に対応。
    - 単元（lot_size）で丸め、max_position_pct・max_utilization の適用、cost_buffer を用いた保守的なコスト見積り。
    - aggregate cap 超過時のスケーリングと余り（fractional）に基づく追加配分ロジックを実装。

- リサーチ（ファクター計算）
  - factor_research モジュールを追加（kabusys.research.factor_research）。
    - Momentum（1M/3M/6M/MA200乖離）および Volatility（ATR20, avg_turnover, volume_ratio 等）の計算関数を実装。DuckDB を用いた SQL ベースの処理で prices_daily 等のテーブル参照。
    - データ不足時は None を返す安全な設計。

- ツール
  - Paper Trading 用検証レポート生成スクリプト tools.paper_verification_report を追加。
    - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を集計し PASS/FAIL 判定を出力。
    - 日付フィルタと DB パス指定（コマンドライン引数および環境変数）をサポート。

- ユーティリティ
  - process_priority ユーティリティ（kabusys.utils.process_priority）を追加。
    - Windows / POSIX（Linux, macOS 等）差分を吸収してプロセス優先度を設定（psutil ベース）。未対応 OS や権限不足時は警告を出してスキップ。
    - set_cpu_affinity を実装（指定コア数での CPU affinity 固定、未対応環境では警告）。

- パッケージ情報
  - パッケージバージョンを __version__ = "0.1.0" として設定。

### 変更 (Changed)
- .env 読み込みの優先順位を明確化: OS 環境変数 > .env.local > .env。テスト等で自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
- validate_config のチェックを充実化:
  - 必須環境変数の存在チェック、テンプレートのままの値（プレースホルダ）に対する警告。
  - config/*.yaml の存在確認および PyYAML がない場合のスキップと警告。
  - KABUSYS_ENV=live 時の追加警告（LINE 未設定や KILL_FLAG_CLEAR_ON_START の危険設定など）。

### 修正 (Fixed)
- MONITOR_POLL_INTERVAL に不正な値（非整数・0 以下）が設定された場合に sleep エラーになる問題を回避。警告を出してデフォルト値（60 秒）にフォールバック。
- run_execution / run_monitoring において DB 接続（SQLite / DuckDB）を finally ブロックで確実にクローズするように変更（リソースリーク対策）。
- process_priority の実行時に未対応 OS や権限エラーでクラッシュしないよう例外を捕捉し、警告でスキップ。

### 注意事項 / 既知の制約 (Known)
- PositionSizing の lot_size は現状グローバル共通（デフォルト 100）。将来的に銘柄別単元対応を検討中（TODO コメントあり）。
- apply_sector_cap は price_map に 0.0 が含まれる（価格欠損）場合にエクスポージャが過少評価される可能性がある旨をログに記録している。価格欠損時のフォールバック実装は将来対応予定。
- calc_regime_multiplier は未知のレジーム文字列を 1.0（Bull 相当）でフォールバックするため、運用前にレジームラベルが想定どおりであることを確認すること。
- 一部の機能（ExecutionEngine、BrokerClientFactory、monitoring_db 等）は本 CHANGELOG に記載されたローンチ用 API（呼び出し先）を前提としており、実行環境（kabuステーション接続や Broker 実装）に依存します。paper_trading では Mock を利用して本番と分離する設計です。

---

今後の予定（例）
- 銘柄別単元対応（lot_map）
- .env / secrets のより安全な取り扱い（暗号化やシークレットストア連携）
- テストカバレッジ拡充と CI ワークフロー定義

（以上）