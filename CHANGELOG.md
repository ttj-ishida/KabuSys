CHANGELOG
=========
すべての変更は Keep a Changelog の形式に従い、セマンティックバージョニング（MAJOR.MINOR.PATCH）を使用しています。

[0.1.0] - 2026-03-22
-------------------

Added
- パッケージ初期リリース。モジュール構成と公開 API を導入。
  - kabusys.__version__ = "0.1.0"、主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。
- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動ロードする仕組みを追加。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env のパース器を実装（コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応）。
  - OS 環境変数を保護する protected 機能を実装し、.env.local を .env より優先して上書きする挙動を実現。
  - 必須環境変数取得用 _require()、設定値の検証（KABUSYS_ENV, LOG_LEVEL）と便利プロパティ（is_live / is_paper / is_dev）を提供。
  - デフォルトの API ベース URL や DB パス（DUCKDB_PATH / SQLITE_PATH）などのデフォルト値を定義。
- 戦略関連（src/kabusys/strategy）
  - 特徴量エンジニアリング（feature_engineering.build_features）
    - research で計算された生ファクターを取り込み、ユニバースフィルタ（最低株価・平均売買代金）を適用。
    - 指定の数値カラムを z-score 正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップして外れ値を抑制。
    - features テーブルへ日付単位で置換（トランザクション＋バルク挿入）することで冪等性と原子性を確保。
    - 価格取得は target_date 以前の最新価格を参照して休場日や当日の欠損に対応。
  - シグナル生成（signal_generator.generate_signals）
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum, value, volatility, liquidity, news）を計算し、重み付け合算で final_score を算出。
    - デフォルト重みを定義し、ユーザー重みを部分的に上書き可能（入力検証と合計が 1.0 でない場合の再スケール対応）。
    - Bear レジーム検知（AI の regime_score 平均が負の場合、かつ十分なサンプル数が存在する場合）で BUY シグナルを抑制。
    - BUY/SELL の判定ロジックを実装（BUY: final_score >= threshold、SELL: ストップロス率 -8% やスコア低下）。
    - positions を参照してエグジット判定を行い、SELL シグナルを優先（BUY から除外）するポリシーを実装。
    - signals テーブルへ日付単位の置換（トランザクション＋バルク挿入）で冪等性を確保。失敗時はROLLBACK を試みる。
- 研究用ユーティリティ（src/kabusys/research）
  - ファクター計算（factor_research.calc_momentum / calc_volatility / calc_value）
    - prices_daily / raw_financials を用いた各種ファクター（モメンタム、MA200乖離、ATR、相対ATR、平均売買代金、出来高比率、PER, ROE）を計算。
    - データ不足時は None を返すなど堅牢に設計。
  - 特徴量探索（feature_exploration）
    - 将来リターン calc_forward_returns（複数ホライズンに対応、入力検証、1クエリで取得）。
    - IC（Spearman の ρ）計算 calc_ic と rank ユーティリティ（同順位は平均ランク、丸めで ties の扱いを安定化）。
    - factor_summary による基本統計（count, mean, std, min, max, median）。
  - research パッケージは外部ライブラリに依存せず、DuckDB と標準ライブラリのみを使用する方針。
- バックテスト（src/kabusys/backtest）
  - シミュレータ（simulator.PortfolioSimulator）
    - BUY/SELL の擬似約定ロジック、スリッページ・手数料の適用、平均取得単価管理、全量クローズの挙動を実装。
    - SELL を先に処理することで資金確保を行う設計。
    - mark_to_market で終値評価、終値欠損時は 0 で評価して警告を出力。
  - メトリクス（metrics.calc_metrics）
    - CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades を計算するユーティリティを提供。入力チェック（データ不足時の安全フォールバック）を実装。
  - バックテストエンジン（engine.run_backtest）
    - 本番 DB から日付範囲を限定してインメモリ DuckDB へデータをコピー（signals / positions を汚染しない）。
    - 日次ループ: 前日シグナルの約定 → positions 書き戻し → mark-to-market → generate_signals（bt_conn上）→ シグナル読み取り → 発注（シミュレータへ渡す）を実行。
    - get_trading_days の利用により営業日リストに基づくシミュレーションを実施。
    - コピー対象テーブルについてはエラー時に警告を出してコピーをスキップする堅牢性を実装。
- パブリック API のエクスポートを各モジュールで整理（strategy/__init__.py, backtest/__init__.py, research/__init__.py など）。

Changed
- SQL クエリのスキャン範囲にバッファを導入して週末・祝日欠損を扱いやすくし、パフォーマンスと堅牢性を改善（例: momentum/volatility の scan 範囲や forward returns の end_date 計算）。
- DB 書き込み操作は日付単位の削除→挿入のパターンを採用し、トランザクションで包むことで冪等性・原子性を確保。例外時には ROLLBACK を試み、ROLLBACK 失敗時は警告をログに出力。

Fixed
- 欠損データに対する保護:
  - prices が取得できない場合は SELL 判定をスキップして誤クローズを防ぐ（signal_generator._generate_sell_signals）。
  - features に存在しない保有銘柄は final_score=0 として扱う旨を明記し、ログに警告を出力。
  - mark_to_market で終値欠損時に 0 評価して警告を出す実装を追加。
- .env パーサーの強化:
  - 引用符付き文字列内のバックスラッシュエスケープを正しく処理するよう改善。
  - コメントの認識ルールを明確化（クォートなしでは '#' の直前が空白/タブならコメントとみなす）。
- 数値・重みの検証強化:
  - generate_signals() の weights 入力検証を追加し、不正値はログでスキップ、合計が 1 でない場合はリスケールまたはデフォルトにフォールバック。

Known limitations / Not implemented
- 一部の戦略ルールは未実装として明記:
  - トレーリングストップ（peak_price に基づく -10% 等）は未実装（positions テーブルに peak_price / entry_date が必要）。
  - 時間決済（保有 60 営業日超過）も未実装。
  - PBR・配当利回り等のバリューファクターは現バージョンで未実装。
- 発注・実マーケット接続層（execution）がこのリリースで具体的な API 呼び出しロジックを含まない（execution パッケージの実装は別途）。
- 部分利確・部分損切りには未対応（SELL は全量クローズ）。
- 一部の統計関数はサンプル数が少ない場合に None を返す設計（安全優先）。

Security
- .env 読み込みで OS 環境変数が保護される（.env により既存の OS 環境変数を上書きしない既定の挙動、.env.local は上書きを許可するが protected に含まれるキーは無視）。
- 自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を提供（テストや CI 用）。

その他（実装上の設計方針）
- ルックアヘッドバイアス防止のため、すべての計算は target_date 時点のデータのみを参照する設計（features / signals / research 関数群）。
- 外部依存を極力排し、DuckDB と標準ライブラリのみで動作することを目標に実装。
- ログレベルのデフォルトは INFO。設定ミスや不正な環境変数値は ValueError または警告ログで明示する。

今後の予定（候補）
- execution 層の具体的なブリッジ実装（kabu API 等）とモニタリング周りの実装強化。
- 部分決済やトレーリングストップの実装、より豊富なバリューファクター（PBR, 配当利回りなど）。
- テストカバレッジの拡充（特に DB 書き込みトランザクションやエッジケース）。