# Changelog

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
このファイルはコードベース（初期リリース相当）の内容から推測して作成しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- なし

## [0.1.0] - 2026-03-22
初回リリース。日本株の自動売買・リサーチ・バックテストを行うためのコアモジュール群を追加。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージエントリを追加（src/kabusys/__init__.py）。公開 API として data/strategy/execution/monitoring を露出。
  - バージョン情報: 0.1.0

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機構を実装。
    - 自動ロードはプロジェクトルート（.git または pyproject.toml）を起点に行う（CWD 非依存）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途を想定）。
  - .env パーサ:
    - export キーワード対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い等を考慮した堅牢なパース処理を実装。
  - .env 読み込み: OS 環境変数を保護する protected 機構を実装し、.env と .env.local の優先度（OS > .env.local > .env）を確立。
  - Settings クラスを提供（settings インスタンス経由で利用）。
    - 必須設定の取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）
    - duckdb/sqlite のデフォルトパス（data/kabusys.duckdb, data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL のバリデーションを実装
    - is_live / is_paper / is_dev の判定プロパティを追加

- 戦略 - 特徴量作成 (src/kabusys/strategy/feature_engineering.py)
  - 研究モジュールの生ファクターを統合し features テーブルへ保存する処理を実装（build_features）。
    - 処理フロー: momentum/volatility/value の取得 → ユニバースフィルタ（株価 >= 300円、20日平均売買代金 >= 5億円）→ Zスコア正規化 → ±3 でクリップ → features へ日付単位の置換（トランザクションで原子性確保）。
    - DuckDB を使用した SQL と Python の組合せによる実装。
    - 外れ値対策のため Z スコアを ±3 でクリップ。

- 戦略 - シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - features と ai_scores を統合して銘柄ごとの final_score を計算し、signals テーブルへ書き込む処理を実装（generate_signals）。
    - スコア計算: momentum/value/volatility/liquidity/news の各コンポーネントを算出（シグモイド変換等）。デフォルト重みを実装し、ユーザ渡しの weights を検証・補完・正規化。
    - AI ニューススコアが未登録の場合は中立（0.5）で補完。
    - Bear レジーム判定: ai_scores の regime_score の平均が負（かつサンプル数 >= 3）であれば BUY シグナルを抑制。
    - BUY シグナル閾値デフォルト 0.60。BUY / SELL の日付単位置換（トランザクションで原子性を確保）。
    - SELL（エグジット）判定を実装（ストップロス: -8% 超、スコア低下: final_score < threshold）。
    - 不備時のログ出力（価格欠損時の SELL 判定スキップ、features にない保有銘柄は score=0.0 扱いで SELL 等）。

- リサーチ (src/kabusys/research/)
  - ファクター計算モジュール (factor_research.py)
    - モメンタム (1M/3M/6M, ma200_dev)、ボラティリティ（20日 ATR, atr_pct）、流動性（20日平均売買代金、volume_ratio）、バリュー（per, roe）を DuckDB から計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - ウィンドウ/データ不足時の None 処理、カレンダーバッファ等を考慮。
  - 特徴量探索ユーティリティ (feature_exploration.py)
    - 将来リターン計算（calc_forward_returns、デフォルトホライズン [1,5,21]）を実装。複数ホライズンを単一クエリで取得。
    - スピアマンの rank 相関 IC 計算 (calc_ic) を実装（同順位は平均ランク、データ不足時は None）。
    - factor_summary：各ファクター列の基本統計量（count, mean, std, min, max, median）を計算。
    - rank ユーティリティを提供（同順位の平均ランク処理、浮動小数の丸め対策）。

- バックテスト (src/kabusys/backtest/)
  - シミュレータ (simulator.py)
    - PortfolioSimulator を実装。BUY/SELL の擬似約定、スリッページ・手数料モデル、平均取得単価更新、SELL 時の realized_pnl 計算、日次時価評価（mark_to_market）と DailySnapshot/TradeRecord の記録を提供。
    - SELL を先に処理してから BUY（資金確保のため）。SELL は保有全量をクローズ（部分利確非対応）。
    - ログ警告や価格欠損時の挙動（0 評価やスキップ）を実装。
  - メトリクス (metrics.py)
    - バックテスト評価指標の計算を実装（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）。
    - 数式・年次化の扱い（Sharpe は営業日252日で年次化）、境界条件での 0.0 戻しを実装。
  - エンジン (engine.py)
    - run_backtest を実装。実行フロー:
      1. 本番 DB からインメモリ DuckDB へ必要テーブルをコピー（_build_backtest_conn）。日付フィルタ（start_date - 300日 〜 end_date）でコピーし、本番データを汚さない設計。
      2. 各取引日に対し、前日シグナル約定、positions 書き戻し、時価評価、generate_signals によるシグナル生成、シグナリング → 発注ロジックを繰り返す。
    - 補助関数: _fetch_open_prices / _fetch_close_prices / _write_positions / _read_day_signals を提供。
    - デフォルトパラメータ: initial_cash=10_000_000, slippage_rate=0.001, commission_rate=0.00055, max_position_pct=0.20。
  - public API エクスポート: run_backtest, BacktestResult, DailySnapshot, TradeRecord, BacktestMetrics をパッケージで公開。

- モジュール結合
  - research モジュール側で data.stats.zscore_normalize を利用する設計。strategy と backtest 間の役割分担を明確化（generate_signals は DB を介して信号を保存し、バックテストはそれを読み取る）。

### 修正 (Changed)
- 初回リリースのため該当なし（本CHANGELOGはコード現物からの初期機能記載）。

### 修正済みのバグ (Fixed)
- 初回リリースのため該当なし。

### 既知の制限・未実装 (Notes / Known issues)
- signal_generator のエグジット条件について未実装項目あり（ドキュメント参照）:
  - トレーリングストップ（peak_price に基づく -10%）は未実装（positions テーブルに peak_price / entry_date が必要）。
  - 時間決済（保有 60 営業日超過）も未実装。
- calc_value は PBR・配当利回りを未実装。PER は EPS が NULL/0 の場合 None を返す。
- generate_signals:
  - AI スコアが存在しない銘柄はニューススコアを中立扱い（0.5）にする設計。そのため AI データがないと挙動が保守的になる。
  - weight 辞書の不正値（未知キー、非数値、負値、NaN/Inf）は無視され、デフォルト重みへフォールバックまたは再スケールされる。
- .env 自動ロードはプロジェクトルートが特定できない場合はスキップされる。
- バックテストのコピーロジックは例外を警告ログでスキップする実装となっており、部分的なデータ欠損があっても可能な限り実行する設計。
- 一部の関数は外部モジュール（kabusys.data.schema, kabusys.data.stats, kabusys.data.calendar_management など）に依存しており、その実装が必要。

### セキュリティ (Security)
- なし（このリリースでは特にセキュリティ修正は含まれない）。

---

注: 本CHANGELOG は提供されたソースコードからの推測に基づいて作成しています。実際のリリースノート運用では、コミット履歴やリリース日付、影響範囲の確認を行ってください。