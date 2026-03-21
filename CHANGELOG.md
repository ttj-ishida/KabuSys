# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。
主要なバージョン方針: 0.y.z は初期実装・機能追加中心。

## [Unreleased]
（現在特に未リリースの変更はありません）

## [0.1.0] - 2026-03-21

初期リリース。日本株の自動売買システムのコア機能を実装しました。
以下はコードベースから推測される主要な追加・仕様です。

### Added
- パッケージ基盤
  - パッケージエントリポイントを追加（src/kabusys/__init__.py）。バージョンは 0.1.0。
  - サブモジュールの公開: data, strategy, execution, monitoring。

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env パーサ実装: export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - OS 環境変数を保護する protected ロジック（.env.local は override=True）。
  - Settings クラスを提供し、必要な環境変数取得メソッドを実装（J-Quants トークン、kabu API、Slack、DB パス等）。
  - env（KABUSYS_ENV）および LOG_LEVEL の値検証（許容値チェック）と便利なブールプロパティ（is_live / is_paper / is_dev）。
  - Path 型の設定（duckdb / sqlite のデフォルトパス）。

- データ取得・保存（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装。
    - 固定間隔スロットリングによるレート制限制御（120 req/min）。
    - リトライ（指数バックオフ）、最大試行回数、429 の Retry-After 優先処理、408/429/5xx に対するリトライ。
    - 401 受信時は ID トークンを自動リフレッシュして 1 回だけリトライ。
    - モジュールレベルの ID トークンキャッシュを実装（ページネーション間で共有）。
    - fetch_xxx 系関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）を実装しページネーション対応。
    - save_xxx 系関数で DuckDB へ冪等保存（ON CONFLICT DO UPDATE）を実装（raw_prices / raw_financials / market_calendar）。
    - データ型変換ユーティリティ _to_float / _to_int を実装（安全な変換・欠損処理）。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィード収集処理の骨組みを実装。
    - デフォルト RSS ソース（Yahoo Finance）を定義。
    - 受信サイズ制限（MAX_RESPONSE_BYTES）、XML に対して defusedxml を使用するなど、セキュリティ対策を実装。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、スキーム/ホスト小文字化、フラグメント削除）を実装。
    - 記事 ID の生成方針（URL 正規化後の SHA-256 ハッシュ先頭等）をコメントで明示。
    - バルク INSERT のチャンク処理を想定（SQL 上の制限対策）。
    - SSRF・XML Bomb・メモリ DoS を意識した設計がコメントに記載。

- 研究用ファクター計算（src/kabusys/research/factor_research.py）
  - calc_momentum / calc_volatility / calc_value を実装。
    - Momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200 日データが不足する場合は None）。
    - Volatility: 20 日 ATR、相対 ATR（atr_pct）、avg_turnover、volume_ratio（必要行数チェック）。
    - Value: 当日株価と最新財務データから PER, ROE を算出（raw_financials と prices_daily を参照）。
  - DuckDB ベースで SQL + Python により計算し、ルックアヘッドバイアスを防ぐ設計。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - build_features(conn, target_date) を実装。
    - research モジュールの生ファクターを取得しマージ。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5億円）を適用。
    - Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）と ±3 でクリップ。
    - features テーブルへ日付単位での置換（BEGIN/DELETE/INSERT/COMMIT による原子性を保証）。
    - ルックアヘッドバイアス回避のため target_date 時点のデータのみ使用。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - generate_signals(conn, target_date, threshold, weights) を実装。
    - features と ai_scores を統合して各銘柄の component スコア（momentum/value/volatility/liquidity/news）を算出。
    - Sigmoid, 平均化等のユーティリティを実装。
    - デフォルト重み・閾値を定義（例: momentum=0.40, default threshold=0.60）。
    - 重み入力のバリデーションと再スケール処理（未知キーや不正値は無視）。
    - Bear レジーム判定（ai_scores の regime_score の平均が負 → BUY を抑制）。
    - BUY シグナル（score >= threshold）および SELL シグナル（ストップロス -8% / score 低下）を生成。
    - 保有ポジションの取得は positions テーブルより行い、価格欠損時は SELL 判定をスキップ。
    - signals テーブルへ日付単位で置換（原子操作）。
    - 未実装のエグジット条件（トレーリングストップ・時間決済）はコメントで明示（今後の実装予定）。

- 研究支援ツール（src/kabusys/research/feature_exploration.py）
  - calc_forward_returns(conn, target_date, horizons) を実装（複数ホライズン対応、ホライズン検証）。
  - calc_ic(factor_records, forward_records, factor_col, return_col) を実装（Spearman ランク相関、サンプル不足時は None）。
  - rank(values)（同順位は平均ランク）を実装（丸めで ties の検出漏れを防止）。
  - factor_summary(records, columns) により count/mean/std/min/max/median を算出。
  - 実装は外部ライブラリに依存しない（標準ライブラリのみ）。

- モジュールのエクスポート整理
  - strategy と research の __init__.py で公開 API をまとめて定義（build_features / generate_signals / calc_* 等）。

### Changed
- （初版のため既存実装の「変更」はありませんが、設計上の注意点を明示）
  - DuckDB への書き込みは基本的に日付単位での置換（DELETE → INSERT）により冪等性・原子性を担保。
  - データ欠損／非数に対して慎重な扱い（None や非有限値はスコア計算で中立値 0.5 にフォールバックする等）。

### Fixed
- （初版のため bug fix 履歴はなし。実装中に回避したであろう問題点をコメントで明示）
  - JSON デコード失敗時の詳細メッセージ化（jquants_client の _request）。
  - DuckDB に挿入する前に主キー欠損行をスキップし警告を出力（save_* 関数）。

### Security
- 外部入力（RSS/XML）の処理で defusedxml を使用し XML-related 脅威を軽減（news_collector）。
- ネットワーク経由の受信サイズを制限（MAX_RESPONSE_BYTES）してメモリ DoS を抑止（news_collector）。
- URL 正規化でトラッキングパラメータを除去、SSRF 対策の方針をコメントで明示。
- J-Quants クライアントはタイムアウトやエラーハンドリング、トークン自動リフレッシュの実装で堅牢性を向上。

### Performance
- API レートリミットに合わせた固定間隔スロットリングを実装し、レート超過による 429 を回避。
- ページネーション間でのトークンキャッシュによる余計な認証コールの削減。
- DuckDB へのバルク挿入とトランザクションまとめによる DB オーバーヘッド低減。
- news_collector はバルク INSERT のチャンクサイズを採用（_INSERT_CHUNK_SIZE）。

### Known limitations / Todo
- signal_generator のエグジット条件におけるトレーリングストップ・時間決済は未実装（コメントで明示）。
- execution 層（発注 API）との統合は strategy 層から切り離して設計されている（発注ロジック未提供）。
- 一部の設計はコメントで方針のみ提示されており、実運用での追加安全チェックや監視が必要（例: news -> symbol マッピング、SSRF の IP 範囲制限など）。
- tests / CI に関する実装はコードからは確認できない（今後追加推奨）。

---

その他補足:
- README / ドキュメントやマイグレーション/DDL（DuckDB のテーブル定義）等はソース内に含まれていないため、実動作には DB スキーマ定義・実行環境設定が必要です。
- 本 CHANGELOG はソース内のドキュメント文字列と実装から推測して作成しています。実際の変更履歴とは差異があり得ます。