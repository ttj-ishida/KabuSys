# CHANGELOG

すべての重要な変更をここに記載します（Keep a Changelog 準拠）。
日付形式: YYYY-MM-DD

## [Unreleased]
- ドキュメント・リリースノートに反映予定の小さな改善点やリファクタリングが保留中。

## [0.1.0] - 2026-04-24
初回公開リリース。主要な機能群とユーティリティ、CLI を追加しました。

### 追加
- 基本アプリケーション骨格
  - パッケージのバージョン定義を追加（kabusys.__version__ = "0.1.0"）。
- 設定管理
  - 環境変数 / .env ファイルを扱う Settings クラスを追加（kabusys.config）。
  - .env 自動読み込み機能（プロジェクトルート検出: .git / pyproject.toml を基準）。
  - .env の読み込み挙動:
    - export プレフィックス対応
    - クォート文字列のエスケープ処理対応
    - インラインコメントの取り扱い
    - OS 環境変数を保護する保護機能（override オプション）
  - Settings による各種設定プロパティを追加（DB パス、PID/kill flag、しきい値、環境種別判定等）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
- 設定ウィザード / 検証 CLI
  - 対話式 .env 生成・更新ウィザードを追加（kabusys.config_setup）。
    - シークレット入力のマスク
    - デフォルト値、選択肢、説明表示、既存 .env 読み込み
  - 設定検証ツールを追加（kabusys.validate_config）
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検証
    - DB パスや config/*.yaml 存在チェック（PyYAML がない場合は警告）
    - 本番環境向けの追加ガード（LINE 設定、KILL_FLAG_CLEAR_ON_START）
    - --strict オプション（警告を FAIL 扱い）
- 実行・監視用起動スクリプト
  - 実行エンジン起動スクリプトを追加（kabusys.run_execution）
    - 実行環境に応じた DB 分離: KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用（data/paper_trading.db をデフォルト）
    - BrokerClientFactory によるブローカークライアント生成（paper/live を透過）
    - ExecutionEngine 起動・デーモンスレッド運用、停止フラグ検出による安全停止
    - PID ファイル管理、停止フラグ事前チェック
  - 監視ループ起動スクリプトを追加（kabusys.run_monitoring）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値は警告してデフォルトにフォールバック）
    - 監視 DB は環境に依らず本番 sqlite_path を参照
    - stop_requested.flag による安全停止
    - check_once() 呼び出しの例外保護（例外発生時はログを出して次ループへ）
- ロギング / プロセス制御ユーティリティ
  - 統一的ロギング設定ユーティリティを追加（kabusys.utils.logging_setup）
    - StreamHandler を stdout に出力（cron 等でのリダイレクトを想定）
    - TimedRotatingFileHandler による日次ローテーション（デフォルト logs/、30日保持）
    - 既存ハンドラクリア処理を実装（多重登録防止）
    - 環境変数 LOG_LEVEL / LOG_DIR による設定上書き対応
  - プロセス優先度 / CPU affinity 設定ユーティリティを追加（kabusys.utils.process_priority）
    - Windows / POSIX（Linux, Darwin, FreeBSD）差異吸収
    - set_process_priority(level: "high"|"normal"|"low")、set_cpu_affinity(cpu_count) を提供
    - 権限不足や未対応 OS では警告してスキップ
- ポートフォリオ構築ライブラリ（純粋関数）
  - 候補選定・重み計算（kabusys.portfolio.portfolio_builder）
    - select_candidates: スコア降順／同点は signal_rank でブレーク
    - calc_equal_weights / calc_score_weights（score が全て 0 の場合はフォールバック処理）
  - リスク調整（kabusys.portfolio.risk_adjustment）
    - apply_sector_cap: セクター集中上限に基づく候補除外（"unknown" セクターは除外対象外）
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear とフォールバック）
  - ポジションサイジング（kabusys.portfolio.position_sizing）
    - allocation_method による株数算出（"risk_based" / "equal" / "score"）
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap 制御
    - 投資総額が available_cash を超える場合のスケールダウンと残差配分ロジック（小数端数の安定的配分）
    - cost_buffer による手数料・スリッページ考慮
- 解析・レポートツール
  - Paper Trading 検証レポート生成ツールを追加（kabusys.tools.paper_verification_report）
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定
    - 閾値定義（稼働率 99%、注文成功率 90% など）
    - コマンドライン引数で期間指定（--from/--to）と DB パス指定（--db）
    - P95 計算ユーティリティ、SQL クエリの分離とエラーハンドリング
- リサーチ（ファクター計算）モジュール
  - duckdb 接続を受けるファクター計算モジュールを追加（kabusys.research.factor_research）
    - モメンタム / MA / ATR / ボリューム関連の定数と設計方針を実装（関数 calc_momentum 等の骨組み）

### 変更
- ログ出力方針
  - コンソール出力は stdout を使用（stderr ではない） — ログを一元的にファイル・stdout へ出力する設計に統一。
- DB ハンドリング
  - 監視系は環境にかかわらず監視用 sqlite（monitoring.db）を使用する方針を明記。
  - 実行系は paper_trading 環境時に専用 paper DB を使用して本番 DB と分離。

### 修正（バグフィックス相当）
- 環境変数パーサーの堅牢化
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱いを改善。
  - 不正な MONITOR_POLL_INTERVAL 値に対して警告を行い、time.sleep に渡す無効値を避けるフォールバックを実装。
- 設定検証の堅牢化
  - config/*.yaml の存在チェックを行い、PyYAML 未インストール時は警告してスキップする挙動。
  - 本番環境設定時に危険な構成（KILL_FLAG_CLEAR_ON_START=1 など）を警告するチェックを追加。
- ポジションサイズ計算の安全弁
  - 価格欠損時のスキップや lot_size 単位での丸め、aggregate cap 超過時のスケールダウンロジックで |zero-division| や負の値を回避する処理を追加。

### 既知の制限
- 一部モジュール（例: factor_research.calc_momentum）の実装は骨組み・定数までで途切れている箇所があり、完全実装は今後の作業予定。
- lot_size や銘柄ごとの単元差異は現状グローバルな lot_size 固定で扱っており、将来的な拡張（銘柄別 lot_map）は TODO として記載。
- ロギングディレクトリ作成失敗時はファイルログをスキップして stdout のみで継続する設計（その旨を警告）。

### セキュリティ
- .env ファイルは Git にコミットしない旨を config_setup の生成ファイルに明記。

---

参照:
- パッケージバージョンは src/kabusys/__init__.py の __version__（0.1.0）に基づく初回リリース記録です。
- 各機能の詳細は対応ファイルの docstring と関数コメントに基づいて要約しています。