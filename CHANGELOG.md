# CHANGELOG

すべての変更は Keep a Changelog 規約に準拠して記載しています。  
（https://keepachangelog.com/ja/1.0.0/）

## [Unreleased]

なし。

## [0.1.0] - 2026-03-22

初期リリース。日本株の自動売買研究・バックテスト・シグナル生成に必要なコア機能群を提供します。主な追加点・設計上の注記は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - パッケージバージョンを `0.1.0` として公開（`kabusys.__version__`）。
  - 公開モジュール: data, strategy, execution, monitoring（`__all__` に登録）。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートは `.git` または `pyproject.toml` を探索）。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - `.env` と `.env.local` の読み込み順: OS 環境 > .env.local（override）> .env（override=False）。OS 環境変数は保護（上書き防止）。
  - .env のパース機能を独自実装：`export KEY=val`、シングル/ダブルクォート内のエスケープ、インラインコメントの扱い等に対応。
  - 必須設定の取得ユーティリティ `Settings` を提供（プロパティ経由）:
    - J-Quants / kabuステーション / Slack / DB パス（DuckDB, SQLite）等を取得
    - KABUSYS_ENV の検証（development / paper_trading / live）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - 利便性プロパティ: is_live / is_paper / is_dev

- 研究（research）モジュール
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を計算（prices_daily を参照）
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio を計算（ATR の欠損制御を考慮）
    - calc_value: per, roe を raw_financials と prices_daily から計算（target_date 以前の最新財務データを使用）
    - 各関数は (date, code) をキーとする dict のリストを返す
    - SQL + 標準ライブラリで実装（外部依存なし）
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算
    - calc_ic: スピアマンランク相関（IC）を計算（欠損・サンプル不足時は None）
    - factor_summary: 各ファクター列の統計量（count/mean/std/min/max/median）
    - rank: 同順位は平均ランクで処理（丸めで ties 検出漏れを防止）
    - pandas 等に依存しない実装

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date)
    - research のファクターを取得しマージ、ユニバースフィルタ適用、Z スコア正規化、±3 でクリップして `features` テーブルへ日付単位で置換（冪等）
    - ユニバースフィルタ:
      - 株価 >= 300 円（_MIN_PRICE）
      - 20日平均売買代金 >= 5 億円（_MIN_TURNOVER）
    - 正規化対象列は指定（mom_1m, mom_3m, atr_pct, volume_ratio, ma200_dev）
    - トランザクション + バルク挿入で原子性を保証、例外時はロールバック（ロールバック失敗は警告ログ）

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold=0.60, weights=None)
    - `features` と `ai_scores` を統合して各銘柄のコンポーネントスコアを計算
      - momentum / value / volatility / liquidity / news を合成（デフォルト重みを提供）
      - 欠損コンポーネントは中立値 0.5 で補完
      - AI ニューススコアは ai_scores の ai_score をシグモイド変換で使用（未登録は中立）
    - 重み処理:
      - 入力 weights は既知キーのみ受け付け、負値/NaN/Inf/非数は無視
      - 合計が 1.0 でなければ再スケール、合計が <=0 の場合はデフォルトにフォールバック
    - Bear レジーム判定:
      - ai_scores の regime_score の平均が負（かつサンプル数 >= 3）なら Bear とみなし BUY を抑制
    - SELL（エグジット）判定（現実装）:
      - ストップロス: (close / avg_price - 1) < -8%
      - スコア低下: final_score < threshold
      - 未実装（将来的に必要）: トレーリングストップ、時間決済（コメントで明記）
    - `signals` テーブルへ日付単位の置換で書き込み（冪等）
    - SELL 優先ポリシー: SELL 対象は BUY から除外してランクを再付与

- バックテストフレームワーク（kabusys.backtest）
  - run_backtest(conn, start_date, end_date, initial_cash=10_000_000, slippage_rate=0.001, commission_rate=0.00055, max_position_pct=0.20)
    - 本番 DB からバックテスト用にインメモリ DuckDB に必要データをコピー（signals/positions を汚さない）
    - 日次ループ:
      1. 前日シグナルを当日始値で約定（売りを先、買いを後）
      2. シミュレータの保有情報を positions テーブルへ書き戻し（generate_signals の SELL 判定に必要）
      3. 終値で時価評価してスナップショット記録
      4. generate_signals を呼び翌日のシグナル生成
      5. 発注リストを組み立て（ポジションサイジング）
    - デフォルトのスリッページ/手数料/最大ポジション比率を指定可能
  - PortfolioSimulator（kabusys.backtest.simulator）
    - メモリ内でキャッシュ・保有・平均取得単価・取引履歴を管理
    - execute_orders: SELL を先に処理、BUY は割当（alloc）に従って購入（切り捨てで株数決定）
    - BUY: スリッページは +、SELL は -。手数料は約定額に対する割合
    - SELL は保有全量をクローズ（部分利確・部分損切り非対応）
    - mark_to_market: 終値で評価、欠損価格は 0 で評価して警告ログ
    - TradeRecord / DailySnapshot の定義を提供
  - メトリクス（kabusys.backtest.metrics）
    - calc_metrics(history, trades) により BacktestMetrics を計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）
    - 実装では年次化や標準的な定義（営業日252日換算の年次化など）を採用

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 非推奨 (Deprecated)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- 環境変数の取り扱いで OS 環境変数を意図せず上書きしない設計（protected set）を導入。

---

## 既知の制限・注意点
- トレーリングストップや時間経過による決済など、一部のエグジットルールは未実装（コード内コメントに記載）。将来の拡張が必要です。
- features / signals / positions 等のテーブルスキーマ（カラム名）はコード側で想定されており、外部データソースはこれらスキーマに従う必要があります。
- 研究モジュール・バックテストは DuckDB を前提としており、外部 DataFrame ライブラリ（pandas 等）には依存していません。
- generate_signals における重み処理は未知キーを無視するため、ユーザーが意図しないキーを渡した場合は無視されます。合計が 1.0 でない場合は自動で再スケールされます。
- 自動 .env 読み込みはプロジェクトルート（`.git` または `pyproject.toml`）の検出に依存するため、配布形態や実行パスにより自動ロードがスキップされることがあります。自動読み込みを制御するには `KABUSYS_DISABLE_AUTO_ENV_LOAD` を設定してください。

--- 

必要であれば各機能（関数・クラス）の API サマリや使用例を CHANGELOG に付記することも可能です。どの程度の詳細が必要か指示してください。