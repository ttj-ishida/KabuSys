# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
この CHANGELOG はリポジトリ内のソースコードから推測して作成したもので、実際のコミット履歴に基づくものではありません。

## [0.1.0] - 2026-03-26

### Added
- パッケージ初期リリース。日本株自動売買システム「KabuSys」のコア機能群を追加。
  - パッケージメタデータ:
    - src/kabusys/__init__.py に __version__ = "0.1.0"、エクスポート一覧を定義。
  - 環境設定・ローディング:
    - src/kabusys/config.py
      - .env ファイルまたは OS 環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
      - .env / .env.local の優先順位を実装（OS 環境変数 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
      - export KEY=... 形式、クォート付き値（バックスラッシュエスケープ対応）、インラインコメントの処理などを含む堅牢な .env パーサを実装。
      - 環境変数の必須チェック用 _require() と Settings クラスを提供（J-Quants / kabu / Slack / DB パス等のプロパティ）。
      - KABUSYS_ENV / LOG_LEVEL の許容値検証（不正値時は ValueError を発生）。
  - ポートフォリオ構築:
    - src/kabusys/portfolio/portfolio_builder.py
      - 候補選定関数 select_candidates（スコア降順、同点は signal_rank でタイブレーク）。
      - 等金額配分 calc_equal_weights。
      - スコア加重配分 calc_score_weights（全スコアが 0 の場合は等金額にフォールバックし WARNING ログ）。
    - src/kabusys/portfolio/position_sizing.py
      - 株数決定ロジック calc_position_sizes を実装。
      - allocation_method に応じた「risk_based」「equal」「score」方式をサポート。
      - 単元（lot_size）丸め、1銘柄上限（max_position_pct）、ポートフォリオ合計上限（available_cash）に対する aggregate スケーリング（cost_buffer を考慮）。
      - スケールダウン時の再配分で小数端数を lot 単位で補正するアルゴリズムを実装（残差順で追加割当て）。
    - src/kabusys/portfolio/risk_adjustment.py
      - セクター集中制限 apply_sector_cap（既存保有のセクター時価合計に応じて新規候補を除外、"unknown" セクターは除外対象外）。
      - 市場レジームに基づく投下資金乗数 calc_regime_multiplier（"bull"=1.0,"neutral"=0.7,"bear"=0.3、未知レジームは警告の上 1.0 にフォールバック）。
    - src/kabusys/portfolio/__init__.py に主要関数を再エクスポート。
  - ストラテジー（特徴量・シグナル生成）:
    - src/kabusys/strategy/feature_engineering.py
      - 研究モジュール（research）で計算した生ファクターを結合・正規化し features テーブルへ UPSERT（日付単位の置換）で保存。
      - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5億円）を実装。
      - Z スコア正規化、±3 でのクリップ、DuckDB を用いた DB 経由のバルク挿入（トランザクションで原子性保証）。
    - src/kabusys/strategy/signal_generator.py
      - features と ai_scores を統合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算し final_score を算出。
      - AI スコア未登録時に中立値で補完、weights のマージ/正規化、閾値による BUY シグナル生成（デフォルト閾値 0.6）。
      - Bear レジーム検知時には BUY シグナルを抑制（ai_scores の regime_score 集計による判定）。
      - 保有ポジションのエグジット判定（ストップロス -8% / final_score の閾値割れ）による SELL シグナル生成。
      - signals テーブルへの日付単位置換（トランザクション／ROLLBACK ハンドリングを含む）。
    - src/kabusys/strategy/__init__.py に主要 API を再エクスポート。
  - リサーチ・解析:
    - src/kabusys/research/factor_research.py
      - Momentum / Volatility / Value ファクターの算出（mom_1m/3m/6m, ma200_dev, atr_20, atr_pct, avg_turnover, volume_ratio, per, roe 等）。
      - DuckDB SQL を用いた営業日ベースのラグ/移動平均計算。
    - src/kabusys/research/feature_exploration.py
      - 将来リターン calc_forward_returns（複数ホライズンに対応、SQL で一括取得）。
      - IC（Spearman ランク相関）計算 calc_ic、rank ユーティリティ（同順位は平均ランク）。
      - factor_summary（基本統計量）の実装。
    - src/kabusys/research/__init__.py にユーティリティを再エクスポート。
    - src/kabusys/strategy/feature_engineering.py から zscore_normalize を利用。
  - バックテスト:
    - src/kabusys/backtest/metrics.py
      - バックテスト指標の計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）。
    - src/kabusys/backtest/simulator.py
      - PortfolioSimulator クラス（擬似約定、ポートフォリオ状態管理、TradeRecord/DailySnapshot の dataclass）。
      - 約定処理: SELL を先、BUY を後に処理。スリッページ・手数料モデルの引数を受け取り、約定記録を生成。
  - データ・ユーティリティ:
    - DuckDB を前提とした一連のデータ参照・計算処理を実装（features / ai_scores / prices_daily / raw_financials / positions テーブルを参照）。

### Changed
- （初期リリースのため履歴無し）コード中の設計上の注意点や TODO を明文化：
  - position_sizing の lot_size を将来的に銘柄別に拡張する旨の注記。
  - apply_sector_cap の価格欠損時の過少見積り問題の注記。

### Fixed
- （初期リリースのため特定のバグフィックス履歴無し）
- 実装上の堅牢性向上:
  - .env 読み込みに失敗した場合は警告を出して処理を継続（OSError ハンドリング）。
  - DB 書き込み時の例外で ROLLBACK を試み、失敗した場合は警告を出すように安全弁を追加（feature_engineering / signal_generator）。

### Security
- 環境変数読み込み時に OS 環境変数を “protected” として扱い、.env の上書きを制御（誤って OS 環境変数を上書きしない設計）。

### Notes / Known limitations
- 一部アルゴリズムは簡易実装や将来拡張の余地あり（例: position_sizing の銘柄別 lot_size 対応、apply_sector_cap の価格フォールバック）。
- SignalGenerator の未実装項目（トレーリングストップや時間決済）は positions テーブルに peak_price / entry_date 情報が必要で今バージョンでは未対応。
- research モジュールは外部ライブラリに依存せず標準ライブラリ + DuckDB のみで実装されている。
- execution / monitoring 層はパッケージ構成に存在する（名前空間）が、ここに提示されたソースにおいては発注 API への直接呼び出し等は持たない設計（層を分離）。

---

今後のリリースでは、実運用向けの execution 層の具現化（kabu API 連携）、モニタリング（Slack 通知など）、銘柄固有単元対応、さらにバックテスト機能の拡張（部分利確、トレーリングストップ等）などが想定されます。