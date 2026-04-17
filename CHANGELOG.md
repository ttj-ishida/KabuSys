# Changelog

すべての重要な変更点は本ファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

なお、本リリースではプロジェクトのコア機能（監視・実行エンジン・ポートフォリオ構築・リサーチ・AI ニューススコアリングなど）を実装しています。

## [Unreleased]

### Added
- -  

## [0.1.0] - 2026-04-17

### Added
- アプリケーションの基本バージョンを追加（kabusys.__version__ = 0.1.0）。
- 実行エントリ・監視エントリを追加
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。Paper Trading 環境時は専用 SQLite（data/paper_trading.db など）を使用し、本番 DB と分離する実装（スレッド実行、停止フラグ監視、PID ファイル取り扱い）を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグファイルを検出してループ終了。
- 設定・環境変数管理（kabusys.config）
  - .env 自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml で検出）。優先順位は OS 環境変数 > .env.local > .env。
  - .env パーサーを強化：export 形式サポート、クォート付き値のバックスラッシュエスケープ対応、インラインコメント処理。
  - Settings クラスを導入し、環境変数の検証・型変換・デフォルト値を提供（DB パス、Paper Trading 設定、監視しきい値、ログレベル等）。
- Paper Trading 検証用ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成 CLI を追加。期間指定（--from/--to）と DB パス指定（--db）に対応。稼働率 / 成立率 / 送信率 / レイテンシ（P95）などを集計し PASS/FAIL 判定を行う。
- ポートフォリオ構築モジュール（kabusys.portfolio）
  - portfolio_builder: シグナル選別（select_candidates）および重み計算（calc_equal_weights, calc_score_weights）を実装。スコア合計が 0 の場合は等分配へフォールバック（警告）。
  - risk_adjustment: セクター集中上限の適用（apply_sector_cap）および市場レジームに応じた乗数（calc_regime_multiplier）を実装。sell_codes を考慮したエクスポージャー計算や unknown セクターの扱いを明示。
  - position_sizing: 発注株数計算（calc_position_sizes）を実装。risk_based / equal / score の割当方式をサポートし、単元株（lot_size）丸め、コストバッファ（cost_buffer）を考慮した aggregate cap スケーリング、既存ポジション考慮を実装。
- リサーチ / ファクター計算（kabusys.research）
  - factor_research: DuckDB を用いたモメンタム（1/3/6m、MA200乖離）、ボラティリティ（ATR20 等）、バリュー（PER/ROE）計算関数を実装。欠損データ判定と行数条件を整備。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、ファクター統計サマリ（factor_summary）、ランク変換（rank）を実装。外部依存ライブラリに頼らない純 Python 実装。
- AI ニュース NLP スコアリング（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いたニュース記事の銘柄別センチメント集計モジュールを追加。バッチ送信、トークン対策（記事数・文字数トリム）、リトライ（429/5xx/タイムアウト）とエクスポネンシャルバックオフ、レスポンス JSON 検証、スコア ±1.0 クリップ、といった設計方針を備える。ニュースウィンドウ計算（JST→UTC 変換）関数も実装。
- ユーティリティ
  - utils/process_priority.py: クロスプラットフォームでのプロセス優先度設定（Windows / POSIX）および CPU affinity 設定関数を実装。psutil を利用し、権限不足時は警告でスキップ。
- その他
  - monitoring 用 DB 初期化ユーティリティ（init_monitoring_db）呼び出しを実装（冪等に監視テーブルを確保）。
  - パッケージエクスポートを整理（kabusys.portfolio.__all__, kabusys.research.__all__ 等）。

### Changed
- 設定読み込みの挙動を定義：KABUSYS_DISABLE_AUTO_ENV_LOAD により自動 .env ロードを無効化可能。プロジェクトルート未特定時は自動ロードをスキップ。
- run_monitoring / run_execution の起動時にプロセス優先度を「high」に設定する処理を追加（set_process_priority を利用）。
- Paper Trading 実行時の DB 分離を明確化（settings.is_paper による sqlite_path 切り替え）。

### Fixed / Hardened
- .env パーサーの不正入力に対する堅牢性を向上（無効行のスキップ、クォート内のエスケープ処理、コメント判定の改善）。
- ポジションサイズ計算でのゼロ・負価格やデータ欠損に対する早期スキップ処理を追加。aggregate cap のスケーリング時に単元（lot）丸め・端数処理を安全に行うロジックを実装。
- リサーチ SQL／集計での NULL 伝播や行数不足を考慮した条件分岐を明示し、欠損時に None を返すようにして downstream の安全性を確保。
- run_monitoring の MONITOR_POLL_INTERVAL 読み取りで 0 以下や不正値が設定されている場合にデフォルトにフォールバックし警告を出すように修正。

### Documentation / Comments
- 各モジュールに詳細な docstring と実装ノート、設計方針（PortfolioConstruction.md / StrategyModel.md 参照箇所の言及）を追加し、将来的な拡張点（TODO）や重要な挙動（例: レジーム時の BUY シグナル生成方針）を明記。

### Removed
- -  

### Security
- OpenAI API キーが未設定の場合に明確な ValueError を投げるようにし、意図せぬキー漏洩や無効呼び出しによる静的失敗を回避。

## 警告 / 制約
- DuckDB の executemany の制約（空 params の扱い）に注意。ai/news_nlp やその他の一括書き込み前には空パラメータチェックを推奨。
- process_priority / cpu_affinity は権限が必要な操作であり、実行環境によっては警告を出して処理をスキップします（挙動はプラットフォーム依存）。
- news_nlp モジュールは API 呼び出しやレスポンス形式検証など外部依存が多く、実運用時は API レートやコスト、エラーハンドリング方針のチューニングが必要。

---

（今後のリリースではユニットテストの追加、AI スコアリングの部分的失敗時のロールバック戦略、銘柄別 lot_size のマスタ化などを予定しています。）