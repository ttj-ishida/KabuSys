# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

履歴は推定に基づき、ソースコードから実装内容を抽出して記載しています。

## [Unreleased]

（現在なし）

## [0.1.0] - 2026-03-22

初回リリース。日本株自動売買システム「KabuSys」のコア機能群を実装・公開。

### Added
- パッケージ基本情報
  - src/kabusys/__init__.py: パッケージ名称・バージョン（0.1.0）と主要サブパッケージのエクスポート定義。

- 環境設定・ロード機能
  - src/kabusys/config.py:
    - .env / .env.local からの自動ロード機能（プロジェクトルートを .git または pyproject.toml から発見）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
    - .env パーサ実装（export 形式、シングル/ダブルクォート、エスケープ、インラインコメントの扱いをサポート）。
    - OS 環境変数を保護する protected オプション（.env.local は既存 OS 環境を保護しつつ上書き可能）。
    - 必須環境変数チェック（_require）と Settings クラス:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等のプロパティ。
      - DB ファイルパス取得（DUCKDB_PATH, SQLITE_PATH）。
      - 環境種別（KABUSYS_ENV）とログレベル（LOG_LEVEL）の検証・ユーティリティ（is_live / is_paper / is_dev）。

- 戦略（Strategy）
  - src/kabusys/strategy/feature_engineering.py:
    - build_features(conn, target_date): research で生成された生ファクターを統合し、ユニバースフィルタ（最低株価、平均売買代金）を適用、指定カラムを Z スコア正規化（±3 でクリップ）して features テーブルへ日付単位で置換（冪等）。
    - トランザクション管理（BEGIN/COMMIT/ROLLBACK）、欠損や異常値への注意喚起ログ。

  - src/kabusys/strategy/signal_generator.py:
    - generate_signals(conn, target_date, threshold, weights): features と ai_scores を統合し、モメンタム・バリュー・ボラティリティ・流動性・ニュース（AI）を組み合わせて final_score を算出。
    - コンポーネントスコア算出関数（シグモイド、平均化、PER に基づくバリュー等）。
    - Bear レジーム判定（ai_scores の regime_score を集計）。
    - BUY（閾値越え）および SELL（ストップロス・スコア低下）ロジック実装。SELL を優先し BUY から除外するポリシー。
    - 重み（weights）入力の検証・正規化・補完処理。
    - signals テーブルへの日付単位置換（冪等）とトランザクション管理。
  - strategy/__init__.py: build_features, generate_signals の公開。

- Research（研究用ユーティリティ）
  - src/kabusys/research/factor_research.py:
    - calc_momentum(conn, target_date): mom_1m / mom_3m / mom_6m / ma200_dev 等の計算。
    - calc_volatility(conn, target_date): ATR（atr_20, atr_pct）、avg_turnover、volume_ratio 等の計算。
    - calc_value(conn, target_date): raw_financials を参照して PER / ROE を算出（target_date 以前の最新財務データを使用）。
    - DuckDB によるウィンドウ関数活用とデータ不足時の None 戻し。
  - src/kabusys/research/feature_exploration.py:
    - calc_forward_returns(conn, target_date, horizons): 将来リターン（例: 1, 5, 21 営業日）を一括取得する効率的なクエリ実装。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）計算。サンプル数不足時は None。
    - rank(values): 同順位は平均ランクを採るランク関数（丸め誤差対策あり）。
    - factor_summary(records, columns): count/mean/std/min/max/median の統計サマリー。
  - research/__init__.py: 主要関数群の公開（calc_momentum 等、zscore_normalize の re-export を含む）。

- データ統計ユーティリティ参照
  - 各所で kabusys.data.stats.zscore_normalize を利用（実体は data パッケージに存在する想定）。

- バックテストフレームワーク
  - src/kabusys/backtest/simulator.py:
    - PortfolioSimulator: メモリ内でのポートフォリオ管理、BUY/SELL の疑似約定ロジック（スリッページ・手数料反映）、平均取得単価管理、トレード記録（TradeRecord）、日次マーク・トゥ・マーケット（DailySnapshot）。
    - execute_orders: SELL を先に処理してから BUY を実行する実装（資金管理のため）。
    - 約定時のログ（価格欠損・資金不足等）のハンドリング。

  - src/kabusys/backtest/metrics.py:
    - バックテスト評価指標の算出（CAGR / Sharpe / Max Drawdown / Win Rate / Payoff Ratio / total_trades）。
    - calc_metrics() により DailySnapshot と TradeRecord から BacktestMetrics を返す。

  - src/kabusys/backtest/engine.py:
    - run_backtest(conn, start_date, end_date, ...): 本番 DB からインメモリ DuckDB へ必要データをコピーして日次ループでシミュレーションする高水準エンジン。
    - _build_backtest_conn: date フィルタ付きでテーブルをコピー（signals/positions を汚染しない）。
    - _write_positions / _read_day_signals / 価格取得ユーティリティ等の補助関数。
    - 日次ループ: 前日シグナル約定 → positions 書き戻し → 終値評価 → generate_signals 呼び出し → 発注リスト生成（ポジションサイジング）。
  - backtest/__init__.py: run_backtest / BacktestResult / DailySnapshot / TradeRecord / BacktestMetrics の公開。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境変数の読み込み時に OS 環境変数を保護する仕組みを導入（.env/.env.local の優先度と保護キーの扱いを明確化）。
- .env の読み取り失敗時に警告を出す実装（例外を直接投げず安全にフォールバック）。

### Notes / 実装上の注意点（ドキュメント的補足）
- 多くの DB 操作でトランザクション（BEGIN/COMMIT/ROLLBACK）を使用して日付単位の置換（冪等性）を保証している。
- 欠損データや異常値（NaN/Inf）に対しては None 扱い・ログ出力・中立代替（0.5）などで安全に挙動を保つ設計。
- generate_signals の weights はユーザ入力を厳格に検証・補正し、合計が 1.0 となるよう再スケーリングする。
- バックテストでは本番 DB の signals / positions を汚染しないためにインメモリ接続へデータをコピーする方式を採用。
- 一部未実装の仕様は関数内コメントで明示（例: トレーリングストップや時間決済の未実装）。

### Breaking Changes
- なし（初回リリース）

---

開発中の追加事項やバグ修正は今後のリリースで本ファイルに追記します。