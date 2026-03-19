# Changelog

すべての重要な変更はこのファイルで記録します。本プロジェクトは Keep a Changelog の方針に準拠します。
リリースの互換性レベルはセマンティックバージョニングに従います。

現行バージョン: 0.1.0

## [Unreleased]
（無し）

## [0.1.0] - 2026-03-19

初回公開リリース。以下の主要機能・モジュールを実装・追加しました。

### Added
- パッケージ基本情報
  - パッケージ名 kabusys、バージョン "0.1.0" を定義（src/kabusys/__init__.py）。

- 環境設定管理（src/kabusys/config.py）
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動ロードする仕組みを実装。
  - 環境変数自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサーは `export KEY=val` 形式、シングル/ダブルクォート内のエスケープ、行内コメント判定（クォートあり/なしの扱いを区別）に対応。
  - .env ロード時に OS 環境変数を保護するための protected キー集を導入し、`.env.local` で上書き可能。読み込み失敗時は警告で通知。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス等の設定値をプロパティ経由で取得可能。必須環境変数未設定時は ValueError を送出。
  - 環境（KABUSYS_ENV）・ログレベル（LOG_LEVEL）の検証（許容値チェック）と便捷プロパティ（is_live / is_paper / is_dev）を追加。

- データ取得・永続化（J-Quants クライアント）（src/kabusys/data/jquants_client.py）
  - J-Quants API 用クライアントを実装。ページネーション対応の fetch 関数を提供:
    - fetch_daily_quotes（株価日足 / ページネーション対応）
    - fetch_financial_statements（財務データ / ページネーション対応）
    - fetch_market_calendar（JPX カレンダー）
  - API 呼び出し共通の _request 実装:
    - レート制限（120 req/min）を固定間隔スロットリングで順守する RateLimiter を導入。
    - 指数バックオフによる再試行（最大 3 回、408/429/5xx を対象）。429 時は Retry-After を優先。
    - 401 受信時はリフレッシュトークンによる id_token 再取得を 1 回だけ自動実行（無限再帰を防ぐ allow_refresh フラグ）。
    - JSON デコード失敗やネットワークエラー時の適切な例外処理とログ。
    - モジュールレベルでの id_token キャッシュを実装してページネーション間での再利用を行う。
  - DuckDB への保存ユーティリティを実装（冪等性を重視）:
    - save_daily_quotes -> raw_prices に ON CONFLICT DO UPDATE（重複更新）で保存。
    - save_financial_statements -> raw_financials に ON CONFLICT DO UPDATE で保存。
    - save_market_calendar -> market_calendar に ON CONFLICT DO UPDATE で保存。
  - データ型変換ユーティリティ `_to_float` / `_to_int` を実装し、入力値の頑健な変換を保証。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集し raw_news に保存するためのモジュールを追加。
  - デフォルト RSS ソース（Yahoo Finance のビジネスカテゴリ）を定義。
  - セキュリティ対策:
    - defusedxml による安全な XML パース（XML Bomb 等対策）。
    - HTTP(S) 以外のスキーム拒否や受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）による SSRF/DoS 緩和。
    - トラッキングパラメータ（utm_* など）を除去し、クエリをソートすることで URL 正規化処理を実装。
    - 記事 ID は（設計方針）URL 正規化後の SHA-256 ハッシュ（先頭 32 文字）を利用して冪等性を担保（ドキュメントに記載）。
  - テキスト前処理（URL 除去・空白正規化）や DB へのバルク挿入（チャンク化）等を考慮。

- リサーチ関連（src/kabusys/research/*）
  - ファクター計算（ファクター研究）モジュールを実装（src/kabusys/research/factor_research.py）:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日MA乖離）を計算。窓のデータ不足は None を返す。
    - calc_volatility: ATR(20) / atr_pct / avg_turnover / volume_ratio を計算。トゥルーレンジが NULL の伝播を制御。
    - calc_value: raw_financials から直近財務を併合して PER / ROE を計算（EPS が 0 の場合は None）。
    - DuckDB の window 関数を活用し、営業日ベースのラグ・移動平均を計算。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算。サンプル数不足時は None。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を計算。
    - rank: 同順位は平均ランクとするランク変換ユーティリティ。
  - research パッケージの __all__ に主要関数を公開。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - build_features を実装:
    - research モジュール（calc_momentum / calc_volatility / calc_value）から生ファクターを取得し統合。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指定カラム群を Z スコア正規化（kabusys.data.stats.zscore_normalize を使用）し ±3 でクリップ。
    - DuckDB の features テーブルへ日付単位で DELETE → INSERT（トランザクション）することで日付単位の置換（冪等）を保証。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - generate_signals を実装:
    - features と ai_scores を統合し、モメンタム/バリュー/ボラティリティ/流動性/ニュースの各コンポーネントスコアを算出。
    - コンポーネントはシグモイド変換・逆転（ボラティリティは低いほど有利）や PER の変換などで正規化。
    - 欠損コンポーネントは中立 0.5 で補完。
    - 重み（デフォルト値を持つ）を結合して final_score を算出。ユーザー指定 weights は検証・正規化して受け付ける。
    - Bear レジーム判定（ai_scores の regime_score の平均が負かつサンプル数閾値以上）では BUY を抑制。
    - SELL 条件（ストップロス -8% / スコア低下）に基づくエグジット判定を実装。価格欠損時の SELL 判定スキップや保有銘柄が features に無い場合の警告を実装。
    - signals テーブルへ日付単位の置換（トランザクション＋バルク挿入）を行い冪等性を保持。
  - strategy パッケージの __all__ で build_features / generate_signals を公開。

- DB トランザクション方針
  - features / signals 等の書き込みは日付単位の置換を行い、BEGIN/DELETE/INSERT/COMMIT（失敗時は ROLLBACK）で原子性を保証。ROLLBACK 失敗時はログで警告。

### Changed
- （初回リリースのため該当無し）

### Fixed
- （初回リリースのため該当無し）
  - ただし、各モジュールはエラー時にログや警告を残す設計（例: .env 読み込み失敗、データ PK 欠損行のスキップ、価格欠損時の SELL 判定スキップ 等）。

### Security
- 外部データ取込におけるセキュリティ対策を導入:
  - news_collector: defusedxml を使用した安全な XML パース、受信バイト数制限、URL 正規化によるトラッキングパラメータ除去、HTTP(S) スキーム制限等。
  - jquants_client: トークン管理を行い 401 時の安全なトークンリフレッシュを導入。RateLimiter によるレート制限順守。

### Notes / Known limitations
- execution モジュールはパッケージの公開対象に含まれるが（__all__ に含まれる）、今回のスナップショットでは該当実装が存在しないか空の初期状態です。発注・実行層は本バージョンでは実装の想定外。
- news_collector の記事 ID 生成や一部設計方針はドキュメントに記載されているが、実運用で必要なマッピング（news_symbols など）の詳細は今後の実装で補完予定。
- 一部ユーティリティ（例: kabusys.data.stats.zscore_normalize）はこのスナップショットで参照されており、別ファイルで提供される前提です。

---

開発者向け: 今後のリリースでは実行レイヤ（execution）やモニタリング（monitoring）の実装、さらなるテスト・ドキュメント整備、運用向けの CLI / scheduler 統合を予定しています。