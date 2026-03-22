# Changelog

すべての重要な変更を記録します。本ファイルは Keep a Changelog の形式に準拠します。  
リリースはセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-22

初回公開リリース。

### 追加
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を定義（src/kabusys/__init__.py）。
  - サブパッケージ: data, strategy, execution, monitoring を公開対象として定義。

- 環境設定 / ロード機構（src/kabusys/config.py）
  - .env/.env.local ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。プロジェクトルートは .git または pyproject.toml を起点に検出。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用途を想定）。
  - .env パーサは export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理に対応。
  - 設定アクセス用 Settings クラスを提供（必須変数取得時に未設定なら ValueError を送出）。
  - デフォルト値と妥当性チェックを実装（KABUSYS_ENV の有効値検証、LOG_LEVEL 検証等）。
  - DB パス設定（DUCKDB_PATH / SQLITE_PATH）を Path 型で取得。

- 戦略関連
  - 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
    - 研究結果（research モジュール）から生ファクターを取得し、ユニバースフィルタ・Z スコア正規化（クリップ ±3）を行って features テーブルへ UPSERT（対象日単位の置換）する build_features(conn, target_date) を実装。
    - ユニバースフィルタは株価 >= 300 円、20 日平均売買代金 >= 5 億円を適用。
    - 正規化対象カラムと処理フローを明確化し、トランザクション＋バルク挿入で原子性を保証する実装。

  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - features と ai_scores を統合して銘柄ごとのコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。最終スコア final_score を重み付き合算で算出し BUY/SELL シグナルを生成する generate_signals(conn, target_date, ...) を実装。
    - デフォルト重み、閾値、ストップロス率等を StrategyModel.md の仕様に沿って定義（デフォルト閾値 = 0.60、ストップロス = -8%）。
    - Bear レジーム判定（AI レジームスコアの平均が負で、サンプル数閾値を満たす場合）により BUY シグナルを抑制。
    - 保有ポジションのエグジット判定（ストップロス、スコア低下）を実装。SELL シグナルは BUY より先に優先される。
    - 欠損データの安全処理（価格欠損時に判定をスキップ、features 未存在銘柄は score=0.0 扱いでSELL判定等）。
    - 重みの検証・再スケーリングを行い、不正な入力はログで警告して無視。

- リサーチ関連（src/kabusys/research/*）
  - ファクター計算（factor_research.py）
    - momentum（1m/3m/6m、MA200乖離）、volatility（ATR20、相対ATR、20 日平均売買代金、volume_ratio）、value（PER、ROE）等の計算関数を実装（prices_daily / raw_financials を参照）。
    - 欠損データや十分なウィンドウがない場合は None を返す安全設計。
  - 特徴量探索ユーティリティ（feature_exploration.py）
    - 将来リターン計算 calc_forward_returns(conn, target_date, horizons)、IC（Spearman ρ）計算 calc_ic、factor_summary（count/mean/std/min/max/median）、rank（同順位は平均ランク、丸めによる ties 対応）を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。
  - research パッケージの公開 API を整理。

- バックテストフレームワーク（src/kabusys/backtest/*）
  - シミュレータ（simulator.py）
    - PortfolioSimulator を実装（BUY/SELL の擬似約定、スリッページ・手数料モデル、保有・平均取得単価管理、日次マーク・トゥ・マーケット、DailySnapshot/TradeRecord を記録）。
    - SELL は保有全量クローズ、BUY は割当資金に基づく株数計算（手数料込み再計算ロジックあり）。
    - 欠損価格に対してログを出し 0 評価で処理するなど堅牢性を確保。
  - メトリクス（metrics.py）
    - CAGR、Sharpe、Max Drawdown、Win Rate、Payoff Ratio、トレード数を計算する calc_metrics と内部関数を提供。
  - エンジン（engine.py）
    - run_backtest(conn, start_date, end_date, ...) を実装。実運用 DB からインメモリ DuckDB へ必要データをコピーしてバックテストを実行（signals/positions を汚さない）。
    - コピー対象テーブルの範囲を限定し、market_calendar は全件コピーする実装。
    - 日次ループ: 前日シグナルの約定 → positions の書き戻し → 終値で評価 → generate_signals の呼び出し → 発注サイズ計算 → 次日の約定、という流れを実装。
    - positions テーブルへの書き戻しは日付単位で削除→挿入（冪等）。
    - get_trading_days を用いた営業日列挙に対応。

### 改善
- データベース操作の原子性確保
  - features / signals への書き込みは削除→挿入の置換処理をトランザクション＋バルク挿入で行い、失敗時はロールバックしログ出力を行う実装に改善。

- 欠損値・外れ値への対処
  - Z スコアは ±3 でクリップし、以降のスコア計算で安定化を図る。
  - 各計算関数は None / 非有限値を明示的に扱い、安全に処理を継続するように設計。

- 設計方針の明文化
  - ルックアヘッドバイアスを防ぐため、全ての計算とシグナル生成は target_date 時点のデータのみを使用する方針を明記。
  - 発注 API や実運用の execution 層への直接依存を持たない、モジュール分離を徹底。

### 修正（実装上の堅牢化）
- .env パースの堅牢化（クォート内のエスケープ処理やインラインコメントの扱いを改善）。
- SQL クエリの NULL 伝播を考慮した true_range / ATR の計算（NULL がある行は true_range を NULL としてカウントを過大評価しない仕様）。
- generate_signals における weights の検証を強化し、不正入力時にデフォルトへフォールバックまたは正規化するよう修正。
- _generate_sell_signals において価格欠損時は SELL 判定全体をスキップしログを出力するなど誤判定防止。

### 既知の制限 / TODO
- 一部仕様はドキュメント（StrategyModel.md / BacktestFramework.md）に基づくが、以下の機能は未実装または簡易実装のまま:
  - トレーリングストップ（positions に peak_price / entry_date 情報が必要）。
  - 時間決済（保有 60 営業日を超える処理）。
  - PBR・配当利回りの計算は未実装。
- execution パッケージの実体はこのリリースでは含まれておらず、発注の実運用接続は別途実装が必要。
- 一部テーブル（例: features, ai_scores のスキーマ）は data.schema 側の定義に依存。

### セキュリティ
- 現段階では機密情報（API トークン等）は .env / 環境変数で管理する想定。Settings._require は未設定時に ValueError を投げるため、運用では .env.example に従って適切に設定してください。

---

今後のリリースでは、execution 層の統合、追加ファクター・リスク管理機能、トレーリングストップ等の実装を予定しています。ご要望や不具合報告は issue へお願いします。