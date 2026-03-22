# CHANGELOG

すべての重要な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠しています（日本語で要約）。

注: 本リポジトリのバージョンは src/kabusys/__init__.py の __version__ に従います（このスナップショットでは 0.1.0）。

## [Unreleased]

- （現時点のスナップショットは 0.1.0 としてリリース済みの想定のため、未リリース項目はありません）

## [0.1.0] - 2026-03-22

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを追加。モジュール構成: data, strategy, execution, monitoring（__all__ に明記）。
  - バージョン管理: src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

- 環境設定 / 設定管理
  - src/kabusys/config.py を追加。
    - .env / .env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml から探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト向け）。
    - 洗練された .env パーサー（コメント、export プレフィックス、クォート文字列、バックスラッシュエスケープ対応）。
    - Settings クラスを提供し、主要設定をプロパティとして取得:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
      - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - DUCKDB_PATH, SQLITE_PATH
      - KABUSYS_ENV (development/paper_trading/live), LOG_LEVEL（値検証あり）
    - 必須設定が未設定の場合は ValueError を発生させる _require ヘルパー実装。

- 研究（research）モジュール
  - src/kabusys/research/factor_research.py
    - Momentum / Volatility / Value 系ファクター計算関数を実装:
      - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200 日 MA の欠損処理含む）
      - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（true range の NULL 伝播制御、窓不足時の None）
      - calc_value: per, roe（raw_financials の target_date 以前の最新財務データを使用）
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算 calc_forward_returns（任意ホライズン、入力検証あり）
    - Information Coefficient（IC）計算 calc_ic（Spearman ρ、最小サンプル数チェック）
    - ランク変換 rank（同順位は平均ランク、丸めにより ties 対応）
    - factor_summary：基本統計量（count/mean/std/min/max/median）計算
  - research の __init__ を整備して主要関数をエクスポート。

- 戦略（strategy）モジュール
  - src/kabusys/strategy/feature_engineering.py
    - 研究環境で計算した生ファクターを統合・正規化して features テーブルへ UPSERT する build_features を実装。
    - ユニバースフィルタ（最低株価、20日平均売買代金）と Z スコア正規化（指定列、±3 でクリップ）を実装。
    - DuckDB トランザクションで日付単位の置換（DELETE → INSERT）を行い冪等性を確保。
  - src/kabusys/strategy/signal_generator.py
    - features と ai_scores を統合して最終スコア final_score を計算し、BUY/SELL シグナルを生成する generate_signals を実装。
    - コンポーネントスコア（momentum/value/volatility/liquidity/news）の計算、シグモイド変換、欠損補完（中立 0.5）を実装。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつ十分なサンプル数）による BUY 抑制。
    - ストップロスやスコア低下によるエグジット（SELL）判定を実装（_generate_sell_signals）。
    - weights の妥当性検査とリスケール、signals テーブルへの日付単位置換を実装。
  - strategy/__init__.py で build_features / generate_signals を公開。

- バックテスト（backtest）フレームワーク
  - src/kabusys/backtest/simulator.py
    - ポートフォリオシミュレータ（PortfolioSimulator）、日次スナップショット（DailySnapshot）、約定記録（TradeRecord）を実装。
    - execute_orders（SELL 先行、BUY 後処理、スリッページ／手数料考慮、BUY の株数再計算）、mark_to_market（終値で評価）等を実装。
  - src/kabusys/backtest/metrics.py
    - バックテスト指標計算（CAGR, Sharpe, MaxDrawdown, WinRate, PayoffRatio, total_trades）を実装。
  - src/kabusys/backtest/engine.py
    - run_backtest 実装：本番 DB からインメモリ DuckDB へ必要テーブルをコピーして日次ループでシミュレーションを実行。
    - _build_backtest_conn、価格取得ユーティリティ、positions 書き戻し、signals 読込などの補助関数を実装。
  - backtest/__init__.py で主要 API を公開。

- 安全性・堅牢性向上
  - DuckDB 操作でのトランザクション扱い（BEGIN/COMMIT/ROLLBACK）と例外処理を導入。
  - ロギングを適切に追加（info/debug/warning）し、失敗時の診断を補助。
  - .env 読み込みで読み込み失敗を警告により無視（warnings.warn）。

### 変更 (Changed)
- なし（本スナップショットは初期機能の実装を中心とする初回リリース相当）

### 修正 (Fixed)
- .env パーサーの堅牢化:
  - export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、コメントの扱い（クォート無し時の '#' 扱いルール）を実装して現実的な .env フォーマットを広くサポート。
- DuckDB コピー処理の堅牢化:
  - バックテスト用コピーで例外が発生したテーブルはスキップし、警告ログを出すように変更（部分データでの実行を許容）。

### 非推奨 (Deprecated)
- なし

### 削除 (Removed)
- なし

### セキュリティ (Security)
- なし

### 注意事項 / 既知の制限 (Notes / Known limitations)
- 一部機能は意図的に未実装または簡略化されています（今後の実装予定）:
  - トレーリングストップや時間決済（保有 60 営業日超）などは _generate_sell_signals にコメントとして記載されているが未実装。positions テーブルに peak_price / entry_date が必要。
  - features の avg_turnover はユニバースフィルタ用に一時的に用いられるが features テーブル自体には保存しない実装になっています。
  - AI ニューススコアが未登録の場合は中立（0.5）で補完する方針。
  - Bear 判定は _BEAR_MIN_SAMPLES によるサンプル閾値があり、サンプル不足時は Bear とみなさない。
- バックテストでは本番 DB から一定期間のみデータをコピー（start_date - 300 日から）するため、極端に古いデータが必要な解析には注意。
- env 自動読み込みはプロジェクトルートが検出できない場合スキップされます（パッケージ配布後の挙動を考慮）。

---

（今後のリリースでは、運用用 execution 層の実装、監視/通知（monitoring）モジュールの強化、追加の指標・リスク管理ロジックの実装などを予定しています。）