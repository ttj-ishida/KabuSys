# Changelog

すべての重要な変更点をここに記録します。フォーマットは「Keep a Changelog」に準拠します。

全般:
- セマンティクスはメジャー.マイナー.パッチの形式を想定しています。初回公開バージョンは 0.1.0 です。
- 各エントリは機能追加・変更・修正・既知の制限などを記載しています。

なお、本 CHANGELOG は提示されたコードベースの内容から推測して作成しています（実装コメント・コードの振る舞いに基づく記述）。

Unreleased
---------
（なし）

[0.1.0] - 2026-03-22
-------------------

Added
- パッケージ初期リリース "kabusys"。
  - パッケージ構成: data, strategy, execution, monitoring（__all__ に列挙）。
  - バージョン定義: __version__ = "0.1.0"。

- 環境設定管理（kabusys.config）
  - .env/.env.local 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ:
    - export KEY=val 形式の対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理・適切なクローズクォート探索。
    - クォートなしの値におけるインラインコメント認識（直前がスペース/タブの場合）。
  - .env 読み込み時の保護機能:
    - OS 環境変数を protected として .env による上書きを制御（.env.local は override=True だが protected を尊重）。
  - Settings クラス:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須プロパティ。
    - KABU_API_BASE_URL のデフォルト ("http://localhost:18080/kabusapi")。
    - データベースパス: DUCKDB_PATH / SQLITE_PATH のデフォルト（data/ 以下）。
    - KABUSYS_ENV の検証（許可値: development, paper_trading, live）。
    - LOG_LEVEL の検証（許可値: DEBUG, INFO, WARNING, ERROR, CRITICAL）。
    - ヘルパー is_live / is_paper / is_dev。

- 戦略関連（kabusys.strategy）
  - feature_engineering.build_features:
    - research の calc_momentum / calc_volatility / calc_value を統合して features テーブルへ書き込む。
    - ユニバースフィルタ: 株価 >= 300 円、20日平均売買代金 >= 5e8 円。
    - 正規化: kabusys.data.stats.zscore_normalize を使用し、対象カラムを Z スコア正規化、±3 でクリップ。
    - 日付単位の置換（DELETE + bulk INSERT）をトランザクションで行い原子性を確保。ROLLBACK 失敗時は警告ログ。
  - signal_generator.generate_signals:
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news の各コンポーネントスコアを計算。
    - スコア変換: Z スコア → シグモイド（0〜1）への変換、PER の独自スケーリング（PER=20→0.5 等）。
    - 欠損コンポーネントは中立値 0.5 で補完。
    - デフォルト重み（momentum:0.40, value:0.20, volatility:0.15, liquidity:0.15, news:0.10）、重みの入力検証と正規化（合計が 1 でない場合再スケール、無効値は無視）。
    - Bear レジーム判定: ai_scores の regime_score 平均 < 0 を Bear、ただしサンプル数が 3 未満なら Bear とみなさない。
    - BUY シグナル閾値デフォルト 0.60、Bear レジーム時は BUY を抑制。
    - SELL（エグジット）判定:
      - ストップロス: (close / avg_price - 1) < -0.08（-8%）。
      - スコア低下: final_score < threshold。
      - 保有銘柄の価格が取得できない場合は SELL 判定処理をスキップし警告。
      - features に存在しない保有銘柄は final_score = 0.0 と見なして SELL 判定可能。
    - signals テーブルへの日付単位置換（トランザクション＋バルク挿入）。ROLLBACK 失敗時は警告ログ。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_dev を計算（200 日データ不足時は None）。
    - calc_volatility: 20 日 ATR, atr_pct, avg_turnover, volume_ratio を計算（不足時は None）。
    - calc_value: raw_financials から最新財務データを取得し PER / ROE を計算（EPS=0/欠損で PER は None）。
    - DuckDB を用いた SQL ベースの実装で prices_daily / raw_financials のみ参照。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン計算。
    - calc_ic: Spearman（順位相関）による IC 計算（有効レコード < 3 の場合 None を返す）。
    - factor_summary: count/mean/std/min/max/median の統計サマリ。
    - rank: 同順位は平均ランクを付与（round(...,12) を用いて ties の検出精度を担保）。
    - 外部ライブラリに依存せず標準ライブラリ + DuckDB で完結。

- バックテストフレームワーク（kabusys.backtest）
  - engine.run_backtest:
    - 本番 DuckDB からデータをインメモリ DuckDB（init_schema(":memory:")）へ日付フィルタ付きでコピーしバックテスト実行。
    - コピー対象テーブル: prices_daily, features, ai_scores, market_regime（market_calendar は全件コピー）。
    - 日次ループ: 前日シグナルを当日始値で約定 → positions テーブル書き戻し → 終値で時価評価 → generate_signals 呼び出し → 発注リスト組立て → BUY 約定等。
    - バックテストパラメータ: 初期資金, slippage_rate（デフォルト 0.001）, commission_rate（デフォルト 0.00055）, max_position_pct（デフォルト 0.20）。
  - simulator.PortfolioSimulator:
    - 擬似約定モデル（BUY は始値*(1+slippage)、SELL は始値*(1-slippage)）。
    - BUY は与えられた alloc を基に手数料込みで購入株数を切り捨て、手数料は cost * commission_rate。
    - BUY 時に手数料込みで現金が足りない場合、再計算して購入可能な株数に調整。
    - SELL は保有全量をクローズ（部分利確/部分損切りは非対応）。約定で realized_pnl を算出。
    - mark_to_market により終値でポートフォリオ評価、終値欠損時は 0 と評価し警告ログを出力。
    - DailySnapshot / TradeRecord dataclass を用いた履歴記録。
  - metrics.calc_metrics:
    - CAGR, Sharpe (無リスク金利=0、年次化に営業日252日を使用), 最大ドローダウン, 勝率, ペイオフレシオ, 総クローズトレード数 を算出。
    - データ不足時は安全に 0.0 を返す等のガードあり。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Removed
- なし

Security
- なし

Notes / Known limitations
- 一部の戦略仕様は未実装（コード内コメントに明記）:
  - トレーリングストップや保有日数による時間決済は未実装（positions テーブルに peak_price / entry_date が必要）。
  - PBR・配当利回り等の一部バリューファクターは未実装。
- features テーブルへの保存時に avg_turnover はフィルタ用途で参照するが features 列には保存されない（フィルタのみで使用）。
- generate_signals は ai_scores が欠落するケースを中立（0.5）で補完するため、AI スコアがないと既定の挙動になる点に注意。
- .env パーサは多くのケースを扱うが、極端に非標準な .env 構文には対応しない可能性あり。
- バックエンドのデータコピー処理は例外が発生したテーブルをスキップする設計（警告ログ）。データ欠如がバックテスト結果に影響する可能性あり。

Compatibility
- DB スキーマ（prices_daily, features, ai_scores, positions, market_calendar 等）を前提とします。スキーマ変更は互換性に影響します。

---

この CHANGELOG はコードの実装内容から推測して作成しています。実際のリリース履歴や公開日付とは異なる場合があります。必要であればリリース日や追加の変更カテゴリ（例: Fixes の詳細）を指定してください。