# CHANGELOG

すべての注目すべき変更点を記載します。本ファイルは「Keep a Changelog」形式に準拠しています。

なお、以下の変更内容はリポジトリ内のソースコードを基に推測して作成しています（コミット履歴そのものではありません）。実際のコミットメッセージやマイグレーション手順がある場合は適宜差し替えてください。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-17

初回リリース。日本株自動売買システム「KabuSys」ライブラリの基礎機能をまとめて実装しました。主要な追加点は以下の通りです。

### 追加 (Added)

- パッケージ基盤
  - パッケージメタ情報: kabusys.__version__ = 0.1.0、主要サブパッケージを __all__ で公開。

- 設定管理
  - kabusys.config: 環境変数 / .env ファイルの自動読み込み機能を実装。
    - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）。
    - .env および .env.local の読み込み順序・オーバーライドルール（OS 環境変数を保護）。
    - .env 行パーサーは export 形式、クォート（シングル/ダブル）、バックスラッシュエスケープ、インラインコメントに対応。
  - Settings クラス: 各種設定プロパティを提供（J-Quants / kabu API / LINE / DB / 監視しきい値 / システム設定 など）。
    - KABUSYS_ENV, LOG_LEVEL 等のバリデーション。
    - PAPER_FILL_MODE や PAPER_TRADING_SQLITE_PATH などペーパートレード用設定のサポート。

- 環境設定支援 CLI
  - kabusys.config_setup: 対話式ウィザードで .env を生成・更新するツールを追加。
    - 秘匿項目のマスク表示、デフォルト・選択肢対応、保存前の確認表示。
    - .env 書き込みテンプレートに注意書きを付与（絶対に Git にコミットしない等）。

- 設定検証 CLI
  - kabusys.validate_config: .env と config/*.yaml（存在する場合）の事前検証ツールを追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パス親ディレクトリ確認。
    - PyYAML がない場合は YAML 検証をスキップしつつ警告を出す。
    - --strict オプションで警告をエラー扱いにできる。

- 実行 / 監視ランナー
  - run_execution: ExecutionEngine 起動用スクリプト。
    - プロセス優先度を上げる（set_process_priority("high")）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の組み立てとデーモンスレッド実行、停止フラグ対応（data/stop_requested.flag）。
    - execution.pid の管理（pid_file）。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒、0 以下はデフォルトへフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する旨の実装。
    - DuckDB と SQLite の接続、init_monitoring_db の呼び出し、停止フラグ検知処理を実装。

- ユーティリティ
  - kabusys.utils.process_priority:
    - set_process_priority(level): Windows / POSIX の差を吸収してプロセス優先度を設定。エラー時は警告を出して継続。
    - set_cpu_affinity(cpu_count): 指定コア数への CPU affinity 固定（未対応 OS / 権限不足時は警告）。
    - クロスプラットフォーム対応と堅牢な例外処理。

- ポートフォリオ構築（純粋関数群）
  - kabusys.portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順で選定（タイブレークに signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（スコア全0時は等配分にフォールバック）。
  - kabusys.portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限を適用し、上限超過セクターの候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム(bull/neutral/bear)に応じた投下資金乗数を返す（不明レジームは 1.0 でフォールバック）。
  - kabusys.portfolio.position_sizing:
    - calc_position_sizes: allocation_method に基づく発注株数計算（risk_based / equal / score）。
    - 単元株（lot_size）で丸め、1銘柄上限や aggregate cap（利用可能現金）を考慮したスケーリングと端数配分ロジックを実装。
    - cost_buffer による保守的コスト見積りをサポート。
    - TODO コメント: 将来的な銘柄別 lot_size 仕様への拡張案を記載。

- リサーチ（ファクター計算）
  - kabusys.research.factor_research:
    - calc_momentum: 1M/3M/6M リターンと MA200 乖離率を DuckDB を用いて計算。
    - calc_volatility: ATR（20日）・相対 ATR・20日平均売買代金・出来高比などを計算。
    - DuckDB を用いたウィンドウ関数ベースの安定した実装、データ不足時は None を返す設計。

- 検証ツール
  - kabusys.tools.paper_verification_report:
    - ペーパー取引ログ（data/paper_trading.db 想定）から稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）などを集計してレポートを出力。
    - 閾値（稼働率 99% 等）に基づく PASS/FAIL 判定を出力。
    - テーブル欠損や OperationalError 発生時に穏当なデフォルトを使用して失敗しない設計。

### 変更 (Changed)

- なし（初回リリースのため新規実装が中心）。

### 修正 (Fixed)

- なし（初回リリースとして既存不具合修正履歴は無し）。

### 既知の注意点 / 制限 (Notes)

- apply_sector_cap のエクスポージャー計算は price_map に 0.0 が含まれると過少見積りになる可能性があり、将来的に価格フォールバックの導入が想定されている（コメントあり）。
- calc_regime_multiplier は未定義のレジームに対して警告を出し 1.0 を返すが、運用ルールに注意が必要。
- process_priority/set_cpu_affinity は権限不足や未対応プラットフォームで動作しない場合があり、その際はログで警告するのみで処理は継続する設計。
- .env の自動ロードはプロジェクトルートが検出できない場合はスキップされる（テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で抑制可能）。

### セキュリティ (Security)

- .env 書き出しで明記: .env は絶対に Git にコミットしないこと。
- config_setup の秘匿項目は表示時にマスク。

---

今後のリリースでは、ユニットテストの追加、トランザクション安全性の向上（DB 周り）、銘柄別 lot_size 拡張、より詳細なモニタリング指標やアラート機能の追加を想定しています。必要があればこの CHANGELOG をコミット履歴に合わせて更新してください。