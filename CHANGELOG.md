# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

注: 以下は提供されたソースコードから推測して作成した変更履歴です。

## [Unreleased]

追加予定 / 改善候補（コード中のコメントや未実装箇所に基づく）
- トレーリングストップ実装（現在はコメントで未実装と明記されている）。
- 時間決済（一定保有日数での強制決済）の実装。
- PBR・配当利回り等のバリューファクター拡張。
- positions テーブルに peak_price / entry_date 等を保持してトレーリングロジックをサポート。
- 単体テスト・統合テストの整備（自動テスト向けのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD は存在するが、テストスイートは未付属）。
- ドキュメントの拡充（StrategyModel.md / BacktestFramework.md 等の参照はあるが、パッケージ外ドキュメントとの整合性確認を推奨）。

---

## [0.1.0] - 2026-03-22

初回リリース — 基本設計に基づく主要機能を実装。

### Added
- パッケージ基本情報
  - kabusys パッケージのエントリポイント（src/kabusys/__init__.py）。バージョン 0.1.0 を定義。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml で検出）。
  - export 文やシングル/ダブルクォート、行末コメントなどを考慮した .env パーサを実装。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能（テスト等で利用）。
  - 必須設定を取得する Settings クラスを提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_* 等）。
  - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の検証ロジックを実装。
  - デフォルトの DB パス（DUCKDB_PATH, SQLITE_PATH）を設定。

- 研究（research）モジュール
  - ファクター計算（src/kabusys/research/factor_research.py）
    - モメンタム（1/3/6 ヶ月リターン、MA200乖離）、ボラティリティ（20日 ATR・相対ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER, ROE）を DuckDB 上で計算する関数を提供。
    - データ不足に対する安全な None ハンドリングを実装。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（任意の営業日ホライズンに対応、デフォルト [1,5,21]）。
    - スピアマンのランク相関（IC）計算（rank, calc_ic）。
    - factor_summary による基本統計量出力。
  - research パッケージのエクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - build_features(conn, target_date): research モジュールの生ファクターを統合、ユニバースフィルタ（最低株価・最低平均売買代金）を適用、指定カラムを Z スコア正規化して ±3 でクリップし、features テーブルへ日付単位で UPSERT（トランザクション）する処理を実装。
  - ユニバースフィルタの閾値定義（_MIN_PRICE=300 円, _MIN_TURNOVER=5e8 円）。
  - 欠損値・非有限値への堅牢な処理。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - generate_signals(conn, target_date, threshold=0.6, weights=None):
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - コンポーネントスコアはシグモイド変換や PER 特有の変換などで正規化。
    - デフォルト重み（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）を持ち、ユーザ指定の weights を検証・スケールして統合。
    - Bear レジーム検出（ai_scores の regime_score 平均が負）時は BUY シグナルを抑制。
    - BUY シグナル（final_score >= threshold）と SELL（ストップロス -8% または final_score < threshold）を日付単位で signals テーブルへ置換（トランザクション）。
    - 保有銘柄の価格欠損時は SELL 判定をスキップしログ出力。features に存在しない保有銘柄は final_score=0 と見なし SELL の対象とする。
  - 生成ロジックは発注・execution 層に依存しない設計（DB を通じて発注に渡す想定）。

- バックテストフレームワーク（src/kabusys/backtest/**）
  - ポートフォリオシミュレータ（src/kabusys/backtest/simulator.py）
    - PortfolioSimulator: メモリ内でキャッシュ・ポジション・コストベースを管理し、BUY/SELL の約定ロジックを実装（スリッページ・手数料を考慮、SELL は全量クローズ、BUY は資金・手数料を考慮して株数を再計算）。
    - mark_to_market で日次スナップショット DailySnapshot を記録（終値欠損時は 0 評価で警告）。
    - TradeRecord を記録（約定価格・手数料・SELL 時の realized_pnl）。
  - メトリクス計算（src/kabusys/backtest/metrics.py）
    - CAGR、Sharpe Ratio（無リスク金利=0）、Max Drawdown、勝率、Payoff Ratio、総取引数の計算を提供。
  - バックテストエンジン（src/kabusys/backtest/engine.py）
    - run_backtest(conn, start_date, end_date, ...)：本番 DuckDB からインメモリ DB に期間データをコピーして日次ループを実行。generate_signals を用いた日次シミュレーション、positions の書き戻し、約定（前日シグナルを当日始値で執行）、ポジションサイジング（max_position_pct に基づく配分）を実装。
    - バックテスト用のデータコピーはテーブル単位で日付フィルタを行い、market_calendar は全件コピー。
    - 日次の始値・終値取得ユーティリティと signals 読み出し・positions 更新ユーティリティを実装。
  - backtest パッケージのエクスポート（run_backtest, BacktestResult, DailySnapshot, TradeRecord, BacktestMetrics）。

### Changed
- 初期リリースのため該当なし（新規実装中心）。

### Fixed
- 初期リリースのため該当なし。

### Security
- 初期リリースのため該当なし。

### Notes / Known limitations
- 一部戦略ルール（トレーリングストップ、時間決済など）はコメントで未実装として明示されている。
- generate_signals / build_features は DuckDB のテーブルスキーマに依存するため、スキーマ変更時は互換性確認が必要。
- .env 自動ロードはプロジェクトルート検出に .git または pyproject.toml を使うため、配布後の環境では意図どおり動作しない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
- AI スコア（ai_scores テーブル）が存在しない場合の挙動は中立値や BUY 抑制ロジックによって安全装置が働くよう設計されているが、実運用では ai_scores の有無・品質に注意。

---

過去リリースはありません（初版）。