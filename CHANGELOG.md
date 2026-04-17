CHANGELOG
=========

すべての注目すべき変更点をここに記録します。  
このファイルは「Keep a Changelog」形式に準拠しています。

Unreleased
----------

- （現在の作業中の変更はここに記載します）

[0.1.0] - 2026-04-17
--------------------

Added
- 初回リリース: KabuSys パッケージを追加。
  - パッケージバージョンは src/kabusys/__init__.py にて __version__ = "0.1.0" として設定。
- 実行 / 監視起動スクリプトを追加。
  - run_execution.py
    - ExecutionEngine をスレッドで起動し、data/execution.pid を PID ファイルとして扱う。
    - 停止フラグ (data/stop_requested.flag) を検知して安全に停止する処理を実装。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite（data/paper_trading.db をデフォルト）を使用する説明。
    - BrokerClientFactory を用いたブローカー抽象化、および OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせてエンジンを起動。
    - RiskManager 初期設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）のデフォルト値を定義。
  - run_monitoring.py
    - SystemMonitor を起動するポーリングループを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視はプロダクション用 sqlite_path を参照（KABUSYS_ENV に依らない）。
    - 停止フラグ検知でループ終了、例外時はログ出力して次ポーリングへ継続。
    - 起動時に set_process_priority("high") を呼び出し、プロセス優先度を上げる。
- 環境設定 / .env 読み込み機能を追加（src/kabusys/config.py）。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を起点）を実装し、CWD に依存しない自動 .env 読み込みを実現。
  - .env / .env.local の読み込み順序を実装（OS 環境変数は保護）。
  - export KEY=val 形式やシングル/ダブルクォートのエスケープ、インラインコメントの扱いに対応するパーサを実装。
  - Settings クラスを導入し、各種設定プロパティを提供（DB パス、Paper Trading 設定、監視閾値、ログレベル、環境種別判定等）。
  - PAPER_FILL_MODE の検証（有効値: instant/partial/never/reject）や PAPER_TRADING_SQLITE_PATH のサポートを追加。
- ポートフォリオ構築関連の純粋関数群を追加（kabusys.portfolio）。
  - portfolio_builder: select_candidates（スコア降順、タイブレークは signal_rank）、calc_equal_weights、calc_score_weights（全スコア 0 の場合に等配分へフォールバック）。
  - risk_adjustment: apply_sector_cap（セクター集中制限、unknown セクターは除外しない）、calc_regime_multiplier（bull/neutral/bear の乗数、未知レジームは警告して 1.0 フォールバック）。
  - position_sizing: calc_position_sizes（risk_based / equal / score の配分方式を実装、単元株丸め、aggregate cap（利用可能現金超過時のスケールダウン）、cost_buffer を考慮した保守的見積り、端数配分ロジック）。
- 研究・リサーチ関連モジュールを追加（kabusys.research）。
  - factor_research: calc_momentum（mom 1/3/6m、MA200 乖離）、calc_volatility（ATR20、流動性指標）、calc_value（PER/ROE）を DuckDB 上の prices_daily/raw_financials に基づいて計算。
  - feature_exploration: calc_forward_returns（任意ホライズンで将来リターン）、calc_ic（スピアマンランク相関による IC）、factor_summary（基本統計量）、rank（同順位は平均ランク）。
  - DuckDB 接続を受け取り SQL と純粋 Python で完結する設計（外部 API 依存なし）。
- ニュース NLP モジュールを追加（kabusys.ai.news_nlp）。
  - raw_news テーブルの集約（時間ウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST 相当の UTC 表現）→ OpenAI (gpt-4o-mini) でセンチメント評価 → ai_scores へ書込むワークフローを設計。
  - バッチ処理（1 API 呼び出しで最大 20 銘柄）、記事トリム（最大記事数/文字数制限）、レスポンスバリデーション、スコア ±1.0 クリップ、リトライ（指数バックオフ）などの堅牢化方針を記載。
  - calc_news_window ユーティリティを実装。
- ユーティリティを追加（kabusys.utils.process_priority）。
  - set_process_priority(level) で Windows / POSIX の差分を吸収してプロセス優先度を設定。
  - set_cpu_affinity(cpu_count) による CPU ピンニング機能を実装（利用可能コア数超過時は全コア使用）。
  - アクセス権限不足等は警告してフォールバックする安定実装。
- 運用ツールを追加（kabusys.tools.paper_verification_report）。
  - Paper Trading の結果を集計して Pass/Fail 判定付きのテキストレポートを標準出力に生成。
  - 稼働率／注文成功率／送信率／P95 レイテンシ等を算出するクエリと閾値（デフォルト）を提供。
  - コマンドライン引数 --from / --to / --db をサポート。PAPER_TRADING_SQLITE_PATH 環境変数との優先順位を処理。
- パッケージエクスポートと __all__ の整備（portfolio, research 等で公開 API を定義）。

Changed
- デフォルト動作の明文化:
  - 監視 (run_monitoring) は環境にかかわらず本番 sqlite_path を参照する旨を明記（監視は常に本番 DB を見る設計）。
  - run_execution は paper_trading 環境で DB を完全に分離する（paper_trading 用 SQLite を使用）。
- .env 自動読み込みの挙動:
  - プロジェクトルート検出に基づく自動読み込みを導入。自動読み込みを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
  - .env.local は .env より後に読み込み（上書き）されるよう変更。
- ポートフォリオ計算: スコア全ゼロ時の挙動を明確化（calc_score_weights が等配分へフォールバック）。
- position_sizing: cost_buffer パラメータを導入し、約定コストを保守的に見積もる挙動を追加。lot_size による丸めと端数配分により現金利用を最大化するロジックを明示。

Fixed
- .env パーサの堅牢化:
  - export プレフィックス対応、シングル・ダブルクォート内のバックスラッシュエスケープ、インラインコメントの正しい扱いを実装し、誤ったパースによる環境変数破壊を防止。
- 環境変数 MONITOR_POLL_INTERVAL の不正値扱いを安全化（整数変換失敗や 0 以下の値はデフォルト 60 秒へフォールバックし、警告を出力）。
- calc_forward_returns 等の関数で引数検証を強化（horizons の正当性チェック、SQL のスキャン範囲制限による性能対策など）。
- calc_volatility の true_range 計算で high/low/prev_close が NULL の場合に NULL を伝播させ、ATR カウントが過大評価されないよう修正。
- news_nlp: OpenAI の API 呼び出しで 429 / ネットワークエラー / 5xx に対するリトライ方針（指数バックオフ）を用意。API キー未設定時の例外を明示。

Notes
- ai/news_nlp の score_news 関数は大きな機能を設計・実装しており、OpenAI API キーの取り扱いやレスポンスの厳格な検証・部分更新によるフェイルセーフ性を重視しています。実行環境でのテスト・運用時は OPENAI_API_KEY の設定と料金・レート制限に注意してください。
- 一部モジュール（例: monitoring_db, SystemMonitor, ExecutionEngine の内部実装）は本 CHANGELOG の抜粋では詳細を示していませんが、起動スクリプト側で初期化・起動・停止制御が行われることを意図しています。

---
この CHANGELOG はリポジトリの現状のコード読み取りに基づいて作成しました。実際のコミット履歴・リリース日付とは差異がある場合があります。必要があれば各変更点をより細かいコミット単位で分割して追記してください。