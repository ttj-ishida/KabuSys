Keep a Changelog 準拠 — CHANGELOG
=================================

すべての注目すべき変更点をバージョン毎に記録します。  
フォーマットは https://keepachangelog.com/ja/ に準拠します。

Unreleased
----------

（現時点のリポジトリ状態が初回リリースに相当するため Unreleased は空です）

[0.1.0] - 2026-03-19
-------------------

Added
- 基本パッケージ構成を追加
  - パッケージ名: kabusys
  - __version__ = "0.1.0"
  - __all__ に data, strategy, execution, monitoring を公開

- 環境設定管理 (kabusys.config)
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応
  - 柔軟な .env パーサ実装
    - export プレフィックス対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - インラインコメント処理（クォート外、直前がスペース/タブの場合に # をコメントと判定）
  - 環境値検証と Settings クラスを提供
    - 必須項目の取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）
    - enum 検証（KABUSYS_ENV: development/paper_trading/live、LOG_LEVEL の検証）
    - データベースパス（DUCKDB_PATH, SQLITE_PATH）の Path 型返却
    - ヘルパー is_live / is_paper / is_dev

- Data 層（kabusys.data）
  - J-Quants API クライアント (jquants_client)
    - 固定間隔（スロットリング）ベースの RateLimiter（120 req/min）を実装
    - 再試行（指数バックオフ、最大 3 回）、HTTP 408/429/5xx 等のリトライ対象対応
    - 401 応答時はリフレッシュトークンから id_token を自動更新して 1 回リトライ
    - ページネーション対応の取得関数:
      - fetch_daily_quotes
      - fetch_financial_statements
      - fetch_market_calendar
    - DuckDB への保存関数（冪等）
      - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE を使用して保存
      - save_financial_statements: raw_financials テーブルへ ON CONFLICT DO UPDATE
      - save_market_calendar: market_calendar テーブルへ ON CONFLICT DO UPDATE
    - データ変換ユーティリティ: _to_float / _to_int
    - 取得時に fetched_at を UTC ISO 形式で記録（Look-ahead バイアス対策）

  - ニュース収集モジュール (news_collector)
    - RSS フィードから記事収集（デフォルトに Yahoo Finance のビジネス RSS を含む）
    - セキュリティ対策:
      - defusedxml を使用して XML Bomb 等に耐性
      - 受信サイズ上限（MAX_RESPONSE_BYTES: 10 MB）
      - URL 正規化・トラッキングパラメータ削除（utm_*, fbclid 等）
      - 記事 ID を URL 正規化後の SHA-256（先頭32文字）で生成して冪等性確保
      - HTTP/HTTPS 以外のスキーム排除や SSRF に配慮する設計（注: 実装箇所はユーティリティとして整備）
    - DB 保存はチャンク/トランザクションで実施し、INSERT RETURNING を利用する想定（冪等性を確保）

- Research 層（kabusys.research）
  - ファクター計算モジュール (factor_research)
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）
    - Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）
    - Value（per, roe） — raw_financials と prices_daily の組み合わせ
    - 各関数は DuckDB を用いた SQL により実装（営業日を想定した窓設定とスキャンバッファ）
    - データ不足時は None を返す扱いで堅牢に実装
  - 特徴量探索モジュール (feature_exploration)
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、最大 252 営業日の制約）
    - IC（Spearman の ρ）計算 calc_ic（ランク付け、同順位は平均ランク）
    - factor_summary（count/mean/std/min/max/median を算出）
    - rank ユーティリティ（同順位は平均ランク、丸めで ties 判定の安定化）

  - research パッケージから主要関数を export（calc_momentum 等と zscore_normalize を統合公開）

- Strategy 層（kabusys.strategy）
  - 特徴量エンジニアリング (feature_engineering)
    - research の生ファクターを取得して統合
    - ユニバースフィルタ実装（最低株価 300 円、20日平均売買代金 >= 5 億円）
    - 正規化: zscore_normalize を利用して指定カラムを Z スコア化、±3 でクリップ
    - features テーブルへ日付単位の置換（DELETE + INSERT をトランザクション内で行い原子性を確保）
    - 処理はルックアヘッドバイアスを避ける設計（target_date 時点のデータのみ利用）
  - シグナル生成 (signal_generator)
    - features と ai_scores を統合して最終スコア final_score を算出
    - コンポーネントスコア:
      - momentum（momentum_20, momentum_60, ma200_dev）
      - value（PER 逆数ベース）
      - volatility（atr_pct の反転）
      - liquidity（volume_ratio）
      - news（ai_score のシグモイド変換、未登録は中立）
    - 重み付け可能（デフォルト重みを定義し、入力の weights を検証・正規化）
    - Bear レジーム判定（ai_scores の regime_score 平均が負）により BUY シグナルを抑制
    - BUY 閾値（デフォルト 0.60）を満たす銘柄を BUY シグナルとして出力
    - SELL（エグジット）判定:
      - ストップロス（終値／avg_price - 1 < -8%）
      - final_score が閾値未満
      - 保有銘柄の価格欠損時は SELL 判定をスキップして誤クローズを防止
    - signals テーブルへ日付単位の置換（トランザクション + バルク挿入）
    - 欠損コンポーネントは中立 0.5 で補完することで欠損銘柄の不当な降格を回避
    - SELL 優先ポリシー（SELL 対象は BUY から除外し順位を再付与）

Changed
- 初期リリースのため該当なし（新規追加のみ）

Fixed
- 初期リリースのため該当なし

Security
- news_collector で defusedxml を利用し XML パーサ攻撃に対処
- RSS レスポンスサイズ上限と URL 正規化により DoS/SSRF を考慮

Notes / 実装上の設計上のポイント
- 冪等性: データ保存関数は可能な限り ON CONFLICT / DO UPDATE を使い冪等化
- ルックアヘッドバイアス対策: データ取得時に fetched_at をUTCで記録、strategy/research は target_date 時点のデータのみを参照
- トランザクション: features / signals テーブルへの置換は BEGIN/DELETE/INSERT/COMMIT パターンで原子性を確保。失敗時は ROLLBACK を試行し失敗ログを出力
- ロギング: 各モジュールで logger を使用し情報・警告・デバッグを出力
- 入力検証: weights や horizons など外部入力は厳密に検証し、不正値はフォールバックまたはスキップ

互換性 / マイグレーション
- 初期リリースのため互換性破壊はなし
- 今後のバージョンで DB スキーマ変更が入る場合は migrations を提供予定（現状は DuckDB 用 SQL を想定）

既知の制限 / TODO
- strategy の一部エグジット条件（トレーリングストップ、時間決済）は positions テーブルに peak_price / entry_date 等が必要で未実装
- news_collector の一部 SSRF/ネットワーク検査の実装はユーティリティとして整備済だが、外部環境に依存するため運用時に追加設定が必要な場合あり
- execution / monitoring パッケージは公開されているが（__all__）現在のコードベースに具体的な実装は含まれていない

貢献・クレジット
- 初期実装: コードベースから推測して記載（自動生成ドキュメント）

お問い合わせ / バグ報告
- 不具合や改善提案は Issue を作成してください。リポジトリに README / CONTRIBUTING がある場合はそちらに従ってください。