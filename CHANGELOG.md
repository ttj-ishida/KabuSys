# CHANGELOG

すべての変更は Keep a Changelog に準拠しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-22
初回リリース。本バージョンでは日本株の自動売買・研究・バックテストに関するコア機能群を提供します。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを追加。公開 API（__all__）に data, strategy, execution, monitoring を含む。
  - バージョン情報を src/kabusys/__init__.py の __version__ = "0.1.0" にて管理。

- 環境設定管理
  - src/kabusys/config.py: .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
    - .env の自動読み込み機能（プロジェクトルート判定: .git または pyproject.toml を探索）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - .env パース機能:
      - export KEY=val 形式対応。
      - 単一/二重クォート内のバックスラッシュエスケープ処理対応。
      - インラインコメント（クォート外で # の直前がスペース/タブ の場合）を認識。
    - _require による必須変数チェック（未設定時は ValueError）。
    - 主要設定プロパティを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL など）。
    - KABUSYS_ENV / LOG_LEVEL の値検証（許容値を限定）。

- 戦略（feature engineering / signal generation）
  - src/kabusys/strategy/feature_engineering.py:
    - research モジュールで算出した raw ファクターを統合して features テーブルへ UPSERT する build_features(conn, target_date) を実装。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を実装。
    - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ。
    - DuckDB を用いた日付単位の置換（トランザクション＋バルク挿入で冪等性を確保）。
  - src/kabusys/strategy/signal_generator.py:
    - features と ai_scores を統合して final_score を計算し BUY / SELL シグナルを生成する generate_signals(conn, target_date, threshold, weights) を実装。
    - スコア計算ロジック（momentum / value / volatility / liquidity / news の重み付け合算）。
    - シグモイド変換、欠損コンポーネントは中立値 0.5 で補完。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合）。
    - SELL 判定ロジック（ストップロス -8% / final_score が閾値未満）。
    - weights のユーザー入力を検証・正規化して合計が 1.0 になるように調整。
    - signals テーブルへの日付単位置換（冪等）。

- 研究用ユーティリティ（research）
  - src/kabusys/research/factor_research.py:
    - モメンタムファクター（mom_1m/mom_3m/mom_6m、ma200_dev）を calc_momentum(conn, target_date) で計算。
    - ボラティリティ / 流動性ファクター（atr_20, atr_pct, avg_turnover, volume_ratio）を calc_volatility(conn, target_date) で計算。
    - バリューファクター（per, roe）を calc_value(conn, target_date) で計算（raw_financials と prices_daily を参照）。
  - src/kabusys/research/feature_exploration.py:
    - 将来リターン計算 calc_forward_returns(conn, target_date, horizons)（デフォルト [1,5,21]）。
    - IC（Spearman ランク相関）計算 calc_ic。
    - ファクター統計サマリー factor_summary。
    - ランク変換ユーティリティ rank。
    - pandas 等に依存せず標準ライブラリ + DuckDB で実装。
  - research パッケージの __all__ に主要関数を公開。

- バックテストフレームワーク
  - src/kabusys/backtest/simulator.py:
    - PortfolioSimulator と関連データクラス（DailySnapshot, TradeRecord）を実装。
    - execute_orders による疑似約定（SELL を先に、BUY は割当てから株数を算出、スリッページ・手数料反映）。
    - mark_to_market による時価評価と日次スナップショット保存。
    - BUY/SELL の約定時のトレード記録（手数料・実現損益の計算）を保持。
  - src/kabusys/backtest/metrics.py:
    - バックテスト評価指標計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）。
  - src/kabusys/backtest/engine.py:
    - run_backtest(conn, start_date, end_date, initial_cash=..., slippage_rate=..., commission_rate=..., max_position_pct=...) を実装。
    - 本番 DB からインメモリ DuckDB へデータをコピーする _build_backtest_conn を実装（signals/positions を汚染しない）。
    - 日次ループ: 約定（前日シグナルを当日始値で約定）→ positions テーブル書き戻し → 時価評価記録 → generate_signals 呼び出し → ポジションサイジングと発注リスト生成。
    - prices_daily/features/ai_scores/market_regime/market_calendar のコピー処理を実装（コピー時のエラーは警告でスキップ）。
    - _fetch_open_prices / _fetch_close_prices / _write_positions / _read_day_signals 等の補助関数を実装。
  - backtest パッケージの __all__ に主要クラス・関数を公開。

### 変更 (Changed)
- （初回リリースのため既存からの変更はなし）

### 修正 (Fixed)
- （初回リリースのため修正項目はなし）

### 制限・未実装（注意事項）
- signal_generator の SELL 判定で記載されている一部条件は未実装:
  - トレーリングストップ（peak_price / entry_date が positions に必要）
  - 時間決済（保有 60 営業日超過）
- calc_value は現時点で PBR・配当利回りを算出していない（コメントで未実装を明記）。
- feature_exploration は外部依存を避ける設計のため、大規模データ処理で pandas 等と比べて扱いにくい場合がある。
- run_backtest のデータコピーは日付範囲でフィルタするが、外部要因で一部テーブルのコピーがスキップされる場合がある（警告ログ出力）。

### セキュリティ (Security)
- 環境変数読み込み時に OS の既存環境変数を保護する仕組み（protected set）を導入。自動ロードを無効化するフラグも用意。

---

将来的なリリースでは以下を検討しています:
- execution レイヤーの実装（kabu ステーション連携による実取引）。
- monitoring（Slack 通知等）の具体実装・統合。
- feature / research の性能最適化や pandas 等のオプションサポート。
- トレーリングストップや時間決済などエグジット条件の拡充。