# CHANGELOG

すべての notable な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  

現在のリリース履歴はコードベースから推測して作成しています（自動生成された .env や DB 初期化などの挙動を含む）。

※ バージョン番号は src/kabusys/__init__.py の __version__ を参照しています。

Unreleased
----------
（なし）

0.1.0 - 2026-04-17
-----------------
Added
- 基本機能の初回リリース。
- アプリケーション設定管理（kabusys.config）
  - .env 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で検出）。
  - .env, .env.local の読み込み順序と OS 環境変数保護（上書き禁止）をサポート。
  - .env 行パーサを改良し、export プレフィックス、シングル/ダブルクォート、`\` エスケープ、インラインコメントに対応。
  - Settings クラスを提供し、各種設定（DB パス、API トークン、監視閾値、環境フラグ等）をプロパティで取得可能に。
  - PAPER_FILL_MODE 等の列挙的な環境変数値検証を実装。

- 環境設定ウィザード CLI（kabusys.config_setup）
  - 対話式ウィザードで .env を作成・更新するコマンドを提供。
  - デフォルト値、選択肢、シークレット入力、保存前確認を実装。
  - .env を安全に書き出すテンプレート実装。

- 設定検証 CLI（kabusys.validate_config）
  - 必須環境変数や KABUSYS_ENV の妥当性チェック。
  - DB パス・親ディレクトリ存在チェック、config/*.yaml の存在チェック（PyYAML が有れば構文検査も実施）。
  - --strict モードで警告を FAIL 扱いにできる。

- 実行系起動スクリプト（kabusys.run_execution）
  - ExecutionEngine の起動フローを実装（プロセス優先度設定、DB 接続、ブローカーファクトリ利用、コンポーネント組立て、スレッド実行）。
  - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite (PAPER_TRADING_SQLITE_PATH) を使用して本番データと完全分離。
  - 停止フラグ（data/stop_requested.flag）検知による安全な停止、PID ファイル指定。
  - RiskManager / Reconciler / OrderManager 等の組み立てと起動管理（初期設定値の導出含む）。

- 監視系起動スクリプト（kabusys.run_monitoring）
  - SystemMonitor のポーリングループ実装（MONITOR_POLL_INTERVAL で間隔上書き可能、デフォルト 60 秒）。
  - 監視は環境に関係なく本番用 sqlite_path を使用して監視テーブルを記録。
  - 停止フラグ検知・例外保護処理・DuckDB 接続の初期化を実装。

- プロセス制御ユーティリティ（kabusys.utils.process_priority）
  - クロスプラットフォームでのプロセス優先度設定を提供（Windows の HIGH_PRIORITY_CLASS, POSIX 系の nice 値対応）。
  - CPU affinity 設定ユーティリティを追加（最初の N コアに固定）。
  - 権限不足や未対応 OS の場合は安全にスキップして警告を出力。

- ポートフォリオ構築ライブラリ（kabusys.portfolio）
  - portfolio_builder: シグナル選定 (select_candidates)、等分配 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコアが全て 0 の場合は等分配へフォールバックし警告を出す。
  - risk_adjustment: セクター集中抑制 apply_sector_cap（売却予定銘柄を除外、"unknown" セクターは制限対象外）、市場レジームに基づく投下資金乗数 calc_regime_multiplier（bull/neutral/bear のマッピングとフォールバック）。
  - position_sizing: 発注株数算出 calc_position_sizes（risk_based / equal / score、lot_size 単位丸め、per-stock 上限、aggregate cap（資金超過時のスケーリング）を考慮）。cost_buffer を考慮した保守的コスト見積もりと残差分配ロジックを実装。

- リサーチ（kabusys.research.factor_research）
  - DuckDB を用いたファクター計算モジュール（モメンタム、ボラティリティ等）を実装。
  - calc_momentum: 1M/3M/6M リターン、MA200 乖離（データ不足時は None）。
  - calc_volatility（途中まで実装に続く設計）: ATR・平均売買代金・ボラティリティ指標を計算するための SQL ベース実装を追加。

- ペーパートレード検証ツール（kabusys.tools.paper_verification_report）
  - Paper Trading DB を読み取り、稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）等を集計してレポート出力。
  - デフォルトしきい値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を実装。
  - 日付フィルタ（--from / --to）および --db オプションをサポート。
  - P95 計算と欠損値処理を適切に扱う。

Changed
- ログと起動のデフォルト振る舞いを整備
  - run_* スクリプトで起動時にプロセス優先度を "high" に設定するようにした。
  - Settings.env / log_level の妥当性チェックを追加し、無効値は例外化。

Fixed
- .env のパースと読み込みに関する堅牢化
  - クォート内のバックスラッシュエスケープ、export プレフィックス、コメントの扱いなどを改善し、意図しない切断や誤読が発生しにくくした。
  - .env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化できるようにした（テスト用途）。

- MONITOR_POLL_INTERVAL の取り扱いを改善
  - 0 以下や不正値が指定された場合はデフォルト（60 秒）にフォールバックし、警告ログを出す。

- プラットフォーム依存処理の安全化
  - process_priority の実行で権限不足や未実装の API に遭遇した場合に例外を吐かず警告でスキップするようにした。

Security
- 機密情報の取り扱いに関する注意喚起をドキュメント (.env 書き出しヘッダ) に追加：
  - .env を絶対に Git にコミットしない旨を明記。

Notes / Internal
- Monitoring 用の DB 初期化関数 init_monitoring_db や SystemMonitor / ExecutionEngine 等のエンティティは外部モジュールとして利用されることを想定（本 CHANGELOG では呼び出し箇所の説明を中心に記載）。
- calc_volatility の SQL 部分は大きめのクエリで実装されており、欠損値伝播やウィンドウ集計の挙動を明示的に扱っている（ATR 計算の NULL 伝播等）。
- code ベースの多くの関数は副作用のない純粋関数設計を意識している（ポートフォリオ関連関数など）。

将来のリリースで検討したい改善点（TODO）
- 銘柄ごとの lot_size を銘柄マスタで管理する（現在は一律 lot_size 引数）。
- position_sizing の価格フォールバック（価格欠損時に前日終値や取得原価を使う）。
- factor_research の追加ファクターと完全なユニットテストカバレッジ。
- 実行時監視（SystemMonitor）での通知（LINE 連携）やより詳細な健康指標の収集。

---
もし特定のリリース日付やコミット履歴に基づくより正確な CHANGELOG を希望される場合は、git の履歴や追加のメタ情報を提供してください。