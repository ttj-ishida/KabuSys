CHANGELOG
=========

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、安定版・後方互換性・セキュリティ情報の把握を容易にすることを目的としています。

Unreleased
----------

- なし（初回リリースは 0.1.0 を参照してください）

0.1.0 - 2026-03-21
------------------

Added
- パッケージ初版を追加。kabusys 全体の基本機能を実装。
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）
- 設定/環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダを実装。
  - プロジェクトルート検出: .git または pyproject.toml を基準に探索（カレントワーキングディレクトリに依存しない）。
  - .env のパース機能: 空行・コメント・export プレフィックス、シングル／ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いに対応。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能。
  - settings オブジェクトを提供し、J-Quants トークン・kabu API・Slack・DB パス・実行環境（development/paper_trading/live）等の取得・バリデーションを実装。
- Data 層（src/kabusys/data）
  - J-Quants クライアント (src/kabusys/data/jquants_client.py)
    - API 呼び出しの共通処理を実装（固定間隔レートリミッタ、最大再試行、指数バックオフ、ページネーション対応）。
    - 401 に対する自動トークンリフレッシュと 1 回再試行の仕組みを実装。モジュールレベルの ID トークンキャッシュを導入。
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar の取得関数を実装（ページネーション対応）。
    - DuckDB へ保存する冪等保存関数を実装: save_daily_quotes / save_financial_statements / save_market_calendar（ON CONFLICT DO UPDATE を使用）。
    - HTTP レスポンスの JSON デコード失敗検知や型変換ユーティリティ（_to_float / _to_int）を実装。
  - ニュース収集 (src/kabusys/data/news_collector.py)
    - RSS フィード収集と raw_news への冪等保存ロジックを実装。記事 ID は URL 正規化後の SHA-256（先頭 32 文字）を用いる仕様を実装（冪等性確保）。
    - URL 正規化でトラッキングパラメータ（utm_*, fbclid 等）を除去、クエリパラメータのソート、フラグメント除去、小文字化などを実装。
    - defusedxml を使った XML パース、受信バイト数制限（MAX_RESPONSE_BYTES）などの安全対策を組み込み。
- Research 層（src/kabusys/research）
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率 (ma200_dev) を計算。
    - calc_volatility: 20 日 ATR・相対 ATR (atr_pct)、20 日平均売買代金 (avg_turnover)、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（target_date 以前の最新財務データを参照）。
    - DuckDB の SQL ウィンドウ関数を活用し、営業日欠損（週末・祝日）に対応するスキャンレンジを設計。
  - 探索・評価ユーティリティ (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns: 指定 horizon（デフォルト [1,5,21]）について将来リターンを計算。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装。サンプル不足時は None を返す。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランクで処理、丸めによる ties 検出漏れを防ぐ (round(..., 12))。
  - research パッケージ初期化で主要関数をエクスポート。
- Strategy 層（src/kabusys/strategy）
  - 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
    - research の生ファクターを取込み、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を使用）し ±3 でクリップ。
    - features テーブルへ日付単位で置換挿入（トランザクション + バルク挿入で原子性を保証）。
  - シグナル生成 (src/kabusys/strategy/signal_generator.py)
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - デフォルト重みと閾値を実装（デフォルト threshold=0.60、weights は合計 1.0 に再スケール）。
    - final_score を算出、Bear レジーム判定が真の場合は BUY シグナルを抑制。
    - エグジット判定（stop_loss: -8% 以内の損失、score の threshold 割れ）を実装し SELL シグナルを生成。
    - signals テーブルへ日付単位の置換挿入（トランザクション + バルク挿入で原子性を保証）。
  - strategy パッケージ初期化で build_features / generate_signals をエクスポート。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Security
- ニュース収集モジュールで defusedxml を使用して XML Bomb 等を防止。
- RSS URL 正規化とトラッキングパラメータ除去により一意性を担保、SSRF・トラッキングリスクを低減する設計思想を採用（ニュース収集での追加検証処理を想定）。
- J-Quants クライアントでタイムアウトや再試行ロジックを明示的に設定し、外部 API への過負荷・不安定回避を行う。

Notes / Implementation details
- DuckDB をデータ層の永続化に用いる想定。SQL 内でウィンドウ関数・ROW_NUMBER を多用しており、大量データに対する性能は DuckDB の構成に依存。
- 多くの操作は「target_date 時点のみのデータを使用」する方針（ルックアヘッドバイアス回避）。
- 一部の未実装機能（例: トレーリングストップ・時間決済のエグジット条件）はコード内コメントとして記載済み。将来的に positions テーブルに peak_price / entry_date 等を追加することで対応可能。

Breaking Changes
- なし（初回リリース）

参考資料
- この CHANGELOG はリポジトリ内のソースから実装意図・主要仕様を抽出して作成しています。詳細な設計仕様は各モジュールの docstring やコメントを参照してください。