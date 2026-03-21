CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- なし

0.1.0 - 2026-03-21
------------------

初回リリース。日本株の自動売買・研究パイプラインのコア機能を提供します。

Added
- パッケージ初期化
  - kabusys パッケージを追加。公開 API として data, strategy, execution, monitoring をエクスポート。
  - __version__ = "0.1.0" を設定。

- 環境設定 / ロード
  - kabusys.config: .env ファイルまたは OS 環境変数から設定を自動読み込み。
    - プロジェクトルートは __file__ を起点に .git / pyproject.toml を探索して特定（CWD に依存しない）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途）。
  - .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）。
  - Settings クラスを提供し、必須値取得時に ValueError を送出するユーティリティを実装。
    - 主な設定項目: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL
    - KABUSYS_ENV や LOG_LEVEL の値検証（許容値チェック）を導入。

- データ取得／永続化（J-Quants API）
  - kabusys.data.jquants_client: J-Quants API クライアントを実装。
    - レート制御（120 req/min 固定間隔スロットリング）。
    - 再試行（指数バックオフ、最大 3 回）。408/429/5xx を対象にリトライ。429 の Retry-After を考慮。
    - 401 受信時のリフレッシュトークン自動更新（1 回のみ）とトークンキャッシュ。
    - ページネーション対応の fetch_* 関数:
      - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
    - DuckDB へ冪等に保存する save_* 関数:
      - save_daily_quotes -> raw_prices
      - save_financial_statements -> raw_financials
      - save_market_calendar -> market_calendar
    - 取得時刻（fetched_at）を UTC ISO8601 で記録（Look-ahead bias 対策）。
    - 型変換ユーティリティ _to_float / _to_int を実装し不正データを安全に扱う。

- ニュース収集
  - kabusys.data.news_collector: RSS フィードからニュースを収集して raw_news 等に保存する機能。
    - RSS 取得・パース（defusedxml を使用して XML 攻撃防止）。
    - URL 正規化（スキーム/ホストの小文字化、トラッキングパラメータの削除、フラグメント削除、クエリソート）。
    - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を保証。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES, 10MB）やバルク INSERT のチャンク化などメモリ/SQL 安全対策。
    - デフォルト RSS ソースに Yahoo Finance のビジネス系フィードを追加。

- 研究用ファクター計算
  - kabusys.research.factor_research:
    - モメンタム（mom_1m, mom_3m, mom_6m）、MA200 乖離（ma200_dev）を計算（営業日ベースのラグ）。
    - ボラティリティ / 流動性（atr_20, atr_pct, avg_turnover, volume_ratio）を計算。true_range 計算で NULL 伝播を正確に制御。
    - バリュー（per, roe）を計算。raw_financials から直近の財務データを取得して株価と組み合わせ。
    - DuckDB 上の SQL とウィンドウ関数を活用した実装。
  - kabusys.research.feature_exploration:
    - 将来リターン calc_forward_returns（複数ホライズン対応、ホライズン上限 252 営業日の検証）。
    - IC（Spearman の ρ）calc_ic、ランク変換ユーティリティ rank（同順位は平均ランク処理）。
    - factor_summary：各ファクターの統計サマリー（count/mean/std/min/max/median）。
  - research パッケージのエクスポートを整備。

- 特徴量作成（Strategy 用）
  - kabusys.strategy.feature_engineering:
    - research モジュールで計算した raw ファクターを統合し、ユニバースフィルタ（最低株価・平均売買代金）適用。
    - 指定カラムの Z スコア正規化（kabusys.data.stats の zscore_normalize を使用）、±3 clip を実施。
    - features テーブルへ日付単位で置換（BEGIN / DELETE / INSERT / COMMIT を用いたトランザクションで原子性を保証）。
    - ユニバース最低条件: _MIN_PRICE=300 円、_MIN_TURNOVER=5e8 円。

- シグナル生成（Strategy 用）
  - kabusys.strategy.signal_generator:
    - features と ai_scores を統合して各種コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - コンポーネントはシグモイド変換や反転（ボラティリティ）などを適用して [0,1] に正規化。
    - デフォルト重みを実装（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）と閾値（DEFAULT_THRESHOLD=0.60）。
    - Bear レジーム判定（ai_scores の regime_score 平均 < 0 かつ十分なサンプル数）により BUY を抑制。
    - エグジット判定ロジック（ストップロス -8% / スコア低下）を実装。positions テーブルと prices_daily を参照。
    - signals テーブルへ日付単位で置換（トランザクションで原子性を保証）。
    - weights 引数は入力検証し、既知キーのみ受け付け、合計を 1.0 に再スケール。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- RSS パーサに defusedxml を採用し XML 関連の脆弱性に対処。
- ニュース URL の正規化でトラッキングパラメータを除去、非 HTTP/HTTPS スキームや不正なホストを弾く設計を考慮（モジュール内ユーティリティを準備）。
- J-Quants クライアントでトークン管理とリフレッシュの取り扱いを明示し、認証失敗時の無限再帰を防止。

Notes / Implementation details
- DuckDB をコアのデータ永続化・計算基盤として利用。各処理は prices_daily / raw_prices / raw_financials / features / ai_scores / positions / signals 等のテーブルを参照または更新する想定。
- 多くの書き込み処理は ON CONFLICT DO UPDATE を用いた冪等性を備える（重複挿入や再実行に耐える）。
- ルックアヘッドバイアス対策として「そのデータがいつ取得されたか（fetched_at）」や target_date 時点のデータのみを使用する方針を採用。
- 外部依存は可能な限り抑え、標準ライブラリ（urllib, json, datetime 等）中心で実装。research の一部関数は pandas 等に依存しない実装。

開発者向け注意事項
- 環境変数に必須のものが未設定の場合、Settings プロパティは ValueError を送出します（CI / デプロイ時に注意）。
  - 例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD
- .env の自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（ユニットテスト等で有用）。
- J-Quants API のレート制限は内部で遵守しますが、大量フェッチ時は実行時間に注意してください。

---

今後の予定（例）
- execution 層の実装（kabu ステーション / ブローカ API と連携する注文/約定処理）
- monitoring / alerting 周りの実装（Slack 通知・稼働監視）
- ニュースと銘柄マッチング（news_symbols テーブルへの紐付けロジック）
- トレーリングストップ、時間決済などエグジット戦略の拡張

以上。