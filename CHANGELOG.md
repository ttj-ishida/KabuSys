# CHANGELOG

すべての重要な変更をここに記載します。フォーマットは「Keep a Changelog」に準拠しています。  
※以下の履歴は現行コードベースの内容から推測して作成しています。

目次
- [Unreleased](#unreleased)
- [0.1.0 - 2026-03-22](#010--2026-03-22)

## Unreleased
（なし）

## 0.1.0 - 2026-03-22
初期リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - パッケージ初期化: `kabusys` パッケージ（__version__ = 0.1.0）。公開モジュール: data, strategy, execution, monitoring。
- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルート判定は `.git` または `pyproject.toml` を探索して行うため、実行カレントディレクトリに依存しない。
    - 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は上書き、.env は未設定キーのみ設定）。
    - 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - .env の行パースは `export KEY=val`・クォートやエスケープ・コメント対応を行う堅牢な実装。
  - Settings クラスでアプリ設定をプロパティ経由で提供:
    - J-Quants / kabu API / Slack / DB パス（DuckDB/SQLite）など主要設定を取得するためのプロパティを実装。
    - 必須環境変数未設定時は明確な例外（ValueError）を発生させる `_require` を実装。
    - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の検証を実装（受け入れ可能な値の検査）。
- ストラテジー（kabusys.strategy）
  - 特徴量作成（feature_engineering.build_features）
    - 研究側（research）で計算された生ファクターを統合し、ユニバースフィルタ（最低株価・最低平均売買代金）を適用。
    - Zスコア正規化（外部ユーティリティ zscore_normalize を利用）および ±3 でのクリッピング。
    - features テーブルへの日付単位の置換（削除→挿入）をトランザクションで行い冪等性を確保。
    - target_date 時点のデータのみを使用するよう設計（ルックアヘッド防止）。
  - シグナル生成（signal_generator.generate_signals）
    - features と ai_scores を統合し、モメンタム／バリュー／ボラティリティ／流動性／ニュース（AI）を重み付けして final_score を計算。
    - デフォルト重みやしきい値（threshold=0.60）を備え、ユーザ指定の weights を検証・正規化するロジックを実装。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値以上で判定）を実装し、Bear 時は BUY を抑制。
    - SELL（エグジット）判定:
      - ストップロス（終値ベースで -8% 以下）を最優先で判定。
      - final_score が threshold 未満の銘柄をエグジット対象にする。
      - features に存在しない保有銘柄は score=0.0 と見なして SELL 判定（ログ出力あり）。
    - BUY / SELL の優先処理（SELL 優先で BUY から除外）、ランク付け、signals テーブルへの日付単位置換をトランザクションで実行。
    - ルールの一部（トレーリングストップ、時間決済）は設計上コメントで未実装として明示。
- リサーチ（kabusys.research）
  - ファクター計算群（factor_research）:
    - モメンタム（calc_momentum）: 1M/3M/6M リターン、200日MA乖離率（データ不足時は None）。
    - ボラティリティ／流動性（calc_volatility）: 20日 ATR（atr_pct）、20日平均売買代金、出来高比（volume_ratio）。true_range の NULL 伝播を適切に制御。
    - バリュー（calc_value）: raw_financials の最新財務データと当日株価から PER / ROE を算出。EPS=0 の場合は PER を None に。
    - いずれも DuckDB 上の SQL ウィンドウ関数を用いた効率的な実装。
  - 特徴量探索（feature_exploration）:
    - 将来リターン計算（calc_forward_returns）: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得。
    - IC（calc_ic）: Spearman（ランク相関）でファクターと将来リターンの相関を算出。サンプル不足や ties を考慮。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を計算。
    - ランク付けユーティリティ（rank）を実装（同順位は平均ランク）。
    - 外部依存を避け、標準ライブラリと DuckDB の SQL のみで実装。
- バックテスト（kabusys.backtest）
  - シミュレータ（simulator.PortfolioSimulator）
    - メモリ上で約定・ポートフォリオ管理を行う。BUY/SELL の約定ロジック、スリッページ（割合）、手数料率に基づく計算を実装。
    - BUY は部分約定なしで株数は floor(alloc/price) で算出。手数料込みで株数を再計算する処理を実装。
    - SELL は保有全量クローズ、実現損益（realized_pnl）を計算して記録。
    - mark_to_market により DailySnapshot（date, cash, positions, portfolio_value）を保持。終値欠損時は 0 評価にして警告ログ。
    - TradeRecord / DailySnapshot dataclass を定義し、トレード履歴を格納。
  - メトリクス（metrics.calc_metrics）
    - CAGR / Sharpe / Max Drawdown / 勝率 / Payoff Ratio / 総トレード数 を計算するユーティリティを実装。
    - 小規模データやゼロ分散などの境界条件を扱う安全な実装。
  - バックテストエンジン（engine.run_backtest）
    - 本番 DuckDB からバックテスト用に必要データをインメモリ DuckDB にコピーする `_build_backtest_conn` を実装（signals/positions を汚さない）。
    - 日次ループ: 前日のシグナルを当日始値で約定 → positions を書き戻す → 終値で時価評価 → 当日用シグナル生成 → シグナルに基づく発注（ポジションサイジング）という流れを実装。
    - get_trading_days（market_calendar 利用）を用いて営業日のみループを回す想定。
    - デフォルトパラメータ: initial_cash=10_000_000, slippage_rate=0.001, commission_rate=0.00055, max_position_pct=0.20。
    - 各種 I/O 操作（テーブルコピー・INSERT 等）は例外時に警告を出すフェールソフト実装。
- DB / トランザクション設計
  - features / signals / positions などへの書き込みは日付単位の置換（DELETE → INSERT）をトランザクション（BEGIN/COMMIT/ROLLBACK）で行い、原子性と冪等性を確保。
  - 失敗時の ROLLBACK に失敗した場合は警告ログを出力。
- ロギング / 安全対策
  - 多数の箇所で警告・情報・デバッグログを追加し、欠損データや不正入力に対する注意喚起を行う。
  - 入力検証（weights の検証、env 値の検証、数値の finite チェック等）を実装し、不正な値は無視または例外を投げる。

### Changed
（初版のため該当なし）

### Fixed
（初版のため該当なし）

### Removed
（初版のため該当なし）

### Security
（初版のため特記事項なし）

### Notes / Limitations
- 一部アルゴリズム（トレーリングストップ、時間決済など）はドキュメント上で想定されているが現状実装されていません（コメントで未実装として明示）。
- AI スコア（ai_scores）や raw_financials、market_calendar 等のデータ供給が前提です。これらのテーブルや外部サービス連携は別途用意する必要があります。
- zscore 正規化関数は `kabusys.data.stats` に依存しており、本変更ログでは実装細部を示していません（存在を前提として利用）。
- 実運用に際しては発注（execution）層や監視（monitoring）層の実装、Slack 等への通知連携の追加が必要です。

-------------------------
将来のリリースでは、以下を検討・追加予定です（コード内コメントや設計書に基づく推測）:
- execution 層の実装（kabuステーション連携・注文管理）
- monitoring（Slack 通知等）の具体実装
- トレーリングストップ・保有日数による時間決済ルールの実装
- テストカバレッジの拡充と CI/CD の導入

この CHANGELOG はコードベースからの推測に基づいて作成しています。追加情報やリリース日・バージョニング方針が確定している場合は合わせて更新してください。