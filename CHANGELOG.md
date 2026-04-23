# Changelog

このファイルは Keep a Changelog の形式に従って作成されています。  
安定したバージョン管理のため、重要な変更はここに記録してください。

全般的な注意:
- 本リポジトリは日本株自動売買システム「KabuSys」の最初の公開版相当の内容を含みます。
- 以下はソースコードの内容から推測して作成した変更履歴です（実際のコミット履歴ではありません）。

## [Unreleased]
- （開発中の変更や未リリースの修正をここに記載してください）

## [0.1.0] - 2026-04-23
初回リリース

### Added
- 基本パッケージ構成を追加
  - kabusys パッケージ本体（__version__ = 0.1.0）
  - サブパッケージ: portfolio, execution, monitoring, tools, research, utils, config 関連モジュール

- 実行用スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、DB接続（paper_trading の場合は専用 DB を使用）、Broker クライアントの生成、OrderManager / RiskManager / Reconciler の組み立て、エンジンのデーモンスレッド起動と停止フラグ監視を実装。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数で間隔上書き可能、監視用 DB 初期化、停止フラグ検知、例外ハンドリングを実装。

- 設定・環境管理
  - config.Settings クラスを追加し、環境変数経由で設定を一元管理。DUCKDB/SQLite パス、paper_trading 用 DB、ログレベル、各種閾値、KABUSYS_ENV 等をプロパティで提供。
  - 自動 .env ロード機能を追加（プロジェクトルート検出：.git または pyproject.toml）。優先順位: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
  - config_setup: 対話式ウィザードで .env を生成/更新する CLI を追加（秘密値マスク表示、デフォルト値・選択肢サポート）。

- 設定検証
  - validate_config CLI を追加。必須環境変数や KABUSYS_ENV、DB パス、config/*.yaml の存在・パース（PyYAML があれば）などを検証し、エラー/警告/情報を出力。--strict オプションで警告も失敗扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - utils.logging_setup: StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに構成するユーティリティを追加。ログディレクトリ作成失敗時はファイル出力を無効化してコンソールのみで継続。
  - utils.process_priority: Windows/Linux/macOS を吸収したプロセス優先度設定、CPU affinity 設定ユーティリティを追加。権限不足や未対応 OS を安全に扱う。

- ポートフォリオ構築（純関数群）
  - portfolio.portfolio_builder: シグナル選定（score 降順）と等金額／スコア加重の重み計算を追加。スコア全て 0 の場合は等重配分へフォールバック。
  - portfolio.risk_adjustment: セクター集中上限の適用（既存保有を考慮、unknown セクターは除外）と市場レジームに応じた投下資金乗数 calc_regime_multiplier を追加（bull/neutral/bear をマップ、未知レジームはフォールバックで警告）。
  - portfolio.position_sizing: allocation_method（risk_based / equal / score）に基づく株数計算を実装。単元（lot_size）丸め、1銘柄上限、aggregate cap（available_cash によるスケールダウン）、cost_buffer（手数料/スリッページ見積）対応。リスクベース配分で stop_loss を参照。

- 研究用ファクター計算基盤
  - research.factor_research（モメンタム等の計算を想定したモジュールの開始）：DuckDB 接続を受け prices_daily 等テーブルを参照してファクターを計算する設計（モジュール一部の実装含む）。

- ペーパートレード検証ツール
  - tools.paper_verification_report: Paper Trading 用 SQLite DB から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）を集計してレポートを出力する CLI を追加。閾値チェックによる PASS/FAIL 判定を実装。

### Changed
- （初回リリースのため該当なし）

### Fixed / Improved
- .env のパーサを堅牢化
  - export KEY=val 形式に対応。
  - シングル/ダブルクォート内のバックスラッシュエスケープを正しくパース。
  - クォート無しの値でのインラインコメント認識を改良（# の直前が空白またはタブの場合のみコメントと見なす）。
  - .env の読み込みでファイルアクセス失敗時に警告を出すようにした。

- 環境変数ロードの上書き制御
  - .env.local は既存 OS 環境変数を保護しつつ上書き可能（override フラグと protected セットにより実現）。

- ロギング設定の堅牢化
  - ログディレクトリ作成・ファイルハンドラ生成に失敗した場合はコンソール出力（stdout）にフォールバック。
  - 既存ハンドラをクリアしてから再設定し、二重登録を防止。

- 実行/監視の安全性向上
  - run_execution: KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用して本番 DB と分離。停止フラグが立っている場合は起動を中止するガードを追加。
  - run_monitoring: MONITOR_POLL_INTERVAL の不正値を検知して警告を出し、デフォルトにフォールバックするロジックを追加。monitor.check_once() の例外を捕捉してループ継続するようにし、DB 接続は必ずクローズするようにした。

- Paper 検証レポートの堅牢化
  - DB にテーブルが存在しない/クエリエラー（sqlite3.OperationalError）が発生した場合でもレポート生成が壊れないようにフォールバック値を使用して出力する。

- position_sizing のスケーリングアルゴリズム改善
  - aggregate cap によりスケールダウンした際の再配分ロジック（lot_size 単位で残差を大きい順に配分）を実装して、利用可能現金を最大限活用するように改善。

### Security
- 秘密情報（J-Quants トークン、kabu API パスワード等）は config_setup の表示でマスクされ、.env を作成する際にもマスクを考慮。

### Removed
- （初回リリースのため該当なし）

---

今後のリリースでは、以下のような項目が想定されます:
- Strategy / Execution の具体的アルゴリズム実装の追加（Signal Generator / StrategyModel）。
- BrokerClient の具体実装（本番/モック）及び API エラーリトライやレートリミット対応の強化。
- テストカバレッジ拡充（ユニット・統合テスト）、CI/CD 設定の追加。
- ドキュメント（設計書・運用手順）の充実。

（注）上記はコードベースの内容から推測して作成した CHANGELOG です。実際のコミット履歴やリリースノートとは異なる場合があります。必要であれば、実コミットログに基づく差分版を作成できます。