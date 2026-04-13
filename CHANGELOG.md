Changelog
=========
すべての変更は Keep a Changelog の形式に準拠し、セマンティクスは semver を想定しています。

Unreleased
----------
今後の改善予定・既知の TODO / 制約事項:

- AI ニューススコアリング (kabusys.ai.news_nlp)
  - OpenAI へのリクエスト／レスポンスのバリデーションやリトライ処理は実装済み（チャンク送信・429/5xx/タイムアウトのエクスポネンシャルバックオフ）が、部分的な DB 書き込み/ロールバックの取り扱いや詳細なエラーハンドリングの拡充が残っています。
  - JSON レスポンスの厳密チェック、スコアクリップ、部分失敗時の既存スコア保護方針は設計に含まれているが、本番運用上の耐障害性強化を予定。

- ポートフォリオ建構成
  - apply_sector_cap における価格欠損時のフォールバック（例: 前日終値や取得原価）を導入予定（現状 price が 0.0 の場合に過少見積りとなる旨を TODO コメントで記載）。
  - 将来的に銘柄別 lot_size をサポートする設計拡張（現在は共通 lot_size を仮定）。

- ドキュメント・テスト
  - 各モジュールの API（特に ExecutionEngine / BrokerFactory）の統合テストと利用手順書を追加予定。

0.1.0 - 2026-04-13
-----------------
Added
- 初期リリースを公開。主要な機能群を含む。
  - 実行系
    - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
      - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db をデフォルト）に分離して動作。
      - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler を組み合わせてセッションを実行。
      - 起動時にプロセス優先度を設定するユーティリティ呼び出しを実施。
  - 監視系
    - SystemMonitor 起動スクリプト（src/kabusys/run_monitoring.py）
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値時はフォールバック）。
      - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化。
      - 起動時にプロセス優先度を設定。
  - 設定管理
    - Settings クラス（src/kabusys/config.py）
      - .env 自動読み込み（プロジェクトルート検出: .git / pyproject.toml 基準）、.env/.env.local の読み込み順ルール（OS 環境変数保護、.env.local は上書き可）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
      - 各種設定アクセスプロパティ（DB パス、PID/KILL フラグ、しきい値、env/log_level のバリデーション等）。
      - PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL 等の検証ロジックを実装（無効値は ValueError）。
  - ユーティリティ
    - プロセス優先度・CPU affinity 設定ユーティリティ（src/kabusys/utils/process_priority.py）
      - Windows / POSIX(Linux, Darwin, FreeBSD) に対応する nice / priority 設定。
      - アクセス禁止や未サポート環境では警告ログを出して安全にスキップ。
  - ポートフォリオ構築（純粋関数群、DB 非依存）
    - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
      - select_candidates, calc_equal_weights, calc_score_weights（スコア全0時のフォールバック含む）。
    - セクター上限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
      - apply_sector_cap（sell_codes を除外して既存エクスポージャーを計算）。
      - calc_regime_multiplier（bull/neutral/bear の乗数、未知レジームはフォールバック）。
    - 発注株数計算（src/kabusys/portfolio/position_sizing.py）
      - risk_based / equal / score の allocation_method をサポート。
      - 単元株（lot_size）丸め、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap スケーリングアルゴリズムを実装。
      - スケールダウン後の残差処理で lot_size 単位の追加配分を行い再現性を確保。
  - リサーチ / ファクター計算
    - ファクター計算モジュール（src/kabusys/research/factor_research.py）
      - Momentum / Volatility / Value の計算実装（DuckDB を用いた SQL ベースの実装）。
      - データ不足時に None を返す安全設計、200日MA などウィンドウチェック。
    - 特徴量探索（src/kabusys/research/feature_exploration.py）
      - 将来リターン計算（任意ホライズン、入力バリデーション）、IC（Spearman）計算、rank / factor_summary 実装（外部ライブラリに依存しない実装）。
      - rank() は同順位を平均ランクにする等、ties を適切に処理。
    - research パッケージ初期エクスポート（src/kabusys/research/__init__.py）。
  - AI ニュース NLP（初期実装）
    - raw_news を集約して OpenAI (gpt-4o-mini) にバッチ送信するワークフロー設計と一部実装（src/kabusys/ai/news_nlp.py）。
      - タイムウィンドウ計算、チャンク送信、レスポンスバリデーション、スコアのクリップ、API キー取得ロジック、リトライ方針を実装。
  - ツール
    - Paper Trading 検証レポート生成ツール（src/kabusys/tools/paper_verification_report.py）
      - 稼働率・注文成功率・送信率・レイテンシ(P95) 等を集計して標準出力にレポートを出力。
      - デフォルト DB パスは data/paper_trading.db、--db オプション / 環境変数で上書き可能。
  - パッケージ情報
    - バージョン定義: __version__ = "0.1.0"（src/kabusys/__init__.py）

Fixed
- .env パースの堅牢化（src/kabusys/config.py）
  - export KEY=val 形式に対応。
  - シングル／ダブルクォート文字列の内部バックスラッシュエスケープ処理を考慮したパース。
  - クォートなし値に対するインラインコメント（#）の認識ルールを改善（直前がスペース/タブでコメント扱い）。
  - .env 読み込み失敗時は warnings.warn で静かに処理継続。
  - OS 環境変数を保護する protected set を導入し、.env.local の上書きや自動ロードの安全性を強化。
- calc_score_weights のフォールバック
  - 全銘柄のスコア合計が 0.0 の場合に等金額配分へフォールバックして警告を出力。
- calc_regime_multiplier のフォールバック
  - 未知レジーム値のときに警告を出し 1.0 でフォールバック。
- calc_forward_returns の入力バリデーション
  - horizons の正当性チェック（正の整数かつ最大 252）を追加し、不正入力を早期に検出。
- process_priority / set_cpu_affinity の例外ハンドリング強化
  - AccessDenied / NotImplementedError 等の例外をキャッチしてワーニングを出し、起動継続するように改善。
- paper_verification_report の統計計算での耐障害性
  - 対象テーブルが存在しない場合でも OperationalError をハンドリングして N/A 表示にフォールバック。

Changed
- 各起動スクリプトで起動直後にプロセス優先度を設定するように統一。
- run_monitoring は MONITOR_POLL_INTERVAL の不正値に対してデフォルトにフォールバックし、警告ログを出すように変更。

Security
- OpenAI API キーは環境変数 OPENAI_API_KEY または明示的な引数で渡す仕様にしており、明示しない場合は ValueError を発生させることで誤送信を防止。

Removed
- （該当なし）

Notes / Known issues
- apply_sector_cap における price 不在時の扱いは現状要注意（価格が 0.0 の場合にエクスポージャーが過少見積りされる可能性あり）。将来的に前日終値等のフォールバックを導入予定。
- AI スコアリング後の部分的 DB 更新時の復元処理やトランザクション戦略は今後の改善項目です。
- 一部の高度な運用オプション（銘柄別 lot_size 等）は未実装だが設計上は拡張可能。

Author
------
この CHANGELOG はコードの内容に基づいて推測して作成しました。実際のリリースノートや運用ガイドは、デプロイ方針や運用上の決定に合わせて適宜更新してください。