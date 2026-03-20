Keep a Changelog に準拠した変更履歴

すべての注目すべき変更を記録します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

0.1.0 - 2026-03-20
------------------

Added
- 初回リリース。日本株自動売買システム「KabuSys」核心機能を追加。
  - パッケージエントリポイント (src/kabusys/__init__.py)
    - バージョン __version__="0.1.0"
    - public API エクスポート: data, strategy, execution, monitoring
  - 環境設定管理 (src/kabusys/config.py)
    - .env ファイルおよび環境変数読み込み機能を追加（プロジェクトルート検出: .git / pyproject.toml に基づく）
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
    - .env パーサを実装（export 形式、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応）
    - 必須環境変数取得ヘルパ _require と Settings クラス（J-Quants / kabu API / Slack / DB パス / システム env/log レベルの検証を含む）
  - データ取得・保存 (src/kabusys/data/)
    - J-Quants API クライアント (jquants_client.py)
      - 固定間隔スロットリングによるレート制御（120 req/min）
      - 再試行（指数バックオフ、最大 3 回）および HTTP ステータスに応じた挙動（408/429/5xx の再試行）
      - 401 時のトークン自動リフレッシュ（1 回のみ）とモジュールレベルの ID トークンキャッシュ
      - ページネーション対応 fetch_* 関数（daily_quotes / financial_statements / market_calendar）
      - DuckDB への冪等保存関数（save_*）を実装、ON CONFLICT DO UPDATE による upsert
      - 型変換ユーティリティ (_to_float / _to_int) を提供（安全なパース）
    - ニュース収集モジュール (news_collector.py)
      - RSS フィード取得・パース、記事の正規化と冪等保存
      - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）等で生成し重複排除
      - defusedxml を使用した XML パース（XML Bomb 等の対策）
      - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント除去、クエリソート）
      - SSRF 対策（HTTP/HTTPS 限定など）、受信サイズ上限（10 MB）、バルク INSERT のチャンク処理
  - 研究用モジュール (src/kabusys/research/)
    - ファクター計算 (factor_research.py)
      - モメンタム（mom_1m/mom_3m/mom_6m）、MA200 乖離率、ATR（20日）、相対 ATR（atr_pct）、平均売買代金、出来高比率、PER/ROE を DuckDB SQL で算出
      - 欠測・データ不足時の安全な None 処理
    - 特徴量探索 (feature_exploration.py)
      - 将来リターン計算（複数ホライズン対応: デフォルト [1,5,21]）、IC（Spearman）計算、ファクター統計サマリー、ランク関数
      - pandas 等に依存せず標準ライブラリ + DuckDB で実装
    - 研究 API を再エクスポート（research/__init__.py）
      - calc_momentum / calc_volatility / calc_value / zscore_normalize / calc_forward_returns / calc_ic / factor_summary / rank
  - 戦略モジュール (src/kabusys/strategy/)
    - 特徴量エンジニアリング (feature_engineering.py)
      - research で計算した生ファクターを集約して features テーブルに保存
      - ユニバースフィルタ（株価 >= 300 円、20 日平均売買代金 >= 5 億円）
      - Z スコア正規化（対象カラムの指定）、±3 でクリップ、日付単位で冪等的に置換（トランザクションで原子性確保）
    - シグナル生成 (signal_generator.py)
      - features と ai_scores を統合しコンポーネント（momentum/value/volatility/liquidity/news）を計算
      - シグモイド変換、欠損コンポーネントは中立値 0.5 で補完
      - デフォルト重み・閾値（weights: momentum 0.4 / value 0.2 / volatility 0.15 / liquidity 0.15 / news 0.1、threshold=0.60）
      - Bear レジーム検知（ai_scores.regime_score の平均が負かつサンプル >= 3 の場合）により BUY を抑制
      - SELL 判定: ストップロス（終値/avg_price -1 <= -8%）およびスコア低下（threshold 未満）、保有銘柄の価格欠損時は判定をスキップ
      - signals テーブルへ日付単位で冪等的に書き込む（トランザクションで原子性確保）
  - public API エクスポート（strategy/__init__.py）: build_features, generate_signals

Security
- ニュース取得で defusedxml を使用し XML パースの脆弱性を軽減
- RSS URL 正規化 / トラッキングパラメータ除去により不正な URL の影響を軽減
- ニュース収集で受信最大バイト数を設定（メモリ DoS 対策）
- J-Quants クライアントはトークン自動リフレッシュと例外処理を強化（401/429/5xx 処理）

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Deprecated / Removed
- （初版のため該当なし）

Notes
- 研究向けの処理（research/*）は本番の発注・実行層に依存しない設計（ルックアヘッドバイアス防止）
- DuckDB のテーブルスキーマ（prices_daily, raw_prices, raw_financials, features, ai_scores, positions, signals, market_calendar 等）は本リリースの関数に依存するため、実行前に適切なスキーマを用意してください
- 実運用においては環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）を .env に設定することを想定しています

今後の予定（例）
- トレーリングストップや時間決済などの追加エグジット条件実装
- execution 層（kabu ステーション API 連携）の追加実装
- テストカバレッジおよび CI の整備

---