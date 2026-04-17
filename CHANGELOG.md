# Changelog

すべての変更は「Keep a Changelog」フォーマットに準拠し、意味のあるリリース単位で記録しています。

注: 本ファイルはコードベースの内容から推測して作成しています。実際のコミット履歴とは異なる場合があります。

## [Unreleased]
- （現在のコードベースに基づく未リリースの変更はありません）

## [0.1.0] - 2026-04-17
初回リリース。日本株自動売買システム KabuSys のコア機能群を導入。

### Added
- 環境設定・読み込み
  - .env 自動読み込み機能を追加（プロジェクトルートの検出: .git / pyproject.toml）。  
    - 読み込み順序: OS環境変数 > .env.local > .env（.env.local は既存 OS 環境変数を保護しつつ上書き可能）。
  - .env パーサーを実装。export 構文、クォート文字列、バックスラッシュエスケープ、インラインコメント処理に対応。
  - Settings クラスを導入し、アプリケーション設定（J-Quants / kabuAPI / LINE / DB / 監視閾値 / 実行環境等）をプロパティ経由で安全に取得・検証可能に。
  - 環境値の妥当性チェック（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を実装。

- 設定関連 CLI
  - config_setup: 対話式ウィザードで .env の作成・更新を支援する CLI を追加（シークレット入力のマスク、選択肢・デフォルト表示、保存）。
  - validate_config: 起動前検証 CLI を追加。必須環境変数のチェック、KABUSYS_ENV の妥当性、DB パスの存在確認、config/*.yaml の存在とパース検証（PyYAML が無ければ警告）などを実施。--strict オプションで警告も FAIL 扱いにできる。

- 実行/監視ランナー
  - run_execution: ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、SQLite/DuckDB 接続、Broker クライアント生成、OrderManager / RiskManager / Reconciler 組み立て、ExecutionEngine のスレッド実行および停止フラグ監視を実装。  
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と完全分離する想定。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ検出時にループを安全に終了する。監視は環境にかかわらず本番 sqlite_path を使用する仕様を明示。

- モジュール: ポートフォリオ構築
  - portfolio_builder:
    - select_candidates: シグナルをスコア降順でソート、上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア比率配分を実装（スコア合計が 0 の場合はフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック。既存保有を考慮し、上限セクターの新規候補を除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた資金乗数を返す。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づき、銘柄ごとの発注株数を算出。単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash に基づくスケーリング）、cost_buffer（手数料・スリッページ見積り）による保守的見積り、残差処理による追加配分ロジックを実装。

- リサーチ / ファクター計算
  - research.factor_research:
    - calc_momentum: 1ヶ月/3ヶ月/6ヶ月リターン、MA200 乖離率を DuckDB の prices_daily テーブルから計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等を計算（データ不足時に None を返す挙動を明示）。
    - DuckDB を用いて SQL ベースで効率的に計算する設計。

- ユーティリティ
  - utils.process_priority:
    - set_process_priority: psutil を用いて Windows / POSIX (Linux/macOS/FreeBSD) に跨る優先度設定を実装。未対応 OS や許可不足時は警告を出してスキップするフォールバックを持つ。
    - set_cpu_affinity: 指定コア数で CPU affinity を固定するユーティリティ（利用不可時は警告を出す）。

- ツール
  - tools.paper_verification_report:
    - ペーパートレード用検証レポート生成スクリプトを追加。system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（P95）等を算出し、閾値（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200ms）に基づいて PASS/FAIL を判定。コマンドライン引数で期間／DB パスを指定可能。

- パッケージ
  - パッケージ初期化: __version__ = "0.1.0" を設定。主要モジュールの __all__ エクスポートを定義。

### Changed
- 環境分離の明確化:
  - run_monitoring は監視用 DB に関して環境に依存せず本番 sqlite_path を使用する（監視系は常に本番 DB を参照する設計）。
  - run_execution は paper_trading 時に paper 用 SQLite を使用して本番データと分離する運用を採用。

- .env ロードポリシー:
  - OS 環境変数は保護され、.env/.env.local の読み込みは OS 変数を上書きしない（ただし .env.local は override=True で開発向け調整を可能に）。

### Fixed / Robustness
- 環境変数パースや運用面での堅牢化:
  - MONITOR_POLL_INTERVAL の不正値はログ警告を出しデフォルトにフォールバックする実装。
  - process_priority 周りでは AccessDenied や未実装 API を捕捉して安全にスキップする。
  - ファクター計算やレポート生成はデータ欠損（NULL）に対して None を返す、または例外を吸収して部分的に利用可能な指標を返すよう設計。
  - calc_position_sizes / apply_sector_cap は価格欠損時の挙動（スキップ・ログ出力）を明確化。

### Security
- .env ファイル取り扱いに関する注意喚起を追加（config_setup が .env を生成する際に「.env は絶対に Git にコミットしないこと」と明記）。

### Documentation / Notes
- 各モジュールに詳細な docstring を付与（設計の背景・参照テーブル・返り値仕様・注意点などを明記）。
- config_setup と validate_config による起動前チェックのワークフローを整備（ウィザード → validate）。

---

今後の提案（コードから推測）:
- テストカバレッジ（ユニットテスト）を追加して position sizing、risk_adjustment、portfolio_builder、factor_research 等の数値ロジックを検証することを推奨。
- モニタリング・実行の統合運用におけるログ収集・アラート（LINE 通知等）の実装・テストを強化。
- 銘柄ごとの lot_size を銘柄マスタに持たせる拡張（position_sizing の TODO に言及）。
- レジーム検出・シグナル生成コンポーネントと結合したエンドツーエンド検証フローの整備。