# Changelog

すべての変更は Keep a Changelog の仕様に従って記載します。  
このプロジェクトはセマンティックバージョニング（MAJOR.MINOR.PATCH）を採用します。

## [Unreleased]

## [0.1.0] - 2026-03-22
初回リリース。日本株自動売買フレームワークのコア機能群を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基礎
  - パッケージ初期化 (src/kabusys/__init__.py) とバージョン情報 (__version__ = "0.1.0") を追加。
  - public API エクスポート: data, strategy, execution, monitoring（execution は空のパッケージとして配置）。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読み込みする機構を実装。
  - 自動ロードの優先度: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能（テスト用途向け）。
  - プロジェクトルート検出は .git または pyproject.toml を基準に行うため、CWD に依存しない。
  - .env のパース機能を実装:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内でのバックスラッシュエスケープ対応
    - クォート無し時のインラインコメント認識（'#' の前が空白/タブの場合のみ）
  - Settings クラスを提供し、アプリが必要とする主要設定をプロパティ経由で取得可能:
    - J-Quants / kabuステーション API / Slack トークン等の必須設定取得（未設定時は ValueError）
    - DB パス（DuckDB / SQLite）デフォルト値
    - 実行環境判定（development / paper_trading / live）とログレベル検証

- 戦略関連 (src/kabusys/strategy)
  - 特徴量生成 (feature_engineering.build_features)
    - research 側で算出した生ファクターをマージ・ユニバースフィルタ（最低株価・平均売買代金）適用・Zスコア正規化し features テーブルへ UPSERT（トランザクションで日付単位の置換、冪等性を確保）。
    - Zスコアを ±3 でクリップして外れ値の影響を抑制。
    - DuckDB を利用した高速集計と日付ハンドリング（休場日対応）。
  - シグナル生成 (signal_generator.generate_signals)
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum / value / volatility / liquidity / news）を算出。
    - コンポーネントごとの変換関数（シグモイド・逆PER変換等）を実装。
    - デフォルトの重み（momentum:0.40, value:0.20, volatility:0.15, liquidity:0.15, news:0.10）と閾値（BUY=0.60）を備え、ユーザー指定の weights を受け付けるが妥当性検証・正規化を実施。
    - Bear レジーム検出（AI の regime_score の平均が負）により BUY シグナルを抑制するロジックを実装。
    - エグジット条件（SELL）:
      - ストップロス（終値が avg_price から -8% を下回る）
      - final_score が閾値未満に低下
    - SELL 優先ポリシー: SELL 対象は BUY から除外し、BUY のランクを再付与。
    - 日付単位の置換（トランザクション＋バルク挿入）で signals テーブルに出力、冪等性を確保。

- リサーチ関連 (src/kabusys/research)
  - ファクター計算 (factor_research)
    - Momentum（1M/3M/6M リターン, MA200 乖離）、Volatility（20日 ATR、相対ATR、平均売買代金、出来高変化率）、Value（PER, ROE）を DuckDB SQL / ウィンドウ関数で実装。
    - データ不足時は None を返す設計。
  - 特徴量探索 (feature_exploration)
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]。horizons の上限チェックを実装 <= 252）。
    - IC（Spearman の ρ）計算、rank 関数（同順位は平均ランク、比較前に round(v,12) で丸め）を実装。
    - factor_summary による基本統計量（count/mean/std/min/max/median）を計算。
  - research パッケージの public API を整理してエクスポート。

- バックテストフレームワーク (src/kabusys/backtest)
  - シミュレータ (simulator.PortfolioSimulator)
    - 擬似約定ロジック（SELL 先行、BUY は割当額から株数を floor で計算、スリッページおよび手数料モデルを適用）。
    - BUY 時の株数再計算（手数料込みで資金不足の場合の調整）。
    - SELL は保有全量をクローズ（部分利確/部分損切りは未対応）。
    - mark_to_market により終値での時価評価と日次スナップショット記録（終値欠損時は 0 評価で WARNING）。
    - TradeRecord / DailySnapshot のデータクラスを提供。
  - メトリクス (metrics.calc_metrics)
    - CAGR, Sharpe Ratio（無リスク=0）, Max Drawdown, Win Rate, Payoff Ratio, total_trades を計算するユーティリティを実装。
  - バックテストエンジン (engine.run_backtest)
    - 本番 DB からインメモリ DuckDB へ必要データをコピーしてバックテスト用接続を構築（signals/positions を汚染しない）。
    - 日次ループで約定・ポジション書き戻し・時価評価・シグナル生成を行うフローを実装。
    - デフォルトパラメータ: initial_cash=10_000_000, slippage_rate=0.001 (0.1%), commission_rate=0.00055 (0.055%), max_position_pct=0.20。
    - 必要に応じて market_calendar の全件コピーを行う。

- データ層との連携
  - data.stats.zscore_normalize 等を参照して正規化を実施（data モジュール内に正規化ユーティリティを期待）。
  - schema / calendar_management 等のモジュール（init_schema, get_trading_days）を参照することで、DB スキーマ初期化や営業日取得と統合可能な設計。

### Changed
- （初版のため変更履歴なし）

### Fixed
- （初版のため修正履歴なし）

### Removed
- （初版のため削除履歴なし）

### Notes / Known limitations
- execution 層はパッケージ構造として存在するが実装は含まれていません（将来的に発注 API 連携を配置予定）。
- features / signals / positions テーブルのスキーマ依存があるため、互換な schema の初期化（kabusys.data.schema.init_schema）を利用する必要があります。
- 一部の条件（例: トレーリングストップ、時間決済）は _generate_sell_signals 内で未実装と明記されています（positions に peak_price / entry_date が必要）。
- research モジュールは外部ライブラリ（pandas 等）には依存せず標準ライブラリ + DuckDB で実装されていますが、大規模データでのパフォーマンスは DuckDB の設定に依存します。
- calc_forward_returns の horizons 上限は 252 日に設定（入力検証あり）。

### Migration / Usage notes
- 自動的に .env を読み込ませたくない場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 必須の環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）を設定していないと Settings のプロパティ取得時に ValueError が発生します。
- run_backtest を利用する際は本番 DB からコピーされるテーブルに必要なカラムが存在することを確認してください（prices_daily, features, ai_scores, market_regime, market_calendar など）。

---

バージョン 0.1.0 はプロジェクトの基礎機能（データ処理、ファクター計算、特徴量合成、シグナル生成、バックテスト基盤）を含む安定的な初期実装です。今後は execution（実取引）、monitoring、さらに拡張されたポジション管理やリスク管理機能の追加を予定しています。