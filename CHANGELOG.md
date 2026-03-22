CHANGELOG
=========
※フォーマットは "Keep a Changelog" に準拠しています。

[Unreleased]
------------

（現時点のコードベースは初回リリース相当の実装が含まれているため、未リリース変更はありません。）

[0.1.0] - 2026-03-22
--------------------

Added
- パッケージ初期リリース。
- 基本モジュール群を実装:
  - kabusys.config
    - .env ファイルおよび環境変数から設定を自動ロードする機能を実装。
    - プロジェクトルート探索（.git / pyproject.toml ベース）により CWD に依存しない自動ロード。
    - .env/.env.local の読み込み順序と保護対象（OS 環境変数を上書きしない）をサポート。
    - export プレフィックス、クォート、バックスラッシュエスケープ、インラインコメント等に対応した堅牢な .env 行パーサ実装。
    - Settings クラスによる設定 API（J-Quants / kabu API / Slack / DB パス / 環境種別 / ログレベルなど）、必須項目未設定時の明示的エラーチェックを提供。
  - strategy.feature_engineering
    - 研究で算出した生ファクターを正規化・合成して features テーブルへ書き込む build_features を実装。
    - ユニバースフィルタ（最低株価・平均売買代金）と Z スコア正規化（±3 でクリップ）を適用。
    - 日付単位での置換（DELETE → BULK INSERT）をトランザクションで行い原子性を保証。
  - strategy.signal_generator
    - features と ai_scores を統合して final_score を算出し、BUY/SELL シグナルを生成する generate_signals を実装。
    - コンポーネントスコア（momentum/value/volatility/liquidity/news）の計算ロジックを実装。
    - 重みの検証・補完・再スケーリング、閾値による BUY 判定、Bear レジーム時の BUY 抑制、SELL 優先ポリシーを実装。
    - positions / prices の欠損時に安全に動作するガードやログ出力を備える。
  - research.factor_research / feature_exploration
    - calc_momentum / calc_volatility / calc_value を実装。prices_daily / raw_financials を用いたファクター計算を提供。
    - calc_forward_returns：任意ホライズンの将来リターン計算（1/5/21 日をデフォルト）を実装。
    - calc_ic：Spearman（ランク）相関による IC 計算を実装。
    - factor_summary / rank：ファクター統計サマリとランク変換ユーティリティを実装。
    - 外部依存を持たない純粋 Python + DuckDB 実装（pandas 等に依存しない）。
  - backtest（engine / simulator / metrics）
    - PortfolioSimulator：擬似約定ロジック（BUY/SELL の順序、スリッページ、手数料、平均取得単価更新、売却時の realized_pnl 計算）を実装。
    - mark_to_market：終値で時価評価し DailySnapshot を記録する機能を実装（終値欠損時は 0 評価して WARN）。
    - run_backtest：本番 DB からインメモリ DuckDB に必要データをコピーして日次ループでシミュレーションを行うバックテストエンジンを実装。
    - _build_backtest_conn：production DB を汚染しないために date 範囲でテーブルをインメモリにコピーする処理を実装（market_calendar は全件コピー）。
    - backtest.metrics：CAGR / Sharpe / Max Drawdown / Win rate / Payoff ratio 等のメトリクス計算を実装。
  - モジュール公開インターフェースの整備（各パッケージ __init__ によるエクスポート設定）。

Changed / Improved
- DB への書き込みは日付単位の置換（DELETE + BULK INSERT）を基本とし、BEGIN/COMMIT/ROLLBACK を使って原子性を確保する設計に統一。
- 各種関数で math.isfinite を多用し NaN/Inf を排除することで数値安定性を向上。
- generate_signals:
  - ユーザー指定 weights の検証（未知キー・非数値・負値のスキップ）と合計が 1.0 でない場合の再スケールを実装。
  - AI スコア未登録銘柄の補完（中立値）ロジックを追加。
- .env ローダ:
  - .env.local を .env の上書きとして扱う（override=True）一方、OS 側の環境変数は protected として上書きしない。
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- sell 判定:
  - 価格欠損時は SELL 判定全体をスキップする（誤クローズ防止）。
  - features に存在しない保有銘柄は final_score=0.0 として扱い、閾値未満なら SELL 対象とする旨をログ出力。

Fixed
- トランザクション中に例外発生した場合の ROLLBACK 失敗に対する警告ログを追加（失敗時も元の例外を再送出）。
- calc_forward_returns / factor 計算類でホライズンやウィンドウ不足時に None を返す動作を明確化し、誤った除算を防止。

Security
- .env 読み込み時に OS 環境変数を保護（protected set）し、誤って上書きされないようにした。

Notes / Known limitations
- 未実装の機能（コード内に注記あり）:
  - トレーリングストップ（positions に peak_price / entry_date が必要）。
  - 時間決済（保有 60 営業日超過の自動決済）。
  - PBR / 配当利回り等一部バリューファクターは未実装。
- research モジュールはあくまで分析用途であり、発注 API や本番口座へのアクセスは行わない設計。
- run_backtest は production DB を直接書き換えないよう注意しているが、使用時はバックアップを推奨。

ライセンス / その他
- 本リリースは初期機能実装のまとめです。以降のバージョンでドキュメント、テスト、型注釈の拡充や追加のトレードルール実装、パフォーマンス最適化を予定しています。