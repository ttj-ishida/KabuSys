# Changelog

すべての重要な変更点をここに記録します。本日付のリリースはパッケージの初期公開版（0.1.0）に相当します。

フォーマットは「Keep a Changelog」準拠です。非破壊的な修正や内部実装の改善も含め、コードベースから推測される機能と既知の制約を記載しています。

## [0.1.0] - 2026-03-22

### Added
- パッケージの初期実装を追加。
  - src/kabusys/__init__.py
    - パッケージ名、バージョン（0.1.0）および public API のエクスポートを定義。
- 環境変数 / 設定管理モジュールを追加（自動 .env 読み込み・パース機能）。
  - src/kabusys/config.py
    - プロジェクトルート（.git または pyproject.toml）から .env / .env.local を自動で読み込む機能を実装（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - export KEY=val 形式やシングル/ダブルクォート、エスケープ、インラインコメントに対応する堅牢な .env 行パーサを実装。
    - 環境変数の必須チェック用 _require() と Settings クラスを提供。必須変数例:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - デフォルトパス: DUCKDB_PATH= data/kabusys.duckdb、SQLITE_PATH= data/monitoring.db
    - KABUSYS_ENV / LOG_LEVEL の検証（許容値制限）。
- 戦略関連モジュールを追加。
  - src/kabusys/strategy/feature_engineering.py
    - research モジュールで算出した生ファクターを統合し、正規化（Zスコア）→ ±3 クリップ → features テーブルへ UPSERT（トランザクションで日付単位の置換）する build_features() を実装。
    - ユニバースフィルタ（最小株価、最小20日平均売買代金）を実装。
  - src/kabusys/strategy/signal_generator.py
    - features と ai_scores を統合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）を算出し、重み付け合算して final_score を導出、BUY/SELL シグナルを生成して signals テーブルへ書き込む generate_signals() を実装。
    - AI レジームスコア集計による Bear 判定（Bear 相場では BUY を抑制）。
    - SELL 判定ロジック（ストップロス、スコア低下）を実装。positions / prices を参照して堅牢に判定。
    - ユーザ指定の weights の検証と正規化（既知キーのみ受け付け、非数値や負値を無視）。
- research（調査）モジュールを追加。
  - src/kabusys/research/factor_research.py
    - モメンタム（1/3/6 ヶ月リターン、MA200乖離）、ボラティリティ（20日 ATR、相対ATR）、流動性指標（20日平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB の prices_daily / raw_financials テーブルのみで計算する関数群（calc_momentum / calc_volatility / calc_value）を実装。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（スピアマンランク相関）計算（calc_ic）、ファクター統計サマリー（factor_summary）、ランク関数（rank）を実装。外部依存を使わず標準ライブラリのみで動作。
  - src/kabusys/research/__init__.py で外部公開 API をまとめてエクスポート。
- バックテストフレームワークを追加。
  - src/kabusys/backtest/simulator.py
    - PortfolioSimulator、日次スナップショット / 約定レコードの dataclass（DailySnapshot / TradeRecord）を実装。
    - 市場の始値での BUY/SELL 擬似約定ロジック、スリッページ・手数料の適用、全量クローズポリシー、時価評価（mark_to_market）を実装。
  - src/kabusys/backtest/metrics.py
    - CAGR、Sharpe、最大ドローダウン、勝率、ペイオフレシオ、総トレード数を集計する calc_metrics を実装。
  - src/kabusys/backtest/engine.py
    - 本番 DB からインメモリ DuckDB へ必要テーブルをコピーする _build_backtest_conn。
    - 日次ループでの約定・時価評価・シグナル生成・ポジション書き戻しの処理を行う run_backtest を実装（slippage_rate, commission_rate, max_position_pct 等のパラメータ対応）。
    - signals / positions / market_calendar などの取り扱いと、positions 書き戻し用ユーティリティを提供。
  - src/kabusys/backtest/__init__.py で結果型と主要クラスをエクスポート。
- パッケージの public API（strategy.build_features / strategy.generate_signals 等）を __all__ で定義。
- ログ出力やエラー回復（トランザクション rollback 時のワーニング）を各所に実装し堅牢性を向上。

### Changed
- （初期リリース）研究・本番で同一ロジックを再利用できる設計方針を採用：
  - ルックアヘッドバイアス回避のため、すべて target_date 時点のデータのみを参照する仕様を採用（feature_engineering、signal_generator、research 関数群）。
  - 発注 API / execution 層への直接依存を持たない構成（戦略層は DB に signals を書き込むまで）。

### Fixed
- .env 読み込み時の入出力エラー検出と警告出力を追加（ファイル読込失敗時に warnings.warn）。
- 各種数値検証や None / NaN / Inf の扱いを明示的に実装（スコア算出・平均化・シグモイド変換・Zスコアクリップ等で安全な処理）。

### Known limitations / TODO（ドキュメント的記載）
- 戦略の SELL 条件に関して未実装の項目がある（内部コメントに記載）。
  - トレーリングストップ（peak_price のトラッキングが positions テーブルに未実装）。
  - 時間決済（一定保有日数でのクローズ）は未実装。
- calc_value にて PBR・配当利回りは未実装（コメントに明記）。
- PortfolioSimulator の BUY は分割約定や部分利確・部分損切りに未対応（全量購入・全量売却の単純化されたモデル）。
- run_backtest の際、コピー対象テーブルが存在しない/空の場合はスキップするが、テーブルスキーマ依存があるため本番 DB のスキーマ整備が必要。
- data.stats.zscore_normalize 等のユーティリティは本変更履歴のソースに依存して参照しているが、この CHANGELOG は参照先実装の有無を保証しない（実装済みであることを期待）。

### Security
- このリリースではセキュリティ修正の記載はありませんが、環境変数に機密情報（API トークン等）を直接読み込む設計のため、運用時は .env ファイルのアクセス権限管理やシークレット管理の外部化を推奨。

---

今後のリリースでは、上記の既知制約（トレーリングストップ、部分約定、追加ファクター、外部 AI スコア連携の詳細など）の対応状況を逐次記載します。必要であれば、CHANGELOG に記載した各項目の詳細（該当ソースファイルの参照行や設計文書の該当節）を展開して追記できます。