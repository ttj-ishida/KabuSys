CHANGELOG
=========

すべての重要な変更点は Keep a Changelog のフォーマットに従って記載しています。  
バージョン番号はパッケージ内の __version__（src/kabusys/__init__.py）に合わせています。

0.1.0 - 2026-04-17
-----------------

Added
- パッケージの初回リリース（バージョン 0.1.0）。
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite（data/paper_trading.db デフォルト）を使用する仕組みを実装。
    - BrokerClientFactory によるブローカークライアント生成フローを統合。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み合わせて ExecutionEngine を構成。
    - エンジンは daemon スレッドで起動し、プロジェクトルートの data/stop_requested.flag による停止フラグ監視を実装。
    - 起動時にプロセス優先度を "high" に設定するユーティリティ呼び出しを導入。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイントを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。無効値は安全にデフォルトへフォールバック。
    - 監視は本番 sqlite_path（環境に依らず）を使用する設計。
    - プロセス優先度設定・停止フラグ検知・例外安全を実装。
- 設定管理
  - config.Settings 実装を追加（環境変数アクセス・検証・.env ファイル自動読み込み）。
  - .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を探索して行う。OS 環境変数は保護（上書き防止）される設計。
  - .env パーサーはクォート、エスケープ、コメント処理に対応して堅牢化。
  - 各種設定プロパティ（DB パス、PID/フラグパス、paper_trading 用設定、監視しきい値、ログレベル、環境判定メソッド等）を提供。
  - PAPER_FILL_MODE 等の値検証（有効値チェック）を実装。
- Portfolio（ポートフォリオ構築）
  - portfolio_builder: シグナル選別（select_candidates）、等配分（calc_equal_weights）、スコア加重配分（calc_score_weights、スコア全0時は等配分へフォールバック）。
  - risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）。
  - position_sizing: 発注株数算出（risk_based, equal, score）、単元株丸め、ポートフォリオ・1銘柄上限、aggregate cap によるスケールダウン処理、cost_buffer を用いた保守的見積り、残余キャッシュによる端数配分ロジックを実装。
  - モジュールを package レベルでエクスポート（kabusys.portfolio.*）。
- Research（リサーチ）
  - research.factor_research
    - モメンタム（1M/3M/6M・MA200乖離）、ボラティリティ（ATR20・相対ATR・出来高指標）、バリュー（PER・ROE）を DuckDB を使って計算する関数群を実装。
    - データ不足時の None 戻りや行数条件チェックを考慮。
  - research.feature_exploration
    - 将来リターン計算（複数ホライズン、安全チェック）、IC（Spearman 的ランク相関）計算、ファクター統計サマリー（count/mean/std/min/max/median）、ランク関数を実装。
    - 外部依存を避け、標準ライブラリのみで実装。
  - research パッケージは data.stats の zscore_normalize を再エクスポート。
- AI / ニュース NLP
  - ai.news_nlp: raw_news を OpenAI（gpt-4o-mini）でスコアリングする処理の基盤を実装。
    - ニュース収集ウィンドウ（JST ベース → UTC 変換）計算ユーティリティ calc_news_window を実装。
    - API バッチ処理（銘柄ごと最大記事数・文字数でトリム、1回につき最大 20 銘柄）・JSON Mode 想定・レスポンス検証・スコアの ±1.0 クリップ・429/ネットワーク/5xx に対する指数バックオフリトライ機構の方針を実装。
    - API キー未設定時はエラー（ValueError）。
    - 部分失敗を想定した ai_scores テーブルへの差替え戦略（対象コードを限定して DELETE→INSERT）を設計。
  - （注）news_nlp のソースは途中まで含まれており、記事フェッチや書き込み部分は今後の実装継続を想定。
- ユーティリティ
  - utils.process_priority: Windows / POSIX（Linux/Mac/FreeBSD）を吸収するプロセス優先度設定（nice / HIGH_PRIORITY_CLASS 等）を実装。アクセス権限・未対応 OS の場合は警告して安全にスキップ。
  - CPU affinity 設定ユーティリティ（set_cpu_affinity）を追加（None のときは無効化）。
