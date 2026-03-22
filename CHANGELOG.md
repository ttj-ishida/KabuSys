# Changelog

すべての重要な変更はこのファイルに記録します。  
このファイルは Keep a Changelog の書式に準拠しています。  

なお、このリリースノートは提示されたコードベースから実装内容・設計意図を推測して作成したものです。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-22

### Added
- パッケージ初期リリース。モジュール群と主要機能を提供。
- 基本パッケージ情報
  - kabusys.__version__ を "0.1.0" に設定。
  - パッケージの公開 API を __all__ で定義（data, strategy, execution, monitoring）。
- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を読み込む。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を設定することで自動ロードを無効化可能。
  - .env パーサーは export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理、空行/コメント行の無視などに対応。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス等の設定値をプロパティとして取得可能。必須キー未設定時に明示的なエラーを送出。
  - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の値検証を実装。
- 戦略（kabusys.strategy）
  - feature_engineering.build_features:
    - research モジュールで計算された生ファクターを統合・正規化して features テーブルへ書き込む。
    - ユニバースフィルタ（最低株価・最低平均売買代金）を適用。
    - 指数ではなく Z スコア正規化を行い ±3 でクリップして外れ値の影響を抑制。
    - 日付ごとに一括削除→挿入するトランザクショナルな置換（原子性を確保）。
  - signal_generator.generate_signals:
    - features と ai_scores を統合して各銘柄の最終スコア（final_score）を算出。
    - momentum/value/volatility/liquidity/news のコンポーネントスコアを計算し、重み付き合算で final_score を得る（デフォルト重みは StrategyModel.md に準拠）。
    - AI レジームスコアの平均から Bear レジームを判定し、Bear 時は BUY シグナルを抑制。
    - BUY 閾値（デフォルト 0.60）を超えた銘柄を BUY、保有銘柄に対してストップロス（-8%）やスコア低下で SELL を生成。
    - 欠損コンポーネントは中立値 0.5 で補完して不当な降格を回避。
    - signals テーブルへの書き込みは日付単位の置換（トランザクション＋バルク挿入）で冪等性を確保。
    - 重みの入力検証（未知キー・非数値・負値・NaN/Inf を無視）、合計が 1 でない場合の再スケール実装。
- リサーチ（kabusys.research）
  - factor_research モジュール:
    - momentum（1M/3M/6M, ma200_dev）、volatility（ATR/相対ATR/平均売買代金/volume_ratio）、value（PER/ROE）等のファクターを DuckDB を用いて計算。
    - 欠損データや十分なウィンドウがない場合は None を返す設計。
  - feature_exploration モジュール:
    - 将来リターン（複数ホライズン）の一括取得（1,5,21 日など）を実装。ホライズンバリデーションあり。
    - Spearman（ランク）相関（IC）計算、ランク付け（同順位は平均ランク）、およびファクター統計サマリー機能を提供。
    - 標準ライブラリのみで実装され、pandas 等に依存しない方針。
- バックテスト（kabusys.backtest）
  - engine.run_backtest:
    - 本番 DuckDB からデータを日付範囲でインメモリ DuckDB（:memory:）にコピーしてバックテストを実行。signals / positions を汚染しない設計。
    - generate_signals を用いた日次ループ（約定→positions書き戻し→時価評価→シグナル生成→ポジションサイジング）。
  - simulator.PortfolioSimulator:
    - メモリ内でポートフォリオと約定を管理。SELL を先に処理し、BUY は残り資金で配分。
    - スリッページ率・手数料率を考慮して約定価格・手数料を計算。
    - BUY：資金不足時は購入株数を手数料込みで再計算。
    - SELL：保有全量をクローズし realized_pnl を記録。
    - mark_to_market により DailySnapshot を記録（終値欠損時は 0 評価し WARNING）。
  - metrics.calc_metrics:
    - CAGR、シャープレシオ、最大ドローダウン、勝率、ペイオフレシオ、総取引数を算出するユーティリティを実装。
    - 個別の計算は十分なデータがない場合に安全に 0.0 を返す（例: サンプル不足、分散ゼロなど）。

### Changed
- 大きな変更履歴は初版のため該当なし（このリリースが初回実装）。

### Fixed
- 初期リリースのため、コード中で扱っている種々の欠損・境界ケースに対して堅牢化を行っている点を明記：
  - .env 読み込みのファイルアクセスエラーは警告を出して読み込みをスキップ。
  - .env のクォート内でのバックスラッシュエスケープに対応。
  - 数値検証で NaN/Inf を除外する処理を各所に追加。
  - DB 書き込みでトランザクション失敗時にロールバックを試み、ロールバック失敗は警告ログに記録。
  - シグナル生成・売却判定で価格欠損時は処理をスキップし警告を出す。

### Deprecated
- なし

### Removed
- なし

### Security
- なし

---

注意事項（既知の制約・未実装機能）
- トレーリングストップや時間決済（保有60営業日超）等の一部エグジット条件は未実装で、positions テーブルに peak_price / entry_date 等の情報が必要（コメントとして記載あり）。
- execution パッケージは初期構成にとどまり、実際の発注 API との接続ロジックは本コードベースには含まれていない（戦略層は発注層に依存しない設計を目指す）。
- AI スコア周りは ai_scores テーブルの存在に依存する。サンプル数不足時の Bear 判定回避ロジックを導入しているが、AI スコアの収集・更新は別実装が必要。

もしリリース日や追加注釈の修正・追記をご希望であればお知らせください。