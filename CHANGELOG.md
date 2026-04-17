# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。  

履歴は安定リリース（バージョン順、新しいものが上）で管理します。

## [Unreleased]

（現在なし）

---

## [0.1.0] - 2026-04-17

初回リリース。以下の主要機能・ユーティリティを追加しました。

### 追加 (Added)
- アプリケーションパッケージの初期化
  - kabusys パッケージを導入し、バージョンを 0.1.0 に設定。 (src/kabusys/__init__.py)
- 環境設定管理
  - .env 自動読み込み（プロジェクトルート検出ロジックを使用）。OS 環境変数を保護する読み込み順序を実装。 (src/kabusys/config.py)
  - Settings クラスを追加し、各種環境変数（API トークン、DB パス、監視閾値、実行環境等）をプロパティとして提供。検証・正規化ロジックを含む。
- 対話式環境設定ウィザード
  - .env の新規作成・更新を行う CLI を追加。既存値読み込み、シークレットマスク、保存機能を持つ。 (src/kabusys/config_setup.py)
- 設定検証 CLI
  - .env と config/*.yaml の存在・基本的妥当性を検証する CLI を追加。--strict オプションで警告を失敗として扱える。 (src/kabusys/validate_config.py)
- 実行関連スクリプト
  - ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、paper_trading 用 DB 分離、Broker クライアントファクトリの利用、ExecutionEngine の起動・停止制御を実装。停止フラグの検出対応。 (src/kabusys/run_execution.py)
- 監視関連スクリプト
  - SystemMonitor ポーリングループ起動スクリプトを追加。環境変数 MONITOR_POLL_INTERVAL でポーリング間隔上書き可能。Monitoring は環境にかかわらず本番 sqlite_path を使用。停止フラグ処理、例外ハンドリングを実装。 (src/kabusys/run_monitoring.py)
- プロセス優先度 / CPU affinity ユーティリティ
  - Windows / POSIX の差を吸収してプロセス優先度や CPU affinity を設定するユーティリティを追加。権限不足や未対応環境でのフォールバック処理あり。 (src/kabusys/utils/process_priority.py)
- ポートフォリオ構築モジュール
  - 候補選定、重み計算（等分・スコア加重）、ポジションサイズ計算、セクター上限適用、レジーム乗数などの純粋関数群を実装（メモリ内計算）。ロギングと安全なフォールバックを備える。 (src/kabusys/portfolio/*.py)
    - select_candidates, calc_equal_weights, calc_score_weights
    - calc_position_sizes（lot 単位丸め、aggregate cap、cost_buffer 対応）
    - apply_sector_cap（既存保有を考慮したセクター上限適用）
    - calc_regime_multiplier（レジームに応じた乗数）
- ファクター計算（リサーチ）モジュール
  - DuckDB を用いた定量ファクター計算機能を追加（モメンタム、ボラティリティ等。prices_daily/raw_financials を参照）。P95 等の統計処理も実装。 (src/kabusys/research/factor_research.py)
- Paper Trading 検証ツール
  - ペーパートレード用 SQLite ログから稼働率・注文成功率・レイテンシ等の指標を集計してレポートを生成する CLI を追加。閾値ベースの PASS/FAIL 判定を出力。 (src/kabusys/tools/paper_verification_report.py)

### 変更 (Changed)
- DB の取り扱い方針
  - 監視（monitoring）は起動環境にかかわらず本番用 sqlite_path を使用する設計に明示（run_monitoring）。一方、実行エンジンは KABUSYS_ENV=paper_trading 時に paper_trading 用 DB に分離して動作（run_execution）。
- .env 読み込みの挙動
  - OS 環境変数を保護するため、.env の読み込みで既存 OS 環境変数を上書きしない（.env.local の override は可）。 (config.py)
- log / メッセージの改善
  - 各モジュールで起動時や重要イベント（停止フラグ検出、ポーリング開始/終了、入力不備等）にログを出力するように追加。

### 修正 (Fixed)
- .env パーサの堅牢化
  - export プレフィックス、クォート有り文字列のエスケープ、インラインコメントの扱い、空行やコメント行の無視等を正しく処理するように改良。 (config.py)
- ポジションサイズ計算の堅牢化
  - 価格欠損時のスキップ、単元株（lot_size）での丸め、aggregate cap 適用時のスケーリングと残余配分の安定化を実装。 (portfolio/position_sizing.py)
- スコア重み計算のフォールバック
  - 全銘柄のスコアが 0 の場合は等金額配分にフォールバックし警告ログを出力するよう対応。 (portfolio/portfolio_builder.py)
- レジーム乗数の既定値フォールバック
  - 未知のレジーム値が来た場合は 1.0 でフォールバックし警告を出す。 (portfolio/risk_adjustment.py)
- プロセス優先度設定の許容性改善
  - 非対応 OS、権限不足、未実装 API に対して警告を出して処理をスキップすることで起動停止を防止。 (utils/process_priority.py)
- 監視ループの堅牢化
  - check_once の例外を捕捉してループ継続、ポーリング間隔の環境変数値が不正（非正整数）な場合のフォールバック処理を実装。 (run_monitoring.py)

### ドキュメント / 使い勝手 (Docs/UX)
- CLI ヘルプやウィザードの案内メッセージを整備（config_setup, validate_config, paper_verification_report）。
- .env の雛形生成・注意書きを config_setup で追加（.env を Git にコミットしない旨の警告）。

### 既知の制限 (Known issues)
- position_sizing の price 欠損に対する暫定処理:
  - price が欠損 (0.0) の場合、エクスポージャーや計算が過少評価される可能性があり、将来的に前日終値や取得原価等のフォールバック価格を導入する予定。 (portfolio/risk_adjustment.py)
- YAML パース検証は PyYAML に依存。未インストールの場合はファイル存在チェックのみでスキップされる。 (validate_config.py)

---

※ この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミットログやリリースノートがある場合は、それに合わせて調整してください。