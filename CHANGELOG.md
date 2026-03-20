# CHANGELOG

すべての重要な変更履歴をここに記録します。  
このファイルは Keep a Changelog の慣習に従います。

全ての変更は意味のあるまとまり（リリース）単位で記載しています。

## [Unreleased]

(なし)

## [0.1.0] - 2026-03-20

初回リリース。日本株自動売買システム "KabuSys" の基本機能群を実装しました。主な追加点をカテゴリ別にまとめます。

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開（version 0.1.0）。
  - __all__ に data, strategy, execution, monitoring を公開。

- 設定・環境変数読み込み（kabusys.config）
  - .env / .env.local からの自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env ファイルのパース機能を強化:
    - export KEY=val 形式対応
    - シングル/ダブルクォートとバックスラッシュエスケープ対応
    - コメント処理（クォート内は無視、クォート外では '#' の直前が空白/タブの場合のみコメントとみなす）
  - Settings クラスを提供し、J-Quants / kabu API / Slack / データベースパス / 環境モード等のアクセス用プロパティを追加。
  - KABUSYS_ENV と LOG_LEVEL の妥当性検査（許可値チェック）を実装。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - レート制限対応（固定間隔スロットリング、120 req/min）。
  - 再試行（指数バックオフ、最大3回）・429 の Retry-After 優先処理、401 受信時のトークン自動リフレッシュ（1回）を実装。
  - ページネーション対応（pagination_key のループ）。
  - DuckDB への冪等保存関数を実装:
    - save_daily_quotes（raw_prices）
    - save_financial_statements（raw_financials）
    - save_market_calendar（market_calendar）
    - いずれも INSERT ... ON CONFLICT DO UPDATE を使用して重複を排除。
  - 型変換ユーティリティ _to_float / _to_int を提供（堅牢な None/空文字/文字列処理）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからの記事収集の基盤実装（DEFAULT_RSS_SOURCES に Yahoo Finance を登録）。
  - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント除去、クエリソート）。
  - defusedxml を用いた XML パース（XML Bomb 対策）。
  - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）、SSRF 対策等のセキュリティ考慮。
  - バルク INSERT チャンクや ON CONFLICT DO NOTHING による冪等保存の設計。

- 研究用ファクター計算（kabusys.research）
  - factor_research: momentum / volatility / value の計算関数を実装。
    - モメンタム: mom_1m, mom_3m, mom_6m, ma200_dev（200日窓の存在チェック）
    - ボラティリティ: atr_20, atr_pct, avg_turnover, volume_ratio（ATR 算出時の NULL 伝播制御）
    - バリュー: per, roe（raw_financials の最新報告を target_date以前で取得）
  - feature_exploration: 将来リターン calc_forward_returns、IC（Spearman ρ）計算 calc_ic、統計サマリー factor_summary、rank ユーティリティを実装。
  - 研究関数は DuckDB 接続を受け取り、外部ライブラリに依存せず標準ライブラリで実装（本番発注 API にはアクセスしない設計）。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research モジュールから取得した生ファクターをマージ・ユニバースフィルタ適用・正規化して features テーブルへ保存する build_features を実装。
  - ユニバースフィルタ: 最低株価 _MIN_PRICE=300 円、20日平均売買代金 _MIN_TURNOVER=5e8 円。
  - 正規化: zscore_normalize を利用、対象カラムを Z スコア化して ±3 でクリップ（ZSCORE_CLIP=3.0）。
  - DuckDB 上で日付単位の置換（DELETE + bulk INSERT）をトランザクションで原子性保証。

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合し final_score を算出して BUY/SELL シグナルを生成する generate_signals を実装。
  - コンポーネントスコア:
    - momentum / value / volatility / liquidity / news（AI スコア）を計算するユーティリティを提供。
    - シグモイド変換、欠損値は中立 0.5 で補完するポリシー。
  - 重みの入力を受け付け、デフォルト値から補完・正規化・検証（負値/非数値は無視）を行う。
  - Bear レジーム判定（ai_scores の regime_score 平均が負、サンプル数閾値あり）により BUY を抑制。
  - エグジット判定（SELL）: ストップロス（-8%）およびスコア低下を実装。価格欠損時の判定スキップや features にない保有銘柄の扱いを明示。
  - signals テーブルへの日付単位置換をトランザクションで実施。

- API 統合（kabusys.strategy.__init__）
  - build_features / generate_signals をパッケージレベルで公開。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- news_collector で defusedxml を採用して XML 関連の攻撃を緩和。
- RSS 取得時に受信バイト数制限、URL 正規化でトラッキング除去等の対策を導入。
- jquants_client で 401 リフレッシュ・429 の Retry-After など HTTP 調停を実装し誤動作や過剰リクエストを防止。

### Notes / Known limitations
- execution パッケージは空の初期プレースホルダ（実装対象）。発注ロジックおよび kabu ステーション連携は未実装。
- signal_generator の一部エグジット条件（トレーリングストップ・時間決済）は未実装（コメントに記載）。
- news_collector の記事 ID 生成やシンボル紐付け等の詳細実装の一部は実装方針のみを含む（コードの続きで実装される想定）。
- research モジュールは外部依存（pandas 等）を使わない方針。大規模データ処理ではパフォーマンス評価が必要。

## 参考
- パッケージバージョン: 0.1.0（src/kabusys/__init__.py）
- リリース日: 2026-03-20

（以降の変更はバージョンを上げて本ファイルに追記してください）