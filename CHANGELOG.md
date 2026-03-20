# Changelog

すべての変更は Keep a Changelog の形式に従い、セマンティックバージョニングを使用します。
このファイルは、コードベースの現状（src/ 以下）から推測した初期リリース向けの変更履歴です。

## [Unreleased]

### Added
- ドキュメント化・設計方針を含む初期実装の追加（日本株自動売買システム "KabuSys"）。
  - パッケージ情報: kabusys/__init__.py（バージョン 0.1.0）
- 環境設定管理モジュール（kabusys.config）
  - .env ファイルまたは環境変数からの設定読み込みを自動実行（プロジェクトルート判定による）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサは export 形式、クォート、コメント、エスケープを考慮した堅牢な実装。
  - 必須設定取得時は _require() が ValueError を送出して明示的にエラー通知。
  - settings オブジェクトに以下のプロパティを提供（必須・デフォルト値・検証含む）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
    - KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - DUCKDB_PATH, SQLITE_PATH（デフォルトパス）
    - KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL（検証）

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアント実装（認証、ページング、取得・保存ユーティリティ）。
  - レート制限対応（固定間隔スロットリング: 120 req/min）。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を再試行）。
  - 401 受信時はトークン自動リフレッシュで 1 回再試行。
  - id_token のモジュールレベルキャッシュ（ページネーション間で共有）。
  - JSON レスポンスデコードの例外ハンドリング。
  - ページネーション対応の fetch_* 関数:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes (raw_prices)、save_financial_statements (raw_financials)、save_market_calendar (market_calendar)
    - ON CONFLICT DO UPDATE を利用した冪等性
  - 型変換ユーティリティ: _to_float, _to_int（厳密な変換ルール）

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィード収集の基礎実装（defusedxml を使用して XML 攻撃対策）。
  - URL 正規化（スキーム/ホストの小文字化、トラッキングパラメータ除去、フラグメント除去、クエリソート）。
  - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）、SSRF 対策用の入力検証方針（注釈）。
  - 記事IDの生成方針（正規化 URL の SHA-256 の一部を使用して冪等化）。
  - バルク INSERT のチャンク化（_INSERT_CHUNK_SIZE）、ON CONFLICT DO NOTHING 方針。
  - デフォルト RSS ソース一覧（Yahoo Finance のビジネスカテゴリなど）。

- リサーチ / ファクター計算群（kabusys.research.*）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（MA200）を計算。データ不足時は None を返却。
    - calc_volatility: 20 日 ATR（true range の平均）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組合せて PER / ROE を計算（EPS が 0/欠損 の場合は None）。
  - feature_exploration:
    - calc_forward_returns: 翌日/翌週/翌月などの将来リターンを一括取得（LEAD を利用）。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算（同順位は平均ランク）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - rank: 平均ランク同順位処理を行うランク関数（丸めによる ties 対応）
  - すべて DuckDB 接続を受け、prices_daily / raw_financials を参照（外部ライブラリ未依存、標準ライブラリのみで実装）。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features 実装:
    - research モジュールから得た生ファクターをマージ、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）、±3 でクリップ。
    - features テーブルへ日付単位の置換（DELETE + INSERT をトランザクション内で実施して原子性を確保）。
    - 欠損・外れ値・数値検査に対する堅牢な処理。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals 実装:
    - features と ai_scores を結合し、モメンタム/バリュー/ボラティリティ/流動性/ニュースのコンポーネントスコアを計算（シグモイド変換等）。
    - デフォルト重みを持ち、ユーザー指定 weights を検証・正規化（不正値は無視、合計を 1.0 に再スケール）。
    - Bear レジーム判定（ai_scores の regime_score の平均が負の場合、かつ十分なサンプル数があるとき BUY を抑制）。
    - BUY: final_score >= threshold（デフォルト 0.60）の銘柄に対してランク付けして BUY シグナル生成（Bear の場合は抑制）。
    - SELL: 保有ポジション（positions）のストップロス（終値 / avg_price -1 < -8%）および final_score の閾値割れで SELL シグナルを生成。
    - SELL 優先ポリシー（SELL 対象は BUY から除外）、signals テーブルへ日付単位の置換で書き込み。
    - 欠損データに対する中立値補完（コンポーネントが None の場合は 0.5 で補完）等の防御的設計。

- パッケージエクスポート
  - kabusys.strategy に build_features / generate_signals を公開。
  - kabusys.research の主要ユーティリティを __all__ で公開。

### Changed
- （なし：初期実装想定のため）

### Fixed
- （なし）

### Known issues / Not implemented / Limitations
- signal_generator 内で言及されている一部エグジット条件は未実装:
  - トレーリングストップ（peak_price が positions テーブルに必要）
  - 時間決済（保有 60 営業日超過の処理）
- calc_value では PBR や配当利回りは現バージョンで未実装。
- news_collector の実装はセキュリティ対策（defusedxml、最大バイト数、URL 検証）を考慮しているが、外部ネットワーク・HTTP エラー処理やホスト検証の詳細は利用ケースに応じた追加実装が必要。
- モジュールは DuckDB 上の特定スキーマ（prices_daily, raw_prices, raw_financials, features, ai_scores, positions, signals, market_calendar 等）を前提としている。スキーマが存在しない環境では実行前にテーブル定義が必要。

---

## [0.1.0] - 2026-03-20

初回リリース（推定）。上記 Unreleased の内容を基にした最初の安定機能群をパッケージ化。

### Added
- パッケージ公開バージョン情報（kabusys.__version__ = "0.1.0"）。
- 環境設定、自動 .env 読み込み、必須環境変数検証。
- J-Quants API クライアント（取得・保存・認証・再試行・レート制限）。
- ニュース収集（RSS）、URL 正規化、XML セーフパース。
- DuckDB を用いたファクター計算（momentum / volatility / value）。
- 特徴量構築（Z スコア正規化、ユニバースフィルタ、クリッピング、冪等保存）。
- シグナル生成（最終スコア計算、BUY/SELL ルール、Bear 抑制、冪等保存）。
- 研究用ユーティリティ（将来リターン計算、IC 計算、統計サマリー、ランク関数）。

### Known issues / Not implemented
- 上述の未実装エグジット条件、PBR/配当利回り等は将来の課題として残る。

---

注: この CHANGELOG は提供されたソースコードから推測して作成しています。実際のリリースノートやバージョン管理履歴（git のコミットログ等）が利用可能であれば、そちらに基づく正確な履歴への差し替えを推奨します。必要であれば、各機能ごとの変更詳細（関数ごとのインターフェース、期待される DB スキーマ、サンプル環境変数一覧など）も追記できます。