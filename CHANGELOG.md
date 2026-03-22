# Changelog

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣習に従い、セマンティックバージョニングを使用します。

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-22

初回公開リリース。日本株自動売買システムのコア機能群を実装しました。主な追加点は以下のとおりです。

### Added
- パッケージ基礎
  - パッケージメタ情報とエクスポートを追加（src/kabusys/__init__.py）。
  - 公開 API の導出: data, strategy, execution, monitoring を __all__ に定義。

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env ファイルと環境変数からの設定自動読み込み機能を実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - プロジェクトルートは .git または pyproject.toml を基準に自動検出（CWD 非依存）。
    - 環境変数の自動読み込みを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサを実装（コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント等を考慮）。
  - 既存の OS 環境変数を保護するための protected オプション（.env の上書き制御）を実装。
  - Settings クラスを提供し、アプリで利用する設定値をプロパティとして公開。
    - J-Quants / kabuステーション / Slack / DB パス等の必須・任意設定を取得。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL のバリデーションを実装。
    - デフォルトの DB パス（DuckDB/SQLite）を設定。

- 戦略（strategy）
  - 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
    - research モジュールで計算した raw factor を集約・正規化して features テーブルへ保存する build_features() を実装。
    - 処理フロー：
      - calc_momentum / calc_volatility / calc_value からファクター取得
      - 株価・流動性によるユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）
      - 指定列の Z スコア正規化（zscore_normalize を利用）および ±3 でのクリップ
      - features テーブルへの日付単位置換（DELETE → INSERT をトランザクションで実施／冪等性を保証）
    - 欠損値や外れ値処理、最新価格検索（target_date 以下で最新の価格参照）を考慮。

  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - features と ai_scores を統合して最終スコア final_score を計算し、BUY/SELL シグナルを生成する generate_signals() を実装。
    - デフォルト重み・閾値を定義（momentum/value/volatility/liquidity/news 等の重み、BUY 閾値 0.60）。
    - コンポーネントスコアの算出：
      - momentum: momentum_20 / momentum_60 / ma200_dev をシグモイド→平均化
      - value: PER を 20 を基準に逆変換（低いほど高スコア）
      - volatility: atr_pct の反転シグモイド
      - liquidity: volume_ratio をシグモイド
      - news: ai_score をシグモイド（未登録時は中立）
    - 欠損コンポーネントは中立値 0.5 で補完することで不当な降格を防止。
    - Bear レジーム検知（ai_scores の regime_score 平均が負なら Bear。ただしサンプル数閾値を設定）。
    - エグジット（SELL）判定ロジック（ストップロス -8%、final_score < threshold）。
    - SELL を優先して BUY から除外。signals テーブルへの日付単位置換（トランザクションで冪等）。
    - プロバイダ不正入力（weights の無効値）に対するロギングとフォールバック／リスケールを実装。

- リサーチ / ファクター計算（src/kabusys/research）
  - ファクター計算ユーティリティ群を実装（外部ライブラリに依存しない純 Python + DuckDB 実装）。
  - calc_momentum, calc_volatility, calc_value（src/kabusys/research/factor_research.py）
    - Momentum: mom_1m/3m/6m / ma200_dev（200 日のデータ不足時は None）
    - Volatility: 20 日 ATR / atr_pct / avg_turnover / volume_ratio（部分窓対応、データ不足時は None）
    - Value: target_date 以前の最新 raw_financials を用いた PER / ROE（EPS が 0/欠損なら PER は None）
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: target_date の終値から指定ホライズン（デフォルト [1,5,21]）の将来リターンを算出
    - calc_ic: Spearman のランク相関（IC）を計算（有効レコード >= 3 が必要）
    - factor_summary / rank: 基本統計量およびランク付け（同順位は平均ランク）を実装
  - research パッケージの __all__ で主要 API を公開。

- バックテスト（src/kabusys/backtest）
  - シミュレータ（src/kabusys/backtest/simulator.py）
    - PortfolioSimulator を実装。約定ロジック（SELL 先行、BUY は資金割当に基づいて板外で全部買い／全量売却）、スリッページ・手数料モデル、時価評価（mark_to_market）を提供。
    - TradeRecord / DailySnapshot のデータクラスを提供。
    - BUY 時の手数料込み再計算／資金不足時の取り扱いなどの安全処理を実装。
  - メトリクス（src/kabusys/backtest/metrics.py）
    - バックテストの評価指標計算を実装（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）。
    - 数学的に未定義またはデータ不足時の安全値（0.0）設定に注意。
  - エンジン（src/kabusys/backtest/engine.py）
    - run_backtest(): 本番用 DuckDB から必要データをインメモリにコピーし、日次ループで generate_signals を使ってシミュレーションを実行。
    - _build_backtest_conn() による限定期間データのコピー（signals/positions を汚染しないよう設計）。
    - signals -> 約定 -> positions 書き戻し -> 時価評価 -> シグナル生成 のループを実装。
    - 市場暦（market_calendar）をコピーして取引日取得に使用。
    - positions の書き戻しは冪等で行う（DELETE / INSERT）。
    - run_backtest のパラメータとして初期資金、スリッページ率、手数料率、1 銘柄最大比率などを受け付け。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数読み込みに失敗した場合は warnings.warn を発行してフェイルせず継続する実装（.env 読み込みの頑健化）。

### Notes / Implementation details
- 多くの DB 書き込み（features / signals / positions）は「日付単位で DELETE してから INSERT」することで冪等性を確保し、トランザクションで原子性を担保しています。ロールバック失敗時は警告ログが出ます。
- research モジュールは外部ライブラリ（pandas 等）に依存しない実装を目指しています。DuckDB による SQL 集計を多用。
- signal 計算では欠損値に対し中立値（0.5）で補完する設計を採用し、ルックアヘッドバイアス防止のため target_date 時点のデータのみを参照します。
- .env パーサは多くのシェル形式に対処しますが、特殊ケースや複雑なシェル式は対象外です。

### Known issues / TODO
- エグジット条件のうち、以下は未実装（実現には positions テーブルへの追加情報が必要）:
  - トレーリングストップ（peak_price を使った処理）
  - 時間決済（保有日数に基づく自動クローズ）
- Value ファクターにおける PBR / 配当利回りは未実装。
- execution パッケージは空のまま（発注 API との統合は未実装）。
- テストスイートはこのリリースに含まれていない（単体テスト・統合テストの整備が必要）。
- 高頻度の大規模データセットに対するパフォーマンス検証・最適化は今後の課題。

---

以上が v0.1.0 の主要な変更点です。今後のリリースでは execution 層の実装、追加のファクター、Exit ルール強化、テスト整備、ドキュメント拡充を予定しています。