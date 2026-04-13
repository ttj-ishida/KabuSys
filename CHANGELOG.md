Keep a Changelog — 変更履歴
すべての変更点は人間に読める形で記録します。セマンティック バージョニングおよび以下のカテゴリに従います: Added, Changed, Fixed, Deprecated, Removed, Security.

Unreleased
- （現在未リリースの変更はありません）

0.1.0 - 2026-04-13
Added
- 基本パッケージ初期実装を追加（初回リリース）。
  - 実行関連
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。起動時にプロセス優先度を「high」に設定し、SQLite / DuckDB に接続して各種コンポーネント（BrokerClient, OrderRepository, OrderManager, RiskManager, Reconciler）を組み立てて engine.run_session() を実行。
    - paper_trading モード対応: KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、paper 用の専用 SQLite（デフォルト data/paper_trading.db）で本番 DB と完全分離して記録。
  - 監視関連
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に依らず本番 sqlite_path を使用する設計。
    - 監視 DB 初期化（init_monitoring_db 呼び出し）と DuckDB 接続の組み合わせで実行。
  - 設定/環境変数
    - config.py: .env 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。読み込み順は OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化オプションを提供。
    - 環境変数パーサを強化: export プレフィックス、クォート（シングル/ダブル）のエスケープ処理、インラインコメントの扱い、オーバーライド制御（protected set）などを実装。
    - Settings クラスを導入し、各種設定（パス、閾値、PID/KILL ファイルパス、環境種別チェック、PAPER_FILL_MODE 等）をプロパティとして提供。入力値検証を実施（無効な値は ValueError を送出）。
  - ユーティリティ
    - utils.process_priority: プラットフォーム差分を吸収するプロセス優先度設定ユーティリティ（set_process_priority, set_cpu_affinity）。Windows/POSIX の差を吸収し、権限不足や未対応環境では安全にスキップして警告を出力。
  - ポートフォリオ構築
    - portfolio パッケージを追加（純粋関数群）。
      - portfolio_builder: 候補選定 select_candidates、等重配分 calc_equal_weights、スコア重み calc_score_weights。
      - risk_adjustment: セクター上限適用 apply_sector_cap、レジームに応じた資金乗数 calc_regime_multiplier（bull/neutral/bear マップ）。
      - position_sizing: calc_position_sizes による株数決定。risk_based / equal / score の配分方式をサポートし、lot_size 単位丸め、aggregate cap（available_cash によるスケールダウン）、cost_buffer を考慮した保守的見積り等を実装。
  - リサーチ/ファクター
    - research パッケージを追加（DuckDB を用いたファクター計算・解析）。
      - factor_research: calc_momentum, calc_volatility, calc_value を提供。prices_daily / raw_financials を参照し、期間やウィンドウの安全な取り扱いを行う（欠損やデータ不足時は None を返す等）。
      - feature_exploration: 将来リターン calc_forward_returns、IC 計算 calc_ic（Spearman ランク相関）、rank、factor_summary（count/mean/std/min/max/median）などの統計ユーティリティを実装。外部ライブラリに依存しない純 Python 実装。
  - AI / ニュース NLP
    - ai.news_nlp モジュールを追加。raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込むワークフローを実装。
      - バッチ（最大 20 銘柄）/トークン肥大化対策（記事数・文字数上限）、JSON Mode 出力期待、429/5xx/ネットワーク障害時の指数バックオフリトライ、レスポンス検証、スコアの ±1.0 クリップなどを実装。
      - calc_news_window により JST ベースの収集ウィンドウを UTC に変換して厳密に扱う（ルックアヘッドバイアス回避の設計方針）。
  - ツール
    - tools.paper_verification_report: Paper Trading 検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計し、PASS/FAIL 判定を行う CLI を提供。DB 未存在・テーブル未存在時の耐障害性を考慮。
  - パッケージメタ
    - パッケージ初期バージョンを __version__ = "0.1.0" として設定。

Changed
- （初回リリースのため、変更履歴はなし）

Fixed
- .env 読み込み時の細かなパース上の改善（クォート内のエスケープ、export 接頭辞対応、インラインコメント処理など）により、実運用での誤読を低減。
- run_monitoring.py と run_execution.py が例外発生時も安定して DB をクローズするよう finally ブロックを適切に配置。

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーは環境変数または引数で提供する設計としており、未設定時には明示的にエラーを出す（秘密情報の不注意なデフォルト埋め込みを防止）。

Notes / Known limitations
- ai.news_nlp の OpenAI 呼び出し周りはネットワーク/API エラーをリトライする実装だが、部分失敗時の DB 書き込みロールバックやトランザクション戦略は簡易化されているため、運用時に追加の堅牢化（トランザクション管理・監査ログ等）が推奨されます。
- position_sizing の単元株（lot_size）は現在グローバル固定で 100 を想定している。将来的に銘柄別単元対応の拡張がコメントにて示唆されています。
- apply_sector_cap は price_map に 0.0（欠損）を許容するが、欠損時にはエクスポージャーが過小評価される可能性がある点を TODO として記載。
- research モジュールは prices_daily / raw_financials のデータ品質に依存する。データ不足時は None を返す安全化が行われている。

参考
- 自動ロードされる .env の探索ルール: パッケージファイル位置から上位ディレクトリに .git または pyproject.toml を探索してプロジェクトルートを特定。見つからない場合は自動ロードをスキップ。