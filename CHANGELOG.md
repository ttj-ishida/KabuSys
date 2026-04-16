# CHANGELOG

すべての変更は Keep a Changelog に準拠します。  
このファイルは、提供されたコードベースの内容から機能追加・設計上のポイント・既知の問題点を推測して作成したものです。

フォーマット:
- 版本は semver を想定（パッケージ内の __version__ = "0.1.0" を初期リリースとして使用）
- 日付は本ファイル作成日: 2026-04-16

## [Unreleased]
### Added
- (作業中) ai/news_nlp モジュールの続きおよび堅牢化（OpenAI API 呼び出し周りのエラーハンドリング、レスポンス検証、部分更新ロジックなど）。現在ファイル末尾に未完の箇所があり、補完が必要。

### Fixed / Improved / TODO
- ai/news_nlp における未完部分の修正・単体テスト追加（現状は構文的に途中で切れているため実行できない）。
- position_sizing / apply_sector_cap にコメントで示された将来対応（価格フォールバック、銘柄別 lot_size）に関する設計検討・実装予定。

---

## [0.1.0] - 2026-04-16

Initial release — KabuSys 初期機能セットを追加。

### Added
- 基本設定と環境変数読み込み
  - src/kabusys/config.py
    - .env 自動ロード（プロジェクトルート検出: .git / pyproject.toml 基準）
    - .env/.env.local の読み込み順序と OS 環境変数保護機能
    - 複雑な .env 行のパース（export プレフィックス、クォート処理、インラインコメント処理）
    - Settings クラスによるアクセスラッパー（J-Quants・kabu API・DB パス・監視閾値・環境識別等）
    - PAPER_FILL_MODE のバリデーション、KABUSYS_ENV / LOG_LEVEL の厳密チェック

- 実行/監視ランナー
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプト
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用して本番 DB から分離
    - BrokerClientFactory を用いたブローカークライアント生成（Mock 対応想定）
    - OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine の開始・停止処理
    - 停止フラグ (data/stop_requested.flag) と PID ファイル管理、スレッドでの実行制御
    - RiskManager の既定設定（max_position_pct, max_utilization, レート制限等）を明示

  - src/kabusys/run_monitoring.py
    - SystemMonitor 用ポーリングループ起動スクリプト
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒、妥当性チェック付き）
    - 監視は環境にかかわらず本番 sqlite_path を参照する点を明示
    - プロセス優先度設定（高優先度）・停止フラグ検出・例外ログ出力

- プロセス制御ユーティリティ
  - src/kabusys/utils/process_priority.py
    - set_process_priority(level) : Windows / POSIX を吸収して優先度設定（psutil ベース）
    - set_cpu_affinity(cpu_count) : 指定コアに固定する機能（アクセス権限や未対応環境では警告スキップ）

- ポートフォリオ構築関連（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - select_candidates: スコア降順 + タイブレーク（signal_rank）
    - calc_equal_weights / calc_score_weights: 等分配とスコア加重（全スコア 0 の場合は等分配にフォールバック）

  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中の上限チェック（売却予定銘柄をエクスポージャ計算から除外可能）
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear の既定値）

  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に対応した発注株数計算
    - 単元株（lot_size）丸め、per-stock 上限・aggregate cap（available_cash に基づくスケールダウン）ロジック
    - cost_buffer を用いた保守的コスト見積り、remaining_cash を使った残余割付アルゴリズム

  - src/kabusys/portfolio/__init__.py により主要関数をエクスポート

- 研究・ファクター計算
  - src/kabusys/research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離を DuckDB SQL で計算
    - calc_volatility: 20日 ATR・相対 ATR、平均売買代金・出来高比を計算
    - calc_value: raw_financials を用いた PER / ROE の計算（DuckDB）
    - DuckDB を直接用いる SQL ベースの実装でパフォーマンスを考慮したスキャン範囲制限

  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 複数ホライズンの将来リターンを一括取得（入力のホライズン検証あり）
    - calc_ic: スピアマンランク相関（IC）計算（ties に対応）
    - rank, factor_summary: ランク化・統計サマリー（count/mean/std/min/max/median）

  - src/kabusys/research/__init__.py により主要関数をエクスポート（zscore_normalize を data.stats から参照）

- ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成ツール（コマンドライン）
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（P95）を算出
    - 基準値（稼働率 99%、注文成功率 90% 等）に基づく PASS/FAIL 判定、期間指定オプション、DB パス上書き可能
    - P95 計算、NULL 対応、存在しない DB へのエラーメッセージ出力等の堅牢化

- AI / ニュース NLP（初期実装）
  - src/kabusys/ai/news_nlp.py
    - raw_news を OpenAI (gpt-4o-mini) でバッチスコアリングして ai_scores に書き込む設計
    - タイムウィンドウ計算（JST → UTC 変換）、記事トリミング（記事数・文字数制限）、バッチサイズ、リトライ（429/5xx/ネットワーク）などを設計
    - 出力 JSON の厳密検証、スコアの ±1.0 クリッピング、部分成功時の DB 更新戦略（対象コードの絞り込みで既存スコア保護）
    - 現状は API キー必須チェック、ウィンドウ計算関数等を実装済み（ただしファイル末尾に未完の箇所あり）

- パッケージ初期化
  - src/kabusys/__init__.py にパッケージ名と __version__ = "0.1.0" を追加

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Removed
- なし

### Security
- OpenAI API キーは明示的に引数または環境変数 OPENAI_API_KEY で要求（漏洩対策として自動露出はしない設計）

### Notes / Known issues
- ai/news_nlp.py の末尾が途中で切れている（"if not articl" でファイルが中断）。このままではモジュールがインポート/実行できないため、API 呼び出し・レスポンス検証・DB 書き込みロジックの補完が必要。
- position_sizing のコメントで指摘されている通り、価格が欠損（0.0）の場合にエクスポージャが過少見積りされる問題があり将来的に価格フォールバックを検討する旨の TODO が残されている。
- apply_sector_cap は "unknown" セクターを除外対象にしない設計。ただし業務要件により扱いを変更する必要があるかもしれない。
- process_priority / set_cpu_affinity は権限やプラットフォーム依存の制限を受ける可能性があるため、失敗時は警告を出してスキップする安全設計となっている。
- .env の自動ロードはプロジェクトルートが検出できない場合はスキップされる。テスト環境等で自動ロードを無効化するために KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数を用意。

---

メンテナンス/開発者向け補足:
- 多くのコンポーネントは DuckDB / SQLite を想定しており、テスト用にファイルベースの DB を差し替え可能（paper_trading 用 DB は完全分離）。
- ロギングは各モジュールで標準 logging を使用。実行スクリプトは basicConfig(level=INFO) を初期化するため、必要に応じて上書き可能。
- 将来的な改善候補として、銘柄別 lot_size の導入、価格フォールバックの実装、AI スコアリングの耐障害性強化（部分失敗時の再実行・トランザクション性向上）が挙げられる。

もしこの CHANGELOG を特定のリリースノート形式（例: GitHub Releases 用の短縮版）に変換する、あるいは ai/news_nlp の未完部分を補完してリリースに含めたい場合は、その旨を教えてください。必要なら変更候補のパッチ案も作成します。