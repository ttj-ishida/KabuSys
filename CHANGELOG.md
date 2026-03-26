Keep a Changelog準拠の CHANGELOG.md（日本語）

すべての重要な変更点をこのファイルに記録します。セマンティックバージョニングを採用しています。

Unreleased
----------
※現時点のリリース差分は 0.1.0 が初回公開（以下参照）。将来の変更はここに記載します。

0.1.0 - 2026-03-26
------------------
Added
- 初回リリース。日本株自動売買システム "KabuSys" のコアモジュール群を追加。
  - パッケージエントリポイント
    - src/kabusys/__init__.py: パッケージ名、バージョン (__version__ = "0.1.0") と公開モジュールを定義。
  - 環境設定管理
    - src/kabusys/config.py:
      - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装（プロジェクトルート判定は .git または pyproject.toml）。
      - 読み込み優先順位: OS 環境変数 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
      - .env パーサーは export 形式、クォート・エスケープ、インラインコメントを扱う実装。
      - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 環境種別・ログレベル等のプロパティを公開。必須環境変数取得時のエラー（ValueError）を明示。
      - デフォルト:
        - KABU_API_BASE_URL: http://localhost:18080/kabusapi
        - DUCKDB_PATH: data/kabusys.duckdb
        - SQLITE_PATH: data/monitoring.db
      - env（KABUSYS_ENV）: development/paper_trading/live の検証、log_level の検証を実装。
  - ポートフォリオ構築（純関数群）
    - src/kabusys/portfolio/portfolio_builder.py:
      - select_candidates: スコア降順、同点時は signal_rank 昇順で上位 N を選択。
      - calc_equal_weights: 等金額配分（各銘柄 1/N）。
      - calc_score_weights: スコア正規化配分（合計スコアが 0 の場合は等金額にフォールバックし WARNING を出力）。
    - src/kabusys/portfolio/risk_adjustment.py:
      - apply_sector_cap: セクター別の既存エクスポージャが閾値を超える場合、新規候補を除外（"unknown" セクターは適用除外）。
      - calc_regime_multiplier: market regime（"bull"/"neutral"/"bear"）に応じた投下資金乗数を返却（未知レジームは 1.0 にフォールバックし WARNING）。
    - src/kabusys/portfolio/position_sizing.py:
      - calc_position_sizes: allocation_method("risk_based","equal","score") に基づいて発注株数を算出。ロット丸め、per-stock 上限、aggregate cap（利用可能現金に合わせたスケールダウン）、cost_buffer（手数料・スリッページ見積り）を考慮。
      - risk_based: 損切り率(stop_loss_pct) とリスク許容率(risk_pct)から株数を決定。
      - 等金額/スコア基準: weight による配分、max_utilization によるポジション利用率調整。
      - TODO を含む拡張点（銘柄別 lot_size サポートの想定）。
  - ストラテジー（特徴量・シグナル）
    - src/kabusys/strategy/feature_engineering.py:
      - build_features: research モジュール（calc_momentum/calc_volatility/calc_value）から生ファクターを取得し、ユニバースフィルタ（最低株価 300 円・20日平均売買代金 5 億円）を適用。Z スコア正規化（zscore_normalize を使用）、±3 でクリップし features テーブルへ日付単位で UPSERT（トランザクションで原子性確保）。
    - src/kabusys/strategy/signal_generator.py:
      - generate_signals: features と ai_scores を統合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。最終スコア final_score を重み付き合算（デフォルト重みは momentum 0.40 等）。Bear レジーム検出時は BUY シグナル抑制。BUY 閾値デフォルト 0.60。SELL シグナルはストップロス（-8%）およびスコア低下を判定。signals テーブルへ日付単位で置換して書き込み。
      - AI スコア未登録時の動作: ニューススコアは中立（0.5）補完、レジーム判定はサンプル数不足時に Bear とみなさない（誤判定防止）。
  - リサーチ（ファクター計算・解析）
    - src/kabusys/research/factor_research.py:
      - calc_momentum / calc_volatility / calc_value: DuckDB 上の prices_daily/raw_financials テーブルから SQL ウィンドウを活用して各種ファクター（mom_1m/3m/6m, ma200_dev, atr_20, atr_pct, avg_turnover, volume_ratio, per, roe）を計算。
    - src/kabusys/research/feature_exploration.py:
      - calc_forward_returns: 指定ホライズンの日数（デフォルト [1,5,21]）に対する将来リターンを一括取得。
      - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を算出（有効レコード < 3 の場合は None）。
      - factor_summary, rank: 要約統計量・ランク化ユーティリティを提供。外部依存（pandas 等）なしでの実装。
  - バックテスト（シミュレータ・評価指標）
    - src/kabusys/backtest/simulator.py:
      - PortfolioSimulator: メモリ内での擬似約定・ポジション管理を実装。execute_orders は SELL を先に処理（保有全量クローズ）、BUY を後で処理。スリッページ・手数料を反映し TradeRecord を記録。
    - src/kabusys/backtest/metrics.py:
      - calc_metrics: DailySnapshot（履歴）と TradeRecord（約定履歴）から CAGR / Sharpe / MaxDrawdown / WinRate / PayoffRatio / total_trades を計算。

