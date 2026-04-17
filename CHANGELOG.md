# CHANGELOG

すべての重要な変更点をここに記録します。本ファイルは Keep a Changelog の形式に準拠します。

※ 初期リリースの内容はソースコード（src/ 以下）から推測して記載しています。実装の詳細や将来的な変更に伴い更新してください。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-17

### 追加 (Added)
- 初期リリース: KabuSys パッケージ（バージョン 0.1.0）。
- 実行エントリ/運用ツール
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）を検知して安全にループを終了。
    - 起動時にプロセス優先度を "high" に設定する処理を組み込み。
    - Monitoring は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する設計。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB（data/paper_trading.db など）を使用し、発注系を完全に分離（MockBrokerClient 利用を想定）。
    - 起動前に停止フラグを確認し、既にフラグが立っている場合は起動せず終了。
    - エンジンは別スレッドで run_session を実行し、停止フラグ検知で engine.stop() による安全停止を行う。
    - 実行用 PID ファイルを書き込む（data/execution.pid を想定）。
- 設定管理
  - config.py
    - Settings クラスを導入し、環境変数から設定を集約。
    - .env / .env.local の自動ロード機能（プロジェクトルート検出による）。OS 環境変数保護機能（上書き禁止）を提供。
    - .env パーサーがシングル/ダブルクォート、エスケープ、インラインコメント（条件付き）に対応。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
    - 各種設定（J-Quants / kabu API / LINE / DB パス / PID/kill フラグパス / モニタ閾値 / PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL 等）をプロパティで提供し、値検証を実施。
- ポートフォリオ構築関連（純関数群、DB 参照なし）
  - portfolio/portfolio_builder.py
    - BUY シグナルの候補選定 select_candidates。
    - 等金額配分 calc_equal_weights。
    - スコア加重配分 calc_score_weights（全スコアが 0.0 の場合は等金額にフォールバックし WARNING を出力）。
  - portfolio/risk_adjustment.py
    - セクター集中制限を行う apply_sector_cap（売却予定銘柄除外対応、"unknown" セクターは上限不適用）。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier（"bull" / "neutral" / "bear" と未知値フォールバック）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数を算出する calc_position_sizes。
    - allocation_method に応じた計算（"risk_based" / "equal" / "score"）を実装。
    - 単元株（lot_size）での丸め、銘柄毎上限・アグリゲート上限（available_cash）を考慮したスケーリング、cost_buffer（手数料・スリッページ見積）を考慮した保守的見積り、余剰キャッシュを用いた端数配分ロジックを実装。
    - price 欠損や 0 値に対するデバッグログ出力を組み込み。
- リサーチ / ファクター計算（DuckDB ベース）
  - research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離の計算（ウィンドウ不足時は None を返す）。
    - calc_volatility: ATR20、相対ATR、平均売買代金、出来高比の計算（欠損値の伝播を制御）。
    - calc_value: raw_financials から EPS/ROE を取り出し PER/ROE を計算（target_date 以前の最新レコードを取得）。
  - research/feature_exploration.py
    - calc_forward_returns: 指定ホライズン先の将来リターンを一括取得（horizons 検証あり）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（有効レコードが 3 未満なら None）。
    - rank / factor_summary: ランク（同順位は平均ランク）、ファクター列の基本統計量（count/mean/std/min/max/median）を実装。
  - research/__init__.py で主要関数を再エクスポート。
- AI / ニュース NLP
  - ai/news_nlp.py
    - raw_news の記事を OpenAI（gpt-4o-mini）でセンチメント評価し ai_scores テーブルへ書き込む処理を実装（関数は途中まで確認可能）。
    - ニュース収集ウィンドウ計算（calc_news_window）を提供（JST 基準で前日 15:00～当日 08:30 を UTC に変換）。
    - バッチ（最大 20 銘柄）での API 呼び出し、429/ネットワーク/5xx に対する指数バックオフリトライ、JSON 形式検証、スコア ±1.0 クリップ、部分成功時の安全な置換（DELETE→INSERT の絞り込み）等の設計方針を組み込み。
    - API キー未設定時は ValueError を送出。
- ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level) — Windows/Linux/macOS（POSIX）でプロセス優先度を統一的に設定。アクセス権限不足等は警告でスキップ。
    - set_cpu_affinity(cpu_count) — 指定コア数への CPU affinity 固定。入力検証と失敗時のフォールバック（警告）を実装。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成 CLI を追加（python -m kabusys.tools.paper_verification_report）。
    - 日付フィルタ（--from / --to）と --db オプションをサポート。環境変数 PAPER_TRADING_SQLITE_PATH との優先順を実装。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等の指標を算出し、閾値（稼働率 99%、成立率 90%、送信率 95%、P95 200ms）に基づく Pass/Fail を出力。
    - DB 存在チェック、OperationalError に対する保護、P95 計算やフォーマットユーティリティを実装。
- パッケージメタ
  - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。
  - モジュール群の __all__ や各パッケージ __init__ で必要関数をエクスポート。

### 変更 (Changed)
- 初期リリースのため該当なし（初出機能の追加が中心）。

### 修正 (Fixed)
- paper_verification_report.py:
  - DB が存在しない場合やテーブルが不足するケースを想定してエラーハンドリング（OperationalError の保護）を実装。
  - P95 計算・空データ時の表示を安定化（None を "N/A" 表示に変換するユーティリティを追加）。
- config の .env 読み込み:
  - ファイル読み込み失敗時に警告を出すように改良（warnings.warn）。

### 既知の制約 / TODO（ソースからの注記を反映）
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされ得る旨の TODO コメントあり。将来的に前日終値等のフォールバック導入を検討。
- position_sizing:
  - lot_size は現状グローバルな固定値（例: 100）。将来的に銘柄別 lot_map を導入する可能性あり。
- ai/news_nlp.py:
  - 実装は堅牢性（バッチ、リトライ、部分更新）を意図しているが、API 呼び出しや DB 書き込みの最終保存処理は慎重な検証が必要（コードは途中まで収録）。
- 全体: 一部の機能（ExecutionEngine, BrokerClientFactory, SystemMonitor 等）は本 changelog 作成時点のソース断片に依存しており、外部実装（別ファイル）の動作に依存する。

### セキュリティ (Security)
- なし（初期リリース時点で既知のセキュリティ修正はなし）。

---

今後のリリースでは、実運用でのフィードバックに基づく改善点（例: price フォールバック、銘柄別 lot_size、AI モデルの安定性向上、より詳しい監視ログなど）を CHANGELOG に追加してください。