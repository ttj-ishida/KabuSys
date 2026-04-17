# CHANGELOG

このプロジェクトは Keep a Changelog の形式に準拠して変更履歴を記録します。  
各リリースでは主な追加機能、改善点、修正点などを日本語でまとめています。

## Unreleased
- （今後の変更を記載）

---

## [0.1.0] - 2026-04-17

### 追加 (Added)
- 実行・監視用エントリポイントを追加
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。環境によるブローカークライアントの切替（KABUSYS_ENV=paper_trading で MockBrokerClient を使用）や、paper_trading 時に専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離する挙動を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する仕様。
  - 両スクリプトとも起動時にプロセス優先度を設定（高優先度）し、停止フラグ（data/stop_requested.flag）および PID ファイルを利用して安全に停止できるように実装。

- 設定/初期化関連の CLI を追加
  - config_setup.py: 対話式ウィザードで .env ファイルを作成・更新する機能。複数の設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE 設定、ログレベル等）に対応。
  - validate_config.py: .env と config/*.yaml の事前検証ツールを追加。必須/任意環境変数チェック、KABUSYS_ENV・LOG_LEVEL の妥当性検証、DB パスや YAML の存在・パースチェック、KABUSYS_ENV=live に対する追加警告等を提供。--strict オプションで警告を失敗扱いにできる。

- 環境設定の自動読み込みと Settings 実装
  - config.py: プロジェクトルート検知（.git または pyproject.toml）に基づく .env/.env.local の自動読み込み機構を実装（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。.env のパースはクォート、エスケープ、export プレフィックス、インラインコメントの扱い等に対応。
  - Settings クラスを提供し、アプリ内から型付きアクセサで各種設定値（パス、閾値、PAPER_FILL_MODE の検証、env/log_level の検証など）を安全に取得可能にした。

- ポートフォリオ構築・リスク調整・ポジションサイズ計算モジュールを追加
  - portfolio/portfolio_builder.py: 候補選定（スコア降順、タイブレークルール）・等金額/スコア重み計算を提供。スコアが全て 0 の場合は等金額にフォールバックし警告を出す。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）や市場レジームに応じた投下比率乗数（calc_regime_multiplier）を実装。未知レジームは警告のうえフォールバック値（1.0）を使用。
  - portfolio/position_sizing.py: risk_based / equal / score に対応した株数計算を実装。単元株（lot_size）で丸め、銘柄単位および総投資額での上限処理、cost_buffer を考慮したスケーリングロジック、残差処理による追加配分を提供。

- ユーティリティ
  - utils/process_priority.py: Windows / POSIX を吸収したプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を追加。psutil を利用し、権限不足時は警告してスキップする堅牢性を確保。

- 研究・集計ツール
  - research/factor_research.py: DuckDB 接続を受け取りモメンタム・ボラティリティ等のファクターを計算する関数を実装（prices_daily テーブル参照、MA200、ATR、リターン等）。
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート出力ツールを追加。稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを計算し基準値と比較して PASS/FAIL を判定。PAPER_TRADING_SQLITE_PATH 環境変数または --db で DB パス指定可能。

### 変更 (Changed)
- プロジェクト初期構成として、設定自動読み込みの優先度を OS 環境変数 > .env.local > .env と定義。既存の OS 環境変数は保護され、.env.local で上書き可能。
- run_execution/run_monitoring の DB 接続ロジックを環境に応じて分離:
  - paper_trading 環境では paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番データと分離。
  - 監視（run_monitoring）は環境にかかわらず sqlite_path（監視 DB）を使用する旨を明示。

### 修正 (Fixed)
- 環境変数パースの堅牢化:
  - _parse_env_line でクォート内のバックスラッシュエスケープやインラインコメントの扱いに対応し、より実運用に耐える .env 解析を実現。
- MONITOR_POLL_INTERVAL の取り扱い改善:
  - 無効な値（0 以下や非整数）が設定された場合、ログに警告を出しデフォルト（60 秒）にフォールバックするように実装。time.sleep に渡せない値での例外を回避。
- calc_score_weights: 全銘柄のスコア合計が 0 の場合にログ警告を出して等金額配分にフォールバックするように修正。
- calc_regime_multiplier: 未知のレジームに対して警告を出し 1.0 でフォールバックするように修正。
- Paper 検証レポートの集計でデータ欠損時にクラッシュしないよう防御的に処理（テーブル欠如や件数ゼロ時のフィールドが None になるケースを許容）。
- utils/process_priority の例外処理を強化し、権限不足や未実装 API の際に警告して続行するようにした。

### ドキュメント・メッセージ (Documentation)
- 各モジュールにモジュールレベルの docstring を追加し、設計意図（参照テーブル、純粋関数である旨、参照しないリソースなど）や使用上の注意を明記。
- config_setup のウィザードで生成される .env のテンプレートコメントを充実させ、Git にコミットしない旨を明記。

### 既知の制約 (Known issues)
- position_sizing.calc_position_sizes における価格欠損（price が 0.0）の場合、現状はスキップしているため保守的にエクスポージャーが過少見積もられる可能性がある（将来的に前日終値等のフォールバックを検討）。
- apply_sector_cap は sector_map に存在しない銘柄を "unknown" 扱いとしてセクター上限の対象外とする設計上の挙動がある（意図的な設計だが注意が必要）。

### セキュリティ (Security)
- 本リリースの段階でセキュリティ問題は報告されていません。ただし .env ファイルに機密情報を含めるため、生成された .env を Git 等に含めないようドキュメントで注意喚起しています。

---

今後の予定:
- 銘柄ごとの lot_size をマスタ化して個別対応する拡張
- 価格欠損に対するフォールバック価格戦略の実装
- DuckDB を用いたファクター計算の追加最適化・テスト充実

（補足）本 CHANGELOG はソースコードから推測してまとめたものであり、実際の開発履歴やコミット履歴とは異なる場合があります。