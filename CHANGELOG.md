CHANGELOG
=========

この CHANGELOG は「Keep a Changelog」の形式に準拠します。  
バージョニングは SemVer に従います。

Unreleased
----------

- ドキュメント／メタ情報の追加や小さなリファクタ（将来のリリース向けのプレースホルダ）。

[0.1.0] - 2026-04-13
-------------------

Added
- 実行エントリ
  - run_execution: ExecutionEngine を起動する CLI スクリプトを追加。環境変数 KABUSYS_ENV により paper_trading モードを切替可能。paper_trading 時は MockBrokerClient を使用し、data/paper_trading.db を専用 DB として使用（本番 DB と分離）。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する仕様。
- 設定管理
  - config.Settings: .env / .env.local の自動ロード機能を実装（プロジェクトルートの検出は .git または pyproject.toml を基準）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 高度な .env パーサー実装: export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱い、保護された OS 環境変数の上書き制御などに対応。
  - 多数の設定プロパティを追加（DB パス、PID ファイル、監視しきい値、PAPER_FILL_MODE など）と厳密なバリデーション（有効値チェック、必須環境変数の明示的エラー）。
- ポートフォリオ構築
  - portfolio_builder: シグナルの候補選定（スコア降順・タイブレークルール）と等金額 / スコア加重の重み計算を実装。スコアが全て 0 の場合は等分配にフォールバック。
  - risk_adjustment: セクター集中上限の適用（既存ポジションの時価ベース集計、売却予定銘柄の除外対応）と市場レジームに基づく資金乗数（bull/neutral/bear のマッピング）を実装。
  - position_sizing: 複数の割当方式（risk_based / equal / score）に対応した発注株数計算を実装。単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金を超える場合のスケーリング）、コストバッファ考慮、端数処理（残余キャッシュでの優先配分）などを含む。
- 研究・ファクター計算
  - research.factor_research: DuckDB の prices_daily / raw_financials を用いたモメンタム、ボラティリティ（ATR・出来高指標）、バリュー（PER/ROE）ファクター計算を実装。ウィンドウ不足時の None ハンドリングなどを考慮。
  - research.feature_exploration: 将来リターン（複数ホライズン）計算、IC（Spearman のランク相関）計算、ファクター統計サマリー、ランク計算ユーティリティを実装。外部ライブラリに依存せず純粋 Python 実装。
- AI ニューススコアリング
  - ai.news_nlp: raw_news / news_symbols を集約して OpenAI API（gpt-4o-mini）へバッチ送信し、銘柄ごとの ai_score を ai_scores テーブルへ書き込む処理を実装。処理設計上のポイント:
    - タイムウィンドウ計算（JST → UTC の変換）を明確化
    - 1チャンク最大 20 銘柄、1銘柄あたりの記事・文字数のトリム
    - 429 / ネットワーク / 5xx 等に対する指数バックオフリトライ（上限あり）
    - レスポンスのバリデーションとスコアクリッピング（±1.0）
    - 部分失敗に耐える DB 更新（対象コードを絞って DELETE→INSERT）
- ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・P95 レイテンシ等を集計し、閾値（稼働率99%、注文成功率90%、送信率95%、P95 ≤ 200ms）で PASS/FAIL 判定を行う。
- ユーティリティ
  - utils.process_priority: Windows / POSIX を吸収するプロセス優先度設定ユーティリティを追加。nice 値・Windows 優先度クラスに対応し、失敗時は警告を出してスキップ。CPU affinity 設定ユーティリティも提供。

Changed
- DB 関連
  - DuckDB を分析系（research / ai）で利用する設計を採用。実行コンポーネントは sqlite（monitoring / order repository / paper_trading）と DuckDB（時系列・分析）を併用する構成を明示。
- 安全設計
  - Paper Trading と本番 DB を明確に分離（PAPER_TRADING_SQLITE_PATH を使用）。監視は本番 sqlite_path を常に参照するように明記。
  - API 呼び出しや DB クエリの失敗に対してフォールバック（None / 0 の扱い）や例外捕捉を多用し、長時間実行プロセスの耐障害性を高める設計に。

Fixed
- エッジケースハンドリング
  - .env パーシングでのクォート／エスケープ／コメント処理を改善し、誤った環境変数設定による誤動作を低減。
  - ファクター計算やレイテンシ計算でデータ不足時に適切に None を返すよう修正（ゼロ除算や不定値の伝播を回避）。

Security
- OpenAI API キーは明示的に引数または環境変数（OPENAI_API_KEY）での提供を必須化し、未設定時は ValueError を送出することでキー漏洩や未設定のままの不正利用を防止。

Notes
- 初期リリース（0.1.0）はシステムの主要コンポーネント（実行エンジン、監視、ポートフォリオ構築、研究モジュール、AI スコアリング、ユーティリティ群）を一通り揃えたものです。各モジュールは今後以下のような拡張を想定しています:
  - 銘柄別単元（lot_size）や手数料モデルの外部化
  - position_sizing のさらなる最適化とテストカバレッジ拡充
  - AI スコアリングのロギング／メトリクス強化
  - DuckDB スキーマとバックフィルツールの整備

過去の変更や追加要望がありましたら、対象モジュールと期待する動作を指定していただければ CHANGELOG を更新します。