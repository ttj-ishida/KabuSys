# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

- リリースはセマンティックバージョニングに従います。
- 日付は YYYY-MM-DD 形式で記載します。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-19
初回リリース。日本株自動売買システム "KabuSys" のコア機能群を実装したリリースです。以下の主要コンポーネントと機能を含みます。

### Added
- パッケージ初期化
  - kabusys パッケージのエントリポイントを追加（__version__ = 0.1.0、公開モジュール: data, strategy, execution, monitoring）。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定値を読み込む仕組みを実装。
  - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を探索）により CWD に依存せずに .env を読み込む。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサーは export プレフィックス、シングル/ダブルクォート、エスケープシーケンス、行内コメントの処理に対応。
  - Settings クラスを提供し、以下の環境変数を安全に取得:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（valid: development | paper_trading | live、デフォルト: development）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
  - 環境変数未設定時のエラーハンドリング（_require にて ValueError を送出）。

- データ収集クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - 機能:
    - ID トークン取得（refresh token からの POST /token/auth_refresh）
    - 株価日足（fetch_daily_quotes）、財務データ（fetch_financial_statements）、市場カレンダー（fetch_market_calendar）のページネーション対応取得
    - 固定間隔の RateLimiter（120 req/min）によるスロットリング
    - 再試行ロジック（指数バックオフ、最大3回、HTTP 408/429/5xx とネットワークエラーをリトライ）
    - 401 受信時は ID トークンを自動リフレッシュして再試行（1 回のみ）
    - DuckDB への冪等保存関数:
      - save_daily_quotes -> raw_prices（ON CONFLICT DO UPDATE）
      - save_financial_statements -> raw_financials（ON CONFLICT DO UPDATE）
      - save_market_calendar -> market_calendar（ON CONFLICT DO UPDATE）
    - データ整形ユーティリティ: _to_float / _to_int（安全な型変換処理）
    - fetched_at に UTC タイムスタンプを付与して取得時刻のトレーサビリティを確保

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからのニュース収集機能を実装（デフォルトソースに Yahoo Finance を登録）。
  - 特徴:
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリ整列）
    - 記事ID を正規化 URL の SHA-256 ハッシュ（先頭32文字）で生成し冪等性を確保
    - defusedxml を用いて XML 関連の安全対策（XML ボム等）を実施
    - HTTP レスポンス受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）によりメモリDoS を軽減
    - DB へのバルク INSERT をチャンク化して効率的に保存（_INSERT_CHUNK_SIZE）
    - raw_news / news_symbols への紐付け設計に対応（実装の前提を満たす設計）

- 研究（research）モジュール
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日 MA）を計算
    - calc_volatility: 20日 ATR, atr_pct, avg_turnover, volume_ratio を計算
    - calc_value: per, roe を計算（raw_financials の最新財務データを参照）
    - DuckDB クエリベースで実装、営業日欠損を吸収するスキャン範囲設計
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 任意ホライズン（デフォルト 1,5,21 営業日）の将来リターンを計算
    - calc_ic: Spearman のランク相関（Information Coefficient）を計算（有効データが3件未満の場合は None）
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を計算
    - rank: 同順位は平均ランクを返すランク関数（浮動小数丸めで ties を安定化）
  - research パッケージ公開 API を整備（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）

- 戦略（strategy）モジュール
  - 特徴量作成（kabusys.strategy.feature_engineering）
    - research で計算した生ファクターを取り込み、ユニバースフィルタ（最低株価300円、20日平均売買代金 >= 5億円）を適用
    - 指定カラム群（mom_1m, mom_3m, atr_pct, volume_ratio, ma200_dev）を z-score 正規化（kabusys.data.stats の zscore_normalize を使用）し ±3 でクリップ
    - features テーブルへ日付単位で置換（DELETE -> INSERT）することで冪等性と原子性を担保（トランザクションを使用）
    - target_date 時点のみのデータを利用してルックアヘッドバイアスを回避
  - シグナル生成（kabusys.strategy.signal_generator）
    - features と ai_scores を統合し、複数コンポーネント（momentum, value, volatility, liquidity, news）の重み付き合算で final_score を計算（デフォルト重みは StrategyModel に準拠）
    - 重みはユーザ指定を受け付け、妥当性チェック後に正規化して合計が 1.0 になるよう再スケール
    - AI ニューススコアが未登録の銘柄は中立値（0.5）で補完
    - Bear レジーム判定（ai_scores の regime_score の平均が負の場合かつ十分なサンプル数がある場合）により BUY シグナルを抑制
    - BUY シグナルは threshold（デフォルト 0.60）以上の銘柄に付与
    - SELL シグナル（エグジット判定）実装:
      - ストップロス: (close / avg_price - 1) < -8%
      - スコア低下: final_score < threshold
      - 保有銘柄の価格欠損時は SELL 判定をスキップし誤クローズを防止
      - SELL 優先ポリシー: SELL 対象銘柄は BUY から除外しランクを再付与
    - signals テーブルへ日付単位で置換（トランザクション＋バルク挿入）して冪等性を保証

- ロギングと設計メモ
  - 各主要処理で情報/警告/デバッグログを出力して運用観測を容易にする設計。
  - ルックアヘッドバイアス防止の設計原則を本文内ドキュメントに明記。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- news_collector で defusedxml を利用し XML パースの安全性に配慮。
- RSS 収集で外部 URL 正規化とトラッキングパラメータ除去を実装し、ID 再生成による冪等性を確保。

### Notes / Known limitations
- signal_generator のエグジット条件のうちトレーリングストップ（peak_price 依存）と時間決済（保有 60 営業日超）については未実装。position テーブルに peak_price / entry_date が追加されれば実装可能。
- news_collector は記事の銘柄紐付けロジック（news_symbols へのマッピング）を考慮した設計だが、紐付けルールの詳細（NLP ベースの抽出等）は本リリースでは未実装／要拡張。
- DuckDB 側のスキーマ（raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar, raw_news など）が前提となる。本リリースではスキーマ作成スクリプトは含まれていないため、使用前に適切なスキーマを用意してください。
- jquants_client の再試行ポリシーは 408/429/5xx とネットワークエラーを対象とする。その他の 4xx エラーは基本的にリトライしません。

### Upgrade Notes
- 既存の環境変数設定を利用する場合、必須キー（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）を設定してください。
- .env 自動ロードはプロジェクトルート検出ロジックに依存します。パッケージ配布後も .env を同梱して動作させる場合は .git または pyproject.toml を配置するか、KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して手動ロードしてください。

---

今後の予定（例）
- ポジション管理の強化（トレーリングストップ、時間決済の実装）
- ニュース→銘柄マッチング精度向上（NLP/エンティティ抽出）
- モニタリング・アラート（Slack 経由の運用通知）の実装拡充

（本 CHANGELOG はコードベースの内容から推測して作成しています。実際の変更履歴とは差異がある場合があります。）