# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
慣習に従い、変更の種類ごとに分類しています。

## [Unreleased]

(現時点で未リリースの変更はありません)

## [0.1.0] - 2026-04-17

初回リリース。本リポジトリに含まれる主要な機能追加・実装をまとめます。

### 追加 (Added)
- プロジェクトの基本パッケージ構成を実装
  - kabusys パッケージ初期化とバージョン情報 (__version__ = "0.1.0")。
- 設定・環境変数管理 (kabusys.config)
  - .env/.env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）。
  - .env パーサの実装:
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - クォートなしの行で inline コメント（#）の扱い制御
  - _require による必須環境変数チェックと明示的エラーメッセージ。
  - 各種設定プロパティ（DBパス、APIキー、監視閾値、環境種別検証など）を提供。
  - PAPER_FILL_MODE の検証ロジックを実装（instant/partial/never/reject）。
- 実行エントリースクリプト
  - run_execution.py: ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用して本番DBと分離。
    - BrokerClientFactory を用いたブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てと実行スレッド管理。
    - 停止フラグ (data/stop_requested.flag) と PID ファイルの扱い。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関係なく本番 sqlite_path を使用して監視テーブルを記録。
    - 停止フラグ検知でループ終了、KeyboardInterrupt による終了処理。
- ユーティリティ
  - process_priority モジュール (kabusys.utils.process_priority)
    - Windows / POSIX(Linux, Darwin, FreeBSD) の差分を吸収してプロセス優先度を設定する set_process_priority。
    - カレントプロセスの CPU affinity を最初の N コアに固定する set_cpu_affinity。
    - アクセス権限や非対応環境でのフォールバック・警告を実装。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順＋signal_rank で候補選定。
    - calc_equal_weights / calc_score_weights: 重み計算（スコアが全て 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中の上限チェック（max_sector_pct）と候補除外。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数算出。
    - lot_size 単位で丸め、per-stock 上限・aggregate cap を考慮したスケール調整、cost_buffer を用いた保守的見積り。
- 研究・リサーチモジュール（DuckDB ベース）
  - research.factor_research:
    - calc_momentum / calc_volatility / calc_value: 各種ファクターの SQL+Python 実装（Window 関数を多用）。
  - research.feature_exploration:
    - calc_forward_returns: 将来リターン計算（複数ホライズンに対応、入力検証あり）。
    - calc_ic / rank / factor_summary: IC（Spearman）計算、ランク変換、統計サマリー。
  - research パッケージは kabusys.data.stats の zscore_normalize をエクスポートと併せて利用可能に。
- AI ニュース NLP スコアリング (kabusys.ai.news_nlp)
  - raw_news を OpenAI（gpt-4o-mini）へ送信して銘柄別センチメントを ai_scores テーブルへ記録する処理フローを実装。
  - 機能:
    - ニュース収集ウィンドウ計算（JST -> UTC 変換）calc_news_window。
    - 銘柄毎の集約（記事数・文字数上限）、バッチ送信（最大 20 銘柄/回）。
    - 429/5xx/タイムアウト等に対する指数バックオフリトライ、結果の検証、スコアクリッピング（±1.0）。
    - APIキー未設定時の明示的エラー。
  - フェイルセーフポリシー: API失敗でも継続、部分成功時には既存スコア保護のため対象コード絞って置換。
- ツール
  - tools.paper_verification_report
    - Paper Trading の検証レポート生成 CLI。
    - システム稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均/最大/P95）等を集計して判定（PASS/FAIL）を出力。
    - P95 計算ユーティリティ、閾値（稼働率/成功率/送信率/P95 レイテンシ）を定義。
    - コマンドライン引数 --from/--to/--db に対応。

### 変更 (Changed)
- （初回リリースゆえ該当なし）

### 修正 (Fixed)
- .env 読み込みでのエラー発生時に warnings.warn を用いて警告し処理を継続するように実装（IOError の取り扱い）。
- calc_score_weights の全スコアが 0 の場合に等配分へフォールバックし、警告ログを出すように実装。
- 実行中のプロセス優先度設定で権限不足や非対応 OS の場合に警告して処理をスキップする安全策を追加。
- position_sizing の aggregate cap スケーリングで端数処理（lot_size 単位）と残余キャッシュによる再配分を実装してより安定した配分を実現。

### セキュリティ・耐障害性 (Security / Robustness)
- OpenAI への呼び出しはリトライとバリデーションを行い、想定外のレスポンスは破棄して処理継続する設計。
- DB 書き込み前にパラメータが空でないことを確認するなど、DuckDB 特有の制約を考慮した実装。
- 環境変数自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD によって無効化可能（テスト等で利用）。

### 既知の注意点 (Known issues / TODO)
- portfolio.risk_adjustment.apply_sector_cap:
  - price_map に price が欠損（0.0）の場合、エクスポージャーが過少見積りされて制限が逃れる可能性がある。将来的に前日終値や取得原価でフォールバックする検討が必要。
- position_sizing:
  - lot_size は現状全銘柄共通の引数。将来的に銘柄別 lot_map を導入する余地あり（TODO コメントあり）。
- news_nlp モジュールは API キー管理やコストに注意して運用すること（大量バッチはコスト増加）。
- calc_forward_returns の horizons は 1〜252 の範囲に制限（バリデーションあり）。

---

以上がバージョン 0.1.0 の主な実装内容です。必要があれば各機能ごとにより詳細な変更履歴（関数レベルの変更点や入力/出力仕様）を追記します。