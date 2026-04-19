# Changelog

すべての変更は Keep a Changelog の慣例に準拠しています。  
リリース日付はリポジトリ内の現在コードに基づいて推測しています。

## [v0.1.0] - 2026-04-19

### 追加 (Added)
- 実行エントリスクリプトを追加
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。KABUSYS_ENV による Paper Trading 分離（paper_trading 環境では専用 SQLite DB に記録）をサポート。起動時にプロセス優先度を "high" に設定し、停止フラグ／PID ファイルに対応。
  - run_monitoring.py: SystemMonitor をポーリングする監視ループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番 sqlite_path を使用する仕様を採用。

- 環境設定関連の CLI を追加
  - config_setup.py: .env を対話式に作成/更新するウィザードを追加。よく使う設定項目（KABUSYS_ENV、J-Quants トークン、kabu API パスワード、DB パス、ログレベルなど）をサポート。
  - validate_config.py: 起動前に .env および config/*.yaml の不備を検出する検証ツールを追加。--strict オプションで警告を失敗扱いにできる。

- 設定管理モジュール
  - config.py: .env 自動読み込み（プロジェクトルート検出）機能を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化、.env / .env.local の読み込み順（OS 環境変数 > .env.local > .env）、値のパース機能（クォート・エスケープ・インラインコメント対応）を提供。Settings クラスで各種環境設定（DB パス、ログレベル、閾値、env 判定、paper_trading 用パス・fill_mode など）を取得可能に。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30 日保持）を設定するユーティリティを追加。ログディレクトリ自動作成機能、失敗時のフォールバック（コンソールのみ）を実装。
  - utils/process_priority.py: Windows / POSIX を吸収するプロセス優先度設定（high/normal/low）と CPU affinity 設定関数を追加。権限不足など失敗時は警告してスキップ。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（スコア降順、同点は signal_rank でタイブレーク）、等金額配分、スコア加重配分（全スコア 0 の場合は等分にフォールバック）を追加。
  - portfolio/risk_adjustment.py: セクター集中制限を適用する apply_sector_cap、マーケットレジームに応じた投下資金乗数を返す calc_regime_multiplier を追加（未知レジームは警告して 1.0 にフォールバック）。"unknown" セクターはセクター上限の算出対象から除外。
  - portfolio/position_sizing.py: allocation_method（risk_based / equal / score）に基づく発注株数算出を実装。単元株（lot_size）丸め、銘柄上限（max_position_pct）、投下合計のスケールダウン（available_cash を超えた場合の比例縮小）、cost_buffer を用いた保守的見積、残差に対する優先配分ロジックなどを実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: paper_trading 用 SQLite（デフォルト data/paper_trading.db）を読み、システム稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）等を集計して人間向けレポートを出力する CLI を追加。閾値に基づく PASS/FAIL 判定を出力（稼働率、fill/send rate、P95 latency などの基準がソース内で定義）。

- research/factor_research.py（骨子）
  - ファクター計算モジュールを追加（Momentum / Value / Volatility / Liquidity を想定）。DuckDB 接続を受け prices_daily/raw_financials を参照して計算する設計（実装はファイル末尾が切れているが基本仕様・定数が定義済み）。

### 変更 (Changed)
- DB の扱いに関するポリシー
  - 監視（run_monitoring）は KABUSYS_ENV に依らず sqlite_path（本番用監視 DB）を使用する設計に変更。これにより監視と実行の DB 分離が明確化（Execution は is_paper 時に paper_sqlite_path を使用）。

- ログ出力先の標準化
  - logging_setup で StreamHandler は stdout を使用するように明示（cron 等からのリダイレクトを想定）。ファイルハンドラの失敗時はコンソールのみで安全に継続。

- .env パースの堅牢化
  - config._parse_env_line においてクォート内のバックスラッシュエスケープ処理、インラインコメント処理（クォート無しでは '#' の直前が空白/タブの時のみコメントと認識）などを実装。export KEY=val 形式にも対応。

- 各種デフォルト・閾値を Settings で管理
  - CPU / Memory / Disk 閾値、pid/kill flag のパス、paper trading の fill_mode（instant/partial/never/reject）等を Settings 経由で取得するよう整理。

### 修正 (Fixed)
- フォールバック処理の追加・障害耐性向上
  - logging_setup: ログディレクトリ作成失敗やファイルハンドラ作成失敗時に警告を出しつつコンソールログのみで継続するように修正。
  - process_priority: 対応外 OS／権限不足時に例外ではなく警告でスキップするようにして起動スクリプトの堅牢性を向上。
  - run_monitoring.run loop: check_once() 内での例外を捕捉してログ出力した上でポーリングを継続するように修正（監視継続性を確保）。

### ドキュメント (Documentation)
- 各モジュールに docstring / コメントを追加し、設計意図・使い方・注意点（例: calc_regime_multiplier の挙動、position_sizing の lot_size 将来的拡張案等）を明記。

### 既知の制約 / 注意点 (Known issues / Notes)
- run_monitoring は設計上「監視は本番の monitoring DB を参照する」仕様です。開発環境で監視 DB を分離したい場合は sqlite_path を環境変数で変更してください。
- research/factor_research.py の実装はファイル末尾で切れており、関数の一部実装が未完了の可能性があります（現状で設計と多くの定数は定義済み）。
- .env 自動読み込みはプロジェクトルートが検出できない場合はスキップされます。自動ロードを明示的に無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- paper_verification_report における P95 算出は単純ソートに基づいており、大規模データセットでの性能・メモリを要検討。

---

今後の予定（想定）
- research モジュールの詳細実装とテスト補完
- テストの追加（ユニット／統合）
- 配布パッケージ化・CI の整備

もし特定のファイルや変更点について、より詳細な記載（例: 各関数の振る舞い、サンプルコマンド、環境変数一覧）を希望される場合は知らせてください。必要に応じて CHANGELOG の粒度を細かく分けて更新します。