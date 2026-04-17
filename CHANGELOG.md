# Changelog

すべての変更は Keep a Changelog の形式に従います。  
安定版リリースはセマンティックバージョニングに準拠します。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-04-17

### Added
- 基本アプリケーション構成と CLI ツール群を追加。
  - Settings クラス（kabusys.config）:
    - .env / .env.local の自動読み込み（プロジェクトルート検出ロジックを使用、CWD 非依存）。
    - 環境変数取得ラッパー（必須チェック、各種パス・閾値・フラグのプロパティを提供）。
    - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH 等の paper_trading 用設定。
  - 対話式環境設定ウィザード（kabusys.config_setup）:
    - .env の初期作成・更新を対話式に支援。
    - 既存値の読み取り・シークレットマスキング・確認・保存機能。
  - 設定検証ツール（kabusys.validate_config）:
    - 必須環境変数・KABUSYS_ENV・ログレベル・DB パス・config/*.yaml の存在と YAML パース検証。
    - --strict オプション（警告を FAIL 扱いにする）。
  - 実行系 / 監視起動スクリプト:
    - run_execution: ExecutionEngine 起動用（thread ベースのセッション実行、停止フラグ監視、paper_trading 時は専用 DB を使用）。
    - run_monitoring: SystemMonitor ポーリングループ起動（MONITOR_POLL_INTERVAL でポーリング間隔を変更可能、デフォルト 60 秒）。
    - どちらも起動時にプロセス優先度を "high" に設定する呼び出しを行う。
  - プロセス制御ユーティリティ（kabusys.utils.process_priority）:
    - クロスプラットフォームでプロセス優先度設定（Windows / POSIX）と CPU affinity 設定のユーティリティ。
    - 権限不足や未対応 OS の場合は警告を出して安全にフォールバック。
  - ポートフォリオ構築モジュール（kabusys.portfolio）:
    - 銘柄選定、等金額・スコア加重の重み計算（portfolio_builder）。
    - セクター集中制限・レジーム乗数（risk_adjustment）。
    - 発注株数決定、単元株丸め、aggregate cap（position_sizing）。
    - 各関数は純粋関数（メモリ計算のみ）として設計。
  - リサーチ／ファクター計算（kabusys.research.factor_research）:
    - DuckDB 接続を受けてモメンタム・ボラティリティ等のファクターを算出（prices_daily / raw_financials 前提）。
    - mom_1m/mom_3m/mom_6m、MA200 乖離、ATR、20 日平均売買代金等を計算。
  - Paper Trading 検証レポート（kabusys.tools.paper_verification_report）:
    - ペーパートレード用 SQLite DB から稼働率・注文成功率・レイテンシ等を集計して PASS/FAIL レポートを生成。
    - P95 計算、しきい値（稼働率99%、注文成功率90% 等）を定義。

### Changed
- .env パーサーの堅牢化（kabusys.config._parse_env_line）:
  - export キーワード対応、シングル／ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント処理の改善。
  - .env.local は .env を上書きする優先度で読み込まれる（OS 環境変数は保護）。
- データベースの運用分離:
  - paper_trading モードでは paper_trading 専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
  - 監視（run_monitoring）は環境にかかわらず本番 sqlite_path を使用する設計（意図的な動作）。
- ExecutionEngine 起動フロー（run_execution）:
  - BrokerClientFactory を用いたブローカークライアント生成。paper_trading 時は MockBrokerClient を使用する想定。
  - RiskManager のデフォルト設定値をコード上に定義（max_position_pct 等）。initial_portfolio_value は broker.get_available_cash() を参照して初期化。
  - エンジンはデーモンスレッドで run_session を実行し、停止フラグで安全に停止するループを実装。
- ポジションサイジングの挙動:
  - lot_size 単位で丸め、cost_buffer を用いて手数料/スリッページを保守的に見積もり aggregate cap に反映。
  - 投資金額が available_cash を超える場合はスケーリングと余りの順次配分を行うロジックを導入。

### Fixed
- プロセス優先度 / CPU affinity 設定時の例外ハンドリング強化（未サポート定数や権限不足時に安全にフォールバックして警告を出すよう修正）。
- .env ファイル読み込みでアクセス不能なファイルに対して警告を出すように（読み込み失敗時に warnings.warn）。

### Documentation
- 各モジュールに docstring と実装注記（設計意図、想定振る舞い、TODO）を充実させ、使い方や注意点を明示。
  - 例: portfolio モジュールは PortfolioConstruction.md を参照する旨、risk_adjustment の unknown セクターの扱い、position_sizing の将来拡張案等。
  - config_setup の .env テンプレートに「.env を絶対に Git にコミットしないこと」等の注意を記載。

### Security
- .env ファイル生成テンプレートに秘密情報の取り扱い注意（Git 管理除外）を明記。
- Settings._require による必須環境変数の未設定検出で早期失敗を促す（運用ミスによる鍵漏洩や誤起動の防止に寄与）。

### Notes / Known issues
- run_monitoring はコメントにある通り「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する」設計になっているため、意図せず本番 DB を参照しないよう運用上の注意が必要です。
- position_sizing や risk_adjustment の一部ロジックは価格データの欠損（price == 0 または None）に対するフォールバックが未完であり、将来の拡張で前日終値や取得原価の利用を検討する旨を注記。
- Paper Trading 検証レポートは SQLite テーブル構成（system_status / trade_logs / risk_logs 等）を前提としており、スキーマ不整合時は OperationalError を捕捉して柔軟に挙動するが、完全な互換性を保証するものではありません。

---

（この CHANGELOG はコードベースから推測して作成したため、実際のコミット履歴や設計意図と完全に一致しない場合があります。必要であればリポジトリのコミットログに基づく正確な履歴へ差し替えてください。）