- Tools
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成 CLI を追加。
    - 稼働率、注文成功率、送信率、リスク却下数、平均/最大/P95 レイテンシなどを算出して標準出力へ整形レポートを出力。
    - P95 計算、日付フィルタ (--from/--to)、DB パス指定オプション (--db)、閾値による PASS/FAIL 判定を実装。
    - DB テーブル欠損（例: system_status / trade_logs / risk_logs）の場合にフォールバックして安全に動作。
- DB 初期化ユーティリティ
  - monitoring.monitoring_db の init_monitoring_db を参照して、起動時に監視用テーブルが存在することを保証（冪等）。

Changed
- アーキテクチャ／運用
  - paper_trading と live の DB を明確に分離（Settings.paper_sqlite_path）。
  - 監視（run_monitoring）は環境に依らず本番 sqlite_path を参照するポリシーを明示。
  - 実行スクリプト／監視スクリプトは起動時に優先度変更を試み、高優先度で稼働するように設計。
- 設定の自動ロード
  - プロジェクトルートの検出ロジック（.git / pyproject.toml）を導入し、パッケージ配布後もカレントワーキングディレクトリに依存せず .env を自動ロードする挙動に変更。
  - OS 環境変数は保護（protected）され、.env.local は .env より後に上書きロードされる。

Fixed
- 環境変数パースの堅牢化
  - .env の行パーサーで export 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い、クォートなしのコメント検出（直前が空白の場合）などの挙動を正しく処理。
- ポートフォリオ重み付け
  - calc_score_weights が全スコア 0.0 の場合に等金額配分へフォールバックするようにして、0 除算や非期待挙動を防止。
- モニタリングポーリング間隔
  - MONITOR_POLL_INTERVAL の不正値（非整数、0 以下等）を検出してログを出力し、安全にデフォルト（60 秒）へフォールバックするよう修正。
- position_sizing のスケーリング
  - aggregate cap 適用時のスケーリングと端数配分ロジックを実装し、利用可能現金を超える発注量が発生しないよう改善。
- research / factor 計算の NULL 安全性
  - DuckDB クエリ内でウィンドウ集計時のカウント条件や NULL 伝播を考慮して、必要行数未満や NULL データがある場合は None を返すようにして整合性を確保。

Known limitations / Notes
- ai.news_nlp の記事取得・DB 書き込み処理はソースが途中で途切れている個所があり、完全な実行フロー（記事フェッチ関数の実装、DuckDB への書き込み）は今後の作業が必要です。
- position_sizing の lot_size は現状グローバル固定（デフォルト 100）。将来的には銘柄別 lot_size をサポートする予定（TODO コメントあり）。
- apply_sector_cap の価格欠損（price_map に値がない場合）でエクスポージャーが過少見積りになる恐れがある旨をログと TODO で明記。将来的にフォールバック価格（前日終値や取得原価）対応を検討。
- NEWS NLP の OpenAI 呼び出しは gpt-4o-mini を想定しているが、実際の呼び出し・JSON 検証の最終実装と運用テストが必要。
- 一部モジュール（monitoring_db、SystemMonitor、ExecutionEngine 本体等）は本リリースで参照されるが、ここで提示したファイル群以外の実装詳細によっては追加の調整が必要となる場合があります。

参考: 開発方針 / 設計上の注意
- DuckDB をデータ分析エンジンとして利用し、prices_daily / raw_financials 等のテーブルを SQL + Python で処理する設計を採用。
- 本番 API / ブローカ呼び出しとは研究・検証ロジックを分離（research / portfolio は本番 API にアクセスしない）。
- 自動環境ロードは便利性のためデフォルトで有効だが、テスト時等に無効化できる KABUSYS_DISABLE_AUTO_ENV_LOAD フラグを用意。
- フェイルセーフ設計を重視：API 失敗時は個別にリトライ・スキップして他処理に影響を与えない、DB テーブルが欠けていてもツールが破綻しない（デフォルト値や N/A を返す）等。

今後の予定（抜粋）
- ai.news_nlp の残実装（記事フェッチ、バッチ送信ループ、DB 書込）完了。
- ExecutionEngine / SystemMonitor の統合テスト、paper_trading の検証スイート整備。
- 銘柄別 lot_size 対応・手数料/スリッページ見積りの拡充。
- DuckDB テーブルのスキーマ・マイグレーション管理の導入。

--- 
（以上）