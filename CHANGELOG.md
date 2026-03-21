Keep a Changelog に準拠した形式で、このコードベースから推測される変更履歴（日本語）を作成しました。

CHANGELOG.md
=============

すべての変更は "Keep a Changelog" の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- （なし）

[0.1.0] - 2026-03-21
-------------------

Added
- 初回リリース: KabuSys — 日本株自動売買システムのコアライブラリを追加。
  - パッケージエントリポイント: kabusys.__version__ = "0.1.0"。公開 API として data, strategy, execution, monitoring をエクスポート。

- 環境設定 / 設定読み込み (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダを実装。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。プロジェクトルートは .git または pyproject.toml を基準に探索。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサ実装:
    - コメント行、export プレフィックス、シングル/ダブルクォート対応、エスケープシーケンス、インラインコメントの取り扱い等に対応。
  - Settings クラスを提供（プロパティで必要な環境変数を取得／バリデーションを実施）:
    - 必須トークン/キー: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（未設定時は ValueError）。
    - DB パス: DUCKDB_PATH / SQLITE_PATH（デフォルト値あり）。
    - 環境モード: KABUSYS_ENV (development|paper_trading|live) の検証。
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。

- データ取得・保存（kabusys.data.jquants_client）
  - J‑Quants API クライアントを実装。
  - レート制限管理（固定間隔スロットリング、120 req/min）。
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。429 の場合は Retry-After を尊重。
  - 401 Unauthorized を受けた際の自動トークンリフレッシュ（1 回のみ）とモジュールレベルのトークンキャッシュ。
  - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）:
    - 冪等性を確保するため ON CONFLICT DO UPDATE を使用。
    - fetched_at を UTC で記録（Look‑ahead bias をトレース可能に）。
    - 型変換ユーティリティ (_to_float / _to_int) を実装。PK 欠損行のスキップと警告ログ出力。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからの記事収集モジュールを実装（デフォルトに Yahoo Finance のビジネス RSS を含む）。
  - URL 正規化（トラッキングクエリ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）。
  - defusedxml を利用して XML 攻撃（XML Bomb 等）対策。
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB）や HTTP スキーム検証などの安全対策。
  - 記事 ID は正規化後の URL の SHA-256（先頭 32 文字）を用いることで冪等性を担保。
  - DB へのバルク挿入はチャンク化して実行、INSERT RETURNING 等で挿入数を正確に把握。

- 研究用モジュール（kabusys.research）
  - factor_research:
    - モメンタム（1/3/6 か月リターン、200日移動平均乖離）、ボラティリティ（20日 ATR / atr_pct）、流動性（20日平均売買代金/出来高比）、バリュー（PER/ROE）を DuckDB の prices_daily / raw_financials を参照して計算する関数を実装（calc_momentum / calc_volatility / calc_value）。
    - 各計算はデータ不足時に None を返す設計。
  - feature_exploration:
    - 将来リターンの計算（calc_forward_returns、指定ホライズンに対応、SQLで効率的に取得）。
    - IC（Spearman ランク相関）の計算（calc_ic、最小サンプル判定あり）。
    - 基本統計サマリー（factor_summary）とランク変換 util（rank）。
  - 依存は標準ライブラリと duckdb のみ（pandas 等の外部依存を避ける設計）。

- 特徴量作成（kabusys.strategy.feature_engineering）
  - build_features:
    - research の生ファクターを取得してマージ、ユニバースフィルタを適用（最低株価 300 円、20日平均売買代金 >= 5 億円）。
    - 指定列の Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）と ±3 でクリップ。
    - features テーブルへ日付単位で置換（BEGIN/DELETE/INSERT/COMMIT、失敗時の ROLLBACK とログ）。
    - 冪等性を意識した実装。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals:
    - features と ai_scores を統合して、momentum/value/volatility/liquidity/news のコンポーネントスコアを計算。
    - コンポーネントごとの重み（デフォルト: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）と閾値（デフォルト BUY=0.60）をサポート。
    - AI レジームスコアの集計で Bear レジームを判定し、Bear 時は BUY を抑制。
    - SELL 判定（エグジット）を実装:
      - ストップロス（終値/avg_price - 1 < -8%）を最優先。
      - final_score が閾値未満の場合に SELL。
      - 保有銘柄で価格欠損時は SELL 判定をスキップしてログを出力。
    - signals テーブルへの日付単位置換（トランザクション＋バルク挿入）とログ出力。
    - ユーザー指定 weights の検証・正規化（未知キー、非数値、負値、NaN/Inf を無視。合計が 1 でない場合は再スケール）。

- strategy パッケージの公開関数:
  - build_features, generate_signals を __all__ にて公開。

Security
- news_collector で defusedxml を使用、レスポンスバイト上限、HTTP スキーム検査など SSRF / DoS 対策を組み込み。
- jquants_client の HTTP 実装はリトライ/バックオフ/Token Refresh を備え、429 の Retry-After を尊重。

Other notes / Implementation details
- DuckDB を中心に設計。多くの関数は prices_daily / raw_financials / ai_scores / positions / features / signals 等のテーブルを前提としている。
- ログレベルや多くの検証は settings 経由で制御する想定。
- トランザクションを利用して日付単位の置換を行い、原子性を保証。
- エラーハンドリング時に ROLLBACK に失敗すると警告ログを出す実装がある。

Known limitations / Not implemented
- strategy.signal_generator 内で言及されている未実装機能:
  - トレーリングストップ（peak_price が positions テーブルに必要）
  - 時間決済（保有 60 営業日超過）
- execution 層（発注 API 連携）と monitoring の具体実装はこのスナップショット内では未完成／空のモジュール（execution.__init__ は空）。
- 一部ユーティリティ（例: kabusys.data.stats.zscore_normalize）は参照されているが、このスナップショットに定義が含まれていない。パッケージ内に実装済みであることが期待される。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Security
- （上記 Security セクション参照）

----

必要であれば、変更点の粒度をさらに細かく分割（モジュール別の履歴や実装上の注意点を個別に列挙）できます。どの形式／粒度にしますか？