Changed
- 初回リリースのため過去バージョンからの変更はありません。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

注意事項 / 既知の制限・設計メモ
- config:
  - .env 読み込みはプロジェクトルートの検出に .git または pyproject.toml を利用。配布後の挙動に留意。
  - .env ファイル読み込みで既存 OS 環境変数を保護するため protected set を使用。override フラグの挙動に注意。
- portfolio/risk_adjustment.apply_sector_cap:
  - price_map に price が 0.0 の場合、エクスポージャが過少見積もられる問題があり、将来的に前日終値や取得原価をフォールバックする予定（TODO）。
  - "unknown" セクターの銘柄はセクター上限の対象外（ブロックされない）。
- position_sizing:
  - 現状は全銘柄共通の lot_size（デフォルト 100 を想定）で丸め処理。将来的に銘柄別 lot_map への拡張を予定（TODO）。
  - aggregate cap のスケールダウン時、ロット単位で再配分するロジックを持つが、整数ロット丸めにより想定より低い投資額となる場合がある点に注意。
- strategy/signal_generator:
  - Bear レジーム時の完全抑制は generate_signals の上流（シグナル生成）で行われる。regime 判定は ai_scores の regime_score 平均に依存するため、ai_scores の品質が重要。
  - SELL のトレーリングストップや時間決済（保有60営業日超）などは未実装（positions テーブルに peak_price / entry_date が必要）。
- research:
  - SQL ウィンドウ関数を多用しているため、DuckDB のスキーマ（prices_daily, raw_financials 等）構造に依存。データの NULL 扱い・カウント条件に注意。
- backtest/simulator:
  - SELL は保有全量のクローズのみ対応（部分利確・部分損切りは現状非対応）。
  - execute_orders の lot_size デフォルトが 1（後方互換）であるため、日本株利用時は実行側から適切な lot_size を渡すことを推奨。

互換性
- 本リリースは初回公開のため後方互換性に関する破壊的変更は無し。将来的な API 変更はメジャーバージョンで管理予定。

開発上の TODO / 改善候補
- position_sizing: 銘柄別 lot_size 対応（stocks マスタ参照）及びロットマップ受け入れ。
- risk_adjustment: price 欠損時のフォールバック価格導入（前日終値や取得原価など）。
- signal_generator: トレーリングストップ、時間決済、その他エグジット条件の実装。
- feature_engineering: features テーブルのスキーマ変更・拡張に伴う互換確認。
- テスト: 各純関数（特に position sizing / scaling / remainders 処理）に対する網羅的ユニットテストの充実。

必要な環境変数（例）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
- KABU_API_BASE_URL（任意、デフォルトあり）
- DUCKDB_PATH, SQLITE_PATH（任意、デフォルトあり）
- KABUSYS_ENV（任意、development/paper_trading/live、デフォルト: development）
- LOG_LEVEL（任意、DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

お問い合わせ・貢献
- バグ報告・機能要望は issue を立ててください。プルリクエスト歓迎。

--- End of CHANGELOG ---