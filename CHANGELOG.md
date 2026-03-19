CHANGELOG
=========

すべての重要な変更点はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

未リリース
---------

- （なし）

0.1.0 - 2026-03-19
------------------

Added
- 初回リリース。日本株自動売買システム「KabuSys」の基礎モジュール群を追加。
  - パッケージ初期化
    - パッケージバージョン: 0.1.0
    - エクスポート: data, strategy, execution, monitoring

  - 設定 / 環境変数管理 (kabusys.config)
    - .env / .env.local 自動ロード機能（OS 環境変数の保護を考慮し .env → .env.local の順に適用）。
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索（CWD 非依存）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用）。
    - .env パーサは export 構文、クォート（エスケープ対応）、インラインコメントルール等をサポート。
    - 必須環境変数取得時に未設定なら明確なエラーメッセージを送出。
    - 設定プロパティ:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
      - Slack 用: SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - DB パス: DUCKDB_PATH (デフォルト data/kabusys.duckdb), SQLITE_PATH (data/monitoring.db)
      - 環境種別バリデーション (KABUSYS_ENV: development / paper_trading / live)
      - ログレベルバリデーション (LOG_LEVEL)

  - データ取得 / 保存 (kabusys.data.jquants_client)
    - J-Quants API クライアントを実装。
    - レート制限: 120 req/min 固定間隔スロットリング（内部 RateLimiter）。
    - 再試行（リトライ）ロジック: 指数バックオフ、最大 3 回、408/429/5xx を対象。429 の場合は Retry-After ヘッダを優先。
    - 401 レスポンス時はリフレッシュトークンでトークン自動更新を試行（1 回のみ）して再試行。
    - ページネーション対応（pagination_key を利用してページ取得を継続）。
    - DuckDB へ冪等保存:
      - save_daily_quotes -> raw_prices（ON CONFLICT DO UPDATE）
      - save_financial_statements -> raw_financials（ON CONFLICT DO UPDATE）
      - save_market_calendar -> market_calendar（ON CONFLICT DO UPDATE）
    - レスポンス JSON デコード失敗時やネットワークエラー時の明確な扱い。
    - ユーティリティ: _to_float / _to_int（安全な型変換ルールを提供）。
    - fetched_at は UTC ISO8601 形式で記録（Look-ahead bias のトレースを容易に）。

  - ニュース収集 (kabusys.data.news_collector)
    - RSS フィードからの記事収集と raw_news への冪等保存の設計。
    - デフォルト RSS ソース（例: Yahoo Finance）。
    - 記事 ID は URL 正規化後の SHA-256 ハッシュで生成する方針（utm_* 等トラッキングパラメータ除去）。
    - defusedxml を使って XML 関連の攻撃を軽減。
    - 受信最大バイト数制限（10MB）や HTTP スキームチェック等で安全性を強化（メモリ DoS / SSRF 対策を考慮）。
    - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリ整列。
    - バルク INSERT のチャンク処理を導入して SQL パラメータ数/長の問題を回避。

  - リサーチ用モジュール (kabusys.research)
    - ファクター計算（factor_research）:
      - Momentum: mom_1m / mom_3m / mom_6m, ma200_dev（200日移動平均乖離、データ不足時は None）。
      - Volatility: 20日 ATR, atr_pct（ATR/close）, avg_turnover（20日平均売買代金）, volume_ratio。
      - Value: per, roe（raw_financials の最新レコードを参照）。
      - DuckDB ベースで SQL とウィンドウ関数を活用して効率的に計算。
    - 特徴量探索（feature_exploration）:
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン算出。営業日欠損に配慮して範囲を限定。
      - calc_ic: スピアマンのランク相関（IC）を計算。サンプル数 3 未満は None を返す。
      - factor_summary: count/mean/std/min/max/median を計算（None を除外）。
      - rank: 同順位は平均ランクで処理、丸めによる ties 検出漏れ対策（round(..., 12)）を実施。
    - 外部依存を避け、標準ライブラリ＋DuckDB のみで動作する設計。

  - 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
    - research 側で計算した生ファクターを統合して features テーブルに保存する処理を実装。
    - ユニバースフィルタ:
      - 最低株価 300 円以上
      - 20日平均売買代金 >= 5億円
    - 正規化: zscore_normalize を利用して指定カラムを Z スコア化、±3 でクリップ（外れ値抑制）。
    - features への書き込みは日付単位で一度 DELETE してから INSERT（トランザクションで原子性を保証）、冪等。

  - シグナル生成 (kabusys.strategy.signal_generator)
    - features と ai_scores を統合して final_score を計算し、BUY/SELL シグナルを生成。
    - コンポーネントスコア:
      - momentum/value/volatility/liquidity/news を計算（欠損は中立 0.5 で補完）。
      - シグモイド変換や PER に基づく value スコア等を適用。
    - 重み付け:
      - デフォルト重み: momentum:0.40, value:0.20, volatility:0.15, liquidity:0.15, news:0.10
      - ユーザー重みは検証・補完・再スケール（合計が 1 になるように）。
      - 無効な重み値は無視し警告を出す。
    - Bear レジーム判定:
      - ai_scores の regime_score 平均が負の場合は Bear と判定（サンプル数最小値を下回る場合は Bear とみなさない）。
      - Bear レジーム時は BUY シグナルを抑制。
    - エグジット（SELL）判定:
      - ストップロス（終値/avg_price - 1 <= -8%）優先
      - final_score が閾値未満（デフォルト閾値 0.60）
      - positions / 価格欠損時の扱いに注意（価格欠損だと SELL 判定をスキップして安全側に寄せる等）。
    - signals テーブルへの書き込みも日付単位で置換（トランザクションで原子性を保証）。

  - 共通 / 実装方針
    - DuckDB を主要な分析ストアとして利用（prices_daily, raw_prices, raw_financials, features, ai_scores, signals, positions, market_calendar 等を想定）。
    - ルックアヘッドバイアス対策: target_date 時点以前のデータのみを参照し、fetched_at の記録や設計ドキュメントに準拠。
    - 外部サービス（発注 API / 本番ポートフォリオ）への直接アクセスを戦略・研究モジュールで行わない方針。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- defusedxml の採用、HTTP スキームチェック、受信サイズ制限、.env 読み込み時のファイル読み取り例外に対する警告など、安全性・堅牢性を意識した実装を多数採用。

Notes / 今後の拡張予定（設計メモ）
- strategy の SELL 条件にトレーリングストップや時間決済の実装を予定（positions に peak_price / entry_date 情報が必要）。
- news_collector の記事と銘柄紐付け（news_symbols）や自然言語処理パイプラインの統合。
- モジュール間のテストや CI、さらに細かいエラーハンドリングの拡充。

ライセンス
- （ファイル中に明記がないためここでは未記載。必要に応じて LICENSE を追加してください。）