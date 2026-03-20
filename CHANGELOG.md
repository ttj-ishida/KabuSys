# Changelog

すべての注目すべき変更をここに記載します。本ファイルは Keep a Changelog の形式に準拠します。  
基準日: 2026-03-20

※ このリポジトリの初回公開リリースを 0.1.0 として記録しています。

## [Unreleased]
（現在なし）

## [0.1.0] - 2026-03-20

### Added
- パッケージ初期実装（kabusys v0.1.0）
  - src/kabusys/__init__.py
    - パッケージメタ情報（__version__ = "0.1.0"）と公開モジュール一覧を定義。
  - 環境設定・自動.envロード
    - src/kabusys/config.py
      - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読込する機能を追加。
      - 読み込み順序: OS環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能。
      - .env パーサーは `export KEY=val` 形式・クォート文字列・インラインコメント処理に対応。保護された OS 環境変数を上書きしない仕組みを導入（protected set）。
      - Settings クラスを提供し、J-Quants / kabu / Slack / DB パス等の設定値をプロパティ経由で取得。必須項目未設定時は ValueError を送出。KABUSYS_ENV / LOG_LEVEL の検証を実装。
  - データ取得・保存（J-Quants クライアント）
    - src/kabusys/data/jquants_client.py
      - J-Quants API クライアントを実装。ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）を提供。
      - レート制限対応（120 req/min）: 固定間隔スロットリング _RateLimiter 実装。
      - リトライロジック: 指数バックオフ、最大3回、408/429/5xx をリトライ対象。429 の場合は Retry-After を優先。
      - 401 受信時の ID トークン自動リフレッシュ（1回のみ）を実装。モジュールレベルのトークンキャッシュを共有。
      - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を追加。fetched_at を UTC ISO8601 で記録し、ON CONFLICT (upsert) による冪等保存を実装。
      - 型変換ユーティリティ _to_float / _to_int を追加（堅牢な変換と不正値スキップ）。
  - ニュース収集
    - src/kabusys/data/news_collector.py
      - RSS フィードの収集・正規化処理を実装（デフォルト: Yahoo Finance ビジネス RSS）。
      - 記事ID は正規化後の URL の SHA-256 ハッシュ（先頭 32 文字）を利用し冪等性を確保。
      - defusedxml による安全な XML パース、受信サイズ上限（MAX_RESPONSE_BYTES=10MB）、トラッキングパラメータ除去、スキーム検査（HTTP/HTTPS のみ）等、セキュリティ対策を組み込み。
      - バルク INSERT のチャンク化とトランザクションで効率的な DB 挿入を行う設計。
  - リサーチモジュール（ファクター計算／探索）
    - src/kabusys/research/factor_research.py
      - モメンタム（1/3/6M、MA200乖離）、ボラティリティ（20日ATR・相対ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER/ROE）の計算関数を実装。DuckDB の prices_daily / raw_financials テーブルのみ参照。
      - SQL ベースのウィンドウ集計を用い、データ不足時の None 処理を行う。
    - src/kabusys/research/feature_exploration.py
      - 将来リターン計算（calc_forward_returns）、IC（Spearman）計算（calc_ic）、ファクター統計サマリー（factor_summary）、ランク付け（rank）を実装。
      - 外部ライブラリに依存しない純 Python 実装（DuckDB 接続を受ける）。
    - src/kabusys/research/__init__.py から主要関数を公開。
  - 特徴量エンジニアリング
    - src/kabusys/strategy/feature_engineering.py
      - research で計算した生ファクターをマージ・ユニバースフィルタ（最低株価300円、20日平均売買代金5億円）適用・Zスコア正規化（対象カラムは mom_1m,mom_3m,atr_pct,volume_ratio,ma200_dev）・±3クリップ後に features テーブルへ日付単位で置換（トランザクションで原子性確保）する build_features を実装。
      - 欠損や休日を考慮して target_date 以前の最新価格参照や冪等性を重視。
  - シグナル生成
    - src/kabusys/strategy/signal_generator.py
      - features と ai_scores を統合し final_score を計算、BUY/SELL シグナルを生成して signals テーブルへ日付単位で置換する generate_signals を実装。
      - デフォルト重み（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）と閾値（0.60）を提供。入力 weights の検証と再スケールを行う。
      - コンポーネント欠損は中立値 0.5 で補完。AI スコア用にシグモイド変換を使用。
      - Bear レジーム判定（ai_scores の regime_score 平均が負かつ十分なサンプル数）により BUY を抑制。
      - エグジット条件としてストップロス（終値/avg_price - 1 <= -8%）とスコア低下を実装。保有銘柄に価格欠損がある場合は判定をスキップするなど安全性を考慮。
  - パッケージの公開 API
    - src/kabusys/strategy/__init__.py で build_features / generate_signals を公開。

### Changed
- N/A（初回リリースのため既存変更なし）

### Fixed
- N/A（初回リリース）

### Security
- news_collector に以下のセキュリティ対策を含めて実装:
  - defusedxml を用いた XML パース（XML Bomb 対策）
  - URL のスキームチェック（HTTP/HTTPS のみ許可）とトラッキングパラメータ除去（SSRF・トラッキング防止）
  - 受信バイト数上限（MAX_RESPONSE_BYTES）でメモリ DoS を軽減
- jquants_client にてネットワーク系エラーや 429 の Retry-After を尊重する実装を取り入れ、過負荷や不正な再試行を抑制。

### Known limitations / TODO
- signal_generator の SELL 判定において、トレーリングストップ（peak_price 必要）や時間決済（保有 60 営業日超過）は未実装（positions テーブルに追加データが必要）。
- execution パッケージはプレースホルダ（実際の発注ロジックは未実装）。
- monitoring モジュールはパッケージ公開名に含まれるが、実体が未提供の可能性あり（将来の追加予定）。
- 一部の処理（RSS フィード取得など）で外部ネットワーク依存のため、オフライン時の動作確認を要する。

---

以上。リリースノートはコードから推測して作成しています。必要であれば各変更項目をより詳細（関数シグネチャ、ログメッセージ、SQL スキーマ想定など）に展開できます。どの程度の詳細が必要か教えてください。