CHANGELOG
=========

すべての変更は SemVer に従います。  
この CHANGELOG は Keep a Changelog のフォーマットに準拠しています。

Unreleased
----------

（現在未リリースの変更はここに記載します）

0.1.0 - 2026-03-22
-----------------

初回リリース。日本株自動売買フレームワーク「KabuSys」の基本機能を実装しました。
設計方針としては、発注・本番APIへの直接依存を避け、DuckDB を用いたデータ駆動型の戦略実行・研究・バックテスト基盤を提供します。主な追加項目は以下の通りです。

Added
- パッケージ基礎
  - kabusys パッケージ初期化（__version__ = 0.1.0）。
  - public API のエクスポート: data / strategy / execution / monitoring（将来拡張想定）。

- 設定・環境変数管理（kabusys.config）
  - .env ファイル自動ロード機能（プロジェクトルートを .git または pyproject.toml で検出）。
  - .env パーサ実装（コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応）。
  - .env 読み込み時の上書き制御（override）と保護キー（OS 環境変数を破壊しないための protected）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - 必須環境変数取得メソッド _require と Settings クラス（J-Quants / kabuAPI / Slack / DB パス / ログレベル / 環境判定等）。
  - 環境値のバリデーション（KABUSYS_ENV、LOG_LEVEL）。

- 研究（research）モジュール
  - factor_research:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev の計算。
    - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio の計算（true_range の NULL 伝播を正確に扱う実装）。
    - calc_value: per / roe の算出（raw_financials と prices_daily の組合せ）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターン計算（複数ホライズン対応・入力検証）。
    - calc_ic: Spearman のランク相関（IC）計算（ties 対応、最小サンプルチェック）。
    - factor_summary: count/mean/std/min/max/median の統計サマリー計算。
    - rank: 同順位は平均ランクとするランク化ユーティリティ（丸めによる ties 検出改善）。
  - research パッケージ __init__ で主要関数を再エクスポート。

- 特徴量エンジニアリング（strategy.feature_engineering）
  - build_features(conn, target_date):
    - research モジュールの生ファクターを取得し、ユニバースフィルタ（最低株価・最低平均売買代金）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）し ±3 でクリップ。
    - features テーブルへ日付単位の置換（DELETE → INSERT のトランザクション実行で冪等を保証）。
    - DuckDB を使った価格取得・バルク挿入の実装。

- シグナル生成（strategy.signal_generator）
  - generate_signals(conn, target_date, threshold=0.60, weights=None):
    - features と ai_scores を統合。各銘柄の momentum/value/volatility/liquidity/news コンポーネントスコアを算出。
    - コンポーネントの欠損は中立値 0.5 で補完。
    - AI の regime_score による Bear 判定（サンプル不足時は判定しない）。Bear 時は BUY を抑制。
    - BUY シグナルは final_score >= threshold。SELL は保有ポジションに対するストップロス（-8%）やスコア低下で判定。
    - weights の入力検証（未知キー無視、数値検証、負値/NaN/Inf 無視）、総和が 1 でない場合のリスケール処理。
    - signals テーブルへの日付単位置換（トランザクション＋バルク挿入）。
    - 価格欠損や positions/price の不整合時に警告ログを出力して安全側に動作。

- バックテスト（backtest）
  - simulator:
    - PortfolioSimulator: BUY/SELL の擬似約定ロジック（スリッページ・手数料モデル、全量クローズ、平均取得単価の維持）。
    - mark_to_market による DailySnapshot 記録（終値欠損は 0 評価で警告）。
    - TradeRecord / DailySnapshot の dataclass。
  - metrics:
    - calc_metrics: CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total trades を計算する。
    - 内部実装に基づく各指標計算（年次化等の仕様はドキュメントに準拠）。
  - engine:
    - run_backtest(conn, start_date, end_date, ...):
      - 本番 DB からインメモリ DuckDB へ必要データをコピー（signals/positions を汚染しない）。
      - 日次ループでの注文約定、positions の書き戻し、時価評価、シグナル生成、発注リスト作成までを実行。
      - _build_backtest_conn にて date 範囲でのテーブルコピー、market_calendar の全件コピー。
      - positions の書き戻し・signals の読み取り等のヘルパーを提供。

- 全体設計上の注意点（ドキュメント・ログ）
  - 多くの関数に docstring を付与し、参照するテーブル・想定入力・返り値の仕様を明記。
  - DB 書き込み時にトランザクションを使用し、例外発生時は ROLLBACK を試みる（ROLLBACK 失敗時は警告）。
  - 外部 API への直接呼び出しは最小限に抑え、本番発注層（execution）とは分離した設計。
  - ロギングを多用し異常系を知らせる（警告・情報・デバッグログ）。

Changed
- （初版のため過去バージョンからの差分はありませんが）設計上の重要なガイドラインを実装:
  - ルックアヘッドバイアスを防ぐため、target_date 時点のデータのみを利用する方針を各モジュールで徹底。
  - 冪等性確保のため、日付単位の DELETE → INSERT パターンを採用（トランザクションで原子性を保証）。

Fixed
- 初版リリースでの堅牢性向上:
  - .env 読み込み失敗時の警告（OSError を warnings.warn）。
  - パース時のクォート内バックスラッシュエスケープやインラインコメント処理を正しく扱う実装。
  - 係数やスコアの NaN / Inf / 非数値に対する防御的処理（無効値の除外、中立補完、警告ログ）。

Security
- 環境変数ロード時に OS 環境変数を上書きしないデフォルト挙動を採用。上書きする場合でも protected キーは尊重。
- KABUSYS_DISABLE_AUTO_ENV_LOAD によりテスト環境等で自動読み込みを無効化可能。

Migration notes
- 初期リリースのため破壊的変更はありませんが、以下に注意してください:
  - Settings.jquants_refresh_token や slack_bot_token 等は必須（_require により未設定時は ValueError）。
  - backtest.run_backtest は本番 DB からデータをコピーするため、適切なテーブル（prices_daily, features, ai_scores, market_regime, market_calendar 等）が存在する必要があります。
  - generate_signals / build_features は DuckDB 接続と期待するスキーマを前提としています。kabusys.data.schema.init_schema を用いた初期化を推奨します。

既知の制限・TODO
- signal_generator の SELL 判定におけるトレーリングストップや時間決済は未実装（注記あり）。
- feature_engineering では avg_turnover をフィルタに用いるが features テーブルへは保存していない（フィルタ用のみ）。
- calc_forward_returns はホライズン上限 252 営業日を想定している（入力検証あり）。
- execution 層（実際の発注・Kabu API 連携）は分離されており、実装は今後の課題。

付記
- 各モジュールの実装上の詳細・設計仕様はソース内の docstring および参照ドキュメント（StrategyModel.md, BacktestFramework.md, Research ドキュメント等）を参照してください。