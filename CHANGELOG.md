Keep a Changelog
=================
すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog のガイドラインに従って変更履歴を管理しています。

フォーマット:
- すべてのバージョンは日付付きで記載しています。
- 主要な変更点はカテゴリ別（Added / Changed / Fixed / Security / その他）にまとめています。

[0.1.0] - 2026-03-22
--------------------

Added
- パッケージ初期公開: kabusys 0.1.0
  - トップレベル:
    - kabusys.__version__ = "0.1.0"
    - __all__ に主要サブパッケージ（data, strategy, execution, monitoring）を公開
- 設定管理モジュール (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを提供
  - 自動ロード機能:
    - プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動読み込み
    - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能
    - .env.local は .env をオーバーライド（ただし OS 環境変数は保護）
  - .env パーサを実装:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント無視を適切に処理
    - クォートなしの場合は '#' の直前が空白またはタブのときのみコメント扱い
  - 環境変数の必須チェック用 _require()、環境値検証（KABUSYS_ENV, LOG_LEVEL）を実装
  - 各種設定プロパティを提供（J-Quants / kabu API / Slack / DB パス等）
- 戦略モジュール (kabusys.strategy)
  - feature_engineering.build_features(conn, target_date)
    - research 側で計算された raw factor を取得し正規化（Zスコア）して features テーブルに UPSERT（日付単位で置換）
    - ユニバースフィルタ（最低株価・平均売買代金）を適用
    - Z スコアを ±3 でクリップして外れ値影響を抑制
    - トランザクションで原子性を担保し、失敗時はロールバックを試行
  - signal_generator.generate_signals(conn, target_date, threshold, weights)
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算
    - シグナル統合ロジック（重み付け、重みの検証と正規化）
    - Sigmoid 変換・欠損補完（None を中立 0.5 に補完）
    - Bear レジーム判定（ai_scores の regime_score 平均が負 → BUY 抑制）
    - BUY/SELL シグナル生成、signals テーブルへ日付単位の置換（トランザクション）
    - SELL 優先ポリシー（SELL 対象は BUY から除外）
- Research モジュール (kabusys.research)
  - factor_research:
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、MA200 乖離率を計算
    - calc_volatility(conn, target_date): ATR20 / 相対 ATR、平均売買代金、出来高比率を計算
    - calc_value(conn, target_date): raw_financials から最新財務を取得して PER / ROE を計算
  - feature_exploration:
    - calc_forward_returns(conn, target_date, horizons): 指定ホライズンの将来リターンを一度のクエリで取得
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマン IC（ランク相関）を実装
    - factor_summary(records, columns): count/mean/std/min/max/median を計算
    - rank(values): 平均ランク（同順位を平均ランク）でのランク付け（丸め処理で ties の扱いを安定化）
  - research パッケージは上記ユーティリティを外部公開（__all__）
- バックテストフレームワーク (kabusys.backtest)
  - simulator:
    - PortfolioSimulator: BUY/SELL の擬似約定ロジック、スリッページ・手数料考慮、全量クローズの実装
    - DailySnapshot / TradeRecord データクラスを提供
    - execute_orders: SELL を先に処理 → BUY（資金確保のため）
    - mark_to_market: 終値評価、価格欠損時に WARNING を出力して 0 評価
  - metrics:
    - calc_metrics(history, trades) と各種内部関数（CAGR, Sharpe, MaxDrawdown, WinRate, PayoffRatio）
    - 入力に対する堅牢なゼロ除算・データ不足ガード実装（データ不足時は 0.0 返却等）
  - engine:
    - run_backtest(conn, start_date, end_date, ...): 本番 DB からインメモリ DuckDB へデータをコピーして日次シミュレーションを実行
    - _build_backtest_conn: 必要なテーブル（prices_daily, features, ai_scores, market_regime, market_calendar 等）を日付範囲でコピー
    - 日次ループ: 約定（open）、positions 書き戻し、時価評価、generate_signals 呼び出し、ポジションサイジング・注文作成を実施
    - 公開 API として run_backtest / BacktestResult を提供
- DB/SQL 周りの堅牢化
  - トランザクションを用いた日付単位の置換パターン（DELETE → INSERT）を一貫して採用
  - INSERT 実行中の例外発生時に明示的に ROLLBACK を試行し、失敗時は WARN ログ出力
- ロギングと警告
  - 重要な異常ケース（価格欠損、weights の無効値、データ不足など）で適切に logger.warning()/logger.info()/logger.debug() を出力

Changed
- 設計方針の表明:
  - ルックアヘッドバイアスを防ぐため target_date 時点のデータのみを使用する方針を各モジュールで徹底
  - 発注 API / 本番口座に直接アクセスしない（DuckDB の prices_daily / raw_financials 等のみ参照）
- 重み（weights）処理の挙動:
  - ユーザ指定 weights は既定のキーのみ受け付け、非数値・負値・NaN/Inf を無効化してフォールバック
  - 合計が 1.0 でなければスケーリングして合計 1.0 に正規化、合計 <= 0 の場合はデフォルトに戻す
- 欠損データ対策:
  - features ない銘柄は final_score を 0.0 と見なして SELL の判定対象とする（警告ログを出力）
  - AI スコア未登録時はニューススコアを中立（0.5）で補完
  - 各種計算でデータ不足（行数不足・NULL）を検出した場合は None を返すことで下流処理で中立補完する設計

Fixed
- DB 書込失敗時の安全策:
  - transactions 内での例外発生時にロールバックを行い、ロールバック失敗時には警告ログを出すことで不整合リスクを低減
- 入力検証の追加:
  - calc_forward_returns の horizons に対する型チェックと範囲チェック（1〜252）を追加
  - generate_signals の weights チェック強化（無効なエントリのスキップ）
- 数値処理の安定化:
  - NaN / Inf / 非有限値を明示的に扱う（評価除外、ログ出力、None 返却など）
  - rank() で round(..., 12) を用いて浮動小数点丸め誤差による ties の検出漏れを防止

Security
- 環境変数の自動読み込み時に OS 環境変数を保護（.env が既存の OS 環境を意図せず上書きしない）
- .env 読み込み失敗は警告で扱い、例外を送出しない（サービス起動の妨げにならない）

開発者向けメモ / 互換性
- public API:
  - strategy: build_features, generate_signals をエクスポート
  - research: calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank をエクスポート
  - backtest: run_backtest, BacktestResult, DailySnapshot, TradeRecord, BacktestMetrics をエクスポート
- 環境変数:
  - いくつかの必須環境変数は Settings プロパティ経由で取得（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。未設定時は ValueError を送出。
  - DB パス (DUCKDB_PATH, SQLITE_PATH)、KABUSYS_ENV、LOG_LEVEL 等にデフォルト値を用意
- DB スキーマ期待値:
  - 多くの関数は prices_daily, features, ai_scores, positions, raw_financials, market_calendar 等のテーブルを前提とする。init_schema（kabusys.data.schema）での初期化やスキーマ互換性に注意してください。
- テスト / CI:
  - 自動 .env 読み込みはテスト時に KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能

今後の予定（例）
- features に保存するカラムや value ファクターの拡張（PBR、配当利回り等）
- position テーブルに peak_price / entry_date を追加してトレーリングストップや時間決済を実装
- execution レイヤー（実際の発注インタフェース）との統合（現状は分離）

注記
- この CHANGELOG は提示されたコードベースの内容から機能・修正点を推測してまとめたものです。実際の変更履歴やリリースノートと差異がある場合があります。