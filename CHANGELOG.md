CHANGELOG
=========

すべての重要な変更点を記録します。本ドキュメントは「Keep a Changelog」の形式に準拠しています。

注意: コードベースから推測して作成した初期のリリースノートです。実装上の振る舞いや未実装の仕様はソース内のドキュメント（コメント）に基づき記載しています。

[0.1.0] - 2026-03-22
-------------------

Added
- 基本パッケージ構成を追加
  - パッケージ: kabusys（src/kabusys）
  - エントリポイントバージョン: 0.1.0（src/kabusys/__init__.py）
  - public API: data, strategy, execution, monitoring を __all__ に公開

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local ファイルおよび OS 環境変数から設定を自動ロード
  - プロジェクトルート検出: __file__ を起点に .git または pyproject.toml を探索して自動ロードする実装
  - .env パーサの強化:
    - export KEY=val 形式対応
    - シングル・ダブルクォート内のバックスラッシュエスケープ処理対応
    - クォートなしのインラインコメント処理（直前が空白/タブの場合のみコメントと認識）
    - 無効行のスキップ
  - 上書き制御: .env と .env.local の読み込み順（OS 環境変数 > .env.local > .env）と protected キー保護
  - 自動ロード無効化オプション: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - Settings クラス:
    - JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID などの必須値取得（未設定時は ValueError を送出）
    - KABUSYS_ENV（development|paper_trading|live）と LOG_LEVEL の妥当性チェック
    - デフォルト値: KABUSYS_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH など

- 研究（research）モジュール（src/kabusys/research/）
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_dev を DuckDB 上で計算
    - calc_volatility: 20日 ATR（atr_20）/ atr_pct / avg_turnover / volume_ratio を計算（true_range の NULL 伝播を制御）
    - calc_value: raw_financials から最新の財務データを取得して PER/ROE を計算
    - DuckDB のウィンドウ関数や行数チェックによりデータ不足時は None を返す設計
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得
    - calc_ic: スピアマンのランク相関（IC）を計算（有効サンプル数 < 3 の場合は None）
    - factor_summary: 各ファクター列について count/mean/std/min/max/median を算出
    - rank: 同順位は平均ランクを採る実装（丸めによる ties 対応）

  - research パッケージのエクスポート: calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - research 側で算出した raw factor を統合・正規化して features テーブルへ upsert
  - ユニバースフィルタ実装:
    - 最低株価: 300 円
    - 20日平均売買代金 >= 5 億円
  - 正規化: 指定カラムを z-score 正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ
  - DuckDB トランザクションによる日付単位置換（DELETE→INSERT の原子性を確保）
  - ロギングとエラーハンドリング（ROLLBACK に失敗した場合の警告）

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - features と ai_scores を統合して final_score を計算
  - component スコア計算:
    - momentum, value, volatility, liquidity, news（AI）の重み付け合算
    - z-score を sigmoid で [0,1] に変換
    - PER に基づく value スコアの定義（PER=20 -> 0.5 など）
  - デフォルト重みと閾値:
    - デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10
    - BUY 閾値: 0.60
    - weights の検証・補完・再スケーリング処理（未知キーや無効値は無視）
  - Bear レジーム判定: ai_scores の regime_score の平均が負であれば BUY を抑制（サンプル数閾値あり）
  - SELL（エグジット）ルール:
    - ストップロス（終値 / avg_price - 1 < -8%）
    - final_score が threshold 未満（score_drop）
    - 保有銘柄の価格欠損時の判定スキップとログ出力
  - signals テーブルへの日付単位置換（トランザクション）およびログ出力

- バックテストフレームワーク（src/kabusys/backtest/）
  - simulator:
    - PortfolioSimulator によるメモリ内での約定処理（スリッページ・手数料モデル）
    - BUY は割当金額に基づいて購入（shares は floor）、手数料考慮で再計算
    - SELL は保有全量をクローズ（部分利確/部分損切りは未対応）
    - mark_to_market による DailySnapshot 記録（終値欠損時は 0 評価で警告）
    - TradeRecord の生成（realized_pnl 計算は SELL 時）
  - metrics:
    - バックテスト評価指標の計算: CAGR, Sharpe Ratio（無リスク=0）, Max Drawdown, Win rate, Payoff ratio, total_trades
    - 実装上の注意: 標本数不足やゼロ除算に対する保護（不足時は 0.0 を返す）
  - engine:
    - 本番 DB からインメモリ DuckDB へコピーして isolate されたバックテスト用接続を構築（signals/positions を汚染しない）
    - 日次ループ: 前日シグナル約定 → positions 書き戻し → 時価評価 → generate_signals 呼び出し → 発注リスト作成
    - get_trading_days を用いた営業日列挙、open/close 価格フェッチユーティリティを実装
    - positions の再書き込みは generate_signals の SELL 判定に依存するため明示的に行う
    - run_backtest の公開 API による一括実行（初期資金、スリッページ、手数料、最大ポジション比率パラメータあり）

- パッケージエクスポートの整備
  - strategy の build_features / generate_signals を __all__ で公開
  - backtest の run_backtest, BacktestResult, DailySnapshot, TradeRecord, BacktestMetrics を __all__ で公開

Changed
- （初期リリース）コードベースのファイル分割とドキュメントコメント整備により、各モジュールの役割／仕様が明確化

Fixed
- （該当なし）初期リリースのため修正履歴は無し

Notes / Known limitations
- シグナル生成・売買戦略
  - 一部エグジット条件は未実装（コメントに記載）:
    - トレーリングストップ（peak_price / entry_date を positions に保持する必要あり）
    - 時間決済（保有 60 営業日超過）
  - BUY のサイジングはバックテスト側で決定されるため、本番 execution 層との連携が別途必要
- research モジュールは外部ライブラリ（pandas 等）に依存しない実装を目指しているが、大量データでの操作は DuckDB に依存
- execution パッケージは placeholder（src/kabusys/execution/__init__.py が存在）で、実際の発注 API 連携の実装は別途必要
- features / signals / positions 等のスキーマは data.schema 側に依存（本 CHANGELOG は schema の詳細を含まず、実装を参照）
- バックテストエンジンの一部処理はファイル末尾で切れている（コードの継続部分がある想定）

開発上のメモ（実装からの推測）
- 多くのモジュールは DuckDB を主なデータストアとして想定している（高速な列指向クエリを利用）
- 設計方針としてルックアヘッドバイアス防止を重視し、target_date 時点までのデータのみを使用する仕様が徹底されている
- トランザクション（BEGIN/COMMIT/ROLLBACK）とログ出力を使った冪等性・堅牢性の確保が図られている

ライセンスやその他メタ情報はリポジトリのトップレベル（pyproject.toml 等）を参照してください。必要であれば、次リリース向けの CHANGELOG 下書き（Unreleased の追加、既知の改善点や TODO）も作成できます。