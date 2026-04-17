# Changelog

すべての注目すべき変更を記録します。形式は "Keep a Changelog" に準拠しています。  

リリースに関する説明はコードベースから推測して作成しています。

## [Unreleased]

### Added
- 監視および実行のランチャースクリプトを追加／改善
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ（data/stop_requested.flag）検知、例外捕捉、プロセス優先度設定、SQLite / DuckDB の接続とクローズ処理を実装。
  - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、本番 DB と分離された paper_trading 用 SQLite を使用。停止フラグ、PID ファイル、スレッド管理、依存コンポーネント（OrderRepository / OrderManager / RiskManager / Reconciler）組み立てを実装。

- 設定読み込み・検証機能（kabusys.config）
  - プロジェクトルート探索（.git または pyproject.toml を基準）を行い、.env/.env.local の自動読み込み（上書き制御、OS 環境変数保護）を実装。
  - .env 行パーサーの強化（export プレフィックス対応、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメント処理）。
  - Settings クラスで環境値の取得・検証を提供（J-Quants、kabu API、LINE、DB パス、paper_trading 切替、監視しきい値、ログレベル、環境判定プロパティ等）。
  - PAPER_FILL_MODE の有効値チェック、PAPER_TRADING_SQLITE_PATH による paper_trading 用 DB パス提供。

- ポートフォリオ構築ライブラリ（kabusys.portfolio）
  - portfolio_builder: シグナル選定（スコア降順・タイブレーク）と等配分 / スコア配分重み計算（スコアが全て 0 の場合は等配分へフォールバック）。
  - risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。unknown セクターの扱い、既存ポジション除外（当日売却予定）などの挙動を明記。
  - position_sizing: ポジションサイズ計算（risk_based / equal / score）、単元株丸め（lot_size）、per-stock と aggregate のキャップ、コストバッファを考慮したスケールダウンと remainder に基づく追加配分ロジックを実装。

- リサーチ／ファクター計算（kabusys.research）
  - factor_research: モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20、相対ATR、平均売買代金、出来高比率）、バリュー（PER, ROE）の DuckDB ベース計算を実装。データ不足時の None 扱い、ウィンドウバッファ設定を明確化。
  - feature_exploration: 将来リターン計算（任意ホライズン）、IC（Spearman ランク相関）計算、ファクター統計サマリ（count/mean/std/min/max/median）、安定なランク計算を実装。
  - research パッケージの公開 API を整備（zscore_normalize の再エクスポートなど）。

- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news を OpenAI（gpt-4o-mini）へ送信して銘柄別センチメント ai_score を ai_scores テーブルへ書き込むロジックを実装。バッチ処理（最大銘柄数）、トークン肥大化対策（記事数・文字数制限）、ウィンドウ計算（JST→UTC 変換）、レスポンスバリデーション、スコアクリップ（±1.0）、リトライ（429・ネットワーク・5xx の指数バックオフ）等を実装。
  - 出力フォーマット厳格化（JSON のみ）や、部分成功時に既存スコアを保護する更新戦略を採用。

- ユーティリティ（kabusys.utils）
  - process_priority: クロスプラットフォームでプロセス優先度（high/normal/low）と CPU affinity の設定機能を追加。Windows / POSIX（Linux, Darwin, FreeBSD）対応、失敗時は警告でスキップ。

- ツール類（kabusys.tools）
  - paper_verification_report: Paper Trading 用 SQLite DB からシステム稼働率、注文成功率、送信率、P95 レイテンシなどを集計して CLI でレポート出力するスクリプトを追加。閾値（稼働率 99%、成功率 90% 等）と Pass/Fail 判定を提供。

- パッケージ情報
  - パッケージバージョンを __version__ = "0.1.0" に設定。

### Changed
- DB 周りの振る舞いを明示
  - 監視（monitoring）は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨を明記（run_monitoring）。
  - run_execution は paper_trading 環境時に専用 DB を使用し、本番データと分離。

### Fixed / Hardened
- 各所で例外耐性を向上
  - run_monitoring の check_once() 呼び出しで例外をキャッチして次ループへ継続するように実装。
  - .env 読み込みでファイルオープン失敗時に警告を出して継続する実装。
  - process_priority / set_cpu_affinity は権限不足や未実装 API に対して安全にフォールバック。

### Notes / Known limitations
- ai.news_nlp モジュールは大枠の実装があるが（コード切れの箇所あり）一部実装（例: _fetch_articles の呼び出し先実装、細部の DB 更新手順）が未完成または外部依存がある可能性があるため、運用前の動作確認が必要。
- position_sizing の価格欠損時の扱いに TODO コメントあり（price が 0.0 の場合にエクスポージャーが過少見積もられる問題）。将来的なフォールバック価格の採用を検討する旨が記載されている。
- .env 自動読み込みはプロジェクトルートが特定できない場合はスキップされる（テスト環境等で挙動を制御可能）。
- DuckDB の executemany 前の params 空チェックや一部 DuckDB バージョン依存の注意がコメントにあるため、DuckDB バージョン互換性を要確認。

---

## [0.1.0] - 初回リリース（推定）
リポジトリ初期実装相当。上記の主要機能群（監視・実行ランチャー、設定管理、ポートフォリオ構築、ポジション決定、リスク制御、ファクター計算、特徴量解析、AI ニューススコアリング、Paper Trading レポート、プロセス優先度ユーティリティ等）をまとめて公開。

### Added
- 全体機能群を初期実装として追加（詳細は Unreleased の Added を参照）。

### Security
- 環境変数の必須チェック（_require）により、機密値未設定時に早期に明示的なエラーを出す設計。

---

（注）本 CHANGELOG は提供されたコードの内容とコメントから推測して作成しています。実際のリリース履歴や過去のバージョンとの差分がある場合は、正確なコミット履歴やリリースノートを基に適宜更新してください。