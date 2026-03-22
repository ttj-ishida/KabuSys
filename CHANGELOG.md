# Changelog

すべての注記は Keep a Changelog の形式に従います。  
このファイルはリポジトリ内のコードから推測して作成した変更履歴（初回公開相当）です。

## [0.1.0] - 2026-03-22

### Added
- パッケージ初期リリース。
- 基本モジュール群を追加:
  - kabusys.config
    - .env / .env.local の自動読み込み機能（OS 環境変数が優先、.env.local が .env を上書き）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - .env パーサは export 形式、クォート／エスケープ、インラインコメントの取り扱いに対応。
    - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境種別 / ログレベル等の設定プロパティを公開（必須値は _require() で検証）。
  - kabusys.strategy
    - feature_engineering.build_features
      - research で計算された生ファクターを取り込み、ユニバースフィルタ（価格・20日平均売買代金）を適用。
      - 指定カラムを Z スコア正規化し ±3 でクリップ。
      - DuckDB の features テーブルへ日付単位で冪等に書き込み（トランザクション + バルク挿入）。
    - signal_generator.generate_signals
      - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
      - 重み付け合算による final_score、閾値を超える銘柄の BUY シグナル生成（デフォルト閾値 0.60）。
      - Bear レジーム判定により BUY を抑制。
      - 保有ポジションのエグジット判定（ストップロス・スコア低下）による SELL シグナル生成。
      - signals テーブルへ日付単位で冪等に書き込み（トランザクション + バルク挿入）。
      - 重みのバリデーションと合計 1.0 へのリスケールを実装。
  - kabusys.research
    - factor_research: calc_momentum / calc_volatility / calc_value
      - prices_daily / raw_financials を利用したモメンタム・ボラティリティ・バリュー系ファクターの計算。
      - 必要行数不足時は None を返す設計（安全な欠損取扱い）。
    - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
      - 将来リターン計算（複数ホライズンの同時取得）、Spearman IC（ランク相関）、統計サマリー等の解析ユーティリティ。
      - 外部依存を持たず標準ライブラリで実装。
  - kabusys.backtest
    - simulator: PortfolioSimulator（擬似約定・ポートフォリオ管理）
      - BUY/SELL の約定ロジック（スリッページ・手数料反映）、平均取得単価管理、日次時価評価・スナップショット記録、TradeRecord の収集。
      - SELL は保有全量クローズ（部分利確非対応）。
    - engine: run_backtest
      - 本番 DuckDB から日付範囲でデータを抽出してインメモリ DuckDB にコピー（signals/positions を汚さない）。
      - 日次ループ：前日シグナルの約定 → positions 書き戻し → 時価評価 → generate_signals 呼び出し → 発注量算出 の流れを実装。
      - デフォルトのスリッページ・手数料・最大ポジション比率等のパラメータを提供。
    - metrics: バックテスト評価指標（CAGR / Sharpe / MaxDrawdown / WinRate / PayoffRatio / total_trades）計算ユーティリティ。

### Changed
- （初回リリースのため特になし）

### Fixed
- 各モジュールで欠損データや非有限値（NaN/Inf）を安全に扱う実装を導入（数値チェック、None 補完、ログ出力など）。
- DuckDB 操作時のトランザクション管理を導入して原子性を確保（build_features / generate_signals / positions 書き戻しなどで BEGIN/COMMIT/ROLLBACK を使用）。
- .env 読み込み時にファイルオープン失敗時は警告を出して継続する堅牢性向上。

### Security
- OS 環境変数を上書きしない既定挙動と、上書き禁止キーセット（protected）によりテスト実行等での誤上書きを防止。

### Documentation
- 各モジュールに詳細な docstring を追加（設計方針・処理フロー・参照テーブル・返り値仕様など）。これにより研究/本番の境界やルックアヘッドバイアス回避方針が明確化されている。

### Internals / Notes
- パッケージの公開 API:
  - トップレベル __all__ には data, strategy, execution, monitoring を含む（各サブパッケージ経由での利用を想定）。
  - strategy, research, backtest それぞれで主要関数／型を __all__ によりエクスポート。
- 重み・閾値・閾値未満の扱い・欠損補完（中立 0.5）等、StrategyModel に沿った実装がなされている（設計ドキュメント参照の旨が docstring に明記）。
- バックテストは本番 DB を直接変更しない設計（インメモリ複写）で、market_calendar は全件コピー、日付フィルタ済みのテーブルは必要範囲のみコピーすることで効率化を図っている。

---

注: 本 CHANGELOG はソースコードの注釈・docstring・実装内容から推測して作成しています。実際のリリースノートとして利用する場合は、リポジトリのコミット履歴やリリースポリシーに沿って適宜修正してください。