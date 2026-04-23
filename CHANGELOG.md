# CHANGELOG

このファイルは Keep a Changelog の形式に準拠しており、すべての notable な変更をバージョン順に記録します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

全般:
- 言語: 日本語
- バージョン番号はパッケージの __version__ に対応しています。

## [Unreleased]

（現在なし）

## [0.1.0] - 初回リリース
リリース日: 未指定

### 追加 (Added)
- 基本アプリケーション構成
  - パッケージ初期化とバージョン情報を追加（kabusys.__version__ = "0.1.0"）。
- 環境設定/管理
  - Settings クラスによる環境変数ラッパーを実装（kabusys.config）。
    - J-Quants / kabu API / LINE / DB /監視/システム設定等のプロパティを提供。
    - env 値検証（development / paper_trading / live）およびログレベル検証を実装。
    - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、KILL_FLAG_CLEAR_ON_START 等の設定をサポート。
  - .env 自動ロード機能を実装:
    - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を読み込み。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - 対話式環境設定ウィザードを追加（kabusys.config_setup）。
    - .env の初期作成・更新を支援する CLI。既存 .env の読み込み・マスク表示・保存機能を備える。
- 起動スクリプト
  - 実行エンジン起動スクリプト（kabusys.run_execution）を追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 DB を使用し MockBroker を利用する想定。
    - 停止フラグ（data/stop_requested.flag）、PID ファイル管理、スレッドでのエンジン実行と安全停止処理を実装。
  - 監視ループ起動スクリプト（kabusys.run_monitoring）を追加。
    - ポーリング間隔を環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を参照する設計（監視用 DB として一貫して本番 DB を使用）。
- 設定検証 CLI
  - kabusys.validate_config を追加。
    - .env と config/*.yaml の存在・基本検証を行う CLI。
    - 必須/任意環境変数チェック、KABUSYS_ENV の妥当性、DB パスの親ディレクトリチェック、YAML のパース検証（PyYAML 未インストール時は警告）等を実装。
    - --strict オプションで警告も失敗として扱う。
- ロギング/プロセスユーティリティ
  - 統一ロギング設定ユーティリティを追加（kabusys.utils.logging_setup）。
    - stdout ストリームハンドラ + 日次ローテートファイルハンドラ（TimedRotatingFileHandler）を設定。
    - ログディレクトリ自動作成、失敗時のフォールバック（コンソールのみ）対応。
    - LOG_DIR / LOG_LEVEL 環境変数との連携。
  - プロセス優先度と CPU affinity ユーティリティを追加（kabusys.utils.process_priority）。
    - Windows / POSIX（Linux/macOS/FreeBSD）対応の優先度設定（psutil を使用）。
    - set_process_priority/set_cpu_affinity を提供し、権限不足時は警告を出してスキップ。
- ポートフォリオ構築（純粋関数群）
  - 銘柄選定・重み計算（kabusys.portfolio.portfolio_builder）
    - select_candidates（スコア降順 + tie-break）、calc_equal_weights、calc_score_weights を実装。
  - セクター制約・レジーム乗数（kabusys.portfolio.risk_adjustment）
    - apply_sector_cap：既存保有比率に基づくセクター上限フィルタ実装。unknown セクターは除外しない。
    - calc_regime_multiplier：レジーム（bull/neutral/bear）に応じた投下資金乗数を実装（未知レジームは 1.0 にフォールバック）。
  - ポジションサイズ決定（kabusys.portfolio.position_sizing）
    - calc_position_sizes を実装（allocation_method: risk_based / equal / score）。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金を超える場合のスケーリング）、
      cost_buffer を用いた保守的見積り、端数処理（fractional remainder による優先割当）等を備える。
- 研究/ファクター計算（部分実装）
  - kabusys.research.factor_research にモジュール骨格を追加（モメンタム等の計算方針と定数を定義）。
    - DuckDB を用いた prices_daily / raw_financials を参照する設計。関数 calc_momentum の実装開始（途中まで）。
- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（kabusys.tools.paper_verification_report）。
    - SQLite（paper_trading DB）から稼働率、注文成功率、送信率、レイテンシ等を集計し PASS/FAIL 判定を出力。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を採用。日付フィルタ（--from/--to）と --db オプション対応。

### 変更 (Changed)
- ログ出力の挙動
  - 全起動スクリプトから共通の setup_logging() を呼び出すように統一し、ログ管理を中央化。
- DB の扱い
  - run_execution は paper_trading 環境時に専用の PAPER_TRADING_SQLITE_PATH を使用して本番 DB と完全分離する設計を採用。
  - run_monitoring は監視用に常に sqlite_path（本番相当）を使用するよう明記。

### 修正 (Fixed)
- .env パーサーの堅牢化（kabusys.config._parse_env_line）
  - export プレフィックス対応、シングル／ダブルクォート内でのバックスラッシュエスケープ処理、インラインコメントの取り扱いを実装。
  - クォート無し値に対する # の取り扱いを改善（直前が空白の場合のみコメントとみなす）。
- ログハンドラ二重登録防止
  - setup_logging は既存ハンドラを一度 flush/close してから再設定する仕様により、多重設定を防止。

### その他 / ドキュメント (Documentation)
- 各モジュールに docstring と使用例を追加し、設計意図・注意点（例: price が欠損時の挙動、将来的な拡張案）を明記。
- config_setup のウィザードにより .env のテンプレート生成を自動化。
- validate_config による起動前チェックと YAML パース検証で設定不備の早期検出を支援。

### 既知の制限 / TODO
- research.calc_momentum の実装が途中で終了しており、ファクター計算モジュールは一部未完成。
- position_sizing の lot_size は現在グローバル固定（将来的に銘柄別 lot_map の導入を検討）。
- apply_sector_cap は price_map に欠損（0.0）がある場合にエクスポージャーが過少見積りされる可能性がある旨の TODO を残している。
- ファイル入出力やプロセス優先度設定は権限や環境依存で失敗することがあるため、フォールバック動作を多用している（ログ等で警告を出してスキップ）。

## 既知のセキュリティ関連 (Security)
- 機密情報（API トークン・パスワード等）は .env にて管理する設計。ただし .env を絶対に Git にコミットしない旨を README/ウィザードに明示。
- ロギングにおいてシークレットはウィザード表示時にマスクされるが、ログ出力での露出には注意が必要。運用時はログレベル/出力先の管理を推奨。

---

注: 本 CHANGELOG は提供コードからの推測に基づき作成しています。実際のリリース作業や変更履歴の管理は、コミット履歴やリリースタグに基づいて正式に記録してください。