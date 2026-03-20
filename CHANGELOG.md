# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトの初回公開リリースに相当する変更履歴を、コードベースから推測して作成しています。

全体方針: 互換性の範囲が明示されていない箇所は現状互換性維持を前提としています。必要に応じてマイナー/メジャー配布時に明確化してください。

※ バージョンはパッケージ内の __version__ (0.1.0) に合わせています。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-20

### Added
- 基本パッケージ構成を追加
  - kabusys パッケージのエントリポイント (src/kabusys/__init__.py) を追加。公開 API: data, strategy, execution, monitoring を想定。
- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルート検出: .git または pyproject.toml を起点に探索（CWD 非依存）。
  - .env / .env.local の読み込み順序を実装（OS 環境変数 > .env.local > .env）。
  - .env の行パーサーを実装（export プレフィックス、引用符、インラインコメントの扱いを考慮）。
  - 自動読み込みを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を提供。
  - 必須設定を取得するヘルパー (_require) と Settings クラスを提供。
  - Settings が要求する主要な環境変数:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパス設定）
    - KABUSYS_ENV（development/paper_trading/live）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）

- データ取得・保存（J-Quants クライアント） (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装。
  - レート制限: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter を実装。
  - 再試行ロジック: 指数バックオフ、最大 3 回、HTTP 408/429/5xx を対象にリトライ。
  - 401 レスポンス時にはリフレッシュトークンを用いた id_token の自動再取得を 1 回試行する実装。
  - ページネーション対応の fetch_* 関数を実装:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（マーケットカレンダー）
  - DuckDB へ冪等に保存する save_* 関数を実装（ON CONFLICT DO UPDATE）
    - save_daily_quotes → raw_prices テーブル
    - save_financial_statements → raw_financials テーブル
    - save_market_calendar → market_calendar テーブル
  - 取得時の fetched_at を UTC ISO8601 で記録し、look-ahead バイアスを追跡可能に。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を取得し raw_news へ保存する基礎実装。
  - セキュリティと堅牢性:
    - defusedxml を用いた XML パース（XML Bomb 等の対策）
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）
    - 記事ID 生成方針（URL 正規化後の SHA-256 ハッシュ先頭等を想定）
    - バルク INSERT のチャンク化（_INSERT_CHUNK_SIZE）
  - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを設定。

- 研究用ファクター計算 / 探索 (src/kabusys/research/)
  - factor_research:
    - calc_momentum: 約1M/3M/6M のリターン算出、MA200 乖離率（WINDOW ベース、データ不足時は None）
    - calc_volatility: 20日 ATR / atr_pct、20日平均売買代金、出来高比率
    - calc_value: raw_financials を用いた PER / ROE 計算（price と組み合わせ）
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンをまとめて取得する SQL ベースの実装
    - calc_ic: ランク相関（Spearman rho）計算（結合・欠損除外・サンプル数閾値）
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー
    - rank: 同順位 (ties) を平均ランクで扱うランク付けユーティリティ（丸めによる ties 検出安定化）

- 戦略層 (src/kabusys/strategy/)
  - 特徴量エンジニアリング (feature_engineering.build_features)
    - research モジュールの生ファクター（momentum / volatility / value）を取得しマージ
    - ユニバースフィルタ: 最低株価 300 円、20日平均売買代金 5 億円
    - 数値ファクターを Z スコア正規化し ±3 でクリップ
    - features テーブルへ日付単位で置換（トランザクション + バルク挿入で原子性を保証）
  - シグナル生成 (signal_generator.generate_signals)
    - features / ai_scores / positions を参照して最終スコアを算出
    - コンポーネント: momentum / value / volatility / liquidity / news（AI）
    - デフォルト重みと閾値（weights デフォルト、BUY 閾値 0.60）
    - Bear レジーム判定（ai_scores の regime_score 平均が負でかつサンプル数閾値を満たす場合）
    - BUY シグナル抑制（Bear 時）
    - SELL シグナル（ストップロス: -8% / スコア低下）
    - signals テーブルへ日付単位で置換（トランザクション + バルク挿入）
    - 重みの検証・正規化、無効な重みのスキップ、合計が 1.0 でない場合のリスケールを実装

- DB テーブル利用想定（ドキュメント兼備忘）
  - raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, positions, signals, raw_news などを参照/更新する設計。

### Changed
- 該当なし（初回リリース）

### Fixed
- 該当なし（初回リリース）

### Removed
- 該当なし（初回リリース）

### Security
- ニュース収集で defusedxml を採用、RSS パースの安全性を考慮。
- HTTP レスポンスの取り扱いに受信サイズ制限とトラッキングパラメータ除去などを導入。

### Notes / Limitations / TODO
- 一部エグジット条件は未実装：
  - トレーリングストップ（peak_price / entry_date を positions テーブルで保持する必要あり）
  - 時間決済（保有 60 営業日超過）等は未実装
- news_collector の一部実装（SSRF/IP フィルタなど）は設計に記載があるが、コード全体は一部省略されているため実装状況に注意。
- DuckDB スキーマ（テーブル定義）は本稿に含まれていないため、初期データベースセットアップ手順を別途用意する必要あり。
- J-Quants クライアントはネットワークエラーや API 側の変更に依存するため、実運用前に十分な統合テストを推奨。
- Settings の env 値（KABUSYS_ENV）は小文字化して検証する設計のため、設定時の大文字/小文字の違いに対して寛容。

---

開発者向け補足（設定・起動時の注意）
- 環境変数の自動読み込みを停止する場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に便利）。
- 必須環境変数が設定されていない場合、Settings の対応するプロパティ呼び出しで ValueError が発生します。
- J-Quants API 利用時は JQUANTS_REFRESH_TOKEN を設定してください（get_id_token により id_token を取得します）。

---

以上がコードベースから推測して作成した CHANGELOG.md（v0.1.0）です。追加でバージョン間の差分やリリースノートを詳述したい場合は、対象のコミットや実際の変更履歴（git log）を提供してください。