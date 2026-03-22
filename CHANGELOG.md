# Changelog

すべての重要な変更はこのファイルに記載します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを使用します。

※この CHANGELOG は提供されたコードベースからの推測に基づいて作成した初版の変更履歴です。

## [Unreleased]

(なし)

## [0.1.0] - 2026-03-22

初回リリース。日本株自動売買システム「KabuSys」の基礎モジュールを追加。

### 追加 (Added)
- パッケージ構成
  - パッケージ名: kabusys（バージョン: 0.1.0）
  - 主要サブパッケージ: data, strategy, execution, monitoring（__all__ に公開）

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダを実装
    - 自動ロードの優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルート検出: .git または pyproject.toml を親ディレクトリから探索して判定（CWD 非依存）
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env パーサ実装（_parse_env_line）
    - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、コメント判定の取り扱い
  - .env 読み込みの保護機構: OS 環境変数を protected として上書き回避
  - Settings クラスを提供（settings）
    - 必須環境変数を取得する _require() を実装（未設定時は ValueError）
    - J-Quants / kabu API / Slack / DB パスなどのプロパティを定義
    - KABUSYS_ENV のバリデーション（development / paper_trading / live）
    - LOG_LEVEL のバリデーション（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - duckdb / sqlite ファイルパスのデフォルト値と Path 変換

- 戦略: 特徴量作成 (src/kabusys/strategy/feature_engineering.py)
  - 研究モジュール（research）で算出した生ファクターを統合・正規化して features テーブルへ保存する build_features(conn, target_date) を実装
  - 処理概要:
    - calc_momentum / calc_volatility / calc_value から生ファクターを取得
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用
    - 指定列について Z スコア正規化（zscore_normalize を利用）、±3 にクリップ
    - 日付単位で冪等な置換（DELETE + bulk INSERT）をトランザクションで行い原子性を確保
  - エラーハンドリング: トランザクション失敗時にロールバックを試み、ロールバック失敗は警告ログ

- 戦略: シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - features と ai_scores を統合して final_score を計算し BUY/SELL シグナルを生成する generate_signals(conn, target_date, ...) を実装
  - 特徴:
    - コンポーネントスコア: momentum / value / volatility / liquidity / news（AI）
    - スコア変換: Z スコア → シグモイド変換、欠損は中立 0.5 で補完
    - デフォルト重みと閾値: momentum=0.40, value=0.20, volatility=0.15, liquidity=0.15, news=0.10、BUY 閾値=0.60
    - 外部から与えられた weights は検証・補完後に正規化（不正値は無視）
    - Bear レジーム判定: ai_scores の regime_score 平均が負（サンプル数が所定数未満なら Bear 判定しない）
    - SELL 条件（エグジット）:
      - ストップロス: 終値 / avg_price - 1 < -8%
      - スコア低下: final_score < threshold
      - SELL を優先し BUY から除外
    - signals テーブルへの日付単位置換（トランザクションで原子性保証）
  - ログ出力および警告（データ欠損時の挙動の明示）

- 研究支援モジュール (src/kabusys/research)
  - feature_exploration.py
    - calc_forward_returns(conn, target_date, horizons=[1,5,21]): 将来リターンを一括 SQL で取得（ホライズン検証あり）
    - calc_ic(...): スピアマンランク相関（Information Coefficient）を実装（有効サンプル >= 3）
    - factor_summary(...): count/mean/std/min/max/median を計算するサマリ
    - rank(values): 同順位は平均ランク（丸めで ties 対策）
  - factor_research.py
    - calc_momentum / calc_volatility / calc_value を実装
      - momentum: mom_1m/mom_3m/mom_6m, ma200_dev（200 行未満で None）
      - volatility: atr_20, atr_pct, avg_turnover, volume_ratio（ウインドウ不足時は None）
      - value: per / roe（raw_financials の target_date 以前の最新レコードを使用）
    - DuckDB SQL を多用し、prices_daily / raw_financials のみ参照（外部 API へアクセスしない）

- バックテストフレームワーク (src/kabusys/backtest)
  - simulator.py
    - PortfolioSimulator: メモリ内で約定・保有管理を行うシミュレータ
      - BUY/SELL の約定ロジック（始値、スリッページ、手数料、全量クローズ等）
      - trades（TradeRecord）と日次スナップショット（DailySnapshot）を記録
      - mark_to_market: 終値で時価評価（終値欠損時は 0 として警告）
  - metrics.py
    - calc_metrics(history, trades) を実装（CAGR、Sharpe、最大ドローダウン、勝率、ペイオフ比、トレード数）
    - 内部計算ルーチンを分離して実装
  - engine.py
    - run_backtest(conn, start_date, end_date, ...) を実装
      - 本番 DB からインメモリ DuckDB へ必要テーブルをコピー（signals/positions を汚染しない）
      - 日次ループ: 前日シグナル約定 → positions 書き戻し → mark_to_market → generate_signals → ポジションサイジング → 次日約定リスト作成
      - ヘルパー: _build_backtest_conn（スキーマ初期化）, _fetch_open_prices/_fetch_close_prices, _write_positions, _read_day_signals
      - デフォルトのスリッページ 0.001、手数料率 0.00055、1銘柄最大 20% の割合などを採用
    - run_backtest は BacktestResult（history, trades, metrics）を返す

- パッケージ初期化と公開 API
  - 各サブパッケージの __init__ で主要関数/クラスを公開（backtest, research, strategy など）

### 変更 (Changed)
- 初回リリースのため該当なし

### 修正 (Fixed)
- 初回リリースのため該当なし

### セキュリティ (Security)
- 初回リリースのため該当なし

### 備考 / 実装上の注意
- 多くのモジュールは DuckDB 接続（duckdb.DuckDBPyConnection）を受け取り、prices_daily / raw_financials / features / ai_scores / positions / market_calendar テーブルを前提としている。実行にはこれらのスキーマが必要。
- DB 書き込み操作（features, signals, positions）は日付単位の置換（DELETE + INSERT）を行い、トランザクションで原子性を担保している。
- 多くの箇所で欠損データに対する防御的実装（None チェック、finite チェック、ログ出力）が入っているため、実運用時はログを確認しデータ品質を保つこと。
- settings は必須環境変数未設定時に ValueError を投げるため、実行環境での .env 設定または CI/CD/環境変数の整備が必要。
- AI スコアやレジーム情報が未存在のケースに対して中立値で補完する設計のため、AI スコア未導入時でもシステムは動作する（ただし機能の一部が弱まる）。

### 互換性 / マイグレーション
- 初回リリースのため後方互換性に関する注意点はなし。将来のリリースでは features/signals/positions のスキーマ変更や重み・閾値のデフォルト変更が互換性に影響する可能性あり。

---

作成: 初版（リリース 0.1.0）  
必要があればこの CHANGELOG を元にリリースノートを拡張（例: 具体的な SQL スキーマ、サンプル .env、実行手順）できます。どの程度の詳細を追加するか指示ください。