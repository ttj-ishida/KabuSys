# Changelog

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」仕様に準拠し、セマンティックバージョニングを採用します。

※バージョン 0.1.0 はパッケージ内の __version__ に合わせた初期リリース相当の変更履歴です。

## [Unreleased]
- （現在未リリースの変更なし）

## [0.1.0] - 2026-03-22
初期リリース。日本株自動売買システム「KabuSys」の基本コンポーネントを実装。

### Added
- パッケージ基礎
  - パッケージ定義とエクスポート（kabusys.__init__）。
  - バージョン情報: 0.1.0。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を実装（読み込み順: OS > .env.local > .env）。
  - プロジェクトルートの自動検出（.git または pyproject.toml を基準）による .env の探索。パッケージ配布後も CWD に依存しない設計。
  - .env パーサ実装（コメント行、export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスで主要設定をプロパティとして提供:
    - J-Quants / kabuステーション / Slack トークン類（必須設定は未設定時に ValueError を送出）。
    - データベースパス（DuckDB / SQLite）のデフォルト。
    - 環境（development/paper_trading/live）とログレベル検証ユーティリティ。
    - is_live / is_paper / is_dev ブールヘルパー。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum: mom_1m, mom_3m, mom_6m、200日移動平均乖離（ma200_dev）。
    - Volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比（volume_ratio）。
    - Value: PER（株価/EPS）、ROE（raw_financials から最新財務を取得）。
    - 各関数は DuckDB の prices_daily / raw_financials テーブルを参照し、(date, code) をキーとする dict リストを返す設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）: 指定ホライズン（デフォルト 1,5,21 営業日）の将来終値リターンを取得。
    - IC（Information Coefficient）計算（calc_ic）: Spearman ランク相関を実装（最小サンプル数チェックあり）。
    - ファクター統計サマリー（factor_summary）: count/mean/std/min/max/median を計算。
    - ランク変換ユーティリティ（rank）。
  - zscore_normalize はデータユーティリティ（kabusys.data.stats）として参照・利用可能に設計（実体は data モジュール側に存在）。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date)
    - research のファクター計算結果を取得しマージ、ユニバースフィルタ（最低株価・最低平均売買代金）を適用。
    - 指定カラムを Z スコア正規化（外れ値は ±3 にクリップ）。
    - features テーブルへ日付単位で置換（DELETE + INSERT をトランザクションで実行し冪等性と原子性を確保）。
    - ユニバース基準: 最低株価 300 円、最低 20 日平均売買代金 5 億円。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold=0.60, weights=None)
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum / value / volatility / liquidity / news）を計算し、重み付き合算で final_score を算出。
    - デフォルト重み・閾値を実装（デフォルト threshold=0.60、weights はデフォルト値からスケール補正）。
    - AI スコアの regime_score により市場レジーム（Bear）を判定し、Bear レジーム時は BUY シグナルを抑制。
    - BUY（threshold 以上）と SELL（エグジット判定: ストップロス / スコア低下）の両方を生成し、signals テーブルへ日付単位で置換して保存。
    - 欠損コンポーネントは中立値 0.5 で補完するポリシー（欠損銘柄の不当な降格防止）。
    - 重みの検証: 未知キーや非数値、負値等は無視し、合計が 1 になるよう正規化。

- バックテストフレームワーク（kabusys.backtest）
  - ポートフォリオシミュレータ（kabusys.backtest.simulator）
    - PortfolioSimulator: メモリ上での約定処理・ポジション管理。
    - 実装済み: BUY/SELL 約定ロジック（始値に対するスリッページ、手数料計算、買付時の株数再計算）、全量クローズの SELL、マーク・トゥ・マーケットによる日次スナップショット記録。
    - TradeRecord / DailySnapshot dataclass 定義。
  - バックテストエンジン（kabusys.backtest.engine）
    - run_backtest(conn, start_date, end_date, ...) を実装:
      - 本番 DB からインメモリ DuckDB へ必要データをコピー（データ破壊を防ぐ）。
      - 日次ループ: 前日シグナル約定 → positions 書き戻し → 終値評価 → generate_signals を呼び翌日シグナル生成 → ポジションサイジング → 次日発注へ。
      - DuckDB を利用したデータ抽出ユーティリティ（始値/終値の取得・positions の書き戻し・signals 読取）を提供。
      - スリッページ/手数料/1銘柄最大比率等をパラメータ化。
  - バックテストメトリクス（kabusys.backtest.metrics）
    - calc_metrics(history, trades) により BacktestMetrics を算出:
      - CAGR、Sharpe ratio（無リスク金利=0）、Max Drawdown、Win Rate、Payoff Ratio、総クローズトレード数を計算。
    - 内部での計算ロジックは日次リターン・売買履歴に基づく。

### Changed
- （初版のためなし）

### Fixed
- （初版のためなし）

### Notes / Known limitations
- 一部のエグジット条件は未実装:
  - トレーリングストップ（直近最高値から -10%）および時間決済（保有 60 営業日超過）は positions テーブルに追加情報（peak_price / entry_date 等）が必要であり現バージョンでは実装されていない。
- features / signals / positions 等のテーブルスキーマ（kabusys.data.schema 側）および zscore_normalize 実装は別モジュールに依存する点に注意。
- research モジュールは外部ライブラリ（pandas 等）に依存せず標準ライブラリと DuckDB SQL の組合せで実装されているため、データ量や SQL パフォーマンスに依存する。
- 自動 .env 読み込みはプロジェクトルートの検出に失敗した場合スキップされる。テスト環境等で自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定する。

### Security / Privacy
- .env の読み込み時、既存の OS 環境変数は保護（protected set）され、.env による上書きを防止するロジックを実装（.env.local は override=True だが protected キーは上書きしない）。
- 必須トークン（API トークン・Slack トークン等）は未設定時に明示的に ValueError を投げ、誤操作を防止。

---

参考:
- 本プロジェクトはセマンティックバージョニング (MAJOR.MINOR.PATCH) を採用します。目安:
  - MAJOR バージョンは後方互換性のない変更時に上げます。
  - MINOR バージョンは機能追加（後方互換性あり）のときに上げます。
  - PATCH はバグ修正のときに上げます。