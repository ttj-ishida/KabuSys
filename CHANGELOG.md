# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  

※この CHANGELOG は投入されたコードベースの内容から機能・実装を推定して作成しています。

## Unreleased

- （現在未リリースの変更はここに記載）

---

## [0.1.0] - 2026-04-17

初回公開リリース。本リリースでは自動売買システム「KabuSys」のコア機能群を実装しています。主要な追加点を以下にまとめます。

### Added
- 全体
  - パッケージ初期化とバージョン管理（kabusys.__version__ = 0.1.0）。
  - 環境変数 / .env 管理モジュール（src/kabusys/config.py）。
    - プロジェクトルートの自動検出（.git または pyproject.toml を起点）。
    - .env / .env.local の読み込み仕様：export 形式・クォート処理・インラインコメント対応。
    - 設定値のラッパークラス Settings を提供（DB パス、API トークン、監視閾値、環境種別など）。
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化が可能。
- 実行・監視
  - 実行エントリポイント: run_execution.py
    - ExecutionEngine をスレッドで起動する起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用 DB を使用して本番 DB と分離。
    - BrokerClientFactory から Broker クライアントを生成（実運用 / モックの切り替えを想定）。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み立てて ExecutionEngine を起動。
    - 停止制御: data/stop_requested.flag の検出で安全に停止。PIDファイル管理（data/execution.pid）。
  - 監視エントリポイント: run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。
    - 監視処理は常に本番用 sqlite_path を使用（環境に依存せず監視が行える設計）。
    - 停止フラグの検出でループ終了。例外はログ出力して次のポーリングへ継続。
- データベース / 分析基盤
  - DuckDB 接続を利用した研究・分析モジュール（src/kabusys/research/*）。
    - ファクター計算モジュール（factor_research.py）
      - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20 等）、バリュー（PER, ROE）を計算する関数を実装。
      - prices_daily / raw_financials テーブルに依存する純粋関数群。
    - 特徴量探索（feature_exploration.py）
      - 将来リターン（複数ホライズン）計算、IC（スピアマンランク）計算、ファクター統計サマリ（count/mean/std/min/max/median）を実装。
    - research パッケージの公開 API を整備（calc_momentum/volatility/value、calc_forward_returns、calc_ic、factor_summary、rank、zscore_normalize をエクスポート）。
- ポートフォリオ構築
  - portfolio モジュール（src/kabusys/portfolio/*）
    - portfolio_builder.py：候補選定（スコア降順 + signal_rank タイブレーク）、等金額配分、スコア加重配分（スコア合計が 0 の場合は等金額へフォールバック）。
    - risk_adjustment.py：セクター集中上限適用（既存ポジションを考慮して候補を除外）、レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear）を実装。
    - position_sizing.py：ポジションサイズ計算（risk_based / equal / score の配分方式）、単元株（lot_size）丸め、aggregate cap によるスケールダウン、cost_buffer（手数料/スリッページ想定）対応、各種リスク制約の実装。
    - portfolio パッケージのエクスポートを整理。
- AI / ニュース解析
  - ニュース NLP スコアリングモジュール（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントスコア（-1.0〜1.0）を算出。
    - タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）やバッチサイズ、最大記事数・文字数トリム、スコアクリッピング、リトライ戦略（指数バックオフ）等を実装。
    - レスポンス検証と部分的な DB 更新（対象コードのみ置換）を行い、部分失敗に対する保護を考慮した設計。
    - （注）ファイル末尾が途中で切れているため、実装の一部が継続中である可能性あり。
- ツール
  - paper_verification_report.py（src/kabusys/tools/paper_verification_report.py）
    - Paper Trading 用の検証レポート生成 CLI を実装。--from/--to/--db オプションあり。
    - 指標: 稼働率（uptime）、注文成立率（fill_rate）、送信率、P95 レイテンシ等を算出し、閾値（デフォルト）との比較で PASS/FAIL 判定を表示。
    - P95 計算、各種 SQL クエリとフォーマッタを提供。
- ユーティリティ
  - process_priority.py（src/kabusys/utils/process_priority.py）
    - Windows / POSIX（Linux/Mac/FreeBSD）を吸収してプロセス優先度（high/normal/low）と CPU affinity 固定を行うユーティリティを提供。
    - 許可エラーや未対応環境では警告ログを出して処理をスキップする設計。

### Changed
- -（初回リリースのためなし）

### Fixed
- -（初回リリースのためなし）

### Deprecated
- -（初回リリースのためなし）

### Removed
- -（初回リリースのためなし）

### Security
- 外部 API キー（OpenAI、J-Quants、kabu API など）は環境変数経由でのみ取得する設計。.env の自動ロードは無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

### Notes / Known limitations / TODOs
- config._find_project_root は .git または pyproject.toml を探す実装のため、配布形態によりプロジェクトルートの自動検出が失敗する場合がある（見つからない場合は自動 .env ロードをスキップ）。
- position_sizing.apply_sector_cap 内で price が欠損（0.0）の場合にエクスポージャーが過少見積りされる旨の TODO コメントあり。将来的に価格フォールバックの導入が必要。
- news_nlp.py の末尾が途中で切れており、記事取得部や実際の API 呼び出し・DB 書き換え処理の続きが未表示のため、動作には実装の補完が必要な可能性あり。
- ExecutionEngine / SystemMonitor 等の内部実装（別モジュール）は本 CHANGELOG の範囲外。実行時の細かい挙動（注文フロー、再試行、例外処理の詳細など）は別途ドキュメント参照が必要。
- paper_verification_report の閾値は現状ハードコード（例: 稼働率 99% 等）。運用に合わせてパラメータ化が望ましい。

---

今後のリリースでは、以下を改善予定です（例）:
- news_nlp の堅牢化（部分失敗時のリトライと部分更新の強化）。
- position sizing の lot_map 拡張（銘柄別単元対応）。
- 監視 / 実行のより詳細なメトリクス収集とアラート連携（LINE 等）。
- ドキュメントの充実（API 仕様、運用手順、デプロイ手順）。

（以上）