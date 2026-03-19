# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記録します。  
リリースはセマンティックバージョニングに従います。

現在のバージョン: 0.1.0 (初回公開)

## [Unreleased]
（今後の変更をここに記載）

## [0.1.0] - 2026-03-19
初回リリース。日本株自動売買システム「KabuSys」のコア機能を提供する最小限の実装を追加。

### Added
- パッケージ初期化
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。
  - 公開モジュール一覧（data, strategy, execution, monitoring）を `__all__` に定義。

- 設定 / 環境変数管理 (`kabusys.config`)
  - プロジェクトルートを `.git` または `pyproject.toml` から探索する自動検出機能を実装（CWD に依存しない）。
  - .env ファイルのパーサを実装（コメント・export 形式・クォート・エスケープ対応）。
  - .env/.env.local の自動ロードを実装。優先順位: OS 環境変数 > .env.local > .env。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - 必須環境変数取得のユーティリティ `_require` と `Settings` クラスを提供。J-Quants、kabuステーション、Slack、DB パス等の設定プロパティを含む。
  - 環境（development/paper_trading/live）とログレベル値検証を実装。

- データ取得・保存（J-Quants クライアント） (`kabusys.data.jquants_client`)
  - J-Quants API クライアントを実装。主な機能:
    - 日次株価、財務データ、マーケットカレンダーの取得（ページネーション対応）。
    - 固定間隔レートリミッタ（120 req/min）を実装。
    - リトライ（指数バックオフ、最大3回）、HTTP 408/429/5xx の再試行処理。
    - 401 受信時にリフレッシュトークンで自動的に ID トークンを更新して 1 回リトライ。
    - フェッチ時刻（fetched_at）を UTC で記録してルックアヘッドバイアスのトレースを可能に。
  - DuckDB への保存ユーティリティを実装（raw_prices / raw_financials / market_calendar）。すべて冪等（ON CONFLICT DO UPDATE / DO NOTHING）で保存。
  - 数値変換ユーティリティ `_to_float` / `_to_int` を実装し不正データに寛容に対応。

- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィードから記事を収集して `raw_news` に保存する仕組みを追加。
  - 記事 ID を URL 正規化後の SHA-256 ハッシュで生成し冪等性を担保。
  - URL 正規化でトラッキングパラメータ削除、スキーム/ホスト小文字化、クエリソート、フラグメント削除を実施。
  - セキュリティ対策を実施:
    - defusedxml を用いた XML パース（XML Bomb 等に対する保護）。
    - 最大受信サイズ制限（10 MB）でメモリ DoS を軽減。
    - HTTP/HTTPS 以外のスキーム拒否等 SSRF 緩和（実装意図をコメントで明記）。
  - バルク挿入チャンク処理・トランザクションでパフォーマンスと一貫性を確保。

- 研究モジュール（Research） (`kabusys.research`)
  - ファクター計算（`factor_research`）を実装:
    - Momentum（1M/3M/6M リターン、MA200 乖離率）
    - Volatility（20日 ATR、相対 ATR、20日平均売買代金、出来高比率）
    - Value（PER、ROE を raw_financials と株価から計算）
    - DuckDB に対する SQL ベースの実装。データ不足時は None を返す設計。
  - 特徴量探索（`feature_exploration`）を実装:
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）
    - IC（Spearman の ρ）計算（ランク処理、同順位は平均ランク）
    - ファクター統計サマリー（count/mean/std/min/max/median）
    - 標準ライブラリのみで完結する設計（pandas など非依存）。
  - 研究用 API をパッケージ公開（calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize）。

- 特徴量エンジニアリング (`kabusys.strategy.feature_engineering`)
  - 研究で得た生ファクターを統合・正規化して `features` テーブルへ保存する処理を実装。
  - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）を実装。
  - 正規化（Z スコア）後に ±3 でクリップして外れ値影響を抑制。
  - 日付単位で削除→挿入の置換を行い冪等性を保証（トランザクション + バルク挿入）。

- シグナル生成 (`kabusys.strategy.signal_generator`)
  - `features` と `ai_scores` を組み合わせ、各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出して最終スコア（final_score）を計算。
  - デフォルト重みと閾値を実装（デフォルト threshold=0.60、weights のデフォルト合計は 1.0 にスケールされる）。
  - AI レジームスコアの平均が負の場合は Bear レジームとして BUY を抑制（サンプル数閾値あり）。
  - 保有ポジションのエグジット条件を実装（ストップロス -8%、final_score が閾値未満）。
  - BUY / SELL シグナルを `signals` テーブルに日付単位で置換保存（冪等、トランザクション）。
  - 欠損コンポーネントは中立値 0.5 で補完するポリシーを採用（欠損銘柄の過度な降格回避）。
  - SELL 優先ポリシー（SELL 対象は BUY から除外しランクを再付与）。

- パッケージ公開 API (`kabusys.strategy`, `kabusys.research`)
  - strategy パッケージで build_features / generate_signals を公開。
  - research パッケージで研究用関数と正規化ユーティリティを公開。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Deprecated
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Security
- news_collector: defusedxml を利用して XML ベースの攻撃を軽減。
- jquants_client: トークンリフレッシュ時の再帰を防止する設計（allow_refresh フラグ）を実装。
- 環境変数自動ロードの挙動を明示（必要時に無効化可能）。

### Notes / Known limitations
- execution 層（発注 API との接続）はまだ実装の粒度がなく、strategy は signals テーブルに書き出すのみで直接注文は出しません。
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は未実装（コメントで明示）。
- news_collector の SSRF 完全防止や外部リソース検査は設計上配慮済みだが、運用環境に応じた追加対策（プロキシや IP ブロックリスト等）を推奨。
- DuckDB テーブルスキーマはこの実装に依存する（prices_daily, raw_financials, features, ai_scores, positions, signals, raw_prices, raw_financials, market_calendar, raw_news など）。運用前にスキーマ整備が必要。

---
作業ログや細かい設計判断は各モジュール内の docstring / コメントに記載しています。リリース後の改善要求やバグ報告は CHANGELOG の Unreleased 欄に追記してください。