CHANGELOG
=========

すべての注目すべき変更点をここに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

[Unreleased]: https://example.com/compare/v0.1.0...HEAD

新規リリース
------------

### [0.1.0] - 2026-03-22

初回公開リリース。日本株自動売買フレームワーク「KabuSys」の基本機能を実装しました。
以下はソースコードから推測してまとめた主な追加点と設計上の特徴です。

Added
- パッケージ基礎
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - モジュール構成: data, strategy, execution, monitoring 等の公開 API を準備。

- 環境設定管理 (kabusys.config)
  - .env および環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルート判定: .git または pyproject.toml を起点に探索（CWD に依存しない）。
  - .env の柔軟なパース:
    - export KEY=val 形式対応、シングル/ダブルクォート内のエスケープ対応、インラインコメント処理。
    - コメント・空行を無視。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env と .env.local の優先順（OS 環境変数 > .env.local > .env）。.env.local は上書き可能。
  - 必須環境変数取得用の _require() と Settings クラスを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID など）。
  - KABUSYS_ENV / LOG_LEVEL の検証（許容値のバリデーション）。
  - データベース既定パス: DUCKDB_PATH / SQLITE_PATH。

- 研究用ファクター計算 (kabusys.research.factor_research)
  - モメンタム (calc_momentum)
    - mom_1m / mom_3m / mom_6m、MA200乖離（ma200_dev）を計算。過去データ不足時は None を返す。
  - ボラティリティ・流動性 (calc_volatility)
    - ATR（20日平均 true range）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - true_range は high/low/prev_close の欠損を考慮し、カウント条件を厳密に扱う。
  - バリュー (calc_value)
    - raw_financials から直近の財務データを取得し PER / ROE を計算。EPS 欠損やゼロは考慮。
  - 研究ユーティリティ群の提供（kabusys.research.__init__ でエクスポート）。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features(conn, target_date)
    - research モジュールで計算した生ファクターをマージ・ユニバースフィルタ・Z スコア正規化し、features テーブルへ日付単位で置換（冪等）。
    - ユニバースフィルタ: 株価 >= 300 円、20日平均売買代金 >= 5 億円。
    - 正規化対象カラムと ±3 でクリップするロバスト化。
    - トランザクション（BEGIN / DELETE / INSERT / COMMIT）で原子性を保証。例外時は ROLLBACK（失敗時は警告ログ）。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals(conn, target_date, threshold=0.60, weights=None)
    - features と ai_scores を統合して各銘柄の final_score を算出し、BUY/SELL シグナルを生成して signals テーブルへ日付単位で置換（冪等）。
    - コンポーネントスコア: momentum, value, volatility, liquidity, news（AI スコア）。
    - 重み付けロジック: デフォルト重みを用意し、ユーザ指定 weights を検証して正規化。無効値や未知キーは無視。
    - Sigmoid / Z スコアを用いたスコア変換、欠損コンポーネントは中立値 0.5 で補完。
    - Bear レジーム判定: ai_scores の regime_score 平均が負の場合に BUY を抑制（サンプル数が閾値未満なら Bear と見なさない）。
    - SELL（エグジット）判定:
      - ストップロス: (close / avg_price - 1) <= -8% の場合即時 SELL（最優先）。
      - スコア低下: final_score が threshold 未満。
      - 保有銘柄で価格欠損時は判定スキップ（誤クローズ防止のためログ出力）。
    - INSERT はトランザクションで行い、例外時の ROLLBACK をハンドリング。

- バックテストフレームワーク (kabusys.backtest)
  - ポートフォリオシミュレータ (PortfolioSimulator)
    - 注文約定ロジック（execute_orders）: SELL を先に、BUY は資金に応じて株数を計算（手数料とスリッページを考慮）。
    - BUY は全て約定単元（shares = floor(alloc / entry_price)）、部分利確未対応。
    - SELL は保有全量をクローズ。約定価格・手数料・realized_pnl を記録。
    - mark_to_market で終値ベースの評価額を計算し DailySnapshot を履歴に記録。終値欠損は 0 で評価して警告ログ。
    - trade / history のデータクラス定義 (DailySnapshot, TradeRecord)。
  - バックテストエンジン (run_backtest)
    - 本番 DB から必要テーブルをフィルタしてインメモリ DuckDB へコピー（signals / positions を汚さない）。
    - 日次ループ: 前日シグナルを当日始値で約定 → positions 書き戻し → 終値で評価 → generate_signals 呼び出し → 発注リスト組成。
    - スリッページ率 / 手数料率 / ポジション上限等をパラメータ化。
    - get_trading_days（market_calendar 利用）を使って営業日のみにループ。
  - 評価指標計算 (kabusys.backtest.metrics)
    - calc_metrics: CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades を計算。
    - 内部実装:
      - CAGR: 暦日ベースで年数を計算（days / 365）。
      - Sharpe: リターンを年次化（252 営業日）して算出。
      - Max Drawdown: ピークからの最大下落率を計算。
      - Win Rate / Payoff Ratio: SELL 約定の realized_pnl を利用。

- 研究補助モジュール (kabusys.research.feature_exploration)
  - 前方リターン計算 (calc_forward_returns): デフォルト horizons=[1,5,21]、レンジ制限・SQL による一括取得。
  - IC（スピアマン相関）計算 (calc_ic): ランク変換（rank）、ties の平均ランク処理、最小サンプル数チェック。
  - factor_summary: count/mean/std/min/max/median を算出（None を除外）。
  - 独立した rank 関数: 小数丸め（round(..., 12)）で ties を安定して検出・処理。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Security
- 環境変数読み込み時に OS 環境変数を protected として .env による上書きを制御（意図しない上書きを防止）。

設計上の注意点 / 未実装・将来対応予定（コード中のコメントから推測）
- トレーリングストップや時間決済（60 営業日超過）のエグジット条件はコメントで未実装と明示。
- positions テーブルの peak_price / entry_date が必要な機能は未実装。
- 一部のユーティリティ（例: kabusys.data.stats.zscore_normalize、schema 初期化関数等）は外部ファイルで提供される想定（本リリースのコードから参照実装あり）。
- 外部依存は最小限（DuckDB を使用）。研究モジュールは pandas 等に依存しない純粋な標準ライブラリ / DuckDB ベース設計。

開発者向けメモ
- トランザクション（BEGIN/COMMIT/ROLLBACK）を各所で利用しており、DB 操作の原子性を重視しています。例外時のロギングが用意されていますが、ROLLBACK の失敗ログもキャッチされます。
- generate_signals / build_features は target_date における時点データのみを使用するよう設計されており、ルックアヘッドバイアス対策が取られています。
- 設定は Settings クラス経由で取得する想定。テスト環境等で自動 .env ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

ライセンス、貢献方法等についてはリポジトリのトップレベルドキュメントを参照してください。