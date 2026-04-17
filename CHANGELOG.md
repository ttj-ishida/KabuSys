KEEP A CHANGELOG
すべての重要な変更はこのファイルに記録します。

フォーマットは Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）に準拠しています。

Unreleased
- （なし）

0.1.0 - 2026-04-17
Added
- 全体
  - 初回リリース。パッケージバージョンを __version__ = "0.1.0" として公開。
  - DuckDB と SQLite を併用するデータ処理基盤を導入（多くの処理で DuckDB 接続を受け渡す設計）。
- 設定管理
  - kabusys.config.Settings を追加。環境変数 / .env / .env.local から設定を読み込み、各種設定値（KABUSYS_ENV, LOG_LEVEL, DATABASE パス等）を提供。
  - 自動 .env ロード機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。OS 環境変数は保護され上書きされない。
  - .env 行パーサーを強化（export プレフィックス、シングル/ダブルクォート内のエスケープ、行内コメント処理等に対応）。
  - 設定値バリデーションを追加（KABUSYS_ENV や LOG_LEVEL、PAPER_FILL_MODE の有効値チェック）。
- 実行・監視エントリポイント
  - run_execution.py を追加。ExecutionEngine の起動スクリプトを実装し、paper_trading 環境時には専用の paper_trading DB を使用する動作を実装（本番 DB と分離）。
  - run_monitoring.py を追加。SystemMonitor のポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト60秒）。監視は環境にかかわらず本番 sqlite_path を使用する仕様を明記。
  - 停止フラグ (data/stop_requested.flag) と PID ファイルの扱いを実装。停止フラグ検出で安全に終了する仕組みを追加。
- プロセス制御ユーティリティ
  - kabusys.utils.process_priority を追加。Windows / POSIX（Linux, Darwin, FreeBSD）を吸収する set_process_priority(level) と CPU affinity を固定する set_cpu_affinity(cpu_count) を提供。権限不足や未対応 OS では警告を出してスキップするフェイルセーフを実装。
- ポートフォリオ構築
  - kabusys.portfolio モジュール群を追加。
    - portfolio_builder: シグナルから候補選定（スコア降順、タイブレークルール）と等金額・スコア重み計算を提供。スコア合計が 0 の場合は等金額にフォールバックして警告を出す。
    - risk_adjustment: セクター集中の上限チェック（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知レジームは警告を出してフォールバック。
    - position_sizing: 株数決定ロジックを実装（risk_based / equal / score の allocation_method をサポート）。単元株（lot_size）で丸め、総投資額が現金上限を超える場合はスケーリングと残差処理で最終配分を調整。手数料・スリッページ見積り用 cost_buffer を考慮。
- リサーチ機能
  - kabusys.research にファクター計算・特徴量探索を追加。
    - factor_research: モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20、相対ATR、出来高指標）、バリュー（PER, ROE）を DuckDB の SQL とウィンドウ関数で実装。データ不足時は None を返す設計。
    - feature_exploration: 将来リターン計算（複数ホライズン対応）、スピアマンランク相関（IC）計算、ファクター統計サマリ（count/mean/std/min/max/median）を標準ライブラリのみで実装。pandas 等に依存しない軽量実装。
  - research パッケージの __all__ に主要関数をエクスポート。
- AI / ニュース解析
  - kabusys.ai.news_nlp を追加。raw_news / news_symbols を集約し OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む処理を設計・実装。
    - 処理窓（前日 15:00 JST ～ 当日 08:30 JST）を正しく UTC に変換する calc_news_window を実装。
    - バッチサイズ、1銘柄あたりの最大記事数・最大文字数、API リトライ（429/ネットワーク/5xx に対する指数バックオフ）等を考慮した設計。
    - レスポンス検証・スコアの ±1.0 クリップ・部分更新（対象コードのみ DELETE→INSERT）などの堅牢化戦略を導入。
    - （注）ファイル末尾が切れている箇所がありますが、主要な設計・意図を実装済み。
- ツール
  - kabusys.tools.paper_verification_report を追加。Paper Trading 用 SQLite（デフォルト data/paper_trading.db）からシステム安定性・注文成功率・シグナル精度・API レイテンシ指標を集計し、閾値比較に基づく PASS/FAIL レポートを標準出力へ表示する CLI を実装。P95 算出、日付フィルタ（--from/--to）、DB存在チェック、テーブル未存在時のフォールバック処理を備える。
- 監視 DB 初期化
  - init_monitoring_db（monitoring.monitoring_db）を呼び出して監視用テーブルの存在を保証する処理を run_execution / run_monitoring に組み込み（冪等）。
- パッケージ初期化
  - 各サブパッケージの __init__.py を追加・整理し、主要シンボルをエクスポート。

Changed
- （初回リリースのため該当なし）

Fixed
- .env パーサー
  - export プレフィックスやクォート内のバックスラッシュエスケープ、行内コメントの扱いに起因する誤解析を改善。
- process_priority
  - 未対応 OS や権限制約での失敗をキャッチして警告ログを出し続行するように改善（アプリケーションの起動失敗を防止）。

Security
- OpenAI API キーの取り扱いは明示的に引数または環境変数 OPENAI_API_KEY を要求。未設定時は ValueError を送出して処理を中断する設計（誤った公開を防止）。

Notes / Known issues
- ai/news_nlp.py のファイル末尾で実装が途中で切れている箇所があります（このリリースでは主要設計・多くの関数は実装済み）。完全なデータ書き込みルートや一部のエラーハンドリングは続実装・レビューが必要です。
- position_sizing の price フォールバックについて注記（price が 0.0 の場合にエクスポージャーが過少評価される可能性）。将来的に前日終値や取得原価を使うフォールバックの検討を想定。
- run_monitoring は説明どおり「監視は常に本番 sqlite_path を参照する」設計です。テスト/開発で別途分離したい場合は環境変数等で明示的に設定してください。
- DuckDB の executemany の制約（空 params の扱いなど）に注意して実装している箇所があります。大規模バルク操作時は追加の検証を推奨。

作者
- KabuSys チーム

（以降のリリースでは各モジュールの拡張、AI モジュールの安定化、テスト補強、ドキュメント追加を予定しています。）