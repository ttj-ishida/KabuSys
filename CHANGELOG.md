Keep a Changelog
================

すべての重要な変更点をこのファイルに記録します。  
このプロジェクトは SemVer を採用しています。  

[0.1.0] - 2026-03-22
-------------------

初回リリース — 日本株自動売買システムのコア機能を実装しました。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。バージョンを src/kabusys/__init__.py にて "0.1.0" として定義。
  - パッケージ公開 API（__all__）に data / strategy / execution / monitoring を想定。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダを実装。
    - プロジェクトルートの探索は __file__ を起点に .git または pyproject.toml を検出。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - 読み込み時に OS 環境変数（protected）を上書きしない保護機能を実装。
  - .env パーサ実装（コメント、export プレフィックス、クォート・エスケープ対応、インラインコメントの取り扱いなど）。
  - 必須環境変数取得のユーティリティ _require と、Settings クラスを提供。
    - 主要設定: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL。
    - env / log_level のバリデーション（許容値チェック）を実装。
    - Settings インスタンス settings をエクスポート。

- 戦略: 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - research モジュールから生ファクターを取得し、ユニバースフィルタ（最低株価・平均売買代金）を適用。
  - 指定日基準で Z スコア正規化（指定カラム）と ±3 でのクリッピング。
  - features テーブルへの日付単位の置換（トランザクション + バルク挿入）で冪等性を保証。
  - DuckDB を用いた遅延クエリや欠損データへの耐性（最新価格参照のための MAX(date) JOIN）。

- 戦略: シグナル生成（src/kabusys/strategy/signal_generator.py）
  - 正規化済みの features と ai_scores を統合して final_score を計算。
  - コンポーネントスコア: momentum / value / volatility / liquidity / news（AI）。
  - スコア合成は重み付け（デフォルト値を実装）、ユーザー重みのバリデーションと正規化を実装。
  - Bear レジーム判定（ai_scores の regime_score による平均が負かつサンプル十分性で判定）により BUY を抑制。
  - BUY シグナル: 閾値（デフォルト 0.60）を超える銘柄をランク付けして出力（Bear 時は抑制）。
  - SELL シグナル（エグジット条件）:
    - ストップロス（終値/avg_price - 1 < -8%）、
    - final_score の閾値未満（score_drop）。
    - 価格欠損・保有情報欠損時の安全処理とログ記録。
  - signals テーブルへの日付単位置換（トランザクション・ROLLBACK 保護）で冪等性を保証。
  - 公開関数: generate_signals(conn, target_date, threshold, weights) → 挿入したシグナル数を返す。

- research（src/kabusys/research/*）
  - ファクター計算群（src/kabusys/research/factor_research.py）
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日MA乖離）を DuckDB SQL で算出。データ不足時は None を返す。
    - calc_volatility: 20日 ATR（true_range を厳密に扱う）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を算出。
    - calc_value: raw_financials から最新財務データ（target_date 以前）を取得し PER / ROE を算出（EPS が無効な場合は PER を None）。
  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。サンプル不足時は None。
    - factor_summary: 各ファクターカラムの count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランクで扱うランク関数（丸めにより ties の誤検出を防止）。
  - research パッケージは外部ライブラリに依存せず（標準ライブラリ + DuckDB）実装。

- backtest（src/kabusys/backtest/*）
  - バックテストのコア実装を追加。
  - simulator（src/kabusys/backtest/simulator.py）
    - PortfolioSimulator: メモリ内でポートフォリオ・コスト基準・履歴・約定記録を管理。
    - 約定ロジック: SELL を先に処理し全量クローズ、BUY は配分に基づいて株数を取得。スリッページ・手数料を反映。
    - mark_to_market で終値による時価評価と DailySnapshot 記録（終値欠損時の警告）。
    - TradeRecord / DailySnapshot のデータクラスを提供。
  - メトリクス（src/kabusys/backtest/metrics.py）
    - CAGR, Sharpe Ratio（無リスク=0）、Max Drawdown、勝率、Payoff Ratio、総クローズトレード数を計算。
    - calc_metrics() により一括取得。
  - エンジン（src/kabusys/backtest/engine.py）
    - run_backtest(conn, start_date, end_date, ...) を実装。
      - 本番 DuckDB から必要テーブルをフィルタして in-memory DuckDB にコピー（signals/positions を汚染しない）。
      - 日次ループ: 前日シグナルを始値で約定 → positions を書き戻し（generate_signals の SELL 判定のため）→ 終値で時価評価 → generate_signals 実行 → ポジションサイジング → 次日の発注リスト組成。
      - デフォルトパラメータ: initial_cash=10_000_000, slippage_rate=0.001, commission_rate=0.00055, max_position_pct=0.20。
    - DB コピー処理は失敗時にログを出してスキップする堅牢化。

- API エクスポート
  - 各モジュールの公開関数/クラスをパッケージレベルにエクスポート（例: build_features, generate_signals, run_backtest, BacktestResult, DailySnapshot, TradeRecord, BacktestMetrics, など）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境変数自動ロードで OS 環境変数を保護する protected 設定を追加（.env による上書きを防止）。

注意・設計上のポイント
- DuckDB を中心に SQL ベースでファクター計算・シグナル生成を実装。外部 API や pandas 等の依存を最小化。
- ルックアヘッドバイアス回避のため、すべての処理は target_date 時点までのデータのみを参照する方針。
- テーブル書き込みは日付単位の置換（DELETE + INSERT）をトランザクションで行い冪等性を確保。例外時は ROLLBACK を試行し、失敗をログ。
- 欠損データ・データ不足に対する安全処理（None、警告ログ、補完ルール）を多用し、本番運用での破綻を低減。

今後の予定（例）
- features に含める追加ファクター（PBR、配当利回り等）の実装。
- positions テーブルの拡張（peak_price / entry_date 等）によりトレーリングストップや時間決済の実装。
- execution 層の実装（kabu ステーション連携）およびモニタリング（Slack 通知等）の統合。

---