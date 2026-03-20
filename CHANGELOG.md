# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングに従います。 (https://semver.org/)

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-20
初回公開リリース。

### Added
- パッケージの基本構成を追加
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）
  - エクスポートモジュール: data, strategy, execution, monitoring

- 設定・環境変数管理
  - .env ファイルまたは環境変数から設定をロードする auto-load 機能を追加（プロジェクトルートは .git / pyproject.toml を基準に検出）。（src/kabusys/config.py）
  - .env と .env.local の読み込み順序をサポート。OS 環境変数は保護され .env.local は上書き可能。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロード無効化が可能。
  - .env パーサーは `export KEY=val` 形式、クォート、インラインコメントを考慮した堅牢な実装。
  - Settings クラスを提供し、アプリケーション設定をプロパティで取得可能（J-Quants / kabu API / Slack / DB パス / 環境 / ログレベル 等）。
  - KABUSYS_ENV、LOG_LEVEL の検証（許容値チェック）とユーティリティプロパティ（is_live/is_paper/is_dev）。

- データ収集・保存（J-Quants API クライアント）
  - J-Quants API クライアントを実装（認証・ページネーション・取得関数）。（src/kabusys/data/jquants_client.py）
    - fetch_daily_quotes（株価日足／ページネーション対応）
    - fetch_financial_statements（財務データ／ページネーション対応）
    - fetch_market_calendar（マーケットカレンダー）
  - API レート制御（固定間隔スロットリング、120 req/min）を実装（内部 RateLimiter）。
  - リトライ戦略（指数バックオフ、最大 3 回）と HTTP 429/408/5xx のリトライ、429 の Retry-After 優先処理を実装。
  - 401 受信時のトークン自動リフレッシュ（1 回のみ）とモジュールレベルの ID トークンキャッシュを実装。
  - DuckDB へ冪等に保存する関数を実装（ON CONFLICT DO UPDATE を使用）:
    - save_daily_quotes（raw_prices テーブル）
    - save_financial_statements（raw_financials テーブル）
    - save_market_calendar（market_calendar テーブル）
  - 保存処理で PK 欠損行のスキップ警告、保存件数のログ出力を行う。
  - 値変換ユーティリティ _to_float / _to_int を実装（安全な変換ポリシー）。

- ニュース収集モジュール
  - RSS フィードから記事を収集して raw_news に冪等保存する機能を実装。（src/kabusys/data/news_collector.py）
    - デフォルト RSS ソース（Yahoo Finance のビジネスカテゴリ）を定義。
    - URL 正規化（スキーム/ホスト小文字化、追跡パラメータ除去、フラグメント除去、クエリキーソート）。
    - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を保証。
    - defusedxml を使った XML パースで XML Bomb 等の攻撃を防御。
    - HTTP/HTTPS 以外のスキーム拒否、受信サイズの上限（10 MB）設定（メモリ DoS 対策）。
    - バルク INSERT をチャンク化して DB へまとめて保存（パフォーマンス配慮）。
    - 挿入件数を正確に返すための戦略（INSERT RETURNING 等想定）とログ出力。

- リサーチ（研究）用モジュール
  - ファクター計算（価格データ・財務データからの量的ファクター）を実装。（src/kabusys/research/factor_research.py）
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）を DuckDB のウィンドウ関数で計算。
    - calc_volatility: 20日 ATR（true_range の平均）、atr_pct、20日平均売買代金、volume_ratio を計算。true_range の NULL 伝播制御等、欠損考慮。
    - calc_value: raw_financials から直近財務データを取得して PER, ROE を計算（EPS が 0 の場合は None）。
  - 特徴量探索ツールを実装。（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21）による将来リターンを一括 SQL で取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。サンプル不足（<3）時は None を返す。
    - rank: 同順位は平均ランクを返す安定的なランク関数（丸め処理で ties 検出の信頼性向上）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
  - 研究モジュールは外部ライブラリに依存せず標準ライブラリ＋DuckDB のみで実装。

- 特徴量エンジニアリング（戦略向け）
  - build_features を実装し、research モジュールから得た生ファクターを正規化・合成して features テーブルへ UPSERT する。（src/kabusys/strategy/feature_engineering.py）
    - ユニバースフィルタ: 株価 >= 300 円、20日平均売買代金 >= 5 億円。
    - 正規化: kabusys.data.stats.zscore_normalize を使用。対象カラムは mom_1m, mom_3m, atr_pct, volume_ratio, ma200_dev。
    - Z スコアは ±3 でクリップして外れ値影響を抑制。
    - 日付単位で古い行を削除してからトランザクションで挿入（冪等性・原子性を確保）。
    - 欠損や非有限値の扱いに注意（スキップ／None）。

- シグナル生成（戦略）
  - generate_signals を実装し、features と ai_scores を統合して signals テーブルに BUY/SELL シグナルを書き込む。（src/kabusys/strategy/signal_generator.py）
    - コンポーネントスコア: momentum / value / volatility / liquidity / news（AI）を計算。
    - スコア変換: Z スコアをシグモイド変換して [0,1] に変換（欠損は None とし後段で中立 0.5 を補完）。
    - デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10。ユーザ重みは検証・正規化（非数値・負値は無視、合計で再スケール）。
    - BUY 閾値デフォルト: 0.60。Bear レジーム時は BUY を抑制。
    - Bear 判定: ai_scores の regime_score 平均が負かつサンプル >= 3 で Bear と判定。
    - SELL 条件（実装済）:
      - ストップロス: (close / avg_price - 1) <= -8%
      - final_score が threshold 未満
      - SELL は BUY より優先し、BUY から除外してランクを再付与。
    - 日付単位で古いシグナルを削除してからトランザクションで挿入（冪等・原子性）。
    - positions / prices 欠損時の安全な挙動（価格欠損で SELL 判定スキップ、features にない保有銘柄は score=0 として扱う等）。

### Changed
- 初回リリースのため履歴なし。

### Fixed
- 初回リリースのため履歴なし。

### Security
- RSS パーサーに defusedxml を使用し XML ベースの攻撃を軽減（news_collector）。
- ニュース URL の正規化とスキームチェックで SSRF リスクを低減。
- .env 読み込みでファイル読み込み失敗時に警告を出すが、例外を露出しない堅牢性を確保（config）。

### Notes / Implementation details
- DuckDB を用いた SQL 実装ではウィンドウ関数や LEAD/LAG/AVG/COUNT を多用。休場日や欠損データを考慮した日付範囲のバッファ（カレンダー日数×係数）を設定している。
- 外部 API (J-Quants) 呼び出しは rate limiter・リトライ・自動トークン更新を組み合わせて堅牢に設計。
- 研究モジュールは本番の発注や execution レイヤには依存しない設計。
- 一部の仕様（例: positions テーブルに peak_price / entry_date があると実装可能なトレーリングストップ等）は将来的な拡張余地あり（signal_generator 内に TODO コメントあり）。

---

今後のリリースで想定される追加事項:
- execution 層（発注ロジック）実装および kabu ステーション API 統合の追加
- monitoring / Slack 通知の実装強化
- ニュース記事と銘柄紐付け（news_symbols）の詳細実装と NER/マッチング改善
- テストカバレッジ・E2E テスト・CI の整備

もし CHANGELOG の記載内容に詳細な補足や別バージョンに分けたい変更点の希望があれば教えてください。