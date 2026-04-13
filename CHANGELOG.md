# Changelog

すべての変更は Keep a Changelog に準拠して記載しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

- リリースノートの形式: https://keepachangelog.com/ja/1.0.0/
- バージョンポリシー: MAJOR.MINOR.PATCH

## [Unreleased]

### Added
- 監視・実行・検証・ポートフォリオ構築・リサーチ・AI 等、システム全体の主要コンポーネントを整理・実装。
  - 実行ランナー: run_execution.py（ExecutionEngine 起動スクリプト）。Paper Trading 環境時に MockBrokerClient を使用する設定と、paper_trading 用 SQLite DB（data/paper_trading.db）との分離をサポート。
  - 監視ランナー: run_monitoring.py（SystemMonitor のポーリングループ起動）。環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き対応。
  - 検証ツール: tools/paper_verification_report.py による Paper Trading 検証レポート生成（稼働率・注文成功率・送信率・P95 レイテンシ等）。
  - ポートフォリオ構築モジュール: portfolio/*（候補選定、等重/スコア重み算出、単元丸め・リスクベースの株数算出、セクター上限適用、レジーム乗数）。
  - リサーチモジュール: research/*（モメンタム／ボラティリティ／バリューのファクター計算、将来リターン計算、IC 計算、統計サマリー、ランク変換）。
  - AI ニュース NLP: ai/news_nlp.py — raw_news を集約して OpenAI（gpt-4o-mini）でセンチメントを算出し ai_scores テーブルへ保存する処理（バッチ化・トークン対策・スコアクリップ・リトライ処理を含む）。
  - ユーティリティ: utils/process_priority.py — Windows / POSIX を吸収するプロセス優先度設定および CPU affinity 設定ユーティリティ。
  - 設定管理: config.py — .env/.env.local の自動読み込み（プロジェクトルート検出）、堅牢な .env パーサ、環境変数必須チェックや各種検証ロジック（PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等）。

### Changed
- DB 周りの設計:
  - monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用する仕様（監視データは本番 DB を対象にする設計判断）。
  - ExecutionEngine 起動時に paper_trading モードを検出して専用 SQLite（paper_sqlite_path）を使用することで本番 DB と完全に分離。
  - DuckDB をファクタ／リサーチ処理用の列指向 DB として統合（prices_daily / raw_financials 等の分析用テーブル参照）。
- 設定ロードの挙動:
  - 自動ロード順序を OS 環境 > .env.local > .env に明確化。OS 環境変数の保護（protected set）を実装。
- エラーハンドリングとフォールバックの強化:
  - MONITOR_POLL_INTERVAL の不正値（整数変換失敗や 0 以下）に対してデフォルト値へフォールバックする警告ログを追加。
  - プロセス優先度設定や CPU affinity の適用で権限不足や未対応 OS が発生した場合、例外をキャッチして警告を出し処理を継続するように変更。
  - calc_score_weights で全銘柄のスコア合計が 0 の場合、等金額配分へフォールバックして警告を出力。
  - apply_sector_cap でセクターが "unknown" の銘柄はセクター上限判定から除外する挙動を明確化。
  - position_sizing のスケーリングロジックを整備（lot_size 単位での丸め、aggregate cap を越えた際のスケールダウンと残差配分処理）。
- ドキュメント／コメントを充実させ、設計上の注意点（例: Look-ahead バイアス回避、DuckDB executemany の注意点等）を明記。

### Fixed
- SQLite / DuckDB 接続後のクリーンアップ（finally ブロック）を追加して、例外時にも接続がクローズされるように改善。
- news_nlp の API キー未設定時に明確な ValueError を送出するように実装。
- factor_research / feature_exploration の境界条件（データ不足時に None を返す等）を実装し、欠損データによる計算エラーを回避。

### Security
- 環境変数の自動ロード機能は KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能にしてテストや CI の安全性に配慮。

---

## [0.1.0] - 2026-04-13

初回公開リリース。上記の主要機能群を含む初版として公開。

### Added
- コア機能:
  - ExecutionEngine と関連コンポーネント（OrderManager, OrderRepository, Reconciler, RiskManager 等）。
  - SystemMonitor と監視データ初期化処理（init_monitoring_db）。
  - Portfolio 構築関連の純粋関数群（選定・重み付け・ポジションサイズ算出・セクター上限・レジーム乗数）。
  - Research ツール群（ファクター計算、将来リターン、IC、統計サマリー）。
  - AI を使ったニューススコアリング（OpenAI 統合、バッチ送信、リトライ、レスポンス検証）。
  - CLI/スクリプト:
    - run_execution.py
    - run_monitoring.py
    - python -m kabusys.tools.paper_verification_report（検証レポート出力）
- 設定・ユーティリティ:
  - Settings クラス（環境変数取得・検証）、.env 自動ロード（.env/.env.local）。
  - process_priority と CPU affinity 設定ユーティリティ（Windows/POSIX を吸収）。
  - DuckDB 統合（解析処理向け）。

### Changed
- Paper Trading モードを想定した DB 分離（data/paper_trading.db をデフォルト）。
- 監視は本番 sqlite_path を用いる挙動に統一（環境によらず監視対象は本番 DB）。
- logging の初期化を run_* スクリプト内で行うように標準化。

### Fixed
- .env パーサのロバスト化（コメント、クォート、export 形式に対応）。
- ポーリング間隔やプロセス優先度設定時の例外処理を改善。

---

（注）
- 本 CHANGELOG は、提供されたコードベースの実装内容・コメントから推測して作成しています。実際のコミット履歴ではなく機能的観点での要約であるため、正確なコミット単位の差分は含まれていません。必要であれば、実際の git 履歴やリリース単位の情報を元に追記・修正してください。