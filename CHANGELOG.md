# CHANGELOG

すべての重要な変更点を記録します。本リポジトリは Keep a Changelog の慣例に従います。  
リリースはセマンティックバージョニングに従います。

## [Unreleased]
（今後の変更履歴をここに記載）

---

## [0.1.0] - 2026-03-22

最初の公開リリース。日本株自動売買フレームワーク「KabuSys」のコア機能を実装しています。以下はコードベースから推測してまとめた主要な追加点、設計方針、注意事項です。

### 追加 (Added)
- パッケージ基礎
  - パッケージ初期化: kabusys/__init__.py にてバージョン情報と公開サブモジュールを定義。
  - サブモジュール構成: data, strategy, execution, monitoring（execution は空の初期化ファイルを含む）。

- 環境設定管理 (src/kabusys/config.py)
  - .env/.env.local 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml で検出）。
  - .env 行パーサー実装（export プレフィックス、シングル/ダブルクォート、エスケープ、行末コメントの扱いに対応）。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 必須環境変数チェック用 Settings クラスを提供（プロパティ経由で各種トークン・パス等を取得）。
  - デフォルト設定:
    - KABUS_API_BASE_URL = "http://localhost:18080/kabusapi"
    - DUCKDB_PATH = "data/kabusys.duckdb"
    - SQLITE_PATH = "data/monitoring.db"
    - KABUSYS_ENV の検証（development/paper_trading/live のみ許容）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）

- ファクター計算（研究モジュール）(src/kabusys/research/factor_research.py)
  - calc_momentum: 1M/3M/6M リターンと 200 日移動平均乖離(ma200_dev) を計算。
  - calc_volatility: ATR（20日）、相対ATR(atr_pct)、20日平均売買代金、出来高比率を計算。
  - calc_value: raw_financials から最新の EPS/ROE を取得し PER/ROE を計算。
  - 各関数は DuckDB の prices_daily / raw_financials テーブルを参照し、date/code をキーとする辞書リストを返す。

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - build_features: research モジュールが出力する raw factor を統合して features テーブルへ日付単位で置換（冪等）する処理を実装。
  - ユニバースフィルタ: 株価 >= 300 円、20日平均売買代金 >= 5億円 を適用。
  - 正規化: 指定カラム（mom_1m, mom_3m, atr_pct, volume_ratio, ma200_dev）を Z スコア正規化し ±3 でクリップ。
  - トランザクション＋バルク挿入により atomic な日次置換を保証。

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - generate_signals: features と ai_scores を統合して final_score を計算し、BUY/SELL シグナルを生成して signals テーブルへ日付単位で置換（冪等）。
  - スコア算出:
    - コンポーネント: momentum / value / volatility / liquidity / news（AI スコア）。
    - 各コンポーネント計算ロジック（シグモイド変換、PER の特殊処理、atr 反転等）を実装。
    - weights のバリデーションと正規化（ユーザー指定は既知キーのみ受け付け、合計が 1.0 に再スケール）。
  - Bear レジーム検出: ai_scores の regime_score 平均が負かつサンプル数 >= 3 の場合に BUY を抑制。
  - SELL 条件（実装済み）:
    - ストップロス（終値 / avg_price - 1 < -8%）
    - スコア低下（final_score < threshold）
  - SELL が BUY より優先されるポリシーを適用（SELL 対象を BUY から除外し、BUY のランクを再付与）。

- 研究用探索ツール (src/kabusys/research/feature_exploration.py)
  - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）に基づく将来リターンを一括取得。
  - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を計算（有効レコード 3 未満は None）。
  - rank: 同順位は平均ランクとするランク関数（丸めで ties 検出を安定化）。
  - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。

- バックテストフレームワーク (src/kabusys/backtest)
  - simulator.py:
    - PortfolioSimulator: メモリ内での約定ロジックとポートフォリオ管理（BUY/SELL の約定・スリッページ・手数料の適用）。
    - DailySnapshot / TradeRecord dataclass を定義。
    - mark_to_market による終値評価と履歴記録。
  - metrics.py:
    - バックテスト指標計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）。
  - engine.py:
    - run_backtest: 本番 DuckDB からインメモリ DB へ必要テーブルをコピーして日次ループでシミュレーションを実行。
    - データコピーは date 範囲フィルタを行い、market_calendar は全件コピー。
    - positions テーブルの書き戻し、signals の読み取り、ポジションサイジング（max_position_pct）等の補助関数を実装。

- エクスポート
  - 各パッケージの __init__ で主要関数/クラスを公開（例: strategy.build_features / strategy.generate_signals / backtest.run_backtest など）。
  - research/__init__.py で研究・分析用ユーティリティをまとめて公開。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### 設計上の注意・既知の制約 (Notes)
- データベース
  - DuckDB を利用する設計になっているため、実行環境に DuckDB が必要。
  - build_features / generate_signals / run_backtest は DuckDB 接続を前提とする。
- 外部 API/実口座アクセス
  - research およびバックテスト用モジュールは外部発注 API を直接叩かない設計（安全性のため）。
- .env 処理
  - 自動ロードはプロジェクトルートの検出に依存（.git または pyproject.toml）。パッケージ配布後やテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 必須環境変数（取得時に例外を投げる）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- 欠損データへの耐性
  - 多くの場所で None/非有限値に対する保護ロジック（スキップ、警告ログ、デフォルト補完）を実装。
- 未実装 / 将来対応候補
  - signal_generator のエグジット条件でトレーリングストップや時間決済は未実装（コード内注記あり）。positions テーブルに peak_price / entry_date があれば実装可能。
- ロギング
  - 各処理で警告・情報ログを出力する設計。LOG_LEVEL は環境変数で制御される。

### 互換性と移行 (Compatibility / Migration)
- 現バージョンは初回リリースのため破壊的変更はなし。
- 環境変数と DB スキーマが期待どおりに存在することを確認してください（features, ai_scores, prices_daily, raw_financials, positions, signals, market_calendar 等のテーブルが前提）。

### セキュリティ (Security)
- トークン等の機密情報は環境変数経由で取得する設計。ソースコードやリポジトリに直接埋め込まないでください。

---

（今後のリリースでは追加/変更/修正点をこのファイルの Unreleased → バージョンに移動して記載してください）