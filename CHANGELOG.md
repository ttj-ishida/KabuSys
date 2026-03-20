# Changelog

すべての重要な変更点はこのファイルに記録します。本ファイルは「Keep a Changelog」の規約に準拠しています。

全ての変更はセマンティックバージョニングに従います。  

## [0.1.0] - 2026-03-20

初回公開リリース。本ライブラリは日本株自動売買システム（KabuSys）のコア機能を提供します。主な追加点・設計方針は以下の通りです。

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（src/kabusys/__init__.py、バージョン = 0.1.0）。
  - strategy、execution、monitoring、data モジュールを公開 API に含める設定。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイル／環境変数から設定を自動読み込みする機能を実装。
    - 読み込み優先度: OS環境変数 > .env.local > .env。
    - プロジェクトルート検出は .git または pyproject.toml を基準に親ディレクトリ探索して行うため、CWD に依存しない。
    - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - より堅牢な .env 行パーサを実装（export 形式、シングル/ダブルクォート、エスケープ、インラインコメント処理などに対応）。
  - Settings クラスを導入し、アプリケーションで使う主要設定（J-Quants トークン、Kabu API、Slack、DBパス、環境種別、ログレベルなど）をプロパティ経由で取得。必須環境変数未設定時に明示的に ValueError を送出する `_require` を実装。

- データ取得・保存（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装。
    - 固定間隔の RateLimiter（120 req/min）を実装してレート制限を守る。
    - リトライ（指数バックオフ）ロジックを実装（最大 3 回、HTTP 408/429/5xx 対応）。
    - 401 受信時にリフレッシュトークンから id_token を再取得して 1 回リトライする自動リフレッシュ機構を実装。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）を実装。
    - DuckDB へ冪等に保存する save_* 関数を実装（raw_prices / raw_financials / market_calendar に対して ON CONFLICT DO UPDATE を使用）。
    - 日付・時刻の fetched_at を UTC ISO8601 で記録して「いつデータを取得したか」をトレース可能に。
  - 型変換ユーティリティ（_to_float / _to_int）を追加して入力データの堅牢性を確保。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集して raw_news に保存する基盤を実装。
  - 記事 ID を URL 正規化後の SHA-256 ハッシュ（先頭 32 文字）で生成し冪等性を確保。
  - URL 正規化機能を実装（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリのソートなど）。
  - defusedxml を用いた XML パースで XML Bomb 等の攻撃を防御。
  - 受信バイト数上限（MAX_RESPONSE_BYTES = 10MB）を設定してメモリ DoS を軽減。
  - DB 保存時はバルク挿入・チャンク処理でパフォーマンスに配慮（チャンクサイズ上限を設定）。

- リサーチ（src/kabusys/research/*）
  - ファクター計算（factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日移動平均乖離率）計算を実装（prices_daily を参照）。
    - Volatility（20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率）を実装。
    - Value（PER、ROE）を実装（raw_financials と prices_daily を組み合わせ）。
    - データ不足時は None を返す設計で安全に扱える実装。
  - 特徴量探索（feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）を実装（複数ホライズン対応、効率的な範囲スキャン）。
    - Spearman ランク相関（IC）計算（calc_ic）を実装（ties 対応の rank 関数含む）。
    - factor_summary で基本統計量（count/mean/std/min/max/median）を計算。
  - research パッケージの公開 API を整理（calc_momentum / calc_volatility / calc_value / zscore_normalize / calc_forward_returns / calc_ic / factor_summary / rank をエクスポート）。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - 研究環境で計算した生ファクターを統合・正規化して features テーブルへ保存する実装を追加。
  - 処理フロー:
    - calc_momentum / calc_volatility / calc_value で raw factors を取得。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指定カラムを Z スコア正規化（zscore_normalize）し ±3 でクリップ。
    - 日付単位での置換（DELETE + bulk INSERT）により冪等性と原子性を保証（トランザクション使用）。
  - DB から当日欠損や休場日に対応するため、target_date 以前の最新価格を参照する実装。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - features と ai_scores を統合し final_score を計算、BUY/SELL シグナルを生成して signals テーブルへ保存する実装を追加。
  - スコア計算:
    - momentum / value / volatility / liquidity / news（AI）をコンポーネントとして計算し、重み付き合算で final_score を算出（デフォルト重みを実装）。
    - 欠損コンポーネントは中立値 0.5 で補完し不当に降格しない設計。
    - ユーザー指定 weights を検証・補完・再スケールするロジックを実装（不正な重みは警告して無視）。
  - Bear レジーム検知（AI の regime_score 平均が負かつサンプル数閾値以上で判定）により BUY を抑制する機能を実装。
  - SELL（エグジット）判定実装:
    - ストップロス（終値 / avg_price - 1 < -8%）を優先的に判定。
    - final_score が閾値未満の銘柄を SELL。
    - 一部の条件（トレーリングストップ、時間決済）は positions テーブルの拡張が必要で未実装として注記。
  - signals テーブルへの日付単位置換（DELETE + bulk INSERT）により冪等性と原子性を保証（トランザクション使用）。

### Changed
- （初回リリースのため特記すべき変更履歴はありません）

### Fixed
- （初回リリースのため過去バグ修正履歴はありません）

### Security
- news_collector で defusedxml を使用して XML の安全なパースを行うなど、外部入力に対する安全対策を講じています。
- J-Quants クライアントはトークンの自動リフレッシュを行いますが、_request 内で allow_refresh を制御して無限再帰を防止しています。

### Notes / Limitations
- 現在実装されている SELL 条件にはトレーリングストップや保有期間による決済等は含まれていません（positions テーブルの拡張が必要）。
- news_collector の完全な SSRF 防止（外部ホストへ接続する前の IP/ホスト検証等）や RSS フィード取得の細かいネットワーク制限は追加で監査・強化が可能。
- 一部のユーティリティ（zscore_normalize）は data.stats 側に依存しています（エクスポート済み）。本リリースは内部 API に依存しているため、互換性を壊す変更は今後のバージョンで注意が必要です。

---

今後の予定（非包括的）:
- positions テーブル拡張に伴うトレーリングストップ / 時間決済の実装。
- news_collector の URL/ネットワークの追加セキュリティ対策。
- 追加の戦略評価メトリクス（ブートストラップ IC 分布、セクタ調整等）。

もし CHANGELOG に追記すべき点（意図したが記載漏れの機能や実装上の注意点）があればお知らせください。