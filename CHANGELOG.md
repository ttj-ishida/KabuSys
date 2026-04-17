# Changelog

すべての注記は Keep a Changelog のフォーマットに準拠しています。  

最新リリースはセマンティックバージョニングに従っています。

## [0.1.0] - 2026-04-17

### 追加
- 全体
  - 初期公開リリース。自動売買システム KabuSys のコア機能群を追加。
- 起動スクリプト
  - run_monitoring.py を追加。SystemMonitor のポーリングループを起動するスクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）を検出すると安全にループを終了。
    - 監視処理は環境（KABUSYS_ENV）にかかわらず本番の sqlite_path を使用して初期化。
  - run_execution.py を追加。ExecutionEngine を起動するスクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite DB を使用して本番 DB と分離。
    - BrokerClientFactory を利用してブローカークライアントを生成。
    - エンジンは別スレッドで起動し、停止フラグ（data/stop_requested.flag）で停止可能。
    - 実行用 PID ファイル（data/execution.pid）をサポート。
- 設定管理
  - config.py を追加。
    - .env / .env.local の自動読み込み機能（OS 環境変数の保護、優先順: OS > .env.local > .env）。
    - .env ファイルの堅牢なパーサ実装（export プレフィックス対応、クォート内バックスラッシュエスケープ、インラインコメント扱いの改善）。
    - 必須環境変数未設定時に明示的なエラーを投げる _require() を提供。
    - 各種設定プロパティ（DB パス、PID パス、監視しきい値、PAPER_FILL_MODE のバリデーション等）を提供。
- ポートフォリオ構築
  - portfolio モジュールを追加（純粋関数群、DB 参照なし）。
    - portfolio_builder.py:
      - select_candidates(): スコア降順での銘柄選定、signal_rank によるタイブレーク。
      - calc_equal_weights(), calc_score_weights(): 等配分・スコア加重配分（スコア全て 0 の場合は等配分にフォールバック）。
    - risk_adjustment.py:
      - apply_sector_cap(): セクター集中上限チェック（max_sector_pct）により候補を除外、当日売却予定銘柄を除外してエクスポージャー計算。
      - calc_regime_multiplier(): 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返すユーティリティ。
    - position_sizing.py:
      - calc_position_sizes(): risk_based / equal / score の各配分方式を実装。単元（lot_size）丸め、per-stock 上限・aggregate cap（available_cash）によるスケーリング、cost_buffer による保守的見積りなどを実装。
- リサーチ機能
  - research パッケージを追加（DuckDB を利用）。
    - factor_research.py:
      - calc_momentum(), calc_volatility(), calc_value(): prices_daily / raw_financials を用いた各種ファクター計算（MA200、ATR20、PER/ROE 等）。
      - DuckDB 上のウィンドウ関数を活用した効率的なクエリ実装。
    - feature_exploration.py:
      - calc_forward_returns(): 将来リターン計算（任意ホライズン）を実装。
      - calc_ic(): スピアマン順位相関（IC）計算の実装（ties は平均ランク処理）。
      - factor_summary(), rank(): 基本統計・ランク計算ユーティリティを提供。
- AI / NLP
  - ai/news_nlp.py を追加（OpenAI を用いたニュースのセンチメントスコアリング）。
    - ニュース集約ウィンドウの定義（JST ベース → UTC に変換）。
    - バッチ送信（銘柄最大 20 件 / コール）、最大文字数と記事数でトリムする対策。
    - 再試行戦略（429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ）とレスポンス検証、スコアの ±1.0 クリップ。
    - DuckDB のテーブル（raw_news, news_symbols, ai_scores）を想定した読み書き設計。
- ツール
  - tools/paper_verification_report.py を追加。Paper Trading 用の検証レポート生成スクリプト。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL 判定を出力。
    - コマンドライン引数 (--from, --to, --db) をサポート。
- ユーティリティ
  - utils/process_priority.py を追加。
    - Windows と POSIX(Linux/Mac/FreeBSD) を吸収したプロセス優先度設定（high/normal/low）。
    - set_cpu_affinity() による CPU コアピン留め機能を実装。
    - 権限不足や未サポート環境は警告でスキップし、安全に動作。

### 変更
- run_monitoring / run_execution
  - 起動時にプロセス優先度を "high" に設定するように変更（set_process_priority を最初に呼び出す）。
- DB 接続
  - 監視用テーブルの存在保証のため init_monitoring_db() を起動時に呼び出す（冪等化）。
- 設定読み込み
  - 環境変数自動ロードの挙動をプロジェクトルート検出に基づいて変更（.git または pyproject.toml を探索）。
  - .env の読み込み優先度を明確化（OS 環境変数保護、.env.local は .env を上書き）。

### 修正
- .env パーサの堅牢化
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、コメント判定の誤動作などを修正。
- ポートフォリオ計算の頑健性向上
  - position_sizing の aggregate スケーリングで単元（lot_size）単位の端数処理と残余キャッシュを利用した補正ロジックを強化。
  - calc_score_weights() が全スコア 0 の場合に等金額配分へフォールバックするイシューを改善（警告ログ追加）。
- research モジュール
  - ファクター計算でデータ不足時に None を返す扱いを統一。
  - calc_forward_returns() の horizons バリデーション（正の整数かつ <= 252）を追加。

### 既知の問題
- ai/news_nlp.py は API 周りの実装でエッジケースに慎重な設計を行っているが、実運用では OpenAI のレート制限・コスト・レスポンスフォーマット変化に注意が必要。API キー未設定時は明示的にエラーを発生させる設計。
- position_sizing で price 情報が欠落（0.0）の場合、エクスポージャーやサイズ算定が過少見積りになる可能性がある旨を TODO コメントで記載。将来的にはフォールバック価格の導入を検討。

### セキュリティ
- 環境変数の読み込みは OS 環境変数を保護する設計となっており、.env の自動上書きはデフォルトで無効（.env.local での上書きは可能、ただし OS 環境変数は保護）。

---

今後の予定（例）
- ai/news_nlp の部分的実装の実運用検証およびログ・エラー処理の強化。
- stocks マスタを用いた個別 lot_size 対応（position_sizing の拡張）。
- モニタリング・検証レポートの定期バッチ化（スケジューラ統合）。