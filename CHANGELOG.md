# Changelog

すべての重要な変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の規約に従っています。  

※ 日付はコードベースのスナップショットから推定して付与しています。

## [Unreleased]
- 今後のリリースで扱う予定の変更点や改善点をここに記載します。

## [0.1.0] - 2026-03-22

初回公開リリース。日本株自動売買システムのコア機能を実装しています。主要な追加点と設計上の注記は以下の通りです。

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージを追加。エントリポイントで version を "0.1.0" として公開。
  - __all__ に data / strategy / execution / monitoring を含めたモジュール公開。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - プロジェクトルート検出ロジック (_find_project_root) を導入し、__file__ を基準に .git または pyproject.toml を探索して自動的に .env を読み込む。
  - .env の自動読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用途）。
  - .env パース実装: export 形式、クォート文字列中のエスケープ、インラインコメント処理などに対応。
  - 必須環境変数未設定時に ValueError を投げる _require 関数。
  - 設定項目: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV 判定（development / paper_trading / live）、LOG_LEVEL 検証。
  - 環境変数の上書き制御（protected set）を実装し、OS 環境を保護。

- 戦略 / 特徴量処理 (src/kabusys/strategy)
  - feature_engineering.build_features(conn, target_date)
    - research モジュールで計算した生ファクターを取り込み、ユニバースフィルタ（最低株価・最低平均売買代金）を適用、Zスコア正規化・±3クリップ後に features テーブルへ日付単位で UPSERT（トランザクションで原子性保証）。
    - 外れ値処理と欠損値扱いに関するポリシーを明確化。
  - signal_generator.generate_signals(conn, target_date, threshold=0.60, weights=None)
    - features と ai_scores を統合して各銘柄のコンポーネントスコアを計算し、重み付き合算で final_score を算出。
    - Bear レジーム判定（ai_scores の regime_score の平均が負かつ十分なサンプル数がある場合）による BUY 抑制。
    - BUY（threshold 以上）および SELL（エグジット条件）を生成し signals テーブルへ日付単位で置換（トランザクションで原子性保証）。
    - 重みのバリデーションとリスケーリング、AI スコア未登録時の中立補完、SELL 優先ポリシー実装。

- リサーチ（研究用）モジュール (src/kabusys/research)
  - factor_research:
    - calc_momentum(conn, target_date): mom_1m/mom_3m/mom_6m、ma200_dev（200日MA）、データ不足時の None 処理。
    - calc_volatility(conn, target_date): 20日 ATR（atr_20）、相対ATR（atr_pct）、avg_turnover、volume_ratio。
    - calc_value(conn, target_date): raw_financials から最新財務データを取り込み per/roe を算出。
  - feature_exploration:
    - calc_forward_returns(conn, target_date, horizons=[1,5,21]): 各銘柄の将来リターンを複数ホライズンで計算（1クエリでまとめて取得）。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンのランク相関（IC）計算。サンプル不足時は None。
    - factor_summary(records, columns): 各ファクター列について count/mean/std/min/max/median を計算。
    - rank(values): 同順位は平均ランクとするランク付け実装（round による誤差耐性あり）。

- データ処理ユーティリティ
  - research と strategy から利用する zscore_normalize を data.stats 側に想定して参照（実装は別ファイルに存在する前提）。

- バックテストフレームワーク (src/kabusys/backtest)
  - simulator:
    - PortfolioSimulator クラス（メモリ内状態管理）：注文約定ロジック（売り優先→買い、スリッページ・手数料モデル、BUY の株数算出と手数料込み再計算、SELL の全量クローズ、mark_to_market による DailySnapshot 記録）。
    - TradeRecord / DailySnapshot dataclass を定義。
  - metrics:
    - calc_metrics(history, trades) と BacktestMetrics 型を提供。
    - CAGR、Sharpe、Max Drawdown、win rate、payoff ratio、総トレード数の内部実装。
  - engine:
    - run_backtest(conn, start_date, end_date, initial_cash=10_000_000, slippage_rate=0.001, commission_rate=0.00055, max_position_pct=0.20)
      - 本番 DuckDB からインメモリ DuckDB へ必要テーブルをコピーしてバックテスト用接続を構築（_build_backtest_conn）。
      - 日次ループで (1) 前日シグナルの約定、(2) positions の反映、(3) 時価評価、(4) generate_signals の呼び出し、(5) ポジションサイジング→注文生成と実行のワークフローを実装。
      - date 範囲でのテーブルコピー制御、market_calendar のコピー、コピー失敗時の警告ログを実装。

### 変更 (Changed)
- （初期リリースのため該当なし）  
  - 将来的なバージョンでの設計変更点を想定。

### 修正 (Fixed)
- トランザクションのロールバック失敗時に logger.warning を出す保護処理を追加（feature_engineering / signal_generator の DB 書き込み周り）。
- .env 読み込みでファイルオープンに失敗した場合に warnings.warn で通知し処理を継続するように実装。

### 非推奨 (Deprecated)
- （初期リリースのため該当なし）

### 削除 (Removed)
- （初期リリースのため該当なし）

### セキュリティ (Security)
- 環境変数の自動上書きを OS 環境変数が保護されるよう protected set で防止（.env を読み込む際に既存の OS 環境変数を保護）。
- 必須トークン等は未設定時に明示的に失敗するため、誤った動作を未然に防止。

### 既知の制限と注意点 (Notes / Known limitations)
- 未実装のエグジット条件:
  - トレーリングストップ（peak_price に依存）および時間決済（保有 60 営業日超）は実装予定。_generate_sell_signals 内に TODO 記載。
- ai_scores が不十分な場合の Bear 判定:
  - regime 判定はサンプル数閾値（_BEAR_MIN_SAMPLES）未満だと Bear とみなさない実装（誤判定防止）。
- features / signals / positions への書き込みは「日付単位の置換（DELETE → INSERT）」で行われるため、外部からの同時書き込みや並列実行時は注意が必要。
- データ依存:
  - 多くの処理は DuckDB の prices_daily / raw_financials / market_calendar 等のテーブル構造に依存するため、スキーマ変更時は該当クエリの更新が必要。
- data.stats.zscore_normalize の具象実装は別モジュールに依存している想定。

---

今後のリリースにて以下の改善が見込まれます（例）：
- execution 層（kabuステーション連携）と monitoring（Slack 通知等）の具体実装。
- パフォーマンス最適化（大規模銘柄数での DuckDB クエリ最適化、並列化）。
- ユニットテストと CI の充実、API ドキュメントの拡充。

以上。