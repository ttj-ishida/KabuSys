# Changelog

すべての重要な変更はこのファイルに記録します。本プロジェクトは Keep a Changelog の形式に従います。  
安定版リリースの履歴はセマンティック バージョニング (https://semver.org/) に従います。

## [Unreleased]

（現在の配布では未解放の変更はありません。）

## [0.1.0] - 2026-03-21

初回リリース。日本株自動売買システムのコア機能群を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基本情報
  - kabusys パッケージを追加。バージョンは 0.1.0 に設定（src/kabusys/__init__.py）。
  - パッケージ公開 API として data, strategy, execution, monitoring をエクスポート。

- 環境設定管理
  - .env ファイル / 環境変数の自動読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - export KEY=val 形式、シングル/ダブルクォート、インラインコメント処理に対応するパーサを実装。
    - OS 環境変数（読み込み前の keys）を protected として .env.local の上書きを制御。
  - Settings クラスを追加。主要プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID の必須取得。
    - KABUSYS_ENV（development/paper_trading/live）の検証。
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）の検証。
    - デフォルトの DB パス（DUCKDB_PATH, SQLITE_PATH）を Path として返すユーティリティ。

- J-Quants API クライアント
  - rate limiting（120 req/min 固定間隔スロットリング）実装。
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象、429 の Retry-After 優先）。
  - 401 受信時の自動トークンリフレッシュ（1 回のみ）と id_token キャッシュ共有（ページネーション間）。
  - ページネーション対応 API 呼び出し:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（四半期等の財務データ）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB への保存ユーティリティ（冪等実装、ON CONFLICT DO UPDATE）:
    - save_daily_quotes（raw_prices テーブル、fetched_at を UTC ISO8601 で記録）
    - save_financial_statements（raw_financials テーブル）
    - save_market_calendar（market_calendar テーブル）

- ニュース収集（RSS）モジュール
  - RSS から記事を取得・正規化して raw_news に保存する機能を追加（defusedxml を利用した XML パース）。
  - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント除去、クエリキーソート）。
  - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を確保。
  - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）、チャンク挿入、セキュリティ対策（サニタイズ等）。
  - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを設定。

- 研究（research）モジュール
  - ファクター計算（src/kabusys/research/factor_research.py）:
    - calc_momentum（1M/3M/6M リターン、MA200 乖離）
    - calc_volatility（20日 ATR、相対 ATR、平均売買代金、出来高比率）
    - calc_value（per/roe を raw_financials と prices_daily から計算）
    - 営業日相当の窓幅、欠損時の None 扱いなどを明確に実装
  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）:
    - calc_forward_returns（指定ホライズンの将来リターン: デフォルト [1,5,21]）
    - calc_ic（Spearman のランク相関による IC 計算）
    - factor_summary（count/mean/std/min/max/median）
    - rank（同順位は平均ランクで処理）
  - research パッケージの __all__ を整備して外部 API を公開。

- 戦略（strategy）モジュール
  - 特徴量作成（feature_engineering.build_features）:
    - research の生ファクターを統合し、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）を適用。
    - Z スコア正規化（data.stats.zscore_normalize を利用）、±3 でクリップ。
    - features テーブルへの日付単位の置換（DELETE + bulk INSERT をトランザクションで実行し原子性を保証）。
  - シグナル生成（signal_generator.generate_signals）:
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - デフォルト重みと閾値（weights、threshold=0.60）を実装。ユーザー指定重みの検証・補完・再スケール機能を実装。
    - AI レジームスコアによる Bear 判定（サンプル数閾値を導入）を行い、Bear 時は BUY を抑制。
    - BUY 条件（閾値超）・SELL 条件（ストップロス -8%、スコア低下）を実装。
    - SELL 優先ポリシー（SELL 対象は BUY から除外）、signals テーブルへ日付単位置換で保存。
    - トランザクション / ROLLBACK の堅牢な扱いとログ出力を実装。

### Changed
- （この初回リリースでは既存機能の変更履歴はありません）

### Fixed
- HTTP 呼び出し・認証の堅牢化:
  - _request において 401 発生時に無限再帰しないよう allow_refresh フラグを利用して id_token リフレッシュを一回だけ行う仕様を導入。
  - ネットワーク/HTTP エラー時の詳細ログ・再試行ポリシーを整備。
- DB 書き込みの堅牢化:
  - features / signals への書き込みを日付単位で削除 → 挿入する形にし、例外時は ROLLBACK を試みログ出力することで整合性を保護。

### Security
- ニュース収集での XML パースに defusedxml を導入し XML ブラスト等の攻撃に対処。
- URL 正規化とトラッキングパラメータ除去を実装し、同一記事の重複検出と追跡パラメータの除去を実現。
- .env 読み込み時に OS 環境変数を保護し、テストや CI 実行環境での環境上書きを制御。

### Internal
- 各モジュールに設計方針・処理フローを詳細な docstring で記載（保守性向上）。
- DuckDB を想定した SQL 実装・ウィンドウ関数利用でパフォーマンスと表記の明確化を図成。
- ロギング（logger）を各モジュールで利用し、情報・警告・デバッグの出力を整理。

注: 本 CHANGELOG は提供されたコードベースの実装内容から推測して作成しています。実際のコミット履歴・チケット等と照合して補正してください。