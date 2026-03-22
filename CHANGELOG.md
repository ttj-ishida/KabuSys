Keep a Changelog
================

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトはまだ初期バージョンのため、主に「Added（追加）」項目で構成されています。

[Unreleased]: https://example.com/kabusys/compare/0.1.0...HEAD

0.1.0 - Initial release
-----------------------

リリース: 初回公開（初期機能セット）

Added
- パッケージ初期化
  - kabusys パッケージの __version__ を 0.1.0 に設定。主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索（配布後の動作を考慮）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途）。
    - OS 環境変数は protected キーとして扱い .env/.env.local による上書きを防止。
  - .env パーサーの強化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープに対応。
    - インラインコメントの扱いやクォートなし時のコメント判定を実装。
  - 必須環境変数を取得する _require を提供（未設定時は ValueError）。
  - settings オブジェクトで主要設定をプロパティとして公開:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト localhost:18080/kabusapi）
    - Slack 関連: SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DB パス: DUCKDB_PATH（data/kabusys.duckdb）, SQLITE_PATH（data/monitoring.db）
    - システム環境: KABUSYS_ENV（development/paper_trading/live の検証）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev ヘルパー

- リサーチ（kabusys.research）
  - ファクター計算ユーティリティを提供:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離率（データ不足時に None を返す）。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比率（volume_ratio）。
    - calc_value: latest raw_financials と当日の株価から PER / ROE を計算（EPS が 0/欠損時は None）。
  - 研究用補助:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。
    - calc_ic: スピアマンランク相関（IC）計算（同値は平均ランクで処理、サンプル数 < 3 で None を返す）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランクを与えるランク関数（丸めで ties 検出の安定化）。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research モジュールの生ファクターを組み合わせて features テーブルを作成する build_features を実装。
    - ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5 億円）。
    - 数値ファクターは Z スコアで正規化（kabusys.data.stats.zscore_normalize 使用）し ±3 でクリップして外れ値影響を抑制。
    - target_date のデータのみを用いてルックアヘッドを回避。
    - 日付単位で DELETE → INSERT のトランザクション置換（原子性確保）。失敗時に ROLLBACK を試行し失敗ログを出力。

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して最終スコア（final_score）を計算し signals テーブルへ書き込む generate_signals を実装。
    - コンポーネントスコア: momentum / value / volatility / liquidity / news（AI）。
    - スコア変換:
      - Z スコア（±3 クリップ済）をシグモイドで [0,1] に変換。
      - PER は逆数ベースの評価（per=20 -> 0.5、per→0 -> 1.0）。
      - 欠損コンポーネントは中立値 0.5 で補完（欠損銘柄の不当な降格回避）。
    - 重み付け:
      - デフォルト重みを定義（momentum:0.40, value:0.20, volatility:0.15, liquidity:0.15, news:0.10）。
      - 引数 weights を受け付けるが不正値は無視・警告、合計が 1.0 でない場合は再スケール、合計 <=0 の場合はデフォルトにフォールバック。
    - Bear レジーム判定: ai_scores の regime_score 平均が負のとき Bear（サンプル数不足（<3）なら Bear とは見なさない）。
      - Bear レジーム時は BUY シグナルを抑制。
    - SELL（エグジット）判定:
      - ストップロス（終値 / avg_price - 1 < -8%）が最優先。
      - final_score が threshold 未満（デフォルト threshold=0.60）で SELL。
      - positions や価格が欠損する場合の安全なスキップ／警告ロギング。
    - SELL を BUY より優先し、signals テーブルへ日付単位の置換（トランザクション処理）。ROLLBACK 時の警告ログあり。
    - features が空の場合は BUY 生成をスキップし、SELL 判定のみ行う。

- バックテストフレームワーク（kabusys.backtest）
  - ポートフォリオシミュレータ（PortfolioSimulator）を実装:
    - スリッページ・手数料モデルを適用して擬似約定を行う（BUY は始値*(1+slippage)、SELL は始値*(1-slippage)）。
    - BUY は資金に合わせた株数計算、手数料考慮の再計算処理を含む。
    - SELL は保有全量クローズ（部分利確/部分損切りは未対応）。
    - mark_to_market で終値評価を行い日次スナップショット（DailySnapshot）を保持。終値欠損時は 0 として評価し警告。
    - TradeRecord を記録（SELL 時は realized_pnl を含む）。
  - バックテストエンジン（run_backtest）を実装:
    - 本番 DB から backtest 用の in-memory DuckDB に必要テーブルをコピー（prices_daily, features, ai_scores, market_regime は日付範囲で、market_calendar は全件コピーを試みる）。
    - コピー範囲は start_date - 300日 から end_date（研究ロジック再現のためのバッファ）。
    - 日次ループ: 前日シグナルを当日始値で約定 → positions をバックテスト DB に書き戻し（generate_signals の SELL 判定に使用）→ 終値で時価評価 → generate_signals 実行 → signals を読み取り発注（サイジング）→ 次日へ。
    - helper 関数: _fetch_open_prices/_fetch_close_prices/_write_positions/_read_day_signals を提供。
  - バックテストメトリクス（kabusys.backtest.metrics）:
    - CAGR, Sharpe Ratio（無リスク=0、252営業日換算）, Max Drawdown, Win Rate, Payoff Ratio, Total Trades を計算する calc_metrics を実装。
    - 各指標の実装詳細・境界条件（データ不足時の 0.0 フォールバックなど）を明確化。

Security / Safeguards
- DB 書き込み処理は可能な限りトランザクション（BEGIN/COMMIT/ROLLBACK）で保護し、ROLLBACK の失敗はログで通知。
- .env 読み込みでは OS 環境変数を保護（protected set）して意図しない上書きを防ぐ。
- 入力パラメータの検証を行い、不正な weights や horizons は警告または例外で保護。

Known issues / Not implemented
- signal_generator のエグジット条件について、コメントで以下が未実装と明示:
  - トレーリングストップ（直近最高値から -10%）
  - 時間決済（保有 60 営業日超過）
  これらは positions テーブルに peak_price / entry_date が必要で、将来の拡張対象。
- factor_research の PBR / 配当利回りは現バージョンでは未実装。
- PortfolioSimulator の BUY は部分利確・部分損切りに未対応（常に全量買い/全量売りの単純モデル）。
- run_backtest のテーブルコピーは失敗時に警告を出してスキップするが、コピー失敗による再現性問題に注意。

API（主要公開関数）
- kabusys.config.settings — 環境設定オブジェクト
- kabusys.strategy.build_features(conn, target_date) -> int
- kabusys.strategy.generate_signals(conn, target_date, threshold=0.60, weights=None) -> int
- kabusys.research.calc_momentum / calc_volatility / calc_value
- kabusys.research.calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.backtest.run_backtest(conn, start_date, end_date, ...)
- kabusys.backtest.simulator.PortfolioSimulator / DailySnapshot / TradeRecord
- kabusys.backtest.metrics.calc_metrics / BacktestMetrics

その他
- ロギングは各モジュールで適切に行われる（情報ログ・警告・デバッグ）。
- 依存は最小限に抑え、研究用モジュールは標準ライブラリ中心で実装（外部依存を避ける方針）。

---

今後の予定（例）
- エグジット条件の追加実装（トレーリングストップ、時間決済）
- PBR / 配当利回り等のバリューファクター拡張
- 部分利確・部分損切りのサポート、より現実に近い約定モデルの導入
- 単体テストと統合テストの整備（.env 自動ロードのテスト可能性向上）

（注）この CHANGELOG は提供されたソースコードから機能・実装方針を推測して作成しています。実際のリリースノートにあたっては、コミット履歴やリリース日付、実装差分を確認して適宜更新してください。