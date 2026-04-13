# Changelog

すべての重要な変更をここに記録します。  
フォーマットは「Keep a Changelog」準拠です。  

※ この CHANGELOG はリポジトリ内のソースコードの内容から推測して作成しています。

## [Unreleased]

- （現在未リリースの変更はありません）

## [0.1.0] - 2026-04-13

初回公開リリース。以下の主要機能・実装を含みます。

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージ初期化、バージョン情報を __version__ = "0.1.0" として追加。
- 設定管理
  - kabusys.config.Settings クラスを実装し、環境変数ベースの設定取得を提供。
  - .env / .env.local の自動読み込み機能（プロジェクトルートの検出を実施）。OS 環境変数を保護する protected オプションを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
  - 各種設定プロパティ（DB パス、PID/KILL ファイルパス、しきい値、環境種別判定など）を提供。
  - PAPER_FILL_MODE の検証（有効値チェック）を実装。
- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、SQLite/DuckDB 接続、ブローカーファクトリ利用、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、セッション実行を行う。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB（data/paper_trading.db など）を使用し、本番 DB と分離。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数で間隔上書き可。監視は環境にかかわらず本番 sqlite_path を使用する旨を明示。
- モニタリング / ユーティリティ
  - kabusys.monitoring 関連（DB 初期化や SystemMonitor 呼び出しの起動フロー）を参照する起動処理を実装。
  - kabusys.utils.process_priority: プロセス優先度（Windows / POSIX）および CPU affinity 設定ユーティリティを追加。アクセス権限や未対応環境へのフォールバックを考慮。
- ポートフォリオ構築
  - kabusys.portfolio モジュールを提供（純粋関数群）。
    - portfolio_builder: シグナル選定（select_candidates）、等配分（calc_equal_weights）、スコア重み（calc_score_weights。全スコア0のフォールバック処理あり）。
    - risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジーム乗数（calc_regime_multiplier。未知レジームはフォールバック）。
    - position_sizing: 株数決定ロジック（risk_based / equal / score）、単元株丸め、aggregate cap（総投資額が利用可能現金を超えた場合のスケーリング）を実装。
- リサーチ機能
  - kabusys.research モジュールを提供。
    - factor_research: momentum / volatility / value ファクター計算（DuckDB を用いた SQL 実装、複数期間の移動平均・ATR 等）。
    - feature_exploration: 将来リターン計算（複数ホライズン）、IC（Spearman ランク相関）計算、ファクター統計サマリ、ランク付けユーティリティ。
    - DuckDB 接続を受け取り prices_daily / raw_financials テーブルのみ参照する設計。
- AI ニューススコアリング
  - kabusys.ai.news_nlp: raw_news を OpenAI（gpt-4o-mini）でスコアリングして ai_scores に書き込む処理を追加。
    - タイムウィンドウ計算、銘柄ごとの記事集約、バッチ（最大20銘柄）での API 呼び出し、JSON Mode 出力の検証、スコアのクリップ、部分成功時のテーブル更新方針（コードで絞って置換）を実装。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフのリトライ処理を実装。API キー未設定時は ValueError を送出。
- ツール
  - kabusys.tools.paper_verification_report: Paper Trading 用検証レポート生成ツールを追加。
    - 検証基準（稼働率、注文成功率、送信率、P95 レイテンシ）を定義し、SQLite（paper_trading DB）から集計して標準出力でレポート出力。
    - P95 計算、各種集計クエリと期間フィルタ機構を実装。コマンドライン引数（--from/--to/--db）をサポート。
- DB
  - DuckDB および SQLite を併用する設計（分析は DuckDB、本番監視やトレードログは SQLite 想定）。
  - monitoring DB 初期化関数（init_monitoring_db）への接続箇所を確保（起動時に冪等的にテーブル保証）。

### 変更 (Changed)
- 起動処理でプロセス優先度を早期に設定（run_execution/run_monitoring の最初の方で set_process_priority("high") を呼び出し）。
- .env 読み込み優先順位を OS 環境変数 > .env.local > .env に明確化。既存の OS 環境変数は保護され上書きされない。
- position_sizing の aggregate cap スケーリングで lot_size 単位で切り捨て・残余配分ロジックを厳格化し、スケールダウン時の再配分ロジックを導入。
- calc_regime_multiplier の未定義レジームに対しては警告を出して 1.0 にフォールバックする挙動を追加。
- calc_score_weights: 全銘柄スコアが 0 の場合、警告ログを出して等金額配分にフォールバックするよう変更。

### 修正 (Fixed)
- MONITOR_POLL_INTERVAL のパースを堅牢化。0 以下や不正値はデフォルト値（60 秒）にフォールバックして警告を出力するようにした（time.sleep に不正値を渡さないための対策）。
- Settings.env / LOG_LEVEL 等の環境変数に対するバリデーションを強化し、不正値は ValueError を送出する実装に。
- process_priority/set_cpu_affinity: 未対応 OS やアクセス権限不足時の例外を捕捉して警告ログを出し、処理をスキップするフェイルセーフを追加。
- ai/news_nlp: OpenAI API 呼び出し失敗時のリトライやスキップポリシーを明確化（部分失敗時の DB 保護の方針含む）。
- paper_verification_report: データ欠損やテーブル未存在時に sqlite3.OperationalError を捕捉して N/A 表示や 0 を返すハンドリングを追加。

### ドキュメント (Documentation)
- 各モジュールに docstring を充実させ、設計方針・引数・戻り値・注意点（例: ルックアヘッドバイアス回避、DuckDB/SQLite の使い分け等）を明記。
- tools.paper_verification_report および ai.news_nlp に実行方法・環境変数の説明を追加。

### 非互換/削除 (Removed / Breaking Changes)
- なし（初回リリースのため過去互換性は存在しません）。

---

今後の改善候補（コードから推測）
- position_sizing の lot_size を銘柄別に対応可能にする（現状全銘柄共通）。
- apply_sector_cap の price 欠損時のフォールバック価格（前日終値や取得原価）の導入。
- ai.news_nlp の出力検証をさらに堅牢に（部分的に壊れた JSON の扱い等）。
- DuckDB の executemany に関するバージョン依存対策の確認（コメントに注意喚起あり）。

（以上）