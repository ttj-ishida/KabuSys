Keep a Changelog 準拠の CHANGELOG.md を以下に作成しました。リポジトリ内のコードから推測できる追加・変更点・改善点を日本語でまとめています。

注意: これはコードベースの内容から推測して作成した初回リリース向けの変更履歴です。実際のコミット履歴やリリースノートに合わせて調整してください。

========================================
全ての重要な変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠します。
========================================

Unreleased
----------

0.1.0 - 2026-04-18
------------------

Added
- 初期リリース: KabuSys 自動売買システムのコアモジュールを追加。
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
- 起動スクリプト / デーモン:
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度の設定、DB 接続、ブローカークライアント生成、ExecutionEngine の起動／停止監視（stop フラグ）を実装。KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB を使用する（本番 DB と分離）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能、停止フラグ検知でループを終了。
- 環境設定関連 CLI:
  - config_setup.py: .env の対話的ウィザードを追加（初期 .env 作成・更新支援）。シークレット項目のマスク表示、デフォルト値や選択肢の提示、保存確認をサポート。
  - validate_config.py: 起動前設定検証 CLI を追加。必須環境変数のチェック、KABUSYS_ENV や LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在および PyYAML があればパース検証を実施。--strict オプションで警告を FAIL とみなす機能を提供。
- 環境変数読み込み機能:
  - config.py: プロジェクトルート自動検出（.git または pyproject.toml を基準）と .env/.env.local の自動読み込みを実装（OS 環境変数が優先）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応。
  - .env パーサーは "export KEY=val"、クォート（シングル/ダブル）内のバックスラッシュエスケープ、インラインコメントの取り扱い等に対応する堅牢な実装を採用。
  - Settings クラスを提供し、各種設定（J-Quants トークン、kabu API パスワード、DB パス、paper_trading の挙動、監視閾値など）をプロパティとして取得・バリデーション可能に。
- ポートフォリオ構築関連（純粋関数群）:
  - portfolio_builder.py:
    - select_candidates: スコア降順、同点は signal_rank でタイブレークする候補選定。
    - calc_equal_weights / calc_score_weights: 等分配／スコア加重配分。全スコアが 0 の場合は等分配にフォールバック（警告を出力）。
  - risk_adjustment.py:
    - apply_sector_cap: 既存保有を基にセクター別エクスポージャーを計算し、指定上限を超えるセクターの新規候補を除外。unknown セクターは上限適用外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear および未知はフォールバック）を提供。
  - position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算。単元株（lot_size）丸め、1 銘柄上限や aggregate cap（利用可能現金）に応じたスケーリング、cost_buffer を考慮した保守的見積り、残余キャッシュを用いた端数配分ロジックを実装。
- ロギング・ユーティリティ:
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。ログディレクトリ作成失敗時にはファイル出力をスキップしてコンソール出力のみ継続。
- プロセス優先度・CPU affinity ユーティリティ:
  - utils/process_priority.py: Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収して優先度（high/normal/low）を設定する set_process_priority と、指定コア数への固定を行う set_cpu_affinity を提供。psutil ベースでの実装、権限不足や未対応環境での例外は警告に変換して安全にスキップ。
- ペーパートレード検証ツール:
  - tools/paper_verification_report.py: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から集計・指標算出を行い、稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）などの指標と PASS/FAIL 判定を出力する CLI を追加。P95 計算、期間フィルタ（--from/--to）、基準値（稼働率99%、成功率90% 等）を組み込み。
- monitoring DB 初期化ユーティリティ呼び出し:
  - run_execution と run_monitoring で init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等動作）。

Changed
- ログ出力の一元化: 全起動スクリプトは setup_logging(app_name=...) を呼び出すことでログ出力形式とファイル出力先を統一。
- .env 読み込み順序を明確化: OS 環境 > .env.local > .env（.env.local が .env を上書き）。

Fixed / Hardened
- 環境パースの強化: _parse_env_line が export プレフィックス、クォート内エスケープ、インラインコメントなど多数のケースを正しく扱うように実装。
- 設定値のバリデーション: Settings.paper_fill_mode や Settings.env / log_level 等で不正値検出時に明示的な ValueError を送出。
- ロガー設定の堅牢化: ログディレクトリ作成失敗時、ファイルハンドラ作成失敗時にフォールバックしてコンソール出力を維持。
- プロセス優先度設定時の例外処理: 権限不足や未実装 API の場合でも例外を抑えて警告ログを出し続行するように変更。
- run_monitoring のポーリング間隔取得: MONITOR_POLL_INTERVAL の不正値に対してデフォルトにフォールバックして安全に稼働するように実装（0 や負の値、非数を許容しない）。
- apply_sector_cap: "unknown" セクターに対してはセクター上限を適用しない挙動を明確に実装（既知セクターのみブロック）。

Docs / Help
- 各モジュールに詳細な docstring を追加し、設計上の注意点（例えば position_sizing の lot_size 将来的拡張、risk_adjustment の注記等）を明記。
- config_setup と validate_config に使い方とオプションの説明を追加（CLI ヘルプ相当）。

Known issues / TODO
- research/factor_research.py はモメンタム等の計算ロジック群を含むが、ファイル末尾で途中（calc_momentum の実装途中と思われる "start_da" で切れている）で未完成の箇所が存在する。実データでの検証と追加実装が必要。
- position_sizing の価格欠損（price が 0.0）の場合は TODO コメントの通りフォールバック価格戦略が未実装。前日終値や取得原価での補完を今後検討する必要あり。
- BrokerClientFactory.create の具体的実装（MockBrokerClient の選択等）は本 changelog のコードスニペットからは詳細が読み取れないため、ブローカークライアントの振る舞い（paper_trading と live の差分）はドキュメント・実装の確認を推奨。

Security
- 必須環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）が未設定の場合に validate_config がエラーを出すため、運用時に環境変数の管理を徹底すること。

----------------------------------------
この CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノートやコミットメッセージに合わせて必要に応じて修正・追記してください。