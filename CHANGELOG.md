# CHANGELOG

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。

現在のリリース方針: SemVer を採用しています。

## [0.1.0] - 2026-03-22

初回公開リリース。日本株自動売買システムのコア機能を実装しました。以下はコードベースから推測できる主な追加点・仕様です。

### 追加 (Added)
- パッケージ基盤
  - パッケージ名: kabusys
  - バージョン定義: __version__ = "0.1.0"
  - パッケージ公開 API のエクスポート: data, strategy, execution, monitoring（__all__）

- 設定 / 環境変数管理 (kabusys.config)
  - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 読み込み優先順位: OS 環境 > .env.local > .env。.env.local は .env を上書き。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能（テスト用途を想定）。
  - .env パーサの強化:
    - コメント行・空行の無視
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなしのインラインコメント処理（直前に空白/タブがある '#' をコメントとみなす）
  - OS 側の環境変数を保護する protected 機能（デフォルトで既存の os.environ を上書きしない挙動）。
  - Settings クラスを提供:
    - J-Quants / kabu ステーション / Slack / DB パスなどのプロパティを取得
    - 必須変数は未設定時に ValueError を送出（_require）
    - KABUSYS_ENV / LOG_LEVEL の妥当性検査（許可値は定義済み）
    - ユーティリティプロパティ: is_live / is_paper / is_dev

- 研究用ファクター計算 (kabusys.research.factor_research)
  - モメンタム計算 (calc_momentum)
    - 1M/3M/6M リターン、200日移動平均乖離 (ma200_dev) を算出
    - 不足データは None を返す設計
  - ボラティリティ・流動性計算 (calc_volatility)
    - 20日 ATR、相対 ATR (atr_pct)、20日平均売買代金 (avg_turnover)、出来高比率 (volume_ratio)
    - true_range の NULL 伝播制御（high/low/prev_close が NULL の場合は TR を NULL）
  - バリュー計算 (calc_value)
    - target_date 以前の最新財務データから PER / ROE を算出（EPS が 0/欠損なら PER は None）
    - raw_financials と prices_daily を組み合わせて取得
  - research パッケージからのエクスポート設定を追加

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features(conn, target_date) を実装
    - research モジュール (calc_momentum / calc_volatility / calc_value) の出力を集約
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用
    - 指定カラムを Z スコア正規化（zscore_normalize を利用）、±3 でクリップ
    - features テーブルへ日付単位で置換（DELETE → bulk INSERT、トランザクションで原子性保証）
    - 欠損や異常値へのロバストな扱い（math.isfinite 等のチェック、ログ出力）

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals(conn, target_date, threshold=0.60, weights=None) を実装
    - features / ai_scores / positions を参照して BUY/SELL シグナルを生成
    - コンポーネントスコア: momentum / value / volatility / liquidity / news を計算
      - momentum: momentum_20, momentum_60, ma200_dev の平均（シグモイド変換適用）
      - value: PER を基に 1/(1 + per/20) で変換（PER が不正な場合は None）
      - volatility: atr_pct の Z スコアを反転してシグモイド変換
      - liquidity: volume_ratio にシグモイド変換
      - news: ai_scores の ai_score をシグモイド（未登録は中立）
    - 欠損コンポーネントは中立値 0.5 で補完
    - 重みの受け入れ: デフォルト重みを補完し、ユーザ指定は検証後にマージ・再スケール
    - Bear レジーム検知: ai_scores の regime_score 平均が負の場合は BUY を抑制（サンプル数閾値あり）
    - SELL 条件（実装済み）:
      - ストップロス: 終値 / avg_price - 1 < -8%
      - スコア低下: final_score < threshold
      - 価格欠損時は SELL 判定をスキップして警告ログ
    - SELL 優先ポリシー: SELL 対象は BUY から除外し、ランクを再付与
    - signals テーブルへ日付単位置換（トランザクション + bulk insert）、冪等性を確保
    - 多数のログ出力（info/debug/warning）を含む

- バックテストフレームワーク (kabusys.backtest)
  - ポートフォリオシミュレータ (PortfolioSimulator)
    - execute_orders: SELL を先に実行し、その後 BUY（SELL は保有全量をクローズ）
    - スリッページ・手数料モデルを適用（BUY は entry_price = open*(1+slippage_rate)、SELL は exit_price = open*(1-slippage_rate)）
    - 手数料を考慮した株数再計算、平均取得単価の保持
    - mark_to_market: 終値で時価評価し DailySnapshot を記録（終値欠損は 0 として警告）
    - トレード履歴を TradeRecord として保持（realized_pnl を計算）
  - バックテストエンジン (run_backtest)
    - 本番 DB からインメモリ DuckDB へ必要テーブルをコピー（data 範囲を限定）
    - 日次ループ: 約定（前日シグナルを当日始値で約定）→ positions 書き戻し → 時価評価 → generate_signals（当日）→ ポジションサイジング → 次日約定リスト生成
    - ポジション書き戻し・シグナル読み取りユーティリティを提供（_write_positions, _read_day_signals）
    - open/close 価格取得ユーティリティを提供
  - バックテスト指標 (kabusys.backtest.metrics)
    - CAGR, Sharpe Ratio（無リスク=0）、Max Drawdown、Win Rate、Payoff Ratio、Total Trades を計算する calc_metrics を実装
    - 各指標の内部計算関数を実装（戻り値の安定性を重視したチェックを含む）

- 研究用ユーティリティ / 探索 (kabusys.research.feature_exploration)
  - 将来リターン計算 (calc_forward_returns)
    - 複数ホライズン（デフォルト [1,5,21]）でのリターン計算を行い、存在しない場合は None を返す
    - パフォーマンス考慮でスキャン範囲にバッファを設けた実装
  - IC（Information Coefficient）計算 (calc_ic)
    - factor_records と forward_records を code キーで結合して Spearman の ρ を計算（ties の平均ランク対応）
    - 有効レコードが 3 件未満なら None を返す
  - ランク関数 (rank)
    - 同順位は平均ランクにする実装（事前に round(..., 12) による丸めで ties 判定の安定化）
  - 統計サマリー (factor_summary)
    - count, mean, std, min, max, median を返す

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 非対応 / 既知の制約 (Known limitations)
- Trailing stop や時間決済（保有 60 営業日超過）等の一部のエグジット条件は未実装（signal_generator のコメントで言及）。
- execution 層（実際の注文送信）および外部 API 呼び出しは本コードベースの中核部分では直接実装していない（設計方針により層分離）。
- research モジュールは pandas 等の外部ライブラリに依存せず、標準ライブラリ + DuckDB のみで実装されているため、処理は SQL 中心。
- 一部のテーブル（例: features / ai_scores / positions / market_calendar 等）は外部でのスキーマ準備が必要（kabusys.data.schema を参照する想定）。

### 備考 (Notes)
- トランザクションや bulk insert により DB 書き込みは日付単位で置換され、冪等性が考慮されています。
- ロギングが各所に埋め込まれており、運用時のデバッグや監視に寄与します。
- 今後、execution 層の実装（発注 API 連携）、追加のエグジット戦略、レポーティング機能、テストケースの整備が想定されます。

---

今後のリリースでは各モジュールの API 変更、パフォーマンス改善、バグ修正、セキュリティ・耐故障性向上などを個別に記載します。