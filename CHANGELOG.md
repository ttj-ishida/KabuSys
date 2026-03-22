CHANGELOG
=========

すべての重要な変更は Keep a Changelog のガイドラインに従って記載しています。
このプロジェクトはセマンティックバージョニングに従います。  

[0.1.0] - 2026-03-22
--------------------

Added
- パッケージ初期リリース (kabusys 0.1.0)
  - パッケージメタ情報
    - src/kabusys/__init__.py にバージョンと公開 API を追加。

- 環境設定管理
  - src/kabusys/config.py
    - .env ファイルまたは環境変数から設定をロードする Settings クラスを実装。
    - プロジェクトルート自動検出: .git または pyproject.toml を基準に探索（CWD 非依存）。
    - .env/.env.local の自動読み込み (優先度: OS 環境 > .env.local > .env)。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env 行パーサを実装:
      - export KEY=val 形式対応
      - シングル/ダブルクォート内のエスケープ処理対応
      - インラインコメントの取り扱い（クォート有無で挙動を分離）
      - 不正行を無視
    - 読み込み時の保護機構:
      - OS 環境変数を protected として .env による上書きを防止（.env.local は override=True がデフォルトだが OS env は保護）。
    - 必須設定取得用の _require ユーティリティ（未設定時は ValueError）。
    - 利用可能な設定:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL (デフォルト), SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - DUCKDB_PATH / SQLITE_PATH のデフォルトパス
      - KABUSYS_ENV (development/paper_trading/live) と LOG_LEVEL の検証
      - is_live / is_paper / is_dev ヘルパー

- 戦略関連
  - src/kabusys/strategy/feature_engineering.py
    - 研究環境の生ファクターを取り込み、ユニバースフィルタ・正規化・クリップを行い features テーブルへ冪等的に書き込む build_features を実装。
    - ユニバースフィルタ: 最低株価 (300 円)、20日平均売買代金 >= 5億円 を採用。
    - Zスコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3でクリップ。
    - DuckDB トランザクションを用いた日付単位の置換（DELETE+bulk INSERT）で原子性を保証。ロールバック検出時のログ出力。

  - src/kabusys/strategy/signal_generator.py
    - features と ai_scores を統合して final_score を計算し、BUY/SELL シグナルを生成して signals テーブルへ冪等的に書き込む generate_signals を実装。
    - コンポーネントスコア: momentum / value / volatility / liquidity / news（AI）を計算するユーティリティ実装（シグモイド変換や欠損時の中立補完 0.5）。
    - 重みの受け取りと正規化:
      - デフォルト重みを定義し、ユーザ指定は検証（未知キー・非数値・負値などを無視）して合計が1にリスケール。
    - Bear レジーム判定: ai_scores の regime_score 平均が負なら Bear（サンプル数閾値あり）。
    - BUY シグナル閾値（デフォルト 0.60）以上で BUY（Bear レジームでは BUY を抑制）。
    - SELL（エグジット）条件実装:
      - ストップロス（終値/avg_price - 1 < -8%）
      - スコア低下（final_score < threshold）
      - 保有銘柄の価格欠損に対するスキップ処理とログ
      - 未実装の条件（将来的に追加予定）: トレーリングストップ、時間決済（設計コメントあり）
    - トランザクションで日付単位置換（DELETE + bulk INSERT）、失敗時の ROLLBACK/ログと例外伝搬。

- リサーチ / ファクター計算
  - src/kabusys/research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離の計算（必要データ不足時は None）。
    - calc_volatility: 20日 ATR, 相対 ATR (atr_pct), 20日平均売買代金, 出来高比率 を計算。true_range の NULL 伝播を制御。
    - calc_value: raw_financials から最新の財務データを取得し PER/ROE を計算（EPS が 0/欠損の場合は None）。
    - DuckDB のウィンドウ関数を活用した効率的 SQL 実装。

  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: target_date から複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括で計算。
    - calc_ic: ファクター値と将来リターンの Spearman ランク相関（IC）計算。サンプル閾値・欠損処理あり。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）計算。
    - 標準ライブラリのみで実装（pandas 等に依存しない設計）。

  - src/kabusys/research/__init__.py で上記 API を公開。

- バックテストフレームワーク
  - src/kabusys/backtest/simulator.py
    - PortfolioSimulator 実装:
      - BUY/SELL の擬似約定（SELL を先に処理、BUY は資金に応じて調整）。
      - スリッページ（BUY:+, SELL:-）と手数料モデルを適用。
      - BUY 時の平均取得単価更新、SELL 時の実現損益計算と TradeRecord 記録。
      - mark_to_market による日次スナップショット（終値欠損時は 0 を評価して警告）。
    - DailySnapshot, TradeRecord のデータ構造定義。

  - src/kabusys/backtest/metrics.py
    - calc_metrics と各種メトリクス実装:
      - CAGR（暦日ベース）、シャープレシオ（無リスク=0、年次化 252 日）、最大ドローダウン、勝率、Payoff Ratio、トータルトレード数。
      - 境界条件（データ不足、ゼロ除算）に対する安全なハンドリング。

  - src/kabusys/backtest/engine.py
    - run_backtest 実装:
      - 本番 DuckDB 接続からインメモリ DuckDB へ必要テーブルを日付範囲でコピー（signals/positions を汚染しない）。
      - 日次ループ: 前日シグナルの約定 → positions 書き戻し → 時価評価 → generate_signals 呼出 → ポジションサイジング → 次日の約定準備。
      - _build_backtest_conn: init_schema(":memory:") によるインメモリ初期化とテーブルコピー。market_calendar は全件コピー。
      - 各種ヘルパー: open/close 価格取得、positions の冪等書き込み、signals 読取。
      - デフォルトパラメータ: 初期資金 10,000,000 円、スリッページ 0.1%、手数料 0.055%、max_position_pct 20%。

  - src/kabusys/backtest/__init__.py で上記 API を公開。

Changed
- （初版のため「Changed」は無し。今後のリリースで追記予定）

Fixed
- （初版のため「Fixed」は無し。今後のリリースで追記予定）

Notes / Implementation details
- DuckDB を主要なデータ格納／SQL 実行基盤として前提。kabusys.data.stats や kabusys.data.schema 等、別ファイル群に依存している（今回のコードベースには一部参照のみ）。
- 外部 API へのアクセスは設計上最小化:
  - research / strategy / backtest モジュールは本番発注 API に依存せず、DuckDB 上の時系列・財務テーブルのみ参照する。
- ログ出力を多用し、データ欠損や異常入力に対して警告や例外で明示的に通知する設計。
- 未実装 / 将来追加予定:
  - トレーリングストップや時間決済（strategy のエグジット条件に記載）
  - 一部のテーブルスキーマ・補助ユーティリティ（data パッケージの実装）に依存

Security
- 環境変数管理はファイル読み込み時に OS 環境を保護する仕組みを導入しており、.env による上書きを意図的に制御可能。
- シークレット（トークン・パスワード等）は Settings._require を通じて必須チェックを行う。

開発者向けメモ
- .env のパースはシンプルなシェル風の仕様に沿うが、複雑なケースは想定外の振る舞いになる可能性があります。特殊文字列や改行を含む値はテストしてください。
- generate_signals の weights 入力は厳密な検証を行うため、外部 UI 等から渡す際は正規化済みの辞書を渡すことを推奨します。
- run_backtest は本番 DB の signals/positions を変更しないよう設計されていますが、バックテスト用に in-memory DB を作成する際のコピー処理で一部テーブルがスキップされる可能性があるためログを確認してください。

今後のリリースで想定する改善点
- ポジションサイジングの拡張（部分利確、部分損切り）
- エグジット条件の拡張（トレーリングストップ・時間決済）
- telemetry / メトリクス出力の強化、可視化用エクスポート
- テストカバレッジの追加（特に .env パース周りと DB コピー処理）

----------------------------------------
（注）この CHANGELOG は提供されたソースコードから機能・設計を推測して作成したものであり、実装以外のファイル（README、ドキュメント、スキーマ定義等）に依存する記述は含めていません。