CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記載します。
このファイルにはパッケージのリリースごとの大きな追加・変更・修正点を日本語でまとめています。

フォーマット:
- Added: 新規機能、API、モジュール
- Changed: 既存機能の変更（互換性に注意するもの）
- Fixed: バグ修正
- Security: セキュリティ関連の注意点・対策
- その他（Notes）: 運用上・設計上の重要な注記

Unreleased
----------

（今後の変更はここに記載します）

0.1.0 - 2026-03-20
------------------

Added
- 基本パッケージとバージョン情報を追加
  - パッケージ: kabusys (src/kabusys/__init__.py) — バージョン "0.1.0"
- 環境変数・設定管理モジュールを追加
  - src/kabusys/config.py
  - .env ファイル（.env, .env.local）の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）
  - .env パースの高度なサポート（コメント、export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ）
  - 読み込み時の上書き制御（override / protected）と自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD
  - Settings クラスによる環境変数ラッパー（J-Quants / kabu API / Slack / DB パス / ログレベル / 実行環境フラグ等）
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL の許容値検査）
- Data 層: J-Quants API クライアントの実装
  - src/kabusys/data/jquants_client.py
  - レートリミッタ実装（固定間隔スロットリング、120 req/min を想定）
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx 対象）と 401 発生時の自動トークンリフレッシュ
  - ページネーション対応のフェッチ処理（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）
  - DuckDB への冪等的保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を提供。ON CONFLICT で重複更新。
  - 型変換ユーティリティ（_to_float, _to_int）
- Data 層: ニュース収集モジュールの実装
  - src/kabusys/data/news_collector.py
  - RSS 取得・正規化パイプライン（URL 正規化、トラッキングパラメータ除去、テキスト前処理）
  - 記事ID を正規化 URL の SHA-256（先頭 32 文字）で生成し冪等性を確保
  - defusedxml を用いた XML パース（XML Bomb 対策）と受信バイト数制限（MAX_RESPONSE_BYTES）
  - SSRF 回避のためスキームチェックなどの入力検証、DB へバルク挿入（チャンク化）
- Research 層: ファクター計算および解析ツール群
  - src/kabusys/research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離を計算
    - calc_volatility: 20日 ATR, atr_pct, avg_turnover, volume_ratio を計算
    - calc_value: PER, ROE（raw_financials と prices_daily の組み合わせ）
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 将来リターン（任意ホライズン）を一括取得
    - calc_ic: Spearman（ランク相関）に基づく IC 計算
    - factor_summary: 基本統計量（count/mean/std/min/max/median）
    - rank: 同順位は平均ランクにするランク化ユーティリティ
  - research パッケージのエクスポートを追加（__init__.py）
- Strategy 層: 特徴量作成・シグナル生成
  - src/kabusys/strategy/feature_engineering.py
    - build_features: research モジュールの生ファクターを統合、ユニバースフィルタ（最低株価・最低平均売買代金）、Z スコア正規化（カラム指定）、±3 クリップ、features テーブルへの日付単位の置換（トランザクションで原子性確保）
    - ユニバースフィルタの閾値（MIN_PRICE=300 円、MIN_TURNOVER=5e8 円）を定義
  - src/kabusys/strategy/signal_generator.py
    - generate_signals: features と ai_scores を統合して final_score を計算、BUY/SELL シグナルを生成して signals テーブルへ日付単位で置換
    - スコア計算用ユーティリティ（シグモイド変換、コンポーネントスコアの算出: momentum/value/volatility/liquidity/news）
    - 重みの取り扱い（デフォルト重み、ユーザー指定重みの検証と正規化）
    - Bear レジーム判定（ai_scores の regime_score の平均が負 → BUY を抑制）
    - エグジット判定（stop_loss=-8%、スコア低下）を実装（_generate_sell_signals）
    - DB への置換処理はトランザクション + バルク挿入で実装（ROLLBACK の失敗は警告記録）
  - strategy パッケージのエクスポートを追加（__init__.py）

Fixed
- .env パースの堅牢性を向上
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメント処理の向上により .env の解釈ミスを防止（src/kabusys/config.py）
- J-Quants API クライアントの堅牢性改善
  - 401 レスポンス時のトークン自動リフレッシュを 1 回のみ行い無限再帰を防止
  - 429 (Retry-After) ヘッダ対応、指数バックオフの適用によりリトライポリシーを明確化（src/kabusys/data/jquants_client.py）
- DB トランザクション失敗時のログ出力を追加（ROLLBACK の失敗を警告）しデバッグ性を向上（feature_engineering / signal_generator）

Security
- news_collector で defusedxml を利用して XML 関連の攻撃（XML Bomb 等）に対策
- RSS フィード取得時に受信サイズ上限（MAX_RESPONSE_BYTES = 10 MB）を導入しメモリ DoS を低減
- URL 正規化でスキーム/ホストの検証やトラッキングパラメータ除去を行い、SSRF や追跡パラメータによる識別漏洩を低減

Notes
- DuckDB 側に以下のテーブルとスキーマ（想定）を用意することを前提に実装されています:
  - raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, signals, positions, raw_news など
  - 各 save_* / build_features / generate_signals 関数はこれらのテーブル構造に依存しています。スキーマが一致しない場合はエラーになります。
- ルックアヘッドバイアスへの配慮:
  - features / signals / research 関数はいずれも target_date 時点までのデータのみを参照するよう設計されています（過去データのみ使用）。
  - J-Quants の保存処理では fetched_at を UTC で記録し「いつデータを知り得たか」を追跡可能にしています。
- 一部未実装 / 将来追加予定の仕様:
  - signal_generator の SELL 条件のうちトレーリングストップや時間決済は positions に peak_price / entry_date 等の情報が必要であり現バージョンでは未実装。
  - feature_engineering は features テーブルへの UPSERT を行う前提だが、現在は日付単位の DELETE → INSERT による置換を採用（冪等性を満たす）。
- 外部依存:
  - defusedxml を使用（news_collector）
  - DuckDB Python バインディングを前提（duckdb）

開発者向け補足
- 設定取得時に必須の環境変数が欠けていると ValueError を送出します（Settings.jquants_refresh_token 等）。
- KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると .env の自動ロードを無効化できます（テスト時に便利）。
- generate_signals の weights 引数は不正なキーや負値・NaN/Inf を無視し、結果が 1.0 にならない場合は再スケールまたはデフォルト値にフォールバックします。

今後の予定（参考）
- SELL 条件（トレーリングストップ、時間決済）の追加
- features / signals の保存方式をより細粒度な UPSERT に移行（現状は日付単位の置換）
- より詳細なログ出力／モニタリング連携（Slack 通知など）

以